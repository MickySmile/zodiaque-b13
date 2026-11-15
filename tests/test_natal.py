"""FR-03 et FR-05 — signe solaire avec heure incertaine ou inconnue (PRD § 6 ; annexe § D3, E, F).

FR-03 : étant donné une heure à ±10 min dont l'intervalle contient un franchissement, quand le
thème s'affiche, alors les deux signes sont présentés comme possibilités, sans probabilité.
FR-05 : étant donné « heure inconnue », quand le thème s'affiche, alors aucun Ascendant ni aucune
maison n'apparaît et le titre est « carte de référence à midi ».

Toutes les naissances de ce fichier sont fictives : elles sont fabriquées à partir des instants
de franchissement que le moteur calcule lui-même pour 2026, jamais à partir de dates réelles.
Aucun instant astronomique n'est écrit à la main. Les tests marqués `donnees` exigent DE440s.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from functools import cache
from zoneinfo import ZoneInfo

import pytest

from moteur import MODEL_ID, natal, passages
from moteur.civil_time import BirthInput, InputError, load_zone
from moteur.classification import load_canonical
from moteur.positions import OutOfEphemerisRange

PARIS = "Europe/Paris"


@cache
def entries() -> tuple[passages.SunEntry, ...]:
    return passages.sun_entries(2026).entries


def previous_sign(sign_id: str) -> str:
    names = [sign.sign_id for sign in load_canonical().signs]
    return names[names.index(sign_id) - 1]


def fictional_birth(
    moment: datetime, status: str = "known", uncertainty: float = 0.0, **changes: object
) -> BirthInput:
    """Saisie fictive dont l'heure locale à Paris correspond à l'instant donné, à la seconde."""
    local = moment.astimezone(load_zone(PARIS)).replace(microsecond=0)
    record: dict[str, object] = {
        "date_local": local.date().isoformat(),
        "time_local": None if status == "unknown" else local.time().isoformat(),
        "time_status": status,
        "time_uncertainty_seconds": uncertainty,
        "timezone": PARIS,
        "fold": None,
        "latitude_deg": 48.8566,
        "longitude_deg": 2.3522,
        "altitude_m": 35,
        "calendar": "proleptic_gregorian",
        "source": "fictional_demonstration",
    }
    return BirthInput.from_record({**record, **changes})


# --- Journée locale (sans éphéméride) ------------------------------------------------------


@pytest.mark.parametrize(
    ("day", "hours"),
    [(date(2026, 6, 1), 24), (date(2026, 3, 29), 23), (date(2026, 10, 25), 25)],
)
def test_fr_05_local_day_lasts_23_24_or_25_hours(day: date, hours: int) -> None:
    zone = load_zone(PARIS)
    start, end = natal.local_day_bounds(day, zone)
    assert end - start == timedelta(hours=hours)
    assert start.astimezone(zone).date() == day
    assert (start - timedelta(seconds=1)).astimezone(zone).date() == day - timedelta(days=1)
    assert end.astimezone(zone).date() == day + timedelta(days=1)


def test_fr_05_local_day_is_found_even_when_midnight_does_not_exist() -> None:
    """À Santiago du Chili, l'heure d'été commence à minuit : 00:00 n'existe pas ce jour-là."""
    zone = load_zone("America/Santiago")
    day = date(2026, 9, 6)
    start, end = natal.local_day_bounds(day, zone)
    assert start.astimezone(zone).date() == day
    assert (start - timedelta(seconds=1)).astimezone(zone).date() < day
    assert start.astimezone(zone).hour == 1  # la journée commence à 01:00
    assert end - start == timedelta(hours=23)


def test_fr_05_title_is_the_imposed_one() -> None:
    assert natal.REFERENCE_TITLE == "carte de référence à midi"


# --- FR-05 : heure inconnue ----------------------------------------------------------------


@pytest.mark.donnees
def test_fr_05_unknown_time_gives_the_noon_reference_chart_without_angles() -> None:
    quiet = entries()[0].instant_utc + timedelta(days=5)  # loin de toute frontière
    chart = natal.sun_sign_chart(fictional_birth(quiet, "unknown"))
    assert chart.title == "carte de référence à midi"
    assert chart.local_time_kind == "unknown"
    assert chart.ascendant is None and chart.houses is None
    assert chart.ascendant_status == chart.houses_status == "undefined_without_birth_time"
    (result,) = chart.scenarios
    local = result.instant_utc.astimezone(ZoneInfo(PARIS))
    assert (local.hour, local.minute, local.second) == (12, 0, 0)
    assert result.status == "certain"
    assert result.possible_signs == (result.placement.sign_id,)


@pytest.mark.donnees
def test_fr_05_unknown_time_covers_the_whole_local_day() -> None:
    quiet = entries()[0].instant_utc + timedelta(days=5)
    birth = fictional_birth(quiet, "unknown")
    (result,) = natal.sun_sign_chart(birth).scenarios
    assert result.interval_utc == natal.local_day_bounds(birth.date_local, load_zone(PARIS))


@pytest.mark.donnees
def test_fr_05_unknown_time_on_a_day_of_entry_gives_two_possible_signs() -> None:
    """Le jour où le Soleil change de signe, une heure inconnue laisse deux signes possibles."""
    for entry in entries():
        chart = natal.sun_sign_chart(fictional_birth(entry.instant_utc, "unknown"))
        (result,) = chart.scenarios
        assert result.status == "possible"
        assert result.possible_signs == (previous_sign(entry.sign_id), entry.sign_id)
        (transition,) = result.transitions
        assert abs((transition.instant_utc - entry.instant_utc).total_seconds()) < 0.05
        assert transition.boundary_deg == entry.boundary_deg


@pytest.mark.donnees
def test_fr_05_record_has_no_ascendant_no_houses_and_null_stays_null() -> None:
    quiet = entries()[0].instant_utc + timedelta(days=5)
    record = natal.as_record(natal.sun_sign_chart(fictional_birth(quiet, "unknown")))
    assert record["title"] == "carte de référence à midi"
    assert record["ascendant"] is None and record["houses"] is None
    json.dumps(record)  # sérialisable tel quel


# --- FR-03 : heure incertaine --------------------------------------------------------------


@pytest.mark.donnees
def test_fr_03_ten_minutes_around_a_crossing_give_two_possible_signs() -> None:
    """Jeu F4 : heure à ±10 min qui chevauche une frontière. Vrai pour les 13 frontières."""
    for entry in entries():
        birth = fictional_birth(entry.instant_utc + timedelta(minutes=3), "uncertain", 600)
        (result,) = natal.sun_sign_chart(birth).scenarios
        assert result.status == "possible"
        assert result.possible_signs == (previous_sign(entry.sign_id), entry.sign_id)
        (transition,) = result.transitions
        assert (transition.from_sign, transition.to_sign) == result.possible_signs
        assert abs((transition.instant_utc - entry.instant_utc).total_seconds()) < 0.05
        assert result.interval_utc is not None
        assert result.interval_utc[0] < transition.instant_utc < result.interval_utc[1]


@pytest.mark.donnees
def test_fr_03_possible_signs_come_without_any_probability() -> None:
    entry = entries()[3]
    birth = fictional_birth(entry.instant_utc + timedelta(minutes=3), "uncertain", 600)
    record = natal.as_record(natal.sun_sign_chart(birth))
    (scenario,) = record["scenarios"]  # type: ignore[misc]
    assert scenario["uncertainty"]["input_probability_distribution"] is None
    # Aucun des deux signes n'est avancé à la place de l'autre.
    assert scenario["classification"]["sign_id"] is None
    assert scenario["classification"]["degrees_in_sign"] is None
    assert scenario["classification"]["status"] == "possible"
    assert len(scenario["classification"]["possible_signs"]) == 2
    text = json.dumps(record).lower()
    assert 'probability": 0' not in text and "likelihood" not in text and "percent" not in text


@pytest.mark.donnees
def test_fr_03_interval_away_from_any_boundary_gives_one_certain_sign() -> None:
    entry = entries()[3]
    birth = fictional_birth(entry.instant_utc + timedelta(days=2), "uncertain", 600)
    (result,) = natal.sun_sign_chart(birth).scenarios
    assert result.status == "certain"
    assert result.possible_signs == (entry.sign_id,)
    assert result.transitions == ()
    record = natal.as_record(natal.sun_sign_chart(birth))
    assert record["scenarios"][0]["classification"]["sign_id"] == entry.sign_id  # type: ignore[index]


@pytest.mark.donnees
@pytest.mark.parametrize(("offset_minutes", "expected"), [(-11, 1), (-9, 2), (9, 2), (11, 1)])
def test_fr_03_only_a_crossing_inside_the_interval_counts(
    offset_minutes: int, expected: int
) -> None:
    """À ±10 min : un franchissement à 9 min est dans l'intervalle, à 11 min il n'y est pas."""
    entry = entries()[5]
    birth = fictional_birth(entry.instant_utc + timedelta(minutes=offset_minutes), "uncertain", 600)
    (result,) = natal.sun_sign_chart(birth).scenarios
    assert len(result.possible_signs) == expected


@pytest.mark.donnees
def test_fr_03_known_time_is_classified_at_its_instant() -> None:
    """Heure connue : pas d'intervalle. Une minute avant l'entrée, le signe précédent."""
    for entry in entries():
        before = natal.sun_sign_chart(fictional_birth(entry.instant_utc - timedelta(minutes=1)))
        after = natal.sun_sign_chart(fictional_birth(entry.instant_utc + timedelta(minutes=1)))
        assert before.scenarios[0].possible_signs == (previous_sign(entry.sign_id),)
        assert after.scenarios[0].possible_signs == (entry.sign_id,)
        assert before.scenarios[0].interval_utc is None
        assert before.scenarios[0].status == after.scenarios[0].status == "certain"


class LinearBody:
    """Astre synthétique à vitesse constante : remplace l'éphéméride pour éprouver le parcours."""

    def __init__(self, rate_deg_per_day: float, origin_deg: float) -> None:
        self.rate, self.origin = rate_deg_per_day, origin_deg

    def sun_longitude(self, tt_jd: float) -> float:
        return (self.origin + self.rate * tt_jd) % 360.0

    def utc_datetime(self, tt_jd: float) -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=tt_jd)


SYNTHETIC_ZODIAC = [("a", 20.0), ("b", 100.0), ("c", 103.0), ("d", 200.0), ("e", 350.0)]


def test_fr_03_whole_interval_is_scanned_not_only_its_ends() -> None:
    """Annexe D3 : ne jamais calculer seulement les deux extrémités. Un astre synthétique rapide
    traverse en dix minutes un signe synthétique étroit : les extrémités seules le manqueraient."""
    from moteur.classification import Zodiac

    zodiac = Zodiac.from_boundaries(SYNTHETIC_ZODIAC, expected_count=None)
    body = LinearBody(rate_deg_per_day=1440.0, origin_deg=98.0)  # un degré par minute
    possible, transitions, ends = natal._scan(body, zodiac, 0.0, 10.0 / 1440.0)  # type: ignore[arg-type]
    assert possible == ("a", "b", "c")  # le signe « b », large de 3°, est traversé en entier
    assert [(t.from_sign, t.to_sign) for t in transitions] == [("a", "b"), ("b", "c")]
    assert zodiac.classify(ends[0]).sign_id == "a" and zodiac.classify(ends[1]).sign_id == "c"


def test_fr_03_scan_follows_an_interval_that_crosses_zero() -> None:
    """Règle « signe traversant 0° » : l'intervalle de longitude peut commencer après sa fin."""
    from moteur.classification import Zodiac

    zodiac = Zodiac.from_boundaries(SYNTHETIC_ZODIAC, expected_count=None)
    body = LinearBody(rate_deg_per_day=1440.0, origin_deg=355.0)
    possible, transitions, (first, last) = natal._scan(body, zodiac, 0.0, 10.0 / 1440.0)  # type: ignore[arg-type]
    assert possible == ("e",) and transitions == ()
    assert first > last  # 355° puis 5° : l'intervalle franchit 0°


def test_fr_03_scan_stops_if_the_body_moves_backwards() -> None:
    """Le parcours suppose que l'astre avance ; sinon un aller-retour pourrait lui échapper."""
    from moteur.classification import ClassificationError, Zodiac

    zodiac = Zodiac.from_boundaries(SYNTHETIC_ZODIAC, expected_count=None)
    body = LinearBody(rate_deg_per_day=-1440.0, origin_deg=98.0)
    with pytest.raises(ClassificationError, match="progression"):
        natal._scan(body, zodiac, 0.0, 10.0 / 1440.0)  # type: ignore[arg-type]


def test_fr_03_scan_refuses_an_interval_too_long_for_its_step() -> None:
    from moteur.classification import ClassificationError, Zodiac

    zodiac = Zodiac.from_boundaries(SYNTHETIC_ZODIAC, expected_count=None)
    with pytest.raises(ClassificationError, match="trop long"):
        natal._scan(LinearBody(1.0, 98.0), zodiac, 0.0, 3.0)  # type: ignore[arg-type]


def test_fr_03_uncertainty_above_twelve_hours_is_refused() -> None:
    """Au-delà de douze heures de part et d'autre, c'est une heure inconnue."""
    moment = datetime(2026, 6, 1, 10, tzinfo=UTC)
    fictional_birth(moment, "uncertain", 12 * 3600)
    with pytest.raises(InputError, match="douze heures"):
        fictional_birth(moment, "uncertain", 12 * 3600 + 1)


@pytest.mark.donnees
def test_fr_03_uncertainty_is_taken_in_absolute_time() -> None:
    """Lecture retenue (docstring de natal.py) : l'instant plus ou moins la durée, même près d'un
    changement d'heure. Paris, 25/10/2026, 03:05 ± 10 min : de 01:55 à 02:15 UTC."""
    birth = fictional_birth(datetime(2026, 10, 25, 2, 5, tzinfo=UTC), "uncertain", 600)
    (result,) = natal.sun_sign_chart(birth).scenarios
    assert result.interval_utc == (
        datetime(2026, 10, 25, 1, 55, tzinfo=UTC),
        datetime(2026, 10, 25, 2, 15, tzinfo=UTC),
    )


def test_fr_05_local_day_with_an_offset_in_seconds() -> None:
    """Paris en 1900 : temps local, 9 min 21 s d'avance sur Greenwich."""
    zone = load_zone(PARIS)
    start, end = natal.local_day_bounds(date(1900, 6, 1), zone)
    assert end - start == timedelta(hours=24)
    assert start == datetime(1900, 5, 31, 23, 50, 39, tzinfo=UTC)


@pytest.mark.donnees
def test_fr_05_unknown_time_on_a_skipped_day_is_an_explicit_error() -> None:
    """Samoa, 30/12/2011 : la journée n'a pas existé. Message adapté à une heure inconnue."""
    birth = fictional_birth(
        datetime(2026, 6, 1, 10, tzinfo=UTC),
        "unknown",
        date_local="2011-12-30",
        timezone="Pacific/Apia",
    )
    with pytest.raises(InputError, match="journée a été sautée") as raised:
        natal.sun_sign_chart(birth)
    assert "2011" not in str(raised.value) and "Apia" not in str(raised.value)


@pytest.mark.donnees
def test_fr_03_record_names_its_model_and_keeps_interpretation_empty() -> None:
    """Annexe F, enregistrement traçable : modèle, convention de bornes, statut de validation."""
    birth = fictional_birth(entries()[2].instant_utc + timedelta(days=1))
    record = natal.as_record(natal.sun_sign_chart(birth))
    model = record["model"]
    assert model["id"] == MODEL_ID  # type: ignore[index]
    assert model["interval_policy"] == "start_included_end_excluded"  # type: ignore[index]
    assert model["boundary_source_equinox"] == "B1875"  # type: ignore[index]
    assert model["validation_status"] == "not_validated"  # type: ignore[index]  # G1 fermée
    # Empreinte de la grille des frontières, pas un objet : 64 caractères hexadécimaux.
    assert isinstance(model["boundary_sha256"], str)  # type: ignore[index]
    assert len(model["boundary_sha256"]) == 64  # type: ignore[index]
    assert model["boundary_sha256"] == natal.load_canonical().provenance.boundary_source_sha256  # type: ignore[index, union-attr]
    scenario = record["scenarios"][0]  # type: ignore[index]
    assert scenario["interpretation"] == {
        "ruleset_id": None,
        "epistemic_status": "symbolic_proposal",
        "text": None,
    }
    assert scenario["utc_offset_seconds"] in (3600, 7200)


# --- FR-04 avec les positions : heure ambiguë ----------------------------------------------


@pytest.mark.donnees
def test_fr_04_ambiguous_time_gives_one_result_per_occurrence() -> None:
    birth = BirthInput.from_record(
        {
            "date_local": "2026-10-25",
            "time_local": "02:30:00",
            "time_status": "uncertain",
            "time_uncertainty_seconds": 600,
            "timezone": PARIS,
            "fold": None,
            "latitude_deg": 48.8566,
            "longitude_deg": 2.3522,
            "calendar": "proleptic_gregorian",
            "source": "fictional_demonstration",
        }
    )
    chart = natal.sun_sign_chart(birth)
    assert chart.local_time_kind == "ambiguous"
    first, second = chart.scenarios
    assert (first.fold, second.fold) == (0, 1)
    assert second.instant_utc - first.instant_utc == timedelta(hours=1)
    assert second.longitude_deg > first.longitude_deg  # une heure de mouvement solaire


# --- Manifeste, statut, plage --------------------------------------------------------------


@pytest.mark.donnees
def test_fr_03_every_result_carries_its_manifest() -> None:
    """PRD § 7, reproductibilité : moteur, éphéméride et empreinte, données de temps, base des
    fuseaux, modèle de frontières et empreinte, versions des règles, empreinte de la saisie."""
    birth = fictional_birth(entries()[2].instant_utc + timedelta(days=1), "uncertain", 600)
    manifest = natal.sun_sign_chart(birth).manifest
    assert manifest["model_id"] == MODEL_ID
    assert manifest["calculation_engine_version"]
    assert len(manifest["ephemeris_id_and_hash"]["sha256"]) == 64  # type: ignore[index]
    assert len(manifest["boundary_model_id_and_hash"]["boundaries_file_sha256"]) == 64  # type: ignore[index]
    assert len(manifest["boundary_model_id_and_hash"]["boundary_source_sha256"]) == 64  # type: ignore[index]
    assert manifest["timezone_database_version"]
    assert manifest["time_data_version"]
    # Seuil du statut « conditionnel », traçable depuis le résultat.
    assert manifest["time_data_end_utc"] and manifest["time_data_last_leap_second_tai_minus_utc"]
    assert set(manifest["versions"]) == {"skyfield", "numpy", "scipy", "python"}  # type: ignore[call-overload]
    assert manifest["chart_input_hash"] == natal.input_hash(birth)
    assert manifest["data_status"] == "candidate"
    # Pas encore de règles ni de texte : les versions absentes restent nulles, jamais inventées.
    for key in ("symbolic_ruleset_version", "text_generator_version"):
        assert manifest[key] is None


@pytest.mark.donnees
def test_fr_03_same_input_gives_the_same_result_and_the_same_hash() -> None:
    moment = entries()[2].instant_utc + timedelta(minutes=3)
    first = natal.sun_sign_chart(fictional_birth(moment, "uncertain", 600))
    second = natal.sun_sign_chart(fictional_birth(moment, "uncertain", 600))
    assert first == second
    other = natal.sun_sign_chart(fictional_birth(moment, "uncertain", 601))
    assert other.manifest["chart_input_hash"] != first.manifest["chart_input_hash"]


@pytest.mark.donnees
def test_fr_03_manifest_does_not_contain_the_birth_data() -> None:
    """L'empreinte identifie la saisie sans la reproduire."""
    birth = fictional_birth(entries()[2].instant_utc + timedelta(days=1))
    text = json.dumps(natal.sun_sign_chart(birth).manifest)
    assert birth.date_local.isoformat() not in text
    assert "48.8566" not in text and PARIS not in text


def test_birth_input_representation_shows_no_personal_data() -> None:
    birth = fictional_birth(datetime(2026, 6, 1, 10, tzinfo=UTC))
    for text in (repr(birth), str(birth), f"{birth}"):
        assert "2026" not in text and "48.8" not in text and "Paris" not in text


@pytest.mark.donnees
def test_fr_01_date_before_the_ephemeris_gives_an_explicit_message() -> None:
    """Jeu F6 : 1849 est accepté à la saisie, mais DE440s ne commence que le 26 décembre 1849."""
    birth = fictional_birth(datetime(2026, 6, 1, 10, tzinfo=UTC), date_local="1849-06-01")
    with pytest.raises(OutOfEphemerisRange, match="DE440s"):
        natal.sun_sign_chart(birth)


@pytest.mark.donnees
def test_fr_03_time_scale_and_future_are_flagged() -> None:
    """Décision 0010 : temps universel avant 1972 ; PRD § 7 : instants futurs conditionnels."""
    base = datetime(2026, 6, 1, 10, tzinfo=UTC)
    old = natal.sun_sign_chart(fictional_birth(base, date_local="1900-06-01")).scenarios[0]
    recent = natal.sun_sign_chart(fictional_birth(base)).scenarios[0]
    future = natal.sun_sign_chart(fictional_birth(base, date_local="2100-06-01")).scenarios[0]
    assert (old.time_scale, recent.time_scale, future.time_scale) == (
        "ut1_before_1972",
        "utc",
        "utc",
    )
    assert (old.conditional, recent.conditional, future.conditional) == (False, False, True)


@pytest.mark.donnees
def test_decision_0011_result_before_1970_carries_the_timezone_caveat() -> None:
    base = datetime(2026, 6, 1, 10, tzinfo=UTC)
    old = natal.sun_sign_chart(fictional_birth(base, date_local="1930-06-01"))
    recent = natal.sun_sign_chart(fictional_birth(base))
    assert old.timezone_caveat == "zone_history_may_be_merged_before_1970"
    assert recent.timezone_caveat is None
    assert natal.as_record(old)["timezone_caveat"] == old.timezone_caveat


@pytest.mark.donnees
def test_result_objects_show_no_personal_data() -> None:
    """Un résultat porte l'instant de naissance : sa représentation textuelle ne montre rien."""
    entry = entries()[4]
    chart = natal.sun_sign_chart(fictional_birth(entry.instant_utc, "uncertain", 600))
    result = chart.scenarios[0]
    for value in (chart, result, result.transitions[0]):
        assert "masquées" in repr(value)
        assert "2026" not in repr(value) and "246" not in repr(value)


# --- FR-01 au point d'entrée ---------------------------------------------------------------


class UntouchableChain:
    """Chaîne synthétique qui compte ses appels : aucune position ne doit être demandée."""

    def __init__(self) -> None:
        self.calls = 0

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        self.calls += 1
        raise AssertionError(f"la chaîne de positions a été sollicitée : {name}")


def test_fr_01_nonexistent_time_stops_the_sun_sign_chart() -> None:
    """FR-01, au point d'entrée du moteur : heure inexistante, message bloquant, et aucun thème
    n'est calculé. Sans éphéméride : la saisie est refusée avant toute position."""
    from pathlib import Path

    from moteur.civil_time import NonexistentLocalTime
    from moteur.classification import Zodiac

    fixture = Path(__file__).parent / "fixtures" / "births" / "f5-paris-2026.json"
    record = json.loads(fixture.read_text(encoding="utf-8"))["cases"]["nonexistent"]["birth"]
    chain = UntouchableChain()
    zodiac = Zodiac.from_boundaries(SYNTHETIC_ZODIAC, expected_count=None)
    with pytest.raises(NonexistentLocalTime, match="n'existe pas"):
        natal.sun_sign_chart(BirthInput.from_record(record), ephemeris=chain, zodiac=zodiac)  # type: ignore[arg-type]
    assert chain.calls == 0


def test_fr_01_an_existing_time_does_reach_the_positions() -> None:
    """Contre-épreuve du test précédent : pour une heure qui existe, la chaîne est bien sollicitée."""
    from pathlib import Path

    from moteur.classification import Zodiac

    fixture = Path(__file__).parent / "fixtures" / "births" / "f5-paris-2026.json"
    record = json.loads(fixture.read_text(encoding="utf-8"))["cases"]["ambiguous"]["birth"]
    chain = UntouchableChain()
    zodiac = Zodiac.from_boundaries(SYNTHETIC_ZODIAC, expected_count=None)
    with pytest.raises(AssertionError, match="sollicitée"):
        natal.sun_sign_chart(BirthInput.from_record(record), ephemeris=chain, zodiac=zodiac)  # type: ignore[arg-type]
    assert chain.calls == 1
