"""Signe solaire B13 d'une naissance, avec son incertitude (MVP « Mon signe B13 »).

Référence : PRD § 6 (FR-03, FR-04, FR-05) ; annexe technique § D3 (propager l'incertitude sur
l'heure), E (« Statut de l'heure et résultat autorisé »), F (enregistrement traçable,
versionnement).

- Heure connue : un instant, un signe.
- Heure incertaine : l'intervalle entier est parcouru, jamais ses seules extrémités ; si le
  Soleil y franchit une frontière, les signes sont rendus comme possibilités, sans probabilité.
- Heure ambiguë : un résultat par occurrence, jusqu'au choix de la personne.
- Heure inconnue : positions sur toute la journée locale, « carte de référence à midi », ni
  Ascendant ni maisons.

Lecture retenue pour l'incertitude : l'intervalle est pris en temps absolu, l'instant plus ou
moins la durée, pour chaque occurrence. L'annexe D3 attache la précision à l'heure locale ; les
deux lectures ne diffèrent que si l'intervalle touche un changement d'heure. L'effet est nul sur
le signe solaire à l'échelle de la minute ; il sera à trancher pour l'Ascendant (V1).

Chaque résultat porte son manifeste. Rien n'est journalisé.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from moteur.civil_time import (
    BirthInput,
    InputError,
    NonexistentLocalTime,
    Scenario,
    load_zone,
    masked,
    resolve,
    resolve_local_time,
    zone_history_caveat,
)
from moteur.classification import ClassificationError, Placement, Zodiac, load_canonical
from moteur.coordinates import signed_wrap
from moteur.manifest import build_manifest
from moteur.passages import MAX_DAILY_MOTION_DEG, refine_crossing
from moteur.positions import (
    SECONDS_PER_DAY,
    SUN,
    SUN_TARGET_KIND,
    SunEphemeris,
    TimeScale,
    load_ephemeris,
)

REFERENCE_TITLE = "carte de référence à midi"
SAMPLING_STEP_SECONDS = 60.0
# De quoi parcourir une journée locale de 25 heures au pas d'une minute, avec de la marge.
MAX_SAMPLES = 2000

Status = Literal["certain", "possible"]
LocalTimeKind = Literal["unique", "ambiguous", "unknown"]


@dataclass(frozen=True, repr=False)
class Transition:
    """Franchissement d'une frontière par le Soleil à l'intérieur de l'intervalle étudié."""

    instant_utc: datetime
    tt_jd: float
    from_sign: str
    to_sign: str
    boundary_deg: float

    def __repr__(self) -> str:
        return masked("Transition")


@dataclass(frozen=True, repr=False)
class SunSign:
    """Signe solaire pour un instant de référence et, s'il y a lieu, un intervalle autour."""

    fold: int
    instant_utc: datetime  # instant de référence : l'heure saisie, ou midi si elle est inconnue
    utc_offset_seconds: int  # décalage du fuseau utilisé, à montrer pour contrôle (0011)
    time_scale: TimeScale
    conditional: bool
    longitude_deg: float
    latitude_deg: float  # calculée et conservée, ignorée par le classement
    placement: Placement  # classement à l'instant de référence
    status: Status
    possible_signs: tuple[str, ...]  # dans l'ordre du temps ; un seul si le statut est certain
    interval_utc: tuple[datetime, datetime] | None
    # Longitudes au début et à la fin de l'intervalle. Le Soleil avançant toujours, ce sont ses
    # extrêmes ; un début supérieur à la fin signifie que l'intervalle franchit 0°.
    longitude_interval_deg: tuple[float, float] | None
    transitions: tuple[Transition, ...]

    def __repr__(self) -> str:
        return masked("SunSign")


@dataclass(frozen=True, repr=False)
class SunSignChart:
    """Résultat complet : un `SunSign` par instant possible, et le manifeste."""

    time_status: str
    local_time_kind: LocalTimeKind
    title: str | None
    scenarios: tuple[SunSign, ...]
    ascendant: None
    ascendant_status: str
    houses: None
    houses_status: str
    data_status: str
    # Réserve sur l'histoire du fuseau avant 1970 (décision 0011) ; `None` s'il n'y en a pas.
    timezone_caveat: str | None
    manifest: dict[str, object]

    def __repr__(self) -> str:
        return masked("SunSignChart")


def local_day_bounds(day: date, zone: ZoneInfo) -> tuple[datetime, datetime]:
    """Premier instant UTC de la journée locale, et premier instant de la suivante.

    Cherché par dichotomie sur la date locale, à la seconde : juste même si minuit n'existe pas
    ce jour-là, et quelle que soit la durée de la journée (23, 24 ou 25 heures, ou autre).

    Limites : la date locale est supposée ne jamais reculer ; si un recul d'horloge repassait
    minuit, quelques minutes de la journée pourraient manquer. Une journée qui n'a pas existé
    donne un intervalle vide : l'appelant la refuse avant d'arriver ici.
    """

    def first_instant(target: date) -> datetime:
        middle = datetime.combine(target, time(0), tzinfo=UTC)
        low, high = middle - timedelta(hours=36), middle + timedelta(hours=36)
        while high - low > timedelta(seconds=1):
            half = low + (high - low) / 2
            half = half.replace(microsecond=0)
            if half.astimezone(zone).date() >= target:
                high = half
            else:
                low = half
        return high

    return first_instant(day), first_instant(day + timedelta(days=1))


def _scan(
    chain: SunEphemeris, zodiac: Zodiac, start_tt: float, end_tt: float
) -> tuple[tuple[str, ...], tuple[Transition, ...], tuple[float, float]]:
    """Signes traversés par le Soleil sur un intervalle, et instants de franchissement.

    L'intervalle est échantillonné au pas d'une minute, puis chaque changement de signe est
    affiné : on ne se contente jamais des deux extrémités (annexe D3). La progression est
    contrôlée à chaque pas : le Soleil avance toujours ; si ce n'était pas le cas, un aller-retour
    pourrait échapper au parcours, et le calcul s'arrête.
    """
    seconds = (end_tt - start_tt) * SECONDS_PER_DAY
    count = max(2, math.ceil(seconds / SAMPLING_STEP_SECONDS) + 1)
    if count > MAX_SAMPLES:
        raise ClassificationError(
            "intervalle de temps trop long pour être parcouru au pas d'une minute"
        )
    instants = [start_tt + (end_tt - start_tt) * rank / (count - 1) for rank in range(count)]
    longitudes = [chain.sun_longitude(instant) for instant in instants]
    for index in range(count - 1):
        step = signed_wrap(longitudes[index + 1] - longitudes[index])
        if not 0.0 <= step < MAX_DAILY_MOTION_DEG:
            raise ClassificationError(f"progression du Soleil inattendue : {step!r}°")
    names = [zodiac.classify(longitude).sign_id for longitude in longitudes]
    signs = {sign.sign_id: sign for sign in zodiac.signs}

    possible = [names[0]]
    transitions: list[Transition] = []
    for index in range(count - 1):
        before, after = names[index], names[index + 1]
        if before == after:
            continue
        # Deux signes voisins partagent une frontière : celle où l'un finit et l'autre commence.
        if signs[before].end_deg == signs[after].start_deg:
            boundary = signs[after].start_deg
        else:
            raise ClassificationError("deux signes non voisins entre deux instants successifs")
        root, _ = refine_crossing(
            chain.sun_longitude, boundary, instants[index], instants[index + 1]
        )
        transitions.append(Transition(chain.utc_datetime(root), root, before, after, boundary))
        if after not in possible:
            possible.append(after)
    return tuple(possible), tuple(transitions), (longitudes[0], longitudes[-1])


def _sun_sign(
    chain: SunEphemeris,
    zodiac: Zodiac,
    scenario: Scenario,
    interval: tuple[datetime, datetime] | None,
) -> SunSign:
    reference = chain.instant(scenario.instant_utc)
    longitude, latitude = chain.sun_longitude_latitude(reference.tt_jd)
    placement = zodiac.classify(longitude)
    possible: tuple[str, ...] = (placement.sign_id,)
    transitions: tuple[Transition, ...] = ()
    longitude_interval: tuple[float, float] | None = None
    conditional = reference.conditional
    if interval is not None:
        start, end = chain.instant(interval[0]), chain.instant(interval[1])
        possible, transitions, longitude_interval = _scan(chain, zodiac, start.tt_jd, end.tt_jd)
        conditional = conditional or end.conditional
    return SunSign(
        fold=scenario.fold,
        instant_utc=scenario.instant_utc,
        utc_offset_seconds=scenario.utc_offset_seconds,
        time_scale=reference.time_scale,
        conditional=conditional,
        longitude_deg=longitude,
        latitude_deg=latitude,
        placement=placement,
        status="certain" if len(possible) == 1 else "possible",
        possible_signs=possible,
        interval_utc=interval,
        longitude_interval_deg=longitude_interval,
        transitions=transitions,
    )


def input_hash(birth: BirthInput) -> str:
    """Empreinte de la saisie, pour le manifeste : la même saisie donne la même empreinte."""
    record = {
        "date_local": birth.date_local.isoformat(),
        "time_local": None if birth.time_local is None else birth.time_local.isoformat(),
        "time_status": birth.time_status,
        "time_uncertainty_seconds": birth.time_uncertainty_seconds,
        "timezone": birth.timezone,
        "fold": birth.fold,
        "latitude_deg": birth.latitude_deg,
        "longitude_deg": birth.longitude_deg,
        "altitude_m": birth.altitude_m,
        "calendar": birth.calendar,
    }
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sun_sign_chart(
    birth: BirthInput,
    *,
    ephemeris: SunEphemeris | None = None,
    zodiac: Zodiac | None = None,
) -> SunSignChart:
    """Signe solaire d'une naissance, selon le statut de son heure."""
    chain = ephemeris if ephemeris is not None else load_ephemeris()
    partition = zodiac if zodiac is not None else load_canonical()
    zone = load_zone(birth.timezone)

    title: str | None = None
    kind: LocalTimeKind
    results: tuple[SunSign, ...]
    if birth.time_status == "unknown":
        # Référence à midi local ; intervalle : toute la journée locale.
        try:
            noon = resolve_local_time(birth.date_local, time(12, 0), zone).scenarios[0]
        except NonexistentLocalTime as error:
            raise InputError(
                "Cette date n'a pas existé dans ce fuseau : la journée a été sautée. "
                "Vérifie la date de naissance ; aucun thème n'est calculé."
            ) from error
        results = (_sun_sign(chain, partition, noon, local_day_bounds(birth.date_local, zone)),)
        kind, title = "unknown", REFERENCE_TITLE
        angle_status = "undefined_without_birth_time"
    else:
        resolution = resolve(birth)
        margin = timedelta(seconds=birth.time_uncertainty_seconds)
        results = tuple(
            _sun_sign(
                chain,
                partition,
                scenario,
                None
                if birth.time_uncertainty_seconds == 0.0
                else (scenario.instant_utc - margin, scenario.instant_utc + margin),
            )
            for scenario in resolution.scenarios
        )
        kind = resolution.kind
        angle_status = "not_computed_in_this_version"

    manifest = build_manifest(chain, partition, input_hash(birth))
    return SunSignChart(
        time_status=birth.time_status,
        local_time_kind=kind,
        title=title,
        scenarios=results,
        ascendant=None,
        ascendant_status=angle_status,
        houses=None,
        houses_status=angle_status,
        data_status=str(manifest["data_status"]),
        timezone_caveat=zone_history_caveat(birth.date_local),
        manifest=manifest,
    )


def as_record(chart: SunSignChart) -> dict[str, object]:
    """Enregistrement traçable (annexe F), prêt pour le JSON. Une valeur absente reste `null`."""

    def iso(moment: datetime) -> str:
        return moment.astimezone(UTC).isoformat()

    manifest = chart.manifest
    hashes = manifest["boundary_model_id_and_hash"]
    # Empreinte de la grille des frontières (constellations.npz de Skyfield), annexe B et F.
    boundary_sha256 = hashes.get("boundary_source_sha256") if isinstance(hashes, dict) else None
    scenarios = []
    for result in chart.scenarios:
        single = result.status == "certain"
        scenarios.append(
            {
                "fold": result.fold,
                "instant_utc": iso(result.instant_utc),
                "utc_offset_seconds": result.utc_offset_seconds,
                "time_scale": result.time_scale,
                "conditional": result.conditional,
                "position": {
                    "body": "Sun",
                    "body_identifier": SUN,
                    "target_kind": SUN_TARGET_KIND,
                    "longitude_deg": result.longitude_deg,
                    "latitude_deg": result.latitude_deg,
                },
                "classification": {
                    # Plusieurs signes possibles : aucun n'est avancé à la place des autres.
                    "sign_id": result.placement.sign_id if single else None,
                    "degrees_in_sign": result.placement.degrees_in_sign if single else None,
                    "fraction_in_sign": result.placement.fraction_in_sign if single else None,
                    "status": result.status,
                    "possible_signs": list(result.possible_signs),
                },
                "uncertainty": {
                    "time_interval_utc": None
                    if result.interval_utc is None
                    else [iso(result.interval_utc[0]), iso(result.interval_utc[1])],
                    "longitude_interval_deg": None
                    if result.longitude_interval_deg is None
                    else list(result.longitude_interval_deg),
                    "input_probability_distribution": None,
                    "transitions": [
                        {
                            "instant_utc": iso(transition.instant_utc),
                            "from_sign": transition.from_sign,
                            "to_sign": transition.to_sign,
                            "boundary_deg": transition.boundary_deg,
                        }
                        for transition in result.transitions
                    ],
                },
                # Aucun texte interprétatif au MVP du signe : le bloc existe, vide.
                "interpretation": {
                    "ruleset_id": None,
                    "epistemic_status": "symbolic_proposal",
                    "text": None,
                },
            }
        )
    return {
        "title": chart.title,
        "time_status": chart.time_status,
        "local_time_kind": chart.local_time_kind,
        "data_status": chart.data_status,
        "model": {
            "id": manifest["model_id"],
            "reference_frame": manifest["reference_frame"],
            "boundary_source_equinox": manifest["boundary_source_equinox"],
            "boundary_sha256": boundary_sha256,
            "interval_policy": manifest["interval_policy"],
            "validation_status": manifest["validation_status"],
        },
        "scenarios": scenarios,
        "ascendant": None,
        "ascendant_status": chart.ascendant_status,
        "houses": None,
        "houses_status": chart.houses_status,
        "timezone_caveat": chart.timezone_caveat,
        "manifest": manifest,
    }
