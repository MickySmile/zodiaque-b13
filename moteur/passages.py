"""Entrées du Soleil dans chaque signe au cours d'une année (FR-06).

Référence : PRD § 6 (FR-06), § 7 (précision numérique) ; annexe technique § C (« Passage du
Soleil »), D2 (algorithme).

    λ☉(tᵢ) = bᵢ (mod 360°)        le Soleil appartient au signe i pour t ∈ [tᵢ, tᵢ₊₁[

Méthode : longitude solaire sur une grille journalière en échelle TT ; progression contrôlée
(le pas déroulé doit rester positif) ; chaque franchissement encadré, puis affiné par la méthode
de Brent à 0,01 s ; résidu angulaire contrôlé ; une seconde avant et une seconde après, le
Soleil doit être de part et d'autre de la frontière. En cas d'incohérence, le calcul s'arrête.

Écarts à la lettre de l'annexe D2, sans effet sur le résultat :
- l'instant est un jour julien TT en un seul nombre, non en deux parties : sa résolution est
  d'environ 40 microsecondes, 250 fois plus fine que la tolérance de 0,01 s ;
- seul l'instant d'entrée est rendu. La sortie d'un signe est l'entrée du suivant ; le séjour
  commencé en décembre de l'année précédente se lit dans le calendrier de cette année-là.

L'année est l'année civile en UTC. Le résidu peut être négatif : à l'instant d'entrée rendu, le
classement peut encore donner le signe précédent pendant au plus 0,01 s. Les dates sont
indicatives pour une naissance : près d'une frontière, l'heure de naissance compte.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from scipy.optimize import brentq

from moteur.civil_time import load_zone, zone_history_caveat
from moteur.classification import Zodiac, load_canonical
from moteur.coordinates import signed_wrap
from moteur.manifest import build_manifest
from moteur.positions import SECONDS_PER_DAY, SunEphemeris, TimeScale, load_ephemeris

BRENT_TOLERANCE_SECONDS = 0.01
# Le Soleil parcourt au plus 1,02° par jour : 0,01 s valent moins de 1,2 × 10⁻⁷°.
RESIDUAL_TOLERANCE_DEG = 2e-7
# Progression journalière du Soleil : toujours positive, toujours inférieure à cette borne.
MAX_DAILY_MOTION_DEG = 2.0
DEFAULT_TIMEZONE = "Europe/Paris"

NOTICE = "indicatif : près d'une frontière, l'heure de naissance compte"
# Mention d'affichage imposée par l'annexe D2, mot pour mot.
TIME_NOTICE_PARIS = (
    "Instant calculé en TT ; UTC selon la table de secondes intercalaires utilisée ; "
    "heure de Paris selon la version de la base des fuseaux."
)
# Variantes, hors du cas prévu par l'annexe : autre fuseau d'affichage, ou année antérieure à
# 1972, pour laquelle l'instant civil est du temps universel (décision 0010).
TIME_NOTICE_OTHER_ZONE = TIME_NOTICE_PARIS.replace("heure de Paris", "heure locale")
TIME_NOTICE_BEFORE_1972 = (
    "Instant calculé en TT ; temps universel selon le modèle ΔT utilisé ; "
    "heure locale selon la version de la base des fuseaux."
)


class PassageError(Exception):
    """Le calcul des passages est incohérent : il s'arrête, rien n'est corrigé."""


@dataclass(frozen=True)
class SunEntry:
    """Entrée du Soleil dans un signe."""

    sign_id: str
    boundary_deg: float
    tt_jd: float
    instant_utc: datetime
    instant_local: datetime
    time_scale: TimeScale
    conditional: bool  # instant futur : secondes intercalaires et heure légale à venir inconnues
    residual_deg: float  # longitude du Soleil à l'instant trouvé, moins la frontière


@dataclass(frozen=True)
class SunCalendar:
    """Calendrier annuel des entrées du Soleil."""

    year: int
    timezone: str
    entries: tuple[SunEntry, ...]
    notice: str
    time_notice: str
    data_status: str
    timezone_caveat: str | None  # réserve sur l'histoire du fuseau avant 1970 (décision 0011)
    manifest: dict[str, object]


def time_notice(year: int, timezone: str) -> str:
    """Mention d'affichage des instants, selon l'année et le fuseau d'affichage."""
    if year < 1972:
        return TIME_NOTICE_BEFORE_1972
    return TIME_NOTICE_PARIS if timezone == DEFAULT_TIMEZONE else TIME_NOTICE_OTHER_ZONE


def refine_crossing(
    longitude: Callable[[float], float], boundary_deg: float, low_tt: float, high_tt: float
) -> tuple[float, float]:
    """Instant TT où la longitude atteint la frontière, entre deux instants qui l'encadrent.

    Rend l'instant et le résidu. Contrôle qu'une seconde avant et une seconde après, l'astre est
    de part et d'autre de la frontière (annexe D2, étapes 5 à 7).
    """

    def gap(tt_jd: float) -> float:
        return signed_wrap(longitude(tt_jd) - boundary_deg)

    second = 1.0 / SECONDS_PER_DAY
    if gap(low_tt) * gap(high_tt) > 0.0:
        raise PassageError("la frontière n'est pas encadrée par les deux instants donnés")
    root = float(brentq(gap, low_tt, high_tt, xtol=BRENT_TOLERANCE_SECONDS * second))
    residual = gap(root)
    if abs(residual) > RESIDUAL_TOLERANCE_DEG:
        raise PassageError(f"résidu angulaire trop grand au passage : {residual!r}°")
    before, after = gap(root - second), gap(root + second)
    if not (before < 0.0 < after or after < 0.0 < before):
        raise PassageError("une seconde avant et après, l'astre est du même côté de la frontière")
    return root, residual


def sun_entries(
    year: int,
    timezone: str = DEFAULT_TIMEZONE,
    *,
    ephemeris: SunEphemeris | None = None,
    zodiac: Zodiac | None = None,
) -> SunCalendar:
    """Entrées du Soleil dans les signes pendant l'année civile `year` (en UTC)."""
    chain = ephemeris if ephemeris is not None else load_ephemeris()
    partition = zodiac if zodiac is not None else load_canonical()
    zone = load_zone(timezone)

    start = chain.instant(datetime(year, 1, 1, tzinfo=UTC)).tt_jd
    end = chain.instant(datetime(year + 1, 1, 1, tzinfo=UTC)).tt_jd

    # Grille journalière en TT ; un jour de marge de chaque côté.
    days = [start - 1.0 + offset for offset in range(math.ceil(end - start) + 3)]
    longitudes = [chain.sun_longitude(day) for day in days]
    for index in range(len(days) - 1):
        # Pas déroulé : l'écart signé supprime le saut à 360°. Il doit rester positif.
        step = signed_wrap(longitudes[index + 1] - longitudes[index])
        if not 0.0 < step < MAX_DAILY_MOTION_DEG:
            raise PassageError(f"progression journalière du Soleil inattendue : {step!r}°")

    entries: list[SunEntry] = []
    for sign in partition.signs:
        boundary = sign.start_deg
        for index in range(len(days) - 1):
            # Franchissement en montant : écart négatif, puis positif ou nul. La même valeur
            # sert de fin à une paire et de début à la suivante : un Soleil exactement sur la
            # frontière à un point de grille est compté une fois.
            low = signed_wrap(longitudes[index] - boundary)
            high = signed_wrap(longitudes[index + 1] - boundary)
            if not (low < 0.0 <= high and high - low < MAX_DAILY_MOTION_DEG):
                continue
            root, residual = refine_crossing(
                chain.sun_longitude, boundary, days[index], days[index + 1]
            )
            if not start <= root < end:
                continue
            instant = chain.utc_datetime(root)
            entries.append(
                SunEntry(
                    sign_id=sign.sign_id,
                    boundary_deg=boundary,
                    tt_jd=root,
                    instant_utc=instant,
                    instant_local=instant.astimezone(zone),
                    time_scale=chain.instant(instant).time_scale,
                    conditional=chain.is_conditional(root),
                    residual_deg=residual,
                )
            )
    entries.sort(key=lambda entry: entry.tt_jd)
    manifest = build_manifest(chain, partition, None)
    return SunCalendar(
        year=year,
        timezone=timezone,
        entries=tuple(entries),
        notice=NOTICE,
        time_notice=time_notice(year, timezone),
        data_status=str(manifest["data_status"]),
        timezone_caveat=zone_history_caveat(date(year, 1, 1)),
        manifest=manifest,
    )
