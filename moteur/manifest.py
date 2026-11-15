"""Manifeste d'un résultat : ce qu'il faut pour le régénérer à l'identique.

Référence : PRD § 7 (Reproductibilité) ; annexe technique § F (« Versionnement minimal ») ; règle
« Manifeste sur chaque résultat ». Une valeur absente reste nulle, jamais inventée.
"""

from __future__ import annotations

import platform

import numpy as np
import scipy
import skyfield

import moteur
from moteur.boundaries import BOUNDARY_SOURCE_EQUINOX, INTERVAL_POLICY
from moteur.civil_time import timezone_database_version
from moteur.classification import Zodiac
from moteur.coordinates import REFERENCE_FRAME, frame_matrix
from moteur.positions import SunEphemeris


def build_manifest(
    chain: SunEphemeris, zodiac: Zodiac, input_fingerprint: str | None
) -> dict[str, object]:
    """Manifeste commun aux résultats du moteur. `input_fingerprint` : empreinte de la saisie,
    ou `None` pour un résultat qui ne dépend d'aucune saisie personnelle (calendrier annuel)."""
    provenance = zodiac.provenance
    source = chain.manifest()
    return {
        "calculation_engine_version": moteur.__version__,
        "model_id": moteur.MODEL_ID,
        "reference_frame": REFERENCE_FRAME,
        "matrix_icrs_to_ecliptic": [[float(value) for value in row] for row in frame_matrix()],
        "interval_policy": INTERVAL_POLICY,
        "boundary_source_equinox": BOUNDARY_SOURCE_EQUINOX,
        "boundary_model_id_and_hash": {
            "id": None if provenance is None else provenance.model_id,
            "boundaries_file_sha256": None
            if provenance is None
            else provenance.boundaries_file_sha256,
            "boundary_source_sha256": None
            if provenance is None
            else provenance.boundary_source_sha256,
        },
        "ephemeris_id_and_hash": {
            "id": source["ephemeris"],
            "sha256": source["ephemeris_sha256"],
        },
        "observer": source["observer"],
        "position_type": source["position_type"],
        "time_data_version": source["time_data"],
        "time_data_end_utc": source["time_data_end_utc"],
        "time_data_last_leap_second_tai_minus_utc": source[
            "time_data_last_leap_second_tai_minus_utc"
        ],
        "time_scale_policy": source["time_scale_policy"],
        "timezone_database_version": timezone_database_version(),
        "versions": {
            "skyfield": str(skyfield.__version__),
            "numpy": str(np.__version__),
            "scipy": str(scipy.__version__),
            "python": platform.python_version(),
        },
        "symbolic_ruleset_version": None,
        "dominance_ruleset_version": None,
        "synthesis_ruleset_version": None,
        "text_generator_version": None,
        "chart_input_hash": input_fingerprint,
        # « candidate » tant que la porte G1 n'est pas franchie ; un découpage qui ne vient pas
        # des fichiers générés est un démonstrateur.
        "data_status": "synthetic" if provenance is None else provenance.data_status,
        "validation_status": "not_validated"
        if provenance is None or provenance.data_status != "verified"
        else "validated",
    }
