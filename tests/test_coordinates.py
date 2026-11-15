"""Repère du modèle B et normalisation des angles (annexe technique § B, C, G, J)."""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from skyfield import framelib

from moteur import coordinates as c

ANGLES = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)


# --- wrap ----------------------------------------------------------------------------------


@given(ANGLES)
def test_coordinates_wrap_stays_in_half_open_interval(angle: float) -> None:
    result = c.wrap(angle)
    assert 0.0 <= result < 360.0


@given(st.floats(min_value=0.0, max_value=360.0, exclude_max=True))
def test_coordinates_wrap_keeps_a_normalised_angle_unchanged(angle: float) -> None:
    assert c.wrap(angle) == angle


@given(st.floats(min_value=-720.0, max_value=720.0), st.integers(min_value=-3, max_value=3))
def test_coordinates_wrap_ignores_whole_turns(angle: float, turns: int) -> None:
    # Tolérance déclarée : l'addition de tours entiers arrondit au dernier chiffre.
    difference = c.signed_wrap(c.wrap(angle + 360.0 * turns) - c.wrap(angle))
    assert abs(difference) < 1e-9


def test_coordinates_wrap_examples_of_the_annex() -> None:
    """Annexe J : λ = −355° ou 365° donne le même résultat que 5° ; 0° et 360° sont identiques."""
    assert c.wrap(365.0) == 5.0
    assert c.wrap(-355.0) == 5.0
    assert c.wrap(360.0) == c.wrap(0.0) == 0.0


def test_coordinates_wrap_never_returns_360() -> None:
    """Un angle négatif minuscule ne doit pas être arrondi à 360° : la fin est exclue."""
    assert c.wrap(-1e-20) == 0.0
    assert c.wrap(math.nextafter(0.0, -1.0)) == 0.0
    assert c.wrap(math.nextafter(360.0, 0.0)) == math.nextafter(360.0, 0.0)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_coordinates_wrap_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="fini"):
        c.wrap(value)


@given(ANGLES)
def test_coordinates_signed_wrap_stays_in_half_open_interval(angle: float) -> None:
    result = c.signed_wrap(angle)
    assert -180.0 <= result < 180.0


# --- Matrice R -----------------------------------------------------------------------------


def test_coordinates_obliquity_is_the_value_of_the_annex() -> None:
    assert c.EPSILON_0_ARCSEC == 84381.406


def test_coordinates_frame_matrix_is_orthogonal() -> None:
    """Annexe C : RᵀR = I à 10⁻¹² près."""
    r = c.frame_matrix()
    assert np.abs(r.T @ r - np.eye(3)).max() < 1e-12
    assert abs(float(np.linalg.det(r)) - 1.0) < 1e-12


def test_coordinates_frame_matrix_follows_the_definition() -> None:
    """R = Qₓ(−ε₀) · B, avec B la matrice ICRS_to_J2000 de Skyfield (annexe B)."""
    epsilon = math.radians(84381.406 / 3600.0)
    q = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, math.cos(epsilon), math.sin(epsilon)],
            [0.0, -math.sin(epsilon), math.cos(epsilon)],
        ]
    )
    assert np.array_equal(c.frame_matrix(), q @ framelib.ICRS_to_J2000)


def test_coordinates_frame_matrix_is_not_taken_from_the_frame_name() -> None:
    """Annexe B : ne pas se fier au seul nom `ecliptic_J2000_frame`.

    La matrice de ce repère Skyfield ignore le biais de repère : elle est proche de R,
    mais différente. Le test échouerait si R était recopiée de ce repère.
    """
    named = np.asarray(framelib.ecliptic_J2000_frame._matrix)
    difference = float(np.abs(c.frame_matrix() - named).max())
    assert 0.0 < difference < 1e-6


def test_coordinates_frame_matrix_is_a_fresh_copy() -> None:
    first = c.frame_matrix()
    first[0, 0] = 42.0
    assert c.frame_matrix()[0, 0] != 42.0


# --- Directions et longitudes --------------------------------------------------------------


@given(st.floats(min_value=0.0, max_value=360.0, exclude_max=True))
def test_coordinates_direction_and_longitude_are_inverse(longitude: float) -> None:
    vector = c.ecliptic_direction(longitude)
    assert vector[2] == 0.0
    recovered, latitude = c.longitude_latitude_deg(vector)
    assert abs(c.signed_wrap(recovered - longitude)) < 1e-12
    assert abs(latitude) < 1e-12


def test_coordinates_origin_and_direction_of_longitudes() -> None:
    """Annexe B : origine sur l'axe x, longitude croissante de x vers y."""
    assert c.longitude_latitude_deg(np.array([1.0, 0.0, 0.0])) == (0.0, 0.0)
    assert c.longitude_latitude_deg(np.array([0.0, 1.0, 0.0])) == (90.0, 0.0)
    assert c.longitude_latitude_deg(np.array([0.0, 0.0, 2.0])) == (None, 90.0)


def test_coordinates_pole_has_no_longitude() -> None:
    """Annexe B, valeurs absentes : au pôle écliptique la longitude est indéfinie, jamais approchée."""
    longitude, latitude = c.longitude_latitude_deg(np.array([0.0, 0.0, -1.0]))
    assert longitude is None
    assert latitude == -90.0


def test_coordinates_null_vector_is_rejected() -> None:
    with pytest.raises(ValueError, match="nul"):
        c.longitude_latitude_deg(np.zeros(3))


@given(st.floats(min_value=0.0, max_value=360.0, exclude_max=True))
def test_coordinates_icrs_round_trip(longitude: float) -> None:
    """Annexe C : u_ecl = R u_ICRS  ⇔  u_ICRS = Rᵀ u_ecl."""
    vector = c.ecliptic_direction(longitude)
    assert np.abs(c.icrs_to_b(c.b_to_icrs(vector)) - vector).max() < 1e-12
