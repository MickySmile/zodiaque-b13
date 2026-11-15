"""API sans état — routes du MVP : signe, calendrier, frontières, fiches, lieux.

Référence : PRD § 6 (FR-01, FR-03 à FR-06, FR-10, FR-18), § 7 (Reproductibilité,
Confidentialité) ; annexe technique § F (formats) ; règle `.claude/rules/api.md`.

Chaque route rend le manifeste et le statut des données. Aucune saisie ne voyage dans une
adresse, ne revient dans un message d'erreur ni ne passe dans un journal.

Les naissances sont fictives : jeu F5 (`"synthetic": true`), ou instants fabriqués à partir des
franchissements que le moteur calcule lui-même. Les tests marqués `donnees` exigent DE440s ou
GeoNames.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api import main
from moteur import MODEL_ID, natal, passages, places, referentiel
from moteur.boundaries import EXPECTED_ORDER
from moteur.civil_time import BirthInput, load_zone
from moteur.classification import ClassificationError
from moteur.positions import Instant

ROOT = Path(__file__).resolve().parents[1]
F5 = json.loads((ROOT / "tests/fixtures/births/f5-paris-2026.json").read_text(encoding="utf-8"))
GENERATED = json.loads((ROOT / "generes/manifest.json").read_text(encoding="utf-8"))
PARIS = "Europe/Paris"
WITNESS = "SAISIE-TEMOIN-9731"

client = TestClient(main.app)


def birth(case: str, **changes: object) -> dict[str, Any]:
    assert F5["synthetic"] is True
    return {**F5["cases"][case]["birth"], **changes}


def fictional_birth(moment: datetime, **changes: object) -> dict[str, Any]:
    """Saisie fictive dont l'heure locale à Paris correspond à l'instant donné, à la seconde."""
    local = moment.astimezone(load_zone(PARIS)).replace(microsecond=0)
    return birth(
        "ordinary",
        date_local=local.date().isoformat(),
        time_local=local.time().isoformat(),
        **changes,
    )


def error_of(response: Any) -> dict[str, Any]:
    body = response.json()
    assert set(body) == {"error"}
    assert "Traceback" not in response.text
    return dict(body["error"])


@pytest.fixture
def no_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Dossier de données vide : ni éphéméride, ni lieux."""
    monkeypatch.setenv("B13_DONNEES", str(tmp_path))


# --- Frontières et fiches : aucune donnée téléchargée n'est nécessaire -------------------------


def test_fr_18_boundaries_carry_status_and_manifest() -> None:
    response = client.get("/api/boundaries")
    assert response.status_code == 200
    body = response.json()
    assert body["data_status"] == GENERATED["data_status"] == "candidate"
    assert body["status"] == body["data_status"]
    assert body["boundary_validation_status"] == "not_validated"
    assert body["boundary_model_id"] == MODEL_ID
    manifest = body["manifest"]
    assert manifest["model_id"] == MODEL_ID
    assert manifest["data_status"] == "candidate"
    assert (
        manifest["boundary_model_id_and_hash"]["boundaries_file_sha256"]
        == GENERATED["files"]["frontieres.csv"]["sha256"]
    )


def test_fr_10_boundaries_are_the_generated_file_unrounded() -> None:
    with (ROOT / "generes/frontieres.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    signs = client.get("/api/boundaries").json()["signs"]
    assert [sign["sign_id"] for sign in signs] == [row["sign_id"] for row in rows]
    for sign, row in zip(signs, rows, strict=True):
        assert sign["start_deg"] == float(row["start_deg"])
        assert sign["end_deg"] == float(row["end_deg"])
        assert sign["width_deg"] == float(row["width_deg"])
    assert abs(sum(sign["width_deg"] for sign in signs) - 360.0) <= 1e-9


def test_api_thirteen_signs_share_one_shape() -> None:
    signs = client.get("/api/boundaries").json()["signs"]
    assert {sign["sign_id"] for sign in signs} == set(EXPECTED_ORDER)
    shapes = {tuple(sorted(sign)) for sign in signs}
    assert len(shapes) == 1  # le Serpentaire n'a ni champ en plus ni champ en moins
    for sign in signs:
        assert sign["name"]
        assert len(sign["glyph"]) == 1
    assert next(sign for sign in signs if sign["sign_id"] == "Oph")["glyph"] == "⛎"


def test_api_boundaries_invent_no_angle_house_or_aspect() -> None:
    body = client.get("/api/boundaries").json()
    assert body["houses"] is None and body["angles"] is None and body["aspects"] is None
    assert body["bodies"] == []
    assert body["houses_status"] == body["angles_status"] == "not_computed_in_this_version"
    # Aucun Ascendant : la roue ne s'oriente pas sur lui.
    assert body["orientation"] == {
        "anchor": "zero_longitude_left",
        "direction": "counterclockwise",
    }


def test_fr_18_sheets_carry_status_manifest_and_ruleset_version() -> None:
    response = client.get("/api/signs")
    assert response.status_code == 200
    body = response.json()
    assert body["data_status"] == "candidate"
    assert body["manifest"]["model_id"] == MODEL_ID
    version = (ROOT / "referentiel/VERSION").read_text(encoding="utf-8").strip()
    assert body["ruleset_version"] == body["manifest"]["symbolic_ruleset_version"] == version
    recorded = (ROOT / "referentiel/EMPREINTE").read_text(encoding="utf-8").split()
    assert [body["ruleset_version"], body["ruleset_sha256"]] == recorded
    assert set(body["rules"]) == {
        "schema_version",
        "common_rules",
        "general_policy",
        "inherited_categories_decision",
        "historical_heritage",
    }
    assert [sheet["sign_id"] for sheet in body["signs"]] == [
        sign["sign_id"] for sign in client.get("/api/boundaries").json()["signs"]
    ]
    for sheet in body["signs"]:
        # Toute fiche est une proposition symbolique, jamais une mesure.
        assert sheet["sheet_status"] == "transcribed"
        assert sheet["epistemic_status"] == "symbolic_proposal"


def test_fr_15_sheets_are_the_referentiel_unchanged_and_share_one_shape() -> None:
    body = client.get("/api/signs").json()
    symbolic = referentiel.load()
    assert len(body["signs"]) == 13
    assert len({tuple(sorted(sheet)) for sheet in body["signs"]}) == 1
    assert len({tuple(sorted(sheet["sheet"])) for sheet in body["signs"]}) == 1
    for sheet in body["signs"]:
        expected = symbolic.sheet(sheet["sign_id"])
        assert sheet["sheet"] == json.loads(expected.model_dump_json())
        assert sheet["missing"] == list(expected.missing())
        assert sheet["name"] == sheet["sheet"]["name"]
        assert sheet["sheet"]["historical_correspondences"]["active"] is False
    serpentaire = next(sheet for sheet in body["signs"] if sheet["sign_id"] == "Oph")
    assert serpentaire["sheet"]["archetype"]["text"] == "Le praticien qui reste apprenant"
    assert serpentaire["sheet"]["archetype"]["provenance"] == ["C"]
    assert serpentaire["missing"] == []


def test_fr_15_a_rubric_the_prd_leaves_empty_stays_null_with_its_status() -> None:
    body = client.get("/api/signs").json()
    taurus = next(sheet for sheet in body["signs"] if sheet["sign_id"] == "Tau")
    assert taurus["missing"] == ["archetype", "resources", "forbidden_inferences"]
    for name in taurus["missing"]:
        entry = taurus["sheet"][name]
        assert entry["status"] == "missing"
        assert entry["text"] is None and entry["items"] is None and entry["table"] is None


def test_api_invalid_referentiel_gives_no_sheet_and_no_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken() -> None:
        raise referentiel.ReferentielError(f"fiche hors schéma {WITNESS}")

    monkeypatch.setattr(referentiel, "load_canonical", broken)
    response = client.get("/api/signs")
    assert response.status_code == 500
    assert error_of(response)["code"] == "calculation_stopped"
    assert WITNESS not in response.text


def test_api_schema_is_generated_and_lists_the_routes() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {
        "/health",
        "/api/boundaries",
        "/api/signs",
        "/api/sun-sign",
        "/api/calendar/{year}",
        "/api/places/search",
        "/api/places/timezone",
    } <= set(paths)


# --- Confidentialité -----------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/api/sun-sign", "/api/places/search", "/api/places/timezone"])
def test_api_personal_input_never_travels_in_the_url(path: str) -> None:
    operations = client.get("/openapi.json").json()["paths"][path]
    assert set(operations) == {"post"}
    assert operations["post"].get("parameters", []) == []
    assert client.get(path).status_code == 405


def test_api_malformed_request_is_refused_without_echoing_the_input() -> None:
    response = client.post("/api/sun-sign", json=birth("ordinary", unexpected_field=WITNESS))
    assert response.status_code == 422
    error = error_of(response)
    assert error["code"] == "invalid_request"
    # Un nom de champ inconnu est choisi par le client : il n'est pas répété non plus.
    assert error["fields"] == [main.UNKNOWN_FIELD]
    assert "unexpected_field" not in response.text
    assert WITNESS not in response.text
    assert birth("ordinary")["date_local"] not in response.text


def test_api_wrong_type_is_refused_without_echoing_the_input() -> None:
    response = client.post("/api/sun-sign", json=birth("ordinary", date_local=20260601))
    assert response.status_code == 422
    assert error_of(response)["fields"] == ["date_local"]
    assert "20260601" not in response.text


def test_api_engine_refusal_does_not_echo_the_input() -> None:
    response = client.post("/api/sun-sign", json=birth("ordinary", timezone=WITNESS))
    assert response.status_code == 422
    error = error_of(response)
    assert error["code"] == "invalid_input"
    assert "fuseau" in error["message"].lower()
    assert WITNESS not in response.text


def test_api_logs_carry_no_input(caplog: pytest.LogCaptureFixture) -> None:
    record = birth("ordinary", timezone=WITNESS)
    with caplog.at_level(logging.DEBUG):
        client.post("/api/sun-sign", json=record)
        client.post("/api/places/search", json={"query": WITNESS})
    assert WITNESS not in caplog.text
    assert record["date_local"] not in caplog.text


def test_api_native_telemetry_is_switched_off() -> None:
    """La télémétrie de FastAPI enregistrerait les messages d'erreur de validation, donc des
    saisies, et pourrait les exporter : tout est coupé, quelle que soit la variable d'environnement
    FASTAPI_OTEL_AUTO_CONFIGURE."""
    assert main.TELEMETRY_OFF == {
        "tracing": False,
        "metrics": False,
        "logs": False,
        "operation_spans": False,
        "auto_configure": False,
    }
    applied = main.app._telemetry
    assert {key: applied[key] for key in main.TELEMETRY_OFF} == main.TELEMETRY_OFF  # type: ignore[literal-required]
    assert main.app._native_telemetry.enabled() is False


# --- Erreurs : codes explicites, message en français, jamais de trace ---------------------------


def test_api_unknown_address_and_refused_method_answer_in_the_same_french_shape() -> None:
    missing = client.get("/api/absente")
    assert missing.status_code == 404
    assert error_of(missing)["code"] == "not_found"
    refused = client.get("/api/sun-sign")
    assert refused.status_code == 405
    assert error_of(refused)["code"] == "method_not_allowed"


def test_api_unreadable_body_is_refused_without_echoing_it() -> None:
    response = client.post(
        "/api/sun-sign",
        content=f"{{pas du JSON {WITNESS}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code in (400, 422)
    error_of(response)
    assert WITNESS not in response.text


def test_fr_01_date_outside_the_ephemeris_is_refused_in_french() -> None:
    response = client.post("/api/sun-sign", json=birth("ordinary", date_local="1700-06-01"))
    assert response.status_code == 422
    error = error_of(response)
    assert error["code"] == "invalid_input"
    assert "DE440s" in error["message"]


@pytest.mark.parametrize(
    ("date_local", "expected"),
    [
        ("2026-02-31", "n'existe pas dans le calendrier"),
        ("2026-13-01", "n'existe pas dans le calendrier"),
        ("31/02/2026", "format attendu"),
    ],
)
def test_api_impossible_date_gets_a_message_about_what_was_typed(
    date_local: str, expected: str
) -> None:
    """Un 31 février n'est pas une faute de format : le message ne parle pas d'AAAA-MM-JJ."""
    response = client.post("/api/sun-sign", json=birth("ordinary", date_local=date_local))
    assert response.status_code == 422
    error = error_of(response)
    assert error["code"] == "invalid_input"
    assert expected in error["message"]
    assert date_local not in response.text


def test_api_missing_time_is_refused() -> None:
    response = client.post("/api/sun-sign", json=birth("ordinary", time_local=None))
    assert response.status_code == 422
    assert "heure inconnue" in error_of(response)["message"]


@pytest.mark.usefixtures("no_data")
def test_api_sun_sign_without_ephemeris_is_unavailable_never_approximated() -> None:
    response = client.post("/api/sun-sign", json=birth("ordinary"))
    assert response.status_code == 503
    error = error_of(response)
    assert error["code"] == "ephemeris_unavailable"
    assert "éphéméride" in error["message"].lower()
    assert "scenarios" not in response.text


@pytest.mark.usefixtures("no_data")
def test_api_calendar_without_ephemeris_is_unavailable() -> None:
    response = client.get("/api/calendar/2026")
    assert response.status_code == 503
    assert error_of(response)["code"] == "ephemeris_unavailable"


@pytest.mark.usefixtures("no_data")
def test_api_places_without_files_are_unavailable() -> None:
    response = client.post("/api/places/search", json={"query": "Villefictive"})
    assert response.status_code == 503
    assert error_of(response)["code"] == "places_unavailable"


def test_api_calendar_refuses_an_unknown_timezone() -> None:
    response = client.get("/api/calendar/2026", params={"timezone": "Nulle/Part"})
    assert response.status_code == 422
    assert error_of(response)["code"] == "invalid_input"


@pytest.mark.parametrize("year", ["0", "10000", "deux-mille"])
def test_api_calendar_refuses_an_impossible_year(year: str) -> None:
    response = client.get(f"/api/calendar/{year}")
    assert response.status_code == 422
    assert error_of(response)["code"] == "invalid_request"


def test_api_stopped_calculation_gives_no_result_and_no_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def stop(*_: object, **__: object) -> None:
        raise ClassificationError(f"détail interne {WITNESS}")

    monkeypatch.setattr(natal, "sun_sign_chart", stop)
    response = TestClient(main.app, raise_server_exceptions=False).post(
        "/api/sun-sign", json=birth("ordinary")
    )
    assert response.status_code == 500
    error = error_of(response)
    assert error["code"] == "calculation_stopped"
    assert "aucun résultat" in error["message"]
    assert WITNESS not in response.text


def test_api_unexpected_failure_is_contained_and_logs_only_its_type(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def fail(*_: object, **__: object) -> None:
        raise RuntimeError(WITNESS)

    monkeypatch.setattr(natal, "sun_sign_chart", fail)
    with caplog.at_level(logging.DEBUG):
        # Client par défaut : si l'exception sortait de l'application (et finissait dans le
        # journal du serveur avec son message), cet appel la lèverait ici.
        response = client.post("/api/sun-sign", json=birth("ordinary"))
    assert response.status_code == 500
    assert error_of(response)["code"] == "internal_error"
    assert WITNESS not in response.text
    assert "RuntimeError" in caplog.text
    assert WITNESS not in caplog.text


def test_api_response_that_breaks_its_contract_leaks_no_value(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Un champ en trop dans le résultat du moteur : la réponse est refusée par son modèle. Le
    message de cette erreur cite les valeurs fautives ; il ne doit sortir nulle part."""
    record = birth("ordinary")
    monkeypatch.setattr(natal, "sun_sign_chart", lambda *_, **__: None)
    monkeypatch.setattr(
        natal, "as_record", lambda _: {"unexpected": WITNESS, "instant": record["date_local"]}
    )
    with caplog.at_level(logging.DEBUG):
        response = client.post("/api/sun-sign", json=record)
    assert response.status_code == 500
    assert error_of(response)["code"] == "internal_error"
    for text in (response.text, caplog.text):
        assert WITNESS not in text
        assert record["date_local"] not in text
    assert "ResponseValidationError" in caplog.text
    # Le journal dit quel champ rompt le contrat, sans sa valeur.
    assert "réponse hors contrat" in caplog.text and "unexpected" in caplog.text


# --- Contrat des réponses, sans données téléchargées --------------------------------------------


class SyntheticChain:
    """Astre fictif à vitesse constante : il remplace l'éphéméride pour éprouver, sans DE440s,
    que ce que rend le moteur passe par les modèles de l'API. L'année 2026 commence au jour
    1000 ; aucune de ces positions ne décrit le ciel."""

    RATE_DEG_PER_DAY = 0.9856
    ORIGIN_DEG = 280.0

    def instant(self, moment: datetime) -> Instant:
        days = (moment - datetime(2026, 1, 1, tzinfo=UTC)).total_seconds() / 86400.0
        return Instant(1000.0 + days, "utc", False)

    def utc_datetime(self, tt_jd: float) -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=tt_jd - 1000.0)

    def sun_longitude(self, tt_jd: float) -> float:
        return (self.ORIGIN_DEG + self.RATE_DEG_PER_DAY * (tt_jd - 1000.0)) % 360.0

    def sun_longitude_latitude(self, tt_jd: float) -> tuple[float, float]:
        return self.sun_longitude(tt_jd), 0.0

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


@pytest.fixture
def synthetic_chain(monkeypatch: pytest.MonkeyPatch) -> SyntheticChain:
    chain = SyntheticChain()
    monkeypatch.setattr(natal, "load_ephemeris", lambda: chain)
    monkeypatch.setattr(passages, "load_ephemeris", lambda: chain)
    return chain


@pytest.mark.usefixtures("synthetic_chain")
@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"time_status": "uncertain", "time_uncertainty_seconds": 3600},
        {"time_status": "unknown", "time_local": None},
    ],
)
def test_api_sun_sign_response_fits_its_declared_contract(changes: dict[str, Any]) -> None:
    record = birth("ordinary", **changes)
    response = client.post("/api/sun-sign", json=record)
    assert response.status_code == 200
    expected = natal.as_record(natal.sun_sign_chart(BirthInput.from_record(record)))
    assert response.json() == json.loads(json.dumps(expected))


@pytest.mark.usefixtures("synthetic_chain")
def test_api_possible_signs_response_fits_its_declared_contract() -> None:
    """Heure fictive posée sur une entrée de l'astre synthétique : le cas « possible », avec son
    franchissement, passe aussi par son modèle sans données téléchargées."""
    entry = passages.sun_entries(2026).entries[3]
    record = fictional_birth(
        entry.instant_utc, time_status="uncertain", time_uncertainty_seconds=600
    )
    response = client.post("/api/sun-sign", json=record)
    assert response.status_code == 200
    scenario = response.json()["scenarios"][0]
    assert scenario["classification"]["status"] == "possible"
    assert scenario["classification"]["sign_id"] is None
    assert scenario["classification"]["possible_signs"][1] == entry.sign_id
    assert [item["to_sign"] for item in scenario["uncertainty"]["transitions"]] == [entry.sign_id]


@pytest.mark.usefixtures("synthetic_chain")
def test_api_ambiguous_time_response_fits_its_declared_contract() -> None:
    body = client.post("/api/sun-sign", json=birth("ambiguous")).json()
    assert [scenario["fold"] for scenario in body["scenarios"]] == [0, 1]


@pytest.mark.usefixtures("synthetic_chain")
def test_api_nonexistent_time_is_refused_whatever_the_ephemeris() -> None:
    response = client.post("/api/sun-sign", json=birth("nonexistent"))
    assert response.status_code == 422
    assert error_of(response)["code"] == "nonexistent_local_time"


@pytest.mark.usefixtures("synthetic_chain")
def test_api_calendar_response_fits_its_declared_contract() -> None:
    response = client.get("/api/calendar/2026")
    assert response.status_code == 200
    body = response.json()
    expected = passages.sun_entries(2026)
    assert [entry["sign_id"] for entry in body["entries"]] == [
        entry.sign_id for entry in expected.entries
    ]
    assert len(body["entries"]) == 13
    assert body["manifest"] == json.loads(json.dumps(expected.manifest))


# --- Lieux ------------------------------------------------------------------------------------------


def test_api_timezone_from_coordinates_is_shown_for_confirmation() -> None:
    response = client.post(
        "/api/places/timezone", json={"latitude_deg": 48.8566, "longitude_deg": 2.3522}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["timezone"] == PARIS
    assert body["status"] == "found"
    assert body["needs_confirmation"] is True
    assert body["data_status"] == "candidate"
    assert {"timezonefinder", "timezonefinder_data"} <= set(body["manifest"])


def test_api_timezone_at_sea_stays_null_with_an_explicit_status() -> None:
    response = client.post(
        "/api/places/timezone", json={"latitude_deg": 0.0, "longitude_deg": -30.0}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["timezone"] is None
    assert body["status"] == "no_civil_timezone"


def test_api_timezone_unknown_to_the_database_is_not_called_open_sea(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        places,
        "timezone_at",
        lambda *_: places.TimezoneLookup(None, "unknown_to_timezone_database"),
    )
    body = client.post(
        "/api/places/timezone", json={"latitude_deg": 10.0, "longitude_deg": 10.0}
    ).json()
    assert body["timezone"] is None
    assert body["status"] == "unknown_to_timezone_database"


def test_api_timezone_refuses_impossible_coordinates() -> None:
    response = client.post(
        "/api/places/timezone", json={"latitude_deg": 95.0, "longitude_deg": 2.0}
    )
    assert response.status_code == 422
    assert error_of(response)["code"] == "invalid_input"


@pytest.mark.donnees
def test_fr_18_places_carry_status_manifest_and_attribution() -> None:
    response = client.post("/api/places/search", json={"query": "Paris"})
    assert response.status_code == 200
    body = response.json()
    assert body["data_status"] == "candidate"
    assert "GeoNames" in body["attribution"] and "CC BY 4.0" in body["attribution"]
    assert "geonames-cities15000" in body["manifest"]["sources"]
    first = body["places"][0]
    assert (first["name"], first["country_code"], first["timezone"]) == ("Paris", "FR", PARIS)
    assert first["admin1_name"] == "Île-de-France"


@pytest.mark.donnees
def test_api_unknown_place_returns_an_empty_list_never_a_neighbour() -> None:
    body = client.post("/api/places/search", json={"query": "Lieuabsentdutout"}).json()
    assert body["places"] == []


# --- Signe solaire --------------------------------------------------------------------------------


@pytest.mark.donnees
def test_api_sun_sign_is_the_engine_record_unchanged() -> None:
    record = birth("ordinary")
    response = client.post("/api/sun-sign", json=record)
    assert response.status_code == 200
    expected = natal.as_record(natal.sun_sign_chart(BirthInput.from_record(record)))
    assert response.json() == json.loads(json.dumps(expected))


@pytest.mark.donnees
def test_fr_18_sun_sign_carries_status_and_manifest() -> None:
    body = client.post("/api/sun-sign", json=birth("ordinary")).json()
    assert body["data_status"] == "candidate"
    assert body["model"]["validation_status"] == "not_validated"
    manifest = body["manifest"]
    assert manifest["ephemeris_id_and_hash"]["sha256"]
    assert manifest["chart_input_hash"]
    assert body["scenarios"][0]["interpretation"] == {
        "ruleset_id": None,
        "epistemic_status": "symbolic_proposal",
        "text": None,
    }


@pytest.mark.donnees
def test_fr_01_nonexistent_time_blocks_and_computes_nothing() -> None:
    response = client.post("/api/sun-sign", json=birth("nonexistent"))
    assert response.status_code == 422
    error = error_of(response)
    assert error["code"] == "nonexistent_local_time"
    assert "n'existe pas" in error["message"]
    assert "scenarios" not in response.text


@pytest.mark.donnees
def test_fr_04_ambiguous_time_gives_two_scenarios_until_the_occurrence_is_chosen() -> None:
    body = client.post("/api/sun-sign", json=birth("ambiguous")).json()
    assert body["local_time_kind"] == "ambiguous"
    assert [scenario["fold"] for scenario in body["scenarios"]] == [0, 1]
    chosen = client.post("/api/sun-sign", json=birth("ambiguous", fold=1)).json()
    assert [scenario["fold"] for scenario in chosen["scenarios"]] == [1]


@pytest.mark.donnees
def test_fr_05_unknown_time_gives_the_noon_reference_without_angles() -> None:
    record = birth("ordinary", time_status="unknown", time_local=None)
    body = client.post("/api/sun-sign", json=record).json()
    assert body["title"] == "carte de référence à midi"
    assert body["ascendant"] is None and body["houses"] is None
    assert body["ascendant_status"] == "undefined_without_birth_time"


@pytest.mark.donnees
def test_fr_03_uncertain_time_across_a_boundary_gives_two_possible_signs() -> None:
    entry = passages.sun_entries(2026).entries[5]
    record = fictional_birth(
        entry.instant_utc, time_status="uncertain", time_uncertainty_seconds=600
    )
    body = client.post("/api/sun-sign", json=record).json()
    classification = body["scenarios"][0]["classification"]
    assert classification["status"] == "possible"
    assert classification["sign_id"] is None
    assert len(classification["possible_signs"]) == 2
    assert classification["possible_signs"][1] == entry.sign_id
    assert body["scenarios"][0]["uncertainty"]["input_probability_distribution"] is None


# --- Calendrier -----------------------------------------------------------------------------------


@pytest.mark.donnees
def test_fr_06_calendar_gives_thirteen_entries_in_utc_and_paris_time() -> None:
    response = client.get("/api/calendar/2026")
    assert response.status_code == 200
    body = response.json()
    expected = passages.sun_entries(2026)
    assert body["year"] == 2026 and body["timezone"] == PARIS
    assert body["notice"] == "indicatif : près d'une frontière, l'heure de naissance compte"
    assert body["time_notice"] == passages.TIME_NOTICE_PARIS
    assert len(body["entries"]) == 13
    for got, entry in zip(body["entries"], expected.entries, strict=True):
        assert got["sign_id"] == entry.sign_id
        assert got["boundary_deg"] == entry.boundary_deg
        assert datetime.fromisoformat(got["instant_utc"]) == entry.instant_utc
        local = datetime.fromisoformat(got["instant_local"])
        assert local == entry.instant_utc
        assert local.utcoffset() == entry.instant_local.utcoffset()
        assert got["conditional"] is entry.conditional


@pytest.mark.donnees
def test_fr_18_calendar_carries_status_and_manifest() -> None:
    body = client.get("/api/calendar/2026").json()
    assert body["data_status"] == "candidate"
    assert body["manifest"]["ephemeris_id_and_hash"]["sha256"]
    assert body["manifest"]["chart_input_hash"] is None


@pytest.mark.donnees
def test_api_calendar_outside_the_ephemeris_is_refused_in_french() -> None:
    response = client.get("/api/calendar/1849")
    assert response.status_code == 422
    error = error_of(response)
    assert error["code"] == "out_of_ephemeris_range"
    assert "DE440s" in error["message"]


@pytest.mark.donnees
def test_api_calendar_in_another_timezone_changes_only_the_local_reading() -> None:
    paris = client.get("/api/calendar/2026").json()
    tokyo = client.get("/api/calendar/2026", params={"timezone": "Asia/Tokyo"}).json()
    assert tokyo["time_notice"] == passages.TIME_NOTICE_OTHER_ZONE
    for first, second in zip(paris["entries"], tokyo["entries"], strict=True):
        assert first["instant_utc"] == second["instant_utc"]
        assert first["sign_id"] == second["sign_id"]
