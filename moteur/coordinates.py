"""Repère du modèle B et normalisation des angles.

Référence : `docs/prd/01-annexe-technique.md`, § B (conventions), C (formules), G (flottants).

Un seul repère pour toutes les longitudes — frontières, astres, angles, maisons : l'écliptique
moyen J2000 fixe, R = Qₓ(−ε₀) · B, où B est la matrice `ICRS_to_J2000` de Skyfield et
ε₀ = 84 381,406″. R est construite ici à partir de sa définition ; elle n'est pas lue dans le
repère `ecliptic_J2000_frame` de Skyfield, dont la matrice ignore le biais de repère.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray
from skyfield import framelib

EPSILON_0_ARCSEC = 84381.406
"""Obliquité moyenne de l'écliptique à J2000, en secondes d'arc (annexe B)."""

REFERENCE_FRAME = "Rx(-84381.406 arcsec) @ Skyfield.ICRS_to_J2000"
"""Libellé du repère, tel qu'il figure dans les enregistrements (annexe F)."""

Vector = NDArray[np.float64]
Matrix = NDArray[np.float64]


def wrap(angle_deg: float) -> float:
    """Ramène un angle dans [0°, 360°[. Début inclus, fin exclue : 360° n'est jamais rendu."""
    if not math.isfinite(angle_deg):
        raise ValueError(f"angle non fini : {angle_deg!r}")
    result = math.fmod(angle_deg, 360.0)
    if result < 0.0:
        result += 360.0
        if result >= 360.0:  # angle négatif minuscule : l'addition arrondit à 360
            result = 0.0
    return result + 0.0  # −0.0 devient 0.0


def signed_wrap(angle_deg: float) -> float:
    """Ramène un écart angulaire dans [−180°, 180°[."""
    return wrap(angle_deg + 180.0) - 180.0


def frame_matrix() -> Matrix:
    """Matrice R du repère B : u_B = R · u_ICRS. Une copie neuve à chaque appel."""
    epsilon = math.radians(EPSILON_0_ARCSEC / 3600.0)
    cos_e, sin_e = math.cos(epsilon), math.sin(epsilon)
    q = np.array([[1.0, 0.0, 0.0], [0.0, cos_e, sin_e], [0.0, -sin_e, cos_e]])
    result: Matrix = q @ np.asarray(framelib.ICRS_to_J2000, dtype=np.float64)
    return result


def icrs_to_b(vector_icrs: Vector) -> Vector:
    """Exprime un vecteur ICRS dans le repère B."""
    result: Vector = frame_matrix() @ np.asarray(vector_icrs, dtype=np.float64)
    return result


def b_to_icrs(vector_b: Vector) -> Vector:
    """Exprime un vecteur du repère B dans l'ICRS. R est orthogonale : son inverse est Rᵀ."""
    result: Vector = frame_matrix().T @ np.asarray(vector_b, dtype=np.float64)
    return result


def ecliptic_direction(longitude_deg: float) -> Vector:
    """Direction unitaire du cercle B à la longitude donnée : (cos λ, sin λ, 0)."""
    angle = math.radians(longitude_deg)
    return np.array([math.cos(angle), math.sin(angle), 0.0])


def longitude_latitude_deg(vector_b: Vector) -> tuple[float | None, float]:
    """Longitude dans [0°, 360°[ et latitude d'un vecteur exprimé dans le repère B.

    Aux pôles du repère la longitude est indéfinie : `None`, jamais une valeur approchée.
    """
    x, y, z = (float(v) for v in vector_b)
    planar = math.hypot(x, y)
    if planar == 0.0 and z == 0.0:
        raise ValueError("vecteur nul : aucune direction")
    latitude = math.degrees(math.atan2(z, planar))
    if planar == 0.0:
        return None, latitude
    return wrap(math.degrees(math.atan2(y, x))), latitude
