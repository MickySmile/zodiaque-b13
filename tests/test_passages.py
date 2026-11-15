"""FR-06 — dates d'entrée du Soleil dans chaque signe pour une année (PRD § 6, § 7 ; annexe § C,
D2).

Critère d'acceptation : étant donné l'année 2026, quand j'ouvre le calendrier, alors 13 entrées
s'affichent en UTC et en heure de Paris, avec la mention « indicatif : près d'une frontière,
l'heure de naissance compte ».

Aucune date de passage n'est écrite ici : les tests vérifient des propriétés du calcul. Ceux qui
demandent l'éphéméride DE440s sont marqués `donnees`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import cache

import pytest

from moteur import boundaries, passages
from moteur.classification import load_canonical
from moteur.coordinates import signed_wrap
from moteur.positions import OutOfEphemerisRange, load_ephemeris

SECOND = 1.0 / 86400.0


@cache
def calendar(year: int = 2026) -> passages.SunCalendar:
    return passages.sun_entries(year)


# --- Sans éphéméride -----------------------------------------------------------------------


def test_fr_06_solver_tolerance_is_the_one_of_the_prd() -> None:
    """PRD § 7, précision numérique : tolérance du solveur 0,01 s."""
    assert passages.BRENT_TOLERANCE_SECONDS == 0.01


def test_fr_06_notices_are_the_imposed_ones() -> None:
    assert passages.NOTICE == "indicatif : près d'une frontière, l'heure de naissance compte"
    # Annexe D2, mention d'affichage imposée, mot pour mot.
    assert passages.TIME_NOTICE_PARIS == (
        "Instant calculé en TT ; UTC selon la table de secondes intercalaires utilisée ; "
        "heure de Paris selon la version de la base des fuseaux."
    )
    assert passages.time_notice(2026, "Europe/Paris") == passages.TIME_NOTICE_PARIS
    # Hors du cas prévu par l'annexe : autre fuseau, ou année en temps universel (0010).
    assert "heure locale" in passages.time_notice(2026, "America/Montreal")
    assert "Paris" not in passages.time_notice(2026, "America/Montreal")
    assert "secondes intercalaires" not in passages.time_notice(1900, "Europe/Paris")


def linear(rate_deg_per_day: float, origin_tt: float, origin_deg: float):  # type: ignore[no-untyped-def]
    """Astre synthétique à vitesse constante, pour éprouver le solveur sans éphéméride."""
    return lambda tt_jd: (origin_deg + rate_deg_per_day * (tt_jd - origin_tt)) % 360.0


def test_fr_06_solver_finds_a_crossing_to_a_hundredth_of_a_second() -> None:
    longitude = linear(1.0, 1000.0, 350.0)  # atteint 5° après 15 jours, en traversant 0°
    root, residual = passages.refine_crossing(longitude, 5.0, 1014.5, 1015.5)
    assert abs(root - 1015.0) < passages.BRENT_TOLERANCE_SECONDS * SECOND
    assert abs(residual) < passages.RESIDUAL_TOLERANCE_DEG


def test_fr_06_solver_accepts_a_crossing_exactly_on_a_grid_point() -> None:
    longitude = linear(1.0, 1000.0, 100.0)
    root, _ = passages.refine_crossing(longitude, 105.0, 1005.0, 1006.0)
    assert root == 1005.0


def test_fr_06_solver_stops_when_the_boundary_is_not_bracketed() -> None:
    longitude = linear(1.0, 1000.0, 100.0)
    with pytest.raises(passages.PassageError, match="encadrée"):
        passages.refine_crossing(longitude, 150.0, 1005.0, 1006.0)


def test_fr_06_solver_stops_when_the_body_does_not_cross() -> None:
    """Une seconde avant et après, l'astre doit être de part et d'autre de la frontière."""

    def touching(tt_jd: float) -> float:  # atteint la frontière puis repart en arrière
        return 100.0 - abs(tt_jd - 1005.5) * 1e-3

    with pytest.raises(passages.PassageError):
        passages.refine_crossing(touching, 100.0, 1005.5, 1006.0)


# --- Critère d'acceptation (éphéméride requise) --------------------------------------------


@pytest.mark.donnees
def test_fr_06_year_2026_has_thirteen_entries_one_per_sign() -> None:
    entries = calendar().entries
    assert len(entries) == 13
    assert sorted(entry.sign_id for entry in entries) == sorted(boundaries.EXPECTED_ORDER)


@pytest.mark.donnees
def test_fr_06_entries_are_given_in_utc_and_in_paris_time() -> None:
    result = calendar()
    assert result.timezone == "Europe/Paris"
    for entry in result.entries:
        assert entry.instant_utc.utcoffset() == timedelta(0)
        assert entry.instant_local == entry.instant_utc  # le même instant
        offset = entry.instant_local.utcoffset()
        assert offset in (timedelta(hours=1), timedelta(hours=2))  # heure d'hiver ou d'été
        assert str(entry.instant_local.tzinfo) == "Europe/Paris"


@pytest.mark.donnees
def test_fr_06_calendar_carries_the_notice_and_the_status() -> None:
    result = calendar()
    assert result.notice == "indicatif : près d'une frontière, l'heure de naissance compte"
    assert result.time_notice == passages.TIME_NOTICE_PARIS
    assert result.data_status == "candidate"


@pytest.mark.donnees
def test_fr_06_entries_fall_inside_the_year_in_chronological_order() -> None:
    entries = calendar().entries
    start, end = datetime(2026, 1, 1, tzinfo=UTC), datetime(2027, 1, 1, tzinfo=UTC)
    assert all(start <= entry.instant_utc < end for entry in entries)
    assert [entry.tt_jd for entry in entries] == sorted(entry.tt_jd for entry in entries)
    # Dans l'ordre du temps, les signes se suivent dans l'ordre du zodiaque, à une rotation près.
    names = [entry.sign_id for entry in entries]
    pivot = names.index(boundaries.EXPECTED_ORDER[0])
    assert tuple(names[pivot:] + names[:pivot]) == boundaries.EXPECTED_ORDER


@pytest.mark.donnees
def test_fr_06_each_entry_is_on_its_boundary() -> None:
    """Résidu angulaire contrôlé, et frontière qui est bien le début du signe."""
    zodiac = load_canonical()
    starts = {sign.sign_id: sign.start_deg for sign in zodiac.signs}
    chain = load_ephemeris()
    for entry in calendar().entries:
        assert entry.boundary_deg == starts[entry.sign_id]
        assert abs(entry.residual_deg) < passages.RESIDUAL_TOLERANCE_DEG
        longitude = chain.sun_longitude(entry.tt_jd)
        assert abs(signed_wrap(longitude - entry.boundary_deg)) < passages.RESIDUAL_TOLERANCE_DEG


@pytest.mark.donnees
def test_fr_06_one_second_before_and_after_the_sun_changes_sign() -> None:
    """Annexe D2, étape 7 : le Soleil appartient au signe i pour t ∈ [tᵢ, tᵢ₊₁[."""
    zodiac = load_canonical()
    chain = load_ephemeris()
    names = [sign.sign_id for sign in zodiac.signs]
    for entry in calendar().entries:
        before = zodiac.classify(chain.sun_longitude(entry.tt_jd - SECOND)).sign_id
        after = zodiac.classify(chain.sun_longitude(entry.tt_jd + SECOND)).sign_id
        assert after == entry.sign_id
        assert before == names[names.index(entry.sign_id) - 1]


@pytest.mark.donnees
def test_fr_06_calendar_is_reproducible() -> None:
    assert passages.sun_entries(2026) == calendar()


@pytest.mark.donnees
@pytest.mark.parametrize("year", [1850, 1900, 1972, 2000, 2025, 2027, 2050, 2149])
def test_fr_06_other_years_also_have_thirteen_entries(year: int) -> None:
    entries = passages.sun_entries(year).entries
    assert len(entries) == 13
    assert len({entry.sign_id for entry in entries}) == 13


@pytest.mark.donnees
def test_fr_06_entries_shift_from_year_to_year() -> None:
    """Pourquoi une liste fixe de dates serait fausse (PRD § 5, alternatives écartées)."""
    first = {entry.sign_id: entry.instant_utc for entry in calendar(2026).entries}
    second = {entry.sign_id: entry.instant_utc for entry in calendar(2027).entries}
    for sign_id, moment in first.items():
        same_day_next_year = moment.replace(year=2027)
        shift = abs((second[sign_id] - same_day_next_year).total_seconds())
        assert 3600.0 < shift < 86400.0  # quelques heures, pas zéro


@pytest.mark.donnees
def test_fr_06_time_scale_and_future_instants_are_flagged() -> None:
    """Décision 0010 et PRD § 7 : échelle indiquée, instants futurs « conditionnels »."""
    assert {entry.time_scale for entry in passages.sun_entries(1900).entries} == {"ut1_before_1972"}
    assert {entry.time_scale for entry in calendar().entries} == {"utc"}
    assert all(not entry.conditional for entry in passages.sun_entries(2000).entries)
    assert all(entry.conditional for entry in passages.sun_entries(2100).entries)


@pytest.mark.donnees
@pytest.mark.parametrize("year", [1849, 2150])
def test_fr_06_year_outside_the_ephemeris_gives_an_explicit_message(year: int) -> None:
    """Jeu F6 : DE440s ne couvre ni tout 1849 ni tout 2150 ; aucun calendrier partiel."""
    with pytest.raises(OutOfEphemerisRange, match="DE440s"):
        passages.sun_entries(year)


@pytest.mark.donnees
def test_fr_06_another_display_timezone_keeps_the_same_instants() -> None:
    other = passages.sun_entries(2026, "America/Montreal")
    assert [e.tt_jd for e in other.entries] == [e.tt_jd for e in calendar().entries]
    assert all(str(e.instant_local.tzinfo) == "America/Montreal" for e in other.entries)


# --- Constats de la relecture du 15/11/2026 ------------------------------------------------


class LinearChain:
    """Chaîne synthétique : un astre à vitesse constante, pour éprouver la recherche des passages
    sans éphéméride. L'année 2026 commence au jour 1000."""

    def __init__(self, rate_deg_per_day: float, longitude_at_start: float) -> None:
        self.rate, self.origin = rate_deg_per_day, longitude_at_start

    def instant(self, moment: datetime):  # type: ignore[no-untyped-def]
        from moteur.positions import Instant

        days = (moment - datetime(2026, 1, 1, tzinfo=UTC)).total_seconds() / 86400.0
        return Instant(1000.0 + days, "utc", False)

    def utc_datetime(self, tt_jd: float) -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=tt_jd - 1000.0)

    def sun_longitude(self, tt_jd: float) -> float:
        return (self.origin + self.rate * (tt_jd - 1000.0)) % 360.0

    def is_conditional(self, tt_jd: float) -> bool:
        return False

    def manifest(self) -> dict[str, object]:
        return {
            "ephemeris": "synthetic",
            "ephemeris_sha256": None,
            "observer": "geocentric",
            "position_type": "astrometric",
            "time_data": "synthetic",
            "time_data_end_utc": None,
            "time_data_last_leap_second_tai_minus_utc": None,
            "time_scale_policy": "synthetic",
        }


def synthetic_zodiac():  # type: ignore[no-untyped-def]
    from moteur.classification import Zodiac

    boundaries_ = [("a", 20.0), ("b", 100.0), ("c", 117.0), ("d", 200.0), ("e", 350.0)]
    return Zodiac.from_boundaries(boundaries_, expected_count=None)


def test_fr_06_a_crossing_exactly_on_a_grid_day_is_counted_once() -> None:
    """Astre synthétique à 1° par jour, à 99° au 1ᵉʳ janvier : il est exactement sur la frontière
    de 100° un jour de grille. La même valeur ferme une paire et ouvre la suivante."""
    chain = LinearChain(rate_deg_per_day=1.0, longitude_at_start=99.0)
    result = passages.sun_entries(2026, ephemeris=chain, zodiac=synthetic_zodiac())  # type: ignore[arg-type]
    near_first_day = [entry for entry in result.entries if abs(entry.tt_jd - 1001.0) < 0.5]
    assert [entry.sign_id for entry in near_first_day] == ["b"]
    assert abs(near_first_day[0].tt_jd - 1001.0) < passages.BRENT_TOLERANCE_SECONDS * SECOND
    assert result.data_status == "synthetic"  # découpage qui ne vient pas des fichiers générés


def test_fr_06_calculation_stops_if_the_body_does_not_move_forward() -> None:
    chain = LinearChain(rate_deg_per_day=-1.0, longitude_at_start=99.0)
    with pytest.raises(passages.PassageError, match="progression"):
        passages.sun_entries(2026, ephemeris=chain, zodiac=synthetic_zodiac())  # type: ignore[arg-type]


@pytest.mark.donnees
def test_fr_06_calendar_carries_its_manifest() -> None:
    """PRD § 7, reproductibilité : le calendrier porte son manifeste, sans empreinte de saisie."""
    manifest = calendar().manifest
    assert manifest["model_id"] and manifest["calculation_engine_version"]
    assert len(manifest["ephemeris_id_and_hash"]["sha256"]) == 64  # type: ignore[index]
    assert len(manifest["boundary_model_id_and_hash"]["boundaries_file_sha256"]) == 64  # type: ignore[index]
    assert manifest["timezone_database_version"]
    assert manifest["chart_input_hash"] is None
    assert manifest["data_status"] == "candidate"
    assert calendar().timezone_caveat is None
    assert passages.sun_entries(1900).timezone_caveat == "zone_history_may_be_merged_before_1970"


@pytest.mark.donnees
def test_fr_06_entries_agree_with_the_archived_horizons_vectors() -> None:
    """Contrôle non circulaire : aux 13 instants du calendrier, le vecteur du Soleil selon JPL
    Horizons (archivé), transformé par R, tombe sur la frontière. Une mauvaise échelle de temps
    ou une position apparente au lieu d'astrométrique ferait échouer ce test."""
    import numpy as np

    from moteur.coordinates import frame_matrix, longitude_latitude_deg
    from scripts import comparer_horizons as h

    archive = h.latest_archive(h.FIXTURES, 2026, "FRAME").read_text(encoding="utf-8")
    vectors = h.parse_vectors(archive, "FRAME")
    timescale = load_ephemeris()._timescale
    matrix = frame_matrix()
    for entry in calendar().entries:
        tdb_jd = float(timescale.tt_jd(entry.tt_jd).tdb)
        jd, vector = min(vectors, key=lambda item: abs(item[0] - tdb_jd))
        assert abs(jd - tdb_jd) * 86400.0 < 0.05  # même instant, à quelques centièmes de seconde
        longitude, _ = longitude_latitude_deg(matrix @ np.asarray(vector))
        assert longitude is not None
        assert abs(signed_wrap(longitude - entry.boundary_deg)) < 1e-6


@pytest.mark.donnees
@pytest.mark.parametrize("year", list(range(1850, 2150, 20)))
def test_fr_06_every_sampled_year_has_thirteen_entries_in_its_own_year(year: int) -> None:
    """Aucune frontière n'est franchie près du 1ᵉʳ janvier : 13 entrées, une par signe, et la date
    à Paris tombe dans la même année que la date UTC."""
    entries = passages.sun_entries(year).entries
    assert len(entries) == 13
    assert len({entry.sign_id for entry in entries}) == 13
    assert all(entry.instant_local.year == year for entry in entries)
