"""FR-01 et FR-04 — saisie de naissance, heure inexistante, heure ambiguë (PRD § 6 ; annexe § B,
D3, E « Statut de l'heure », F « Saisie de naissance »).

FR-01 : étant donné une heure inexistante (passage à l'heure d'été), quand je valide, alors un
message bloquant s'affiche et aucun thème n'est calculé.
FR-04 : étant donné 02:30 le jour du passage à l'heure d'hiver, quand je valide, alors deux
scénarios sont proposés jusqu'à ce que je précise l'occurrence.

Jeu F5 : saisies fictives, fichier marqué `"synthetic": true`.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from moteur import civil_time as t

FIXTURE = Path(__file__).parent / "fixtures" / "births" / "f5-paris-2026.json"
CASES: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]


def birth(case: str, **changes: object) -> t.BirthInput:
    return t.BirthInput.from_record({**CASES[case]["birth"], **changes})


def test_fixture_is_marked_synthetic() -> None:
    assert json.loads(FIXTURE.read_text(encoding="utf-8"))["synthetic"] is True


# --- FR-01 : saisie et heure inexistante ---------------------------------------------------


def test_fr_01_nonexistent_local_time_blocks_the_calculation() -> None:
    """Paris, 29/03/2026 02:30 : l'heure n'existe pas, aucun instant n'est rendu."""
    with pytest.raises(t.NonexistentLocalTime) as raised:
        t.resolve(birth("nonexistent"))
    assert "n'existe pas" in str(raised.value)


def test_fr_01_nonexistent_time_is_never_shifted_silently() -> None:
    """Annexe E : erreur à résoudre, aucune correction silencieuse, même si l'occurrence est donnée."""
    for fold in (0, 1):
        with pytest.raises(t.NonexistentLocalTime):
            t.resolve(birth("nonexistent", fold=fold))


def test_fr_01_error_messages_never_repeat_the_birth_data() -> None:
    """Règle « aucune trace » : ni date, ni heure, ni lieu dans un message d'erreur."""
    with pytest.raises(t.InputError) as raised:
        t.resolve(birth("nonexistent"))
    message = str(raised.value)
    for fragment in ("2026", "03-29", "02:30", "48.85", "2.35", "Paris"):
        assert fragment not in message


def test_fr_01_ordinary_time_gives_one_instant() -> None:
    resolution = t.resolve(birth("ordinary"))
    assert resolution.kind == "unique"
    assert [s.instant_utc for s in resolution.scenarios] == [
        datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    ]
    assert resolution.scenarios[0].utc_offset_seconds == 7200


def test_fr_01_record_fields_are_those_of_the_annex() -> None:
    value = birth("ordinary")
    assert value.date_local == date(2026, 6, 1)
    assert value.time_local == time(12, 0)
    assert value.time_status == "known"
    assert value.time_uncertainty_seconds == 0.0
    assert value.timezone == "Europe/Paris"
    assert value.fold is None
    assert (value.latitude_deg, value.longitude_deg, value.altitude_m) == (48.8566, 2.3522, 35.0)
    assert value.calendar == "proleptic_gregorian"
    assert value.source == "fictional_demonstration"


@pytest.mark.parametrize(
    "changes",
    [
        {"time_status": "approximate"},
        {"time_status": "known", "time_local": None},
        {"time_status": "uncertain", "time_uncertainty_seconds": 0},
        {"time_uncertainty_seconds": -1},
        {"time_uncertainty_seconds": "dix minutes"},
        {"date_local": "29/03/2026"},
        {"date_local": "2026-02-30"},
        {"time_local": "25:00:00"},
        {"fold": 2},
        {"latitude_deg": 91.0},
        {"longitude_deg": -181.0},
        {"latitude_deg": None},
        {"calendar": "julian"},
        {"timezone": ""},
    ],
)
def test_fr_01_invalid_record_is_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(t.InputError):
        birth("ordinary", **changes)


@pytest.mark.parametrize("zone", ["UTC+1", "+01:00", "GMT+1", "CET", "Europe/Atlantide", "../UTC"])
def test_fr_01_timezone_must_be_a_historical_iana_identifier(zone: str) -> None:
    """Annexe B : identifiant historique IANA, jamais un simple « UTC+1 »."""
    with pytest.raises(t.InputError, match="fuseau"):
        t.resolve(birth("ordinary", timezone=zone))


@pytest.mark.parametrize("year", [1848, 2151])
def test_fr_01_date_outside_the_ephemeris_gives_an_explicit_message(year: int) -> None:
    """Jeu F6 : date hors de DE440s (avant 1849, après 2150)."""
    with pytest.raises(t.InputError, match="1849.*2150"):
        birth("ordinary", date_local=f"{year}-06-01")


def test_fr_01_time_zone_data_comes_from_the_bundled_package() -> None:
    """La version annoncée au manifeste est celle des données réellement utilisées."""
    import tzdata

    assert t.timezone_database_version() == tzdata.IANA_VERSION
    assert t.load_zone("Europe/Paris").key == "Europe/Paris"


def test_fr_01_historical_offsets_are_used() -> None:
    """Fuseau historique : à Paris en 1900, l'heure légale n'est pas UTC+1."""
    resolution = t.resolve(birth("ordinary", date_local="1900-06-01"))
    assert resolution.scenarios[0].utc_offset_seconds == 561  # heure locale de Paris, 9 min 21 s


# --- FR-04 : heure ambiguë -----------------------------------------------------------------


def test_fr_04_ambiguous_local_time_gives_two_scenarios() -> None:
    """Paris, 25/10/2026 02:30 : deux instants possibles tant que l'occurrence n'est pas précisée."""
    resolution = t.resolve(birth("ambiguous"))
    assert resolution.kind == "ambiguous"
    assert [(s.fold, s.instant_utc) for s in resolution.scenarios] == [
        (0, datetime(2026, 10, 25, 0, 30, tzinfo=UTC)),
        (1, datetime(2026, 10, 25, 1, 30, tzinfo=UTC)),
    ]
    assert [s.utc_offset_seconds for s in resolution.scenarios] == [7200, 3600]


@pytest.mark.parametrize(("fold", "hour"), [(0, 0), (1, 1)])
def test_fr_04_choosing_the_occurrence_leaves_one_scenario(fold: int, hour: int) -> None:
    resolution = t.resolve(birth("ambiguous", fold=fold))
    assert resolution.kind == "ambiguous"  # l'heure reste ambiguë ; l'occurrence est choisie
    assert [(s.fold, s.instant_utc) for s in resolution.scenarios] == [
        (fold, datetime(2026, 10, 25, hour, 30, tzinfo=UTC))
    ]


def test_fr_04_fold_is_ignored_for_an_unambiguous_time() -> None:
    assert t.resolve(birth("ordinary", fold=1)) == t.resolve(birth("ordinary"))


def test_fr_04_both_scenarios_are_kept_in_order_of_time() -> None:
    first, second = t.resolve(birth("ambiguous")).scenarios
    assert first.instant_utc < second.instant_utc
    assert (second.instant_utc - first.instant_utc).total_seconds() == 3600.0


# --- Constats de la relecture du 15/11/2026 ------------------------------------------------


@pytest.mark.parametrize("zone", ["etc/GMT+1", "europe/paris", "EUROPE/PARIS", "Etc/GMT-1", "UTC"])
def test_fr_01_timezone_must_match_the_package_list_exactly(zone: str) -> None:
    """Casse comprise : un disque insensible à la casse ne doit pas laisser passer « europe/paris »."""
    with pytest.raises(t.InputError, match="fuseau"):
        birth("ordinary", timezone=zone)


def test_fr_01_timezone_is_checked_even_when_the_time_is_unknown() -> None:
    with pytest.raises(t.InputError, match="fuseau"):
        birth("ordinary", time_status="unknown", time_local=None, timezone="UTC+1")


def test_fr_01_time_given_with_unknown_status_is_ignored() -> None:
    assert birth("ordinary", time_status="unknown").time_local is None


@pytest.mark.parametrize(
    "changes",
    [
        {"date_local": "20260601"},
        {"date_local": "2026-W23-1"},
        {"time_local": "12"},
        {"time_local": "T12:00"},
        {"time_local": "12:00:00+02:00"},
        {"fold": 1.0},
        {"fold": True},
        {"latitude_deg": 10**400},
        {"time_uncertainty_seconds": float("nan")},
    ],
)
def test_fr_01_loosely_formatted_values_are_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(t.InputError):
        birth("ordinary", **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"time_status": "approximate"},
        {"date_local": "2026-02-30"},
        {"time_local": "25:00:00"},
        {"latitude_deg": 91.0},
        {"timezone": "Europe/Atlantide"},
        {"calendar": "julian"},
        {"date_local": "1848-06-01"},
    ],
)
def test_fr_01_no_input_error_repeats_the_birth_data(changes: dict[str, object]) -> None:
    """Règle « aucune trace », sur chaque refus de saisie et non sur un seul."""
    with pytest.raises(t.InputError) as raised:
        birth("ordinary", **changes)
    message = str(raised.value)
    for fragment in ("2026", "06-01", "12:00", "48.85", "2.35", "Paris", "Atlantide", "91"):
        assert fragment not in message


def test_fr_01_result_objects_show_no_personal_data() -> None:
    resolution = t.resolve(birth("ordinary"))
    for value in (birth("ordinary"), resolution, resolution.scenarios[0]):
        assert "2026" not in repr(value) and "masquées" in repr(value)


def local(zone: str, day: str, clock: str, fold: int | None = None) -> t.Resolution:
    return t.resolve_local_time(
        date.fromisoformat(day), time.fromisoformat(clock), t.load_zone(zone), fold
    )


def test_fr_01_edges_of_the_nonexistent_window_in_paris() -> None:
    """Le 29/03/2026 à Paris, 02:00:00 à 02:59:59 n'existent pas ; 01:59:59 et 03:00:00, si."""
    assert local("Europe/Paris", "2026-03-29", "01:59:59").kind == "unique"
    for clock in ("02:00:00", "02:59:59"):
        with pytest.raises(t.NonexistentLocalTime):
            local("Europe/Paris", "2026-03-29", clock)
    assert local("Europe/Paris", "2026-03-29", "03:00:00").kind == "unique"


def test_fr_04_edges_of_the_ambiguous_window_in_paris() -> None:
    """Le 25/10/2026 à Paris, 02:00:00 à 02:59:59 arrivent deux fois ; 01:59:59 et 03:00:00, non."""
    assert local("Europe/Paris", "2026-10-25", "01:59:59").kind == "unique"
    for clock in ("02:00:00", "02:59:59"):
        assert len(local("Europe/Paris", "2026-10-25", clock).scenarios) == 2
    assert local("Europe/Paris", "2026-10-25", "03:00:00").kind == "unique"


def test_fr_04_half_hour_transition() -> None:
    """Lord Howe avance et recule d'une demi-heure : la fenêtre ambiguë dure 30 minutes."""
    zone = t.load_zone("Australia/Lord_Howe")
    ambiguous = [
        minute
        for minute in range(0, 24 * 60, 5)
        if t.resolve_local_time(date(2026, 4, 5), time(minute // 60, minute % 60), zone).kind
        == "ambiguous"
    ]
    assert len(ambiguous) == 6  # six pas de cinq minutes
    first, second = t.resolve_local_time(
        date(2026, 4, 5), time(ambiguous[0] // 60, ambiguous[0] % 60), zone
    ).scenarios
    assert (second.instant_utc - first.instant_utc).total_seconds() == 1800.0


def test_fr_04_change_of_zone_without_summer_time() -> None:
    """Paris, 1911 : passage du temps local à l'heure de Greenwich, recul de 9 min 21 s."""
    zone = t.load_zone("Europe/Paris")
    kinds = {
        t.resolve_local_time(date(1911, 3, 10), time(23, minute, 30), zone).kind
        for minute in range(60)
    } | {
        t.resolve_local_time(date(1911, 3, 11), time(0, minute, 30), zone).kind
        for minute in range(60)
    }
    assert kinds == {"unique", "ambiguous"}


def test_fr_01_whole_skipped_day() -> None:
    """Samoa, 30/12/2011 : la journée entière n'a pas existé."""
    for clock in ("00:00:00", "12:00:00", "23:59:59"):
        with pytest.raises(t.NonexistentLocalTime):
            local("Pacific/Apia", "2011-12-30", clock)
    assert local("Pacific/Apia", "2011-12-31", "12:00:00").kind == "unique"


ZONES = ["Europe/Paris", "Australia/Lord_Howe", "Pacific/Apia", "America/Santiago", "Asia/Kolkata"]


@given(
    st.sampled_from(ZONES),
    st.datetimes(min_value=datetime(1900, 1, 1), max_value=datetime(2100, 1, 1)),
)
def test_fr_04_every_instant_is_found_again_from_its_local_time(
    zone: str, moment: datetime
) -> None:
    """Tout instant, converti en heure locale puis résolu, se retrouve parmi les scénarios."""
    tz = t.load_zone(zone)
    instant = moment.replace(microsecond=0, tzinfo=UTC)
    shown = instant.astimezone(tz)
    resolution = t.resolve_local_time(shown.date(), shown.time(), tz)
    assert len(resolution.scenarios) in (1, 2)
    assert instant in [scenario.instant_utc for scenario in resolution.scenarios]
    if len(resolution.scenarios) == 2:
        assert [s.fold for s in resolution.scenarios] == [0, 1]
        chosen = t.resolve_local_time(shown.date(), shown.time(), tz, shown.fold)
        assert [s.instant_utc for s in chosen.scenarios] == [instant]


def test_decision_0011_history_caveat_before_1970() -> None:
    assert t.zone_history_caveat(date(1969, 12, 31)) == "zone_history_may_be_merged_before_1970"
    assert t.zone_history_caveat(date(1970, 1, 1)) is None


def test_decision_0011_merged_history_is_observed_not_assumed() -> None:
    """Constat de la décision 0011 : avant 1970, le paquet rend pour Amsterdam le décalage de
    Bruxelles. Si ce test échoue un jour, c'est que le paquet a changé : revoir la décision."""
    noon = datetime(1930, 6, 1, 12)
    amsterdam = noon.replace(tzinfo=t.load_zone("Europe/Amsterdam")).utcoffset()
    brussels = noon.replace(tzinfo=t.load_zone("Europe/Brussels")).utcoffset()
    assert amsterdam == brussels
