"""Comparaison à JPL Horizons (skill `frontieres`, étape 3).

Les réponses brutes de Horizons sont archivées dans tests/fixtures/horizons/ : la comparaison se
rejoue hors ligne. Le contrôle du repère R ne demande que ces archives ; les tests marqués
`donnees` exigent en plus l'éphéméride DE440s téléchargée.
"""

from __future__ import annotations

import math
import urllib.parse
from pathlib import Path

import numpy as np
import pytest

from moteur import boundaries
from moteur import coordinates as c
from scripts import comparer_horizons as h
from scripts.telecharger import dossier_donnees

ICRF_ARCHIVE = h.latest_archive(h.FIXTURES, h.REFERENCE_YEAR, "FRAME")
ECLIPTIC_ARCHIVE = h.latest_archive(h.FIXTURES, h.REFERENCE_YEAR, "ECLIPTIC")
ICRF = ICRF_ARCHIVE.read_text(encoding="utf-8")
ECLIPTIC = ECLIPTIC_ARCHIVE.read_text(encoding="utf-8")


def archived_instants() -> list[h.Crossing]:
    """Instants archivés, sans éphéméride : assez pour contrôler le repère hors ligne."""
    return [
        h.Crossing(f"point-{rank}", 0.0, jd, jd, 0.0)
        for rank, (jd, _) in enumerate(h.parse_vectors(ICRF, "FRAME"))
    ]


# --- Requêtes ------------------------------------------------------------------------------


def test_horizons_query_asks_for_astrometric_geocentric_sun_vectors() -> None:
    url = h.build_query([2451545.0, 2451546.5])
    parts = urllib.parse.urlsplit(url)
    assert (parts.scheme, parts.hostname, parts.path) == (
        "https",
        "ssd.jpl.nasa.gov",
        "/api/horizons.api",
    )
    query = dict(urllib.parse.parse_qsl(parts.query))
    assert query["COMMAND"] == "'10'"  # Soleil
    assert query["CENTER"] == "'500@399'"  # centre de la Terre
    assert query["EPHEM_TYPE"] == "'VECTORS'"
    assert query["REF_SYSTEM"] == "'ICRF'"
    assert query["REF_PLANE"] == "'FRAME'"
    # Temps de lumière seul : positions astrométriques, pas apparentes (ni aberration).
    assert query["VEC_CORR"] == "'LT'"
    assert query["TIME_TYPE"] == "'TDB'"
    assert query["TLIST"] == "'2451545.000000000 2451546.500000000'"


def test_horizons_ecliptic_query_differs_only_by_the_plane() -> None:
    first = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(h.build_query([2451545.0])).query))
    second = dict(
        urllib.parse.parse_qsl(urllib.parse.urlsplit(h.build_query([2451545.0], "ECLIPTIC")).query)
    )
    assert second.pop("REF_PLANE") == "'ECLIPTIC'"
    assert first.pop("REF_PLANE") == "'FRAME'"
    assert first == second


def test_horizons_query_carries_nothing_but_instants() -> None:
    """Aucune donnée personnelle ni nom de projet ne part vers le service."""
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(h.build_query([2451545.0])).query))
    assert set(query) == {
        "format",
        "COMMAND",
        "OBJ_DATA",
        "MAKE_EPHEM",
        "EPHEM_TYPE",
        "CENTER",
        "REF_PLANE",
        "REF_SYSTEM",
        "VEC_CORR",
        "VEC_TABLE",
        "OUT_UNITS",
        "CSV_FORMAT",
        "VEC_LABELS",
        "TLIST_TYPE",
        "TIME_TYPE",
        "TLIST",
    }


# --- Lecture des réponses archivées --------------------------------------------------------


@pytest.mark.parametrize(("text", "plane"), [(ICRF, "FRAME"), (ECLIPTIC, "ECLIPTIC")])
def test_horizons_archive_holds_one_vector_per_boundary(text: str, plane: h.Plane) -> None:
    vectors = h.parse_vectors(text, plane)
    assert len(vectors) == 13
    for jd, vector in vectors:
        assert jd > 2400000.0
        assert vector.shape == (3,)
        assert 0.98 < float(np.linalg.norm(vector)) < 1.02  # distance Terre–Soleil, en ua


def test_horizons_both_archives_cover_the_same_instants() -> None:
    first = [jd for jd, _ in h.parse_vectors(ICRF, "FRAME")]
    second = [jd for jd, _ in h.parse_vectors(ECLIPTIC, "ECLIPTIC")]
    assert first == second


def test_horizons_altered_archive_is_refused(tmp_path: Path) -> None:
    copy = tmp_path / ICRF_ARCHIVE.name
    copy.write_text(ICRF.replace("E-01", "E-02", 1), encoding="utf-8")
    copy.with_suffix(".json").write_bytes(ICRF_ARCHIVE.with_suffix(".json").read_bytes())
    with pytest.raises(h.ComparisonError, match="empreinte différente"):
        h.latest_archive(tmp_path, h.REFERENCE_YEAR)


def test_horizons_archive_without_its_record_is_refused(tmp_path: Path) -> None:
    (tmp_path / ICRF_ARCHIVE.name).write_text(ICRF, encoding="utf-8")
    with pytest.raises(h.ComparisonError, match="fiche d'archive absente"):
        h.latest_archive(tmp_path, h.REFERENCE_YEAR)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("Reference frame : ICRF", "Reference frame : Ecliptic of J2000.0"),
        ("LT CORRECTED cartesian states", "GEOMETRIC cartesian states"),
        ("Center body name: Earth (399)", "Center body name: Sun (10)"),
        ("JDTDB", "JDUT"),
        ("$$SOE", ""),
    ],
)
def test_horizons_unexpected_response_is_refused(old: str, new: str) -> None:
    """Un autre repère, des positions non corrigées, un autre centre ou une autre échelle de
    temps ne sont pas comparables."""
    assert old in ICRF
    with pytest.raises(h.ComparisonError):
        h.parse_vectors(ICRF.replace(old, new), "FRAME")


def test_horizons_an_icrf_response_is_not_read_as_ecliptic() -> None:
    with pytest.raises(h.ComparisonError):
        h.parse_vectors(ICRF, "ECLIPTIC")


def test_horizons_missing_archive_is_an_explicit_error(tmp_path: Path) -> None:
    with pytest.raises(h.ComparisonError, match="--interroger"):
        h.latest_archive(tmp_path, h.REFERENCE_YEAR)


def test_horizons_main_without_ephemeris_returns_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert h.main([], ephemeris=tmp_path / "absent.bsp") == 1
    assert "/donnees" in capsys.readouterr().err


def test_horizons_tolerances_are_declared() -> None:
    assert h.CHAIN_TOLERANCE_DEG == 1e-6
    assert h.BOUNDARY_TOLERANCE_DEG == 1e-6
    assert h.FRAME_TOLERANCE_ARCSEC == 0.1
    assert h.EXPLAINED_TOLERANCE_ARCSEC == 1e-6
    assert h.BRENT_TOLERANCE_SECONDS == 0.01


# --- Repère R contre l'écliptique J2000 de Horizons (archives seules) ----------------------


def test_horizons_states_the_obliquity_of_its_ecliptic() -> None:
    """La valeur est lue dans la réponse de Horizons, pas supposée."""
    assert h.horizons_obliquity_arcsec(ECLIPTIC) == 84381.448
    with pytest.raises(h.ComparisonError, match="obliquité"):
        h.horizons_obliquity_arcsec(ICRF)


def frame_rows() -> list[h.FrameRow]:
    return h.compare_frames(
        archived_instants(),
        h.parse_vectors(ICRF, "FRAME"),
        h.parse_vectors(ECLIPTIC, "ECLIPTIC"),
        h.horizons_obliquity_arcsec(ECLIPTIC),
    )


def test_horizons_frame_r_matches_the_j2000_ecliptic_of_horizons() -> None:
    """R, appliquée aux vecteurs ICRF de Horizons, retrouve ses vecteurs écliptiques J2000."""
    rows = frame_rows()
    assert len(rows) == 13
    for row in rows:
        assert row.separation_arcsec <= h.FRAME_TOLERANCE_ARCSEC


def test_horizons_frame_difference_is_explained_by_two_known_conventions() -> None:
    """Avec l'obliquité de Horizons et sans biais de repère, il ne reste que l'arrondi."""
    for row in frame_rows():
        assert row.explained_residual_arcsec <= h.EXPLAINED_TOLERANCE_ARCSEC


def test_horizons_frame_difference_has_the_size_of_the_obliquity_gap() -> None:
    """L'écart n'est pas nul : 84 381,448″ contre 84 381,406″, plus le biais de repère."""
    gap = 84381.448 - c.EPSILON_0_ARCSEC
    worst = max(row.separation_arcsec for row in frame_rows())
    assert 0.5 * gap < worst < 2.0 * gap


@pytest.mark.parametrize("error_arcsec", [1.0, -1.0])
def test_horizons_a_wrong_obliquity_in_r_would_be_caught(
    monkeypatch: pytest.MonkeyPatch, error_arcsec: float
) -> None:
    """Sensibilité du contrôle : une obliquité fausse d'une seconde d'arc dépasse la tolérance."""
    epsilon = math.radians((c.EPSILON_0_ARCSEC + error_arcsec) / 3600.0)
    wrong = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, math.cos(epsilon), math.sin(epsilon)],
            [0.0, -math.sin(epsilon), math.cos(epsilon)],
        ]
    )
    monkeypatch.setattr(h, "frame_matrix", lambda: wrong)
    assert max(row.separation_arcsec for row in frame_rows()) > h.FRAME_TOLERANCE_ARCSEC


def test_horizons_a_reversed_obliquity_in_r_would_be_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sensibilité du contrôle : le sens de la rotation compte."""
    monkeypatch.setattr(h, "frame_matrix", lambda: c.frame_matrix().T)
    assert max(row.separation_arcsec for row in frame_rows()) > 3600.0


# --- Chaîne de positions rejouée hors ligne (éphéméride requise) ---------------------------


@pytest.fixture(scope="module")
def chain() -> h.SunChain:
    return h.SunChain(dossier_donnees() / h.EPHEMERIS_FILE)


@pytest.fixture(scope="module")
def crossings(chain: h.SunChain) -> list[h.Crossing]:
    return h.sun_crossings(boundaries.construct(), chain, h.REFERENCE_YEAR)


@pytest.mark.donnees
def test_horizons_sun_reaches_each_boundary_once_in_the_year(
    chain: h.SunChain, crossings: list[h.Crossing]
) -> None:
    assert tuple(crossing.sign_id for crossing in crossings) == boundaries.EXPECTED_ORDER
    second = 1.0 / h.SECONDS_PER_DAY
    for crossing in crossings:
        # Résidu de la recherche de Brent : 0,01 s de mouvement solaire, soit moins de 2 × 10⁻⁷°.
        assert abs(crossing.residual_deg) < 2e-7
        before = chain.longitude_deg(crossing.tt_jd - second)
        after = chain.longitude_deg(crossing.tt_jd + second)
        assert h.signed_wrap(before - crossing.boundary_deg) < 0.0
        assert h.signed_wrap(after - crossing.boundary_deg) > 0.0


@pytest.mark.donnees
def test_horizons_position_chain_agrees_within_the_declared_tolerances(
    chain: h.SunChain, crossings: list[h.Crossing]
) -> None:
    rows = h.compare(crossings, h.parse_vectors(ICRF, "FRAME"), chain)
    assert tuple(row.sign_id for row in rows) == boundaries.EXPECTED_ORDER
    for row in rows:
        assert abs(row.chain_difference_deg) <= h.CHAIN_TOLERANCE_DEG
        assert abs(row.boundary_difference_deg) <= h.BOUNDARY_TOLERANCE_DEG


@pytest.mark.donnees
def test_horizons_main_replays_offline_and_returns_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert h.main(["--tableau"]) == 0
    output = capsys.readouterr().out
    assert ICRF_ARCHIVE.name in output
    assert ECLIPTIC_ARCHIVE.name in output
    assert output.count("\n| ") >= 28  # deux tableaux : en-tête, séparateur et 13 lignes chacun


@pytest.mark.donnees
def test_horizons_stale_archive_is_detected(chain: h.SunChain, crossings: list[h.Crossing]) -> None:
    """Si les frontières changent, les instants archivés ne sont plus ceux des passages."""
    vectors = [(jd + 0.01, vector) for jd, vector in h.parse_vectors(ICRF, "FRAME")]
    with pytest.raises(h.ComparisonError, match="--interroger"):
        h.compare(crossings, vectors, chain)


@pytest.mark.donnees
def test_horizons_a_shifted_position_would_be_caught(
    chain: h.SunChain, crossings: list[h.Crossing]
) -> None:
    """Sensibilité du contrôle de positions : un vecteur de Horizons décalé de 0,01″ dépasse
    la tolérance. Ce test ne dit rien du repère : R est commune aux deux chaînes."""
    angle = math.radians(0.01 / 3600.0)
    rotation = np.array(
        [
            [math.cos(angle), -math.sin(angle), 0.0],
            [math.sin(angle), math.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    shifted = [(jd, rotation @ vector) for jd, vector in h.parse_vectors(ICRF, "FRAME")]
    rows = h.compare(crossings, shifted, chain)
    assert max(abs(row.chain_difference_deg) for row in rows) > h.CHAIN_TOLERANCE_DEG
