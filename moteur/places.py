"""Lieux : recherche hors ligne dans GeoNames, et fuseau d'après des coordonnées (FR-01).

Référence : PRD § 6 (FR-01) ; décision 0002 (lieux et fuseaux locaux, aucun appel à un tiers) ;
`donnees/sources.toml` (localités de plus de 15 000 habitants, CC BY 4.0).

Régime « mesure » : noms, coordonnées et fuseaux sont lus tels quels dans les fichiers
téléchargés, contrôlés par leur empreinte. Rien n'est complété : une région absente reste
absente, un lieu introuvable ne rend rien — jamais la localité la plus proche. Le lieu ne sert
qu'au fuseau (et, plus tard, aux angles et aux maisons) : les positions sont géocentriques.

Une recherche est une saisie personnelle : elle n'est ni conservée, ni journalisée, ni reprise
dans un message d'erreur.
"""

from __future__ import annotations

import hashlib
import math
import tomllib
import unicodedata
import zipfile
from dataclasses import dataclass
from functools import cache
from importlib import metadata
from pathlib import Path
from typing import Literal

from timezonefinder import TimezoneFinder

from moteur.civil_time import (
    FIXED_OFFSET_AREAS,
    InputError,
    load_zone,
    timezone_database_version,
)
from moteur.positions import SOURCES, EphemerisUnavailable, data_directory

CITIES_SOURCE_ID = "geonames-cities15000"
ADMIN_SOURCE_ID = "geonames-admin1"
TIMEZONE_DATA_PACKAGE = "timezonefinder_data"
GEONAMES_ATTRIBUTION = "Lieux : GeoNames (geonames.org), licence CC BY 4.0"
MIN_QUERY_LENGTH = 2
DEFAULT_RESULTS = 8
MAX_RESULTS = 20

# Colonnes du fichier « cities » de GeoNames utilisées ici (19 colonnes, tabulations).
_COLUMNS = 19
_ID, _NAME, _ASCII, _ALTERNATES, _LATITUDE, _LONGITUDE = 0, 1, 2, 3, 4, 5
_COUNTRY, _ADMIN1, _POPULATION, _TIMEZONE = 8, 10, 14, 17


class PlacesUnavailable(Exception):
    """Les fichiers de lieux manquent ou ne sont pas ceux du registre : aucune recherche."""


class PlaceQueryError(Exception):
    """Demande refusée. Le message est destiné à la personne et ne reprend aucune saisie."""


@dataclass(frozen=True)
class Place:
    """Une localité, telle que GeoNames la décrit."""

    geoname_id: int
    name: str
    admin1_name: str | None  # région ; absente si le fichier des régions ne la connaît pas
    country_code: str
    latitude_deg: float
    longitude_deg: float
    timezone: str
    population: int


@dataclass(frozen=True)
class _Entry:
    place: Place
    main_names: tuple[str, ...]  # nom et nom ASCII, normalisés
    alternates: str  # noms secondaires normalisés, chacun entre deux sauts de ligne


def ascii_fold(text: str) -> str:
    """Retire les signes diacritiques (é → e), sans toucher au reste."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize(text: str) -> str:
    """Forme de comparaison d'un nom : sans accents, sans casse, ponctuation réduite à un espace."""
    folded = ascii_fold(text).casefold()
    return " ".join("".join(char if char.isalnum() else " " for char in folded).split())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _checked(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file():
        raise PlacesUnavailable(f"{label} absent : lance scripts/telecharger.py")
    if not expected_sha256 or _sha256(path) != expected_sha256:
        raise PlacesUnavailable(
            f"{label} : empreinte différente de celle de donnees/sources.toml ; "
            "le fichier n'est pas utilisé"
        )


class PlaceIndex:
    """Localités de GeoNames gardées en mémoire, contrôlées contre leur empreinte déclarée."""

    def __init__(
        self, cities_path: Path, cities_sha256: str, admin_path: Path, admin_sha256: str
    ) -> None:
        _checked(cities_path, cities_sha256, "fichier des localités")
        _checked(admin_path, admin_sha256, "fichier des régions")
        self._sources: dict[str, dict[str, str]] = {
            CITIES_SOURCE_ID: {"file": cities_path.name, "sha256": cities_sha256},
            ADMIN_SOURCE_ID: {"file": admin_path.name, "sha256": admin_sha256},
        }
        regions = self._read_regions(admin_path)
        self._entries = self._read_cities(cities_path, regions)

    @staticmethod
    def _read_regions(path: Path) -> dict[str, str]:
        regions: dict[str, str] = {}
        # Séparateur de lignes de GeoNames : « \\n » seul. `splitlines` couperait aussi sur
        # d'autres caractères Unicode présents dans un nom.
        for line in path.read_text(encoding="utf-8").split("\n"):
            columns = line.split("\t")
            if len(columns) >= 2 and columns[0]:
                regions[columns[0]] = columns[1]
        return regions

    @staticmethod
    def _read_cities(path: Path, regions: dict[str, str]) -> tuple[_Entry, ...]:
        try:
            with zipfile.ZipFile(path) as archive:
                members = archive.namelist()
                if len(members) != 1:
                    raise PlacesUnavailable("fichier des localités : un seul fichier est attendu")
                text = archive.read(members[0]).decode("utf-8")
        except (zipfile.BadZipFile, UnicodeDecodeError) as error:
            raise PlacesUnavailable("fichier des localités illisible") from error
        entries: list[_Entry] = []
        for line in text.split("\n"):
            if not line:
                continue
            columns = line.split("\t")
            if len(columns) != _COLUMNS:
                raise PlacesUnavailable("fichier des localités : format de ligne inattendu")
            try:
                place = Place(
                    geoname_id=int(columns[_ID]),
                    name=columns[_NAME],
                    admin1_name=regions.get(f"{columns[_COUNTRY]}.{columns[_ADMIN1]}"),
                    country_code=columns[_COUNTRY],
                    latitude_deg=float(columns[_LATITUDE]),
                    longitude_deg=float(columns[_LONGITUDE]),
                    timezone=columns[_TIMEZONE],
                    population=int(columns[_POPULATION]),
                )
            except ValueError as error:
                raise PlacesUnavailable(
                    "fichier des localités : valeur numérique illisible"
                ) from error
            main = tuple(dict.fromkeys((normalize(columns[_NAME]), normalize(columns[_ASCII]))))
            alternates = "\n".join(
                normalized
                for normalized in (normalize(name) for name in columns[_ALTERNATES].split(","))
                if normalized
            )
            entries.append(_Entry(place, main, f"\n{alternates}\n"))
        if not entries:
            raise PlacesUnavailable("fichier des localités vide")
        return tuple(entries)

    def search(self, query: str, limit: int = DEFAULT_RESULTS) -> tuple[Place, ...]:
        """Localités dont le nom commence par la recherche ; les plus peuplées d'abord.

        Rang : nom principal exact, nom secondaire exact (« Londres » pour London), nom
        principal commençant ainsi, nom secondaire commençant ainsi. Moins de deux caractères
        utiles : aucun résultat. La normalisation vise les écritures latines ; dans les autres,
        elle peut rapprocher des noms distincts : la personne choisit dans la liste.
        """
        if type(limit) is not int or not 1 <= limit <= MAX_RESULTS:
            raise PlaceQueryError(
                f"nombre de résultats invalide : entre 1 et {MAX_RESULTS} est attendu"
            )
        wanted = normalize(query)
        if len(wanted) < MIN_QUERY_LENGTH:
            return ()
        exact, prefix = f"\n{wanted}\n", f"\n{wanted}"
        ranked: list[tuple[int, int, str, int, Place]] = []
        for entry in self._entries:
            if wanted in entry.main_names:
                rank = 0
            elif exact in entry.alternates:
                rank = 1
            elif any(name.startswith(wanted) for name in entry.main_names):
                rank = 2
            elif prefix in entry.alternates:
                rank = 3
            else:
                continue
            place = entry.place
            ranked.append((rank, -place.population, place.name, place.geoname_id, place))
        ranked.sort(key=lambda item: item[:4])
        return tuple(item[4] for item in ranked[:limit])

    def timezones(self) -> frozenset[str]:
        """Fuseaux cités par le fichier des localités."""
        return frozenset(entry.place.timezone for entry in self._entries)

    def manifest(self) -> dict[str, object]:
        """Sources des lieux, pour le manifeste d'une réponse."""
        return {
            "sources": {key: dict(value) for key, value in self._sources.items()},
            "attribution": GEONAMES_ATTRIBUTION,
        }


def _declared(source_id: str) -> tuple[str, str]:
    """Nom de fichier et empreinte déclarés dans donnees/sources.toml pour une source."""
    try:
        registry = tomllib.loads(SOURCES.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise PlacesUnavailable("donnees/sources.toml illisible") from error
    for source in registry.get("source", []):
        if source.get("id") == source_id:
            return str(source.get("fichier", "")), str(source.get("sha256", ""))
    raise PlacesUnavailable(f"source « {source_id} » absente de donnees/sources.toml")


@cache
def _load(cities: Path, cities_sha256: str, admin: Path, admin_sha256: str) -> PlaceIndex:
    return PlaceIndex(cities, cities_sha256, admin, admin_sha256)


def load_places() -> PlaceIndex:
    """Localités de production, contrôlées contre donnees/sources.toml, chargées une fois."""
    cities_file, cities_sha256 = _declared(CITIES_SOURCE_ID)
    admin_file, admin_sha256 = _declared(ADMIN_SOURCE_ID)
    try:
        folder = data_directory()
    except EphemerisUnavailable as error:
        raise PlacesUnavailable("dossier des données téléchargées indéfini") from error
    return _load(folder / cities_file, cities_sha256, folder / admin_file, admin_sha256)


@cache
def _finder() -> TimezoneFinder:
    return TimezoneFinder()


def lookup_manifest() -> dict[str, object]:
    """Ce qui a servi à déduire un fuseau de coordonnées, pour le manifeste d'une réponse.

    Les contours des fuseaux viennent du paquet `timezonefinder_data` (source
    « timezonefinder-data » de donnees/sources.toml), versionné à part du code qui les lit.
    """
    return {
        "timezonefinder": metadata.version("timezonefinder"),
        "timezonefinder_data": metadata.version(TIMEZONE_DATA_PACKAGE),
        "timezone_database_version": timezone_database_version(),
    }


TimezoneStatus = Literal["found", "no_civil_timezone", "unknown_to_timezone_database"]


@dataclass(frozen=True)
class TimezoneLookup:
    """Fuseau d'un point : son identifiant, ou la raison pour laquelle il n'y en a pas."""

    timezone: str | None
    status: TimezoneStatus


def timezone_at(latitude_deg: float, longitude_deg: float) -> TimezoneLookup:
    """Fuseau civil IANA d'un point, ou son absence avec sa raison.

    Deux absences distinctes : aucun fuseau civil à cet endroit (pleine mer : la carte ne rend
    qu'un décalage fixe), ou fuseau nommé par la carte mais inconnu de la base des fuseaux
    utilisée. Aucun fuseau n'est supposé à la place. Le fuseau rendu est à montrer pour
    confirmation : il vient de contours cartographiques, pas d'un registre des lieux habités.
    """
    for value, label, bound in (
        (latitude_deg, "latitude", 90.0),
        (longitude_deg, "longitude", 180.0),
    ):
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise PlaceQueryError(f"{label} invalide : un nombre est attendu")
        if not math.isfinite(value) or not -bound <= value <= bound:
            raise PlaceQueryError(f"{label} invalide : entre −{bound:.0f}° et {bound:.0f}°")
    name = _finder().timezone_at(lat=float(latitude_deg), lng=float(longitude_deg))
    if name is None or str(name).startswith(FIXED_OFFSET_AREAS):
        return TimezoneLookup(None, "no_civil_timezone")
    try:
        load_zone(name)
    except InputError:
        return TimezoneLookup(None, "unknown_to_timezone_database")
    return TimezoneLookup(str(name), "found")
