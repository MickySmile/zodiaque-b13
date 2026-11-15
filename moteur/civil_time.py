"""Saisie de naissance et heure légale : de l'heure locale aux instants UTC possibles.

Référence : PRD § 6 (FR-01, FR-04) ; annexe technique § B (fuseaux, calendrier), D3 (étapes 1 à
4), E (« Statut de l'heure et résultat autorisé »), F (« Saisie de naissance »).

Une heure locale est unique, ambiguë (recul d'horloge : deux instants) ou inexistante (avance
d'horloge : aucun instant). Une heure inexistante est une erreur à résoudre par la personne,
jamais corrigée en silence ; une heure ambiguë donne deux scénarios jusqu'au choix de
l'occurrence.

Les fuseaux viennent du paquet `tzdata`, lu directement : la version annoncée au manifeste est
celle des données utilisées, quelle que soit la base de fuseaux du système.

Données personnelles : rien n'est journalisé, et aucun message d'erreur ne reprend la date,
l'heure ou le lieu saisis.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from functools import cache
from importlib import resources
from typing import Literal
from zoneinfo import ZoneInfo

import tzdata

TimeStatus = Literal["known", "uncertain", "unknown"]
Kind = Literal["unique", "ambiguous"]

TIME_STATUSES: tuple[TimeStatus, ...] = ("known", "uncertain", "unknown")
CALENDAR = "proleptic_gregorian"
FIRST_YEAR, LAST_YEAR = 1849, 2150  # années couvertes par l'éphéméride DE440s
# Identifiant géographique « Région/Ville » : ni décalage fixe, ni abréviation, ni chemin.
FIXED_OFFSET_AREAS = ("Etc/",)
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
TIME_PATTERN = re.compile(r"\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?")
# Au-delà de douze heures de part et d'autre, l'heure n'apporte plus rien : « heure inconnue ».
MAX_UNCERTAINTY_SECONDS = 12 * 3600.0
# Avant cette année, le paquet `tzdata` fusionne l'histoire de certains fuseaux (décision 0011).
MERGED_ZONE_HISTORY_BEFORE = 1970


class InputError(Exception):
    """Saisie refusée. Le message est destiné à la personne et ne reprend aucune donnée saisie."""


class NonexistentLocalTime(InputError):
    """L'heure locale saisie n'a jamais existé (avance d'horloge) : aucun thème n'est calculé."""


@dataclass(frozen=True, repr=False)
class BirthInput:
    """Saisie de naissance (annexe F). Les noms de champs sont ceux de l'annexe.

    Sa représentation textuelle ne montre aucune donnée : une saisie ne doit apparaître ni dans
    un journal, ni dans un message d'erreur, ni dans un rapport de test.
    """

    date_local: date
    time_local: time | None
    time_status: TimeStatus
    time_uncertainty_seconds: float
    timezone: str
    fold: int | None
    latitude_deg: float
    longitude_deg: float
    altitude_m: float | None
    calendar: str
    source: str | None

    def __repr__(self) -> str:
        return masked("BirthInput")

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> BirthInput:
        """Contrôle un enregistrement et le convertit. Lève `InputError` au premier défaut."""
        status = record.get("time_status")
        if status not in TIME_STATUSES:
            raise InputError("statut de l'heure invalide : known, uncertain ou unknown est attendu")

        calendar = record.get("calendar", CALENDAR)
        if calendar != CALENDAR:
            raise InputError(
                "calendrier non pris en charge : seul le grégorien proleptique est disponible"
            )

        raw_date = record.get("date_local")
        if not isinstance(raw_date, str) or not DATE_PATTERN.fullmatch(raw_date):
            raise InputError("date invalide : le format attendu est AAAA-MM-JJ")
        try:
            date_local = date.fromisoformat(raw_date)
        except ValueError:
            # Bien formée, mais absente du calendrier (31 février, mois 13…). L'erreur d'origine,
            # qui cite la date, n'est pas gardée en cause.
            raise InputError("date invalide : ce jour n'existe pas dans le calendrier") from None
        if not FIRST_YEAR <= date_local.year <= LAST_YEAR:
            raise InputError(
                f"date hors de la période couverte : l'éphéméride DE440s va de {FIRST_YEAR} "
                f"à {LAST_YEAR}"
            )

        raw_time = record.get("time_local")
        time_local: time | None = None
        if raw_time is not None:
            if isinstance(raw_time, str) and TIME_PATTERN.fullmatch(raw_time):
                try:
                    time_local = time.fromisoformat(raw_time)
                except ValueError:
                    time_local = None
            if time_local is None:
                raise InputError("heure invalide : le format attendu est HH:MM:SS, sans fuseau")
        if status != "unknown" and time_local is None:
            raise InputError("heure manquante : indiquez l'heure, ou choisissez « heure inconnue »")
        if status == "unknown":
            time_local = None

        uncertainty = _number(record.get("time_uncertainty_seconds", 0), "incertitude sur l'heure")
        if uncertainty < 0.0:
            raise InputError("incertitude sur l'heure invalide : une durée positive est attendue")
        if uncertainty > MAX_UNCERTAINTY_SECONDS:
            raise InputError(
                "incertitude sur l'heure supérieure à douze heures : choisissez « heure inconnue »"
            )
        if status == "uncertain" and uncertainty == 0.0:
            raise InputError(
                "heure incertaine : indiquez de combien, ou choisissez « heure connue »"
            )

        zone = record.get("timezone")
        if not isinstance(zone, str) or not zone:
            raise InputError(_ZONE_MESSAGE)
        load_zone(zone)  # contrôlé dès la saisie, quel que soit le statut de l'heure

        fold = record.get("fold")
        if fold is not None and (type(fold) is not int or fold not in (0, 1)):
            raise InputError("occurrence invalide : 0 (première) ou 1 (seconde) est attendu")

        latitude = _number(record.get("latitude_deg"), "latitude")
        longitude = _number(record.get("longitude_deg"), "longitude")
        if not -90.0 <= latitude <= 90.0:
            raise InputError("latitude invalide : entre −90° et 90°")
        if not -180.0 <= longitude <= 180.0:
            raise InputError("longitude invalide : entre −180° et 180°")
        raw_altitude = record.get("altitude_m")
        altitude = None if raw_altitude is None else _number(raw_altitude, "altitude")

        source = record.get("source")
        if source is not None and not isinstance(source, str):
            raise InputError("source invalide : un texte est attendu")

        return cls(
            date_local=date_local,
            time_local=time_local,
            time_status=status,
            time_uncertainty_seconds=uncertainty,
            timezone=zone,
            fold=fold if type(fold) is int else None,
            latitude_deg=latitude,
            longitude_deg=longitude,
            altitude_m=altitude,
            calendar=CALENDAR,
            source=source,
        )


def masked(name: str) -> str:
    """Représentation textuelle d'un objet qui porte un instant de naissance : rien n'en sort."""
    return f"{name}(<données personnelles masquées>)"


@dataclass(frozen=True, repr=False)
class Scenario:
    """Un instant possible pour une heure locale."""

    fold: int  # 0 : première occurrence ; 1 : seconde (après le recul d'horloge)
    instant_utc: datetime
    utc_offset_seconds: int

    def __repr__(self) -> str:
        return masked("Scenario")


@dataclass(frozen=True, repr=False)
class Resolution:
    """Instants UTC possibles d'une heure locale."""

    kind: Kind
    scenarios: tuple[Scenario, ...]

    def __repr__(self) -> str:
        return masked("Resolution")


_ZONE_MESSAGE = (
    "fuseau horaire invalide : un identifiant IANA de la forme Région/Ville est attendu, "
    "jamais un simple décalage"
)


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise InputError(f"{label} invalide : un nombre est attendu")
    try:
        number = float(value)
    except OverflowError:
        number = math.inf
    if not math.isfinite(number):
        raise InputError(f"{label} invalide : un nombre est attendu")
    return number


def timezone_database_version() -> str:
    """Version de la base IANA des fuseaux réellement utilisée (celle du paquet `tzdata`)."""
    return str(tzdata.IANA_VERSION)


@cache
def _known_zones() -> frozenset[str]:
    """Identifiants IANA du paquet `tzdata`, tels qu'il les liste lui-même."""
    listing = resources.files("tzdata").joinpath("zones").read_text(encoding="utf-8")
    return frozenset(listing.split())


@cache
def load_zone(name: str) -> ZoneInfo:
    """Fuseau historique IANA, lu dans le paquet `tzdata` et non dans la base du système.

    L'identifiant doit figurer tel quel, casse comprise, dans la liste du paquet : un nom de
    fichier trouvé sur un disque insensible à la casse ne suffit pas.
    """
    if name not in _known_zones() or "/" not in name or name.startswith(FIXED_OFFSET_AREAS):
        raise InputError(_ZONE_MESSAGE)
    source = resources.files("tzdata.zoneinfo").joinpath(*name.split("/"))
    if not source.is_file():
        raise InputError(_ZONE_MESSAGE)
    with source.open("rb") as stream:
        return ZoneInfo.from_file(stream, key=name)


def zone_history_caveat(day: date) -> str | None:
    """Réserve à afficher quand l'histoire du fuseau n'est pas garantie (décision 0011)."""
    if day.year < MERGED_ZONE_HISTORY_BEFORE:
        return "zone_history_may_be_merged_before_1970"
    return None


def resolve_local_time(
    date_local: date, time_local: time, zone: ZoneInfo, fold: int | None = None
) -> Resolution:
    """Classe une heure locale et rend ses instants UTC possibles.

    Une heure locale existe si, convertie en UTC puis ramenée au fuseau, elle redonne la même
    heure. Les deux lectures possibles (`fold` 0 et 1) sont essayées.
    """
    naive = datetime.combine(date_local, time_local)
    found: list[Scenario] = []
    for candidate in (0, 1):
        aware = naive.replace(tzinfo=zone, fold=candidate)
        instant = aware.astimezone(UTC)
        offset = aware.utcoffset()
        if offset is None or instant.astimezone(zone).replace(tzinfo=None) != naive:
            continue
        if all(existing.instant_utc != instant for existing in found):
            found.append(Scenario(candidate, instant, int(offset.total_seconds())))
    if not found:
        raise NonexistentLocalTime(
            "Cette heure locale n'existe pas : ce jour-là, les horloges ont été avancées. "
            "Vérifiez l'heure de naissance ; aucun thème n'est calculé."
        )
    if len(found) == 1:
        return Resolution(
            "unique", (Scenario(0, found[0].instant_utc, found[0].utc_offset_seconds),)
        )
    found.sort(key=lambda scenario: scenario.instant_utc)
    scenarios = tuple(found) if fold is None else tuple(s for s in found if s.fold == fold)
    return Resolution("ambiguous", scenarios)


def resolve(birth: BirthInput) -> Resolution:
    """Instants UTC possibles d'une saisie dont l'heure est connue ou incertaine."""
    if birth.time_local is None:
        raise InputError("heure inconnue : seule la carte de référence à midi est disponible")
    return resolve_local_time(
        birth.date_local, birth.time_local, load_zone(birth.timezone), birth.fold
    )
