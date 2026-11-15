"""Lieux — recherche hors ligne dans GeoNames et fuseau d'après des coordonnées (FR-01).

Référence : PRD § 6 (FR-01 : le lieu fait partie de la saisie) ; décision 0002 (lieux et fuseaux
locaux, aucun service tiers) ; règle de l'interface (lieu absent : coordonnées saisies, fuseau
déduit et montré pour confirmation, jamais la ville la plus proche en silence).

Les localités du petit fichier d'essai sont inventées. Les tests marqués `donnees` lisent les
fichiers GeoNames téléchargés.
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from moteur import places
from moteur.places import PlaceIndex, PlaceQueryError, PlacesUnavailable

# Colonnes du fichier « cities » de GeoNames (19 colonnes séparées par des tabulations).
COLUMNS = 19


def city(
    geoname_id: int,
    name: str,
    alternates: str,
    country: str,
    admin1: str,
    population: int,
    zone: str,
    latitude: str = "10.5",
    longitude: str = "20.25",
) -> str:
    row = [""] * COLUMNS
    row[0], row[1], row[2], row[3] = str(geoname_id), name, places.ascii_fold(name), alternates
    row[4], row[5], row[8], row[10] = latitude, longitude, country, admin1
    row[14], row[17] = str(population), zone
    return "\t".join(row)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def index(tmp_path: Path) -> PlaceIndex:
    rows = [
        city(1, "Villefictive", "Fictiveville,Ville Fictive", "FR", "11", 50_000, "Europe/Paris"),
        city(2, "Villefictive", "", "CA", "10", 900_000, "America/Toronto"),
        # Un nom secondaire qui contient U+2028 : seul « \\n » sépare les lignes du fichier.
        city(3, "Saint-Étienne-du-Test", "Nom\u2028Coupé", "FR", "84", 20_000, "Europe/Paris"),
        city(4, "Autrebourg", "Villefictive-la-Neuve", "BE", "", 5_000_000, "Europe/Brussels"),
        city(5, "Fictivevillette", "", "CH", "", 9_000_000, "Europe/Zurich"),
    ]
    cities = tmp_path / "cities15000.zip"
    with zipfile.ZipFile(cities, "w") as archive:
        archive.writestr("cities15000.txt", "\n".join(rows) + "\n")
    admin = tmp_path / "admin1CodesASCII.txt"
    admin.write_text(
        "FR.11\tÎle-de-Test\tIle-de-Test\t1\nCA.10\tQuébec-Test\tQuebec-Test\t2\n",
        encoding="utf-8",
    )
    return PlaceIndex(cities, sha256(cities), admin, sha256(admin))


def test_places_normalize_ignores_case_accents_and_punctuation() -> None:
    assert places.normalize("  Saint-Étienne ") == "saint etienne"
    assert places.normalize("SAINT ETIENNE") == "saint etienne"
    assert places.normalize("L'Haÿ-les-Roses") == "l hay les roses"


def test_places_search_ranks_main_names_before_alternates_then_by_population(
    index: PlaceIndex,
) -> None:
    found = index.search("villefictive")
    # Les deux homonymes d'abord, le plus peuplé en tête ; le nom secondaire ensuite, même si la
    # localité est plus peuplée.
    assert [place.geoname_id for place in found] == [2, 1, 4]


def test_places_search_reads_the_region_name_and_keeps_missing_ones_null(index: PlaceIndex) -> None:
    by_id = {place.geoname_id: place for place in index.search("villefictive")}
    assert by_id[1].admin1_name == "Île-de-Test"
    assert by_id[2].admin1_name == "Québec-Test"
    assert by_id[4].admin1_name is None  # région absente du fichier : jamais inventée


def test_places_search_matches_without_accents_or_hyphens(index: PlaceIndex) -> None:
    assert [place.geoname_id for place in index.search("saint etienne")] == [3]
    assert [place.geoname_id for place in index.search("Saint-Étienne-du")] == [3]


def test_places_search_ranks_an_exact_alternate_name_before_a_longer_main_name(
    index: PlaceIndex,
) -> None:
    # « Fictiveville » est le nom secondaire exact de la localité 1 ; la localité 5, bien plus
    # peuplée, ne fait que commencer ainsi. Le nom exact passe devant (« Londres » → London).
    assert [place.geoname_id for place in index.search("Fictiveville")] == [1, 5]


def test_places_file_lines_are_split_on_newline_only(index: PlaceIndex) -> None:
    assert [place.geoname_id for place in index.search("nom coupe")] == [3]


def test_places_search_returns_coordinates_and_timezone_as_read(index: PlaceIndex) -> None:
    place = index.search("autrebourg")[0]
    assert (place.latitude_deg, place.longitude_deg) == (10.5, 20.25)
    assert place.timezone == "Europe/Brussels"
    assert place.country_code == "BE"
    assert place.population == 5_000_000


@pytest.mark.parametrize("query", ["", " ", "v", "é"])
def test_places_search_needs_two_characters(index: PlaceIndex, query: str) -> None:
    assert index.search(query) == ()


def test_places_search_unknown_place_returns_nothing_never_a_neighbour(index: PlaceIndex) -> None:
    assert index.search("Lieuabsent") == ()


def test_places_search_respects_the_limit(index: PlaceIndex) -> None:
    assert len(index.search("villefictive", limit=1)) == 1
    with pytest.raises(PlaceQueryError):
        index.search("villefictive", limit=0)
    with pytest.raises(PlaceQueryError):
        index.search("villefictive", limit=places.MAX_RESULTS + 1)


def test_places_index_refuses_a_file_whose_hash_differs(tmp_path: Path, index: PlaceIndex) -> None:
    cities = tmp_path / "cities15000.zip"
    admin = tmp_path / "admin1CodesASCII.txt"
    with pytest.raises(PlacesUnavailable):
        PlaceIndex(cities, "0" * 64, admin, sha256(admin))
    with pytest.raises(PlacesUnavailable):
        PlaceIndex(cities, sha256(cities), admin, "0" * 64)


def test_places_index_refuses_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(PlacesUnavailable):
        PlaceIndex(tmp_path / "absent.zip", "0" * 64, tmp_path / "absent.txt", "0" * 64)


def test_places_errors_never_repeat_the_coordinates() -> None:
    with pytest.raises(PlaceQueryError) as caught:
        places.timezone_at(91.2345, 12.3456)
    assert "91.2345" not in str(caught.value) and "12.3456" not in str(caught.value)
    with pytest.raises(PlaceQueryError) as caught:
        places.timezone_at(12.3456, 181.2345)
    assert "181.2345" not in str(caught.value) and "12.3456" not in str(caught.value)


def test_places_manifest_names_the_sources_and_the_attribution(index: PlaceIndex) -> None:
    manifest = index.manifest()
    assert manifest["attribution"] == places.GEONAMES_ATTRIBUTION
    assert "CC BY 4.0" in places.GEONAMES_ATTRIBUTION
    sources = manifest["sources"]
    assert isinstance(sources, dict)
    assert set(sources) == {places.CITIES_SOURCE_ID, places.ADMIN_SOURCE_ID}


def test_places_unavailable_when_the_data_directory_is_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("B13_DONNEES", str(tmp_path))
    with pytest.raises(PlacesUnavailable):
        places.load_places()


def test_places_timezone_at_paris_coordinates() -> None:
    assert places.timezone_at(48.8566, 2.3522) == places.TimezoneLookup("Europe/Paris", "found")


def test_places_timezone_at_open_sea_is_absent_not_a_fixed_offset() -> None:
    # En pleine mer, la bibliothèque rend un simple décalage (Etc/GMT…) : ce n'est pas un fuseau
    # civil, le moteur le refuse, donc rien n'est rendu.
    assert places.timezone_at(0.0, -30.0) == places.TimezoneLookup(None, "no_civil_timezone")


class _Finder:
    """Carte d'essai : rend toujours le même nom de fuseau."""

    def __init__(self, name: str | None) -> None:
        self.name = name

    def timezone_at(self, *, lat: float, lng: float) -> str | None:
        return self.name


@pytest.mark.parametrize(
    ("name", "status"),
    [
        (None, "no_civil_timezone"),
        ("Etc/GMT+2", "no_civil_timezone"),
        ("Nulle/Part", "unknown_to_timezone_database"),
    ],
)
def test_places_timezone_absence_says_why(
    monkeypatch: pytest.MonkeyPatch, name: str | None, status: str
) -> None:
    monkeypatch.setattr(places, "_finder", lambda: _Finder(name))
    assert places.timezone_at(10.0, 10.0) == places.TimezoneLookup(None, status)  # type: ignore[arg-type]


def test_places_lookup_manifest_names_the_boundary_data_and_its_version() -> None:
    manifest = places.lookup_manifest()
    assert set(manifest) == {"timezonefinder", "timezonefinder_data", "timezone_database_version"}
    assert all(isinstance(value, str) and value for value in manifest.values())


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(91.0, 0.0), (-91.0, 0.0), (0.0, 181.0), (float("nan"), 0.0), (0.0, float("inf"))],
)
def test_places_timezone_at_refuses_impossible_coordinates(
    latitude: float, longitude: float
) -> None:
    with pytest.raises(PlaceQueryError):
        places.timezone_at(latitude, longitude)


@pytest.mark.donnees
def test_places_geonames_finds_paris_first_with_its_timezone() -> None:
    first = places.load_places().search("Paris")[0]
    assert (first.name, first.country_code, first.timezone) == ("Paris", "FR", "Europe/Paris")
    assert first.admin1_name == "Île-de-France"


@pytest.mark.donnees
def test_places_geonames_finds_a_city_by_its_french_name() -> None:
    names = [place.name for place in places.load_places().search("Londres")]
    assert "London" in names


@pytest.mark.donnees
def test_places_geonames_every_timezone_is_known_to_the_engine() -> None:
    from moteur.civil_time import load_zone

    for zone in places.load_places().timezones():
        load_zone(zone)
