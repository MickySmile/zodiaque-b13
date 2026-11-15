"""Manifeste d'un résultat (PRD § 7, Reproductibilité ; annexe technique § F).

Le manifeste d'un calcul étend celui du découpage. L'ensemble de ses clés est fixé ici : en
retirer une, c'est rendre un résultat impossible à régénérer à l'identique.
"""

from __future__ import annotations

from moteur import MODEL_ID
from moteur.classification import load_canonical
from moteur.manifest import boundary_manifest, build_manifest

BOUNDARY_KEYS = {
    "calculation_engine_version",
    "model_id",
    "reference_frame",
    "matrix_icrs_to_ecliptic",
    "interval_policy",
    "boundary_source_equinox",
    "boundary_model_id_and_hash",
    "versions",
    "symbolic_ruleset_version",
    "dominance_ruleset_version",
    "synthesis_ruleset_version",
    "text_generator_version",
    "data_status",
    "validation_status",
}
CALCULATION_KEYS = {
    "ephemeris_id_and_hash",
    "observer",
    "position_type",
    "time_data_version",
    "time_data_end_utc",
    "time_data_last_leap_second_tai_minus_utc",
    "time_scale_policy",
    "timezone_database_version",
    "chart_input_hash",
}


class _Chain:
    """Source d'essai : seules ses déclarations servent au manifeste."""

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


def test_manifest_of_the_boundaries_has_exactly_its_fourteen_keys() -> None:
    manifest = boundary_manifest(load_canonical())
    assert set(manifest) == BOUNDARY_KEYS
    assert manifest["model_id"] == MODEL_ID
    assert manifest["data_status"] == "candidate"
    assert manifest["validation_status"] == "not_validated"


def test_manifest_of_a_calculation_has_exactly_its_twenty_three_keys() -> None:
    zodiac = load_canonical()
    manifest = build_manifest(_Chain(), zodiac, "empreinte-d-essai")  # type: ignore[arg-type]
    assert set(manifest) == BOUNDARY_KEYS | CALCULATION_KEYS
    assert len(manifest) == 23
    assert BOUNDARY_KEYS.isdisjoint(CALCULATION_KEYS)
    # La partie « découpage » est reprise telle quelle, sans valeur changée.
    assert {key: manifest[key] for key in BOUNDARY_KEYS} == boundary_manifest(zodiac)
    assert manifest["chart_input_hash"] == "empreinte-d-essai"
    assert manifest["ephemeris_id_and_hash"] == {"id": "synthetic", "sha256": None}


def test_manifest_of_a_result_without_personal_input_has_a_null_fingerprint() -> None:
    manifest = build_manifest(_Chain(), load_canonical(), None)  # type: ignore[arg-type]
    assert manifest["chart_input_hash"] is None
