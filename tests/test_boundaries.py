"""Construction des 13 frontières du modèle B (annexe technique § B, D1, G ; porte G1).

Ces tests ne contiennent aucune longitude attendue : ils vérifient des invariants et confrontent
le résultat à des chaînes de calcul distinctes. Les intervalles écrits ici à la main sont des
entrées synthétiques du validateur, pas des valeurs astronomiques.
"""

from __future__ import annotations

import dataclasses
import math
from functools import cache

import numpy as np
import pytest
from skyfield import framelib
from skyfield.api import load_constellation_map
from skyfield.positionlib import ICRF

from moteur import MODEL_ID
from moteur import boundaries as b
from moteur import coordinates as c


@cache
def model() -> b.BoundaryModel:
    return b.construct()


@cache
def lookup():  # type: ignore[no-untyped-def]
    return load_constellation_map()


def constellation_by_named_frame(longitude_deg: float) -> str:
    """Seconde chaîne : le repère nommé de Skyfield, sans passer par la matrice R du moteur.

    Ce repère ignore le biais de l'ICRS (environ 0,02″) : il départage sans ambiguïté tout
    point situé à plus de 10⁻⁴° d'une frontière.
    """
    named = np.asarray(framelib.ecliptic_J2000_frame._matrix)
    vector = named.T @ c.ecliptic_direction(longitude_deg)
    return str(lookup()(ICRF(vector)))


# --- Résultat du calcul réel ---------------------------------------------------------------


def test_boundaries_thirteen_intervals_in_the_expected_order() -> None:
    intervals = model().intervals
    assert len(intervals) == 13
    assert tuple(i.sign_id for i in intervals) == b.EXPECTED_ORDER


def test_boundaries_expected_order_is_the_one_of_the_annex() -> None:
    assert b.EXPECTED_ORDER == (
        "Ari",
        "Tau",
        "Gem",
        "Cnc",
        "Leo",
        "Vir",
        "Lib",
        "Sco",
        "Oph",
        "Sgr",
        "Cap",
        "Aqr",
        "Psc",
    )


def test_boundaries_widths_sum_to_a_full_turn() -> None:
    """Σ largeurs = 360° à 10⁻⁹° près."""
    assert abs(math.fsum(i.width_deg for i in model().intervals) - 360.0) < 1e-9


def test_boundaries_every_width_is_positive_and_consistent() -> None:
    for interval in model().intervals:
        assert interval.width_deg > 0.0
        assert interval.width_deg == c.wrap(interval.end_deg - interval.start_deg)
        assert 0.0 <= interval.start_deg < 360.0
        assert 0.0 <= interval.end_deg < 360.0


def test_boundaries_each_boundary_is_shared_by_two_signs() -> None:
    """Une frontière calculée une fois : la fin d'un signe est exactement le début du suivant."""
    intervals = model().intervals
    for current, following in zip(intervals, intervals[1:] + intervals[:1], strict=True):
        assert current.end_deg == following.start_deg


def test_boundaries_exactly_one_interval_crosses_zero() -> None:
    crossing = [i for i in model().intervals if i.end_deg < i.start_deg]
    assert len(crossing) == 1


def test_boundaries_construction_is_deterministic() -> None:
    assert b.construct() == model()


def test_boundaries_model_metadata() -> None:
    result = model()
    assert result.model_id == MODEL_ID == "model_b_iau_ecliptic_j2000_v1"
    assert result.reference_frame == c.REFERENCE_FRAME
    assert result.boundary_source_equinox == "B1875"
    assert result.interval_policy == "start_included_end_excluded"
    assert len(result.boundary_sha256) == 64
    assert np.array_equal(np.array(result.matrix_icrs_to_ecliptic), c.frame_matrix())
    assert "Roman" in result.boundary_source and "Skyfield" in result.boundary_source
    assert "Delporte exact" not in result.boundary_source


def test_boundaries_each_boundary_names_its_grid_line() -> None:
    """Chaque frontière vient d'une ligne de la grille : ascension droite ou déclinaison B1875."""
    lines = model().boundary_lines
    assert len(lines) == 13
    assert [line.longitude_deg for line in lines] == [i.start_deg for i in model().intervals]
    assert {line.kind for line in lines} <= {"right_ascension_hours", "declination_deg"}


# --- Confrontation à une seconde chaîne ----------------------------------------------------


def test_boundaries_midpoints_agree_with_the_named_frame() -> None:
    for interval in model().intervals:
        middle = c.wrap(interval.start_deg + interval.width_deg / 2.0)
        assert constellation_by_named_frame(middle) == interval.sign_id


def test_boundaries_neighbours_agree_with_the_named_frame() -> None:
    """Juste avant une frontière : le signe précédent ; juste après : le signe qui commence."""
    intervals = model().intervals
    offset = 1e-4
    for previous, current in zip(intervals[-1:] + intervals[:-1], intervals, strict=True):
        assert constellation_by_named_frame(c.wrap(current.start_deg - offset)) == previous.sign_id
        assert constellation_by_named_frame(c.wrap(current.start_deg + offset)) == current.sign_id


def test_boundaries_dense_sampling_finds_the_same_boundaries() -> None:
    """Annexe D1, étape 6 : sondage au pas de 0,1°, raffiné par dichotomie jusqu'à 10⁻⁸°."""
    found = b.sample_boundaries(b.SAMPLING_STEP_DEG, b.BISECTION_TOLERANCE_DEG)
    starts = sorted(i.start_deg for i in model().intervals)
    assert len(found) == 13
    for analytic, (low, high) in zip(starts, sorted(found), strict=True):
        assert high - low <= b.BISECTION_TOLERANCE_DEG
        assert low - 1e-12 <= analytic <= high + 1e-12


def test_boundaries_certification_records_the_checks() -> None:
    certification = model().certification
    assert certification["interval_count"] == 13
    assert certification["dense_sampling_step_deg"] == 0.1
    assert certification["dense_sampling_tolerance_deg"] == 1e-8
    assert certification["dense_sampling_transitions"] == 13
    assert certification["sum_tolerance_deg"] == 1e-9
    assert abs(certification["sum_error_deg"]) < 1e-9
    assert certification["candidate_cuts"] > 13
    # Franchir la porte G1 est une décision humaine : le moteur ne s'en attribue pas le mérite.
    assert certification["independent_validation"] == "not_performed"


# --- Validateur : arrêt plutôt que correction ----------------------------------------------


def synthetic(widths: list[float], names: tuple[str, ...] = b.EXPECTED_ORDER) -> list[b.Interval]:
    """Intervalles synthétiques contigus, pour éprouver le validateur. Aucune valeur réelle."""
    intervals = []
    start = 10.0
    for name, width in zip(names, widths, strict=True):
        end = c.wrap(start + width)
        intervals.append(b.Interval(name, start, end, c.wrap(end - start)))
        start = end
    # Ferme le cercle exactement : la fin du dernier intervalle est le début du premier.
    last = intervals[-1]
    closing = intervals[0].start_deg
    intervals[-1] = b.Interval(
        last.sign_id, last.start_deg, closing, c.wrap(closing - last.start_deg)
    )
    return intervals


# Treize largeurs synthétiques inégales, de somme 360° : aucune valeur réelle.
WIDTHS = [360.0 * (10 + rank) / sum(range(10, 23)) for rank in range(13)]


def test_boundaries_validator_accepts_a_coherent_partition() -> None:
    assert abs(b.validate_intervals(synthetic(WIDTHS))) < 1e-9


def test_boundaries_validator_rejects_a_wrong_count() -> None:
    with pytest.raises(b.BoundaryError, match="13"):
        b.validate_intervals(synthetic(WIDTHS)[:12])


def test_boundaries_validator_rejects_a_wrong_order() -> None:
    names = list(b.EXPECTED_ORDER)
    names[7], names[8] = names[8], names[7]
    with pytest.raises(b.BoundaryError, match="ordre"):
        b.validate_intervals(synthetic(WIDTHS, tuple(names)))


def test_boundaries_validator_rejects_a_repeated_constellation() -> None:
    names = list(b.EXPECTED_ORDER)
    names[9] = names[7]
    with pytest.raises(b.BoundaryError, match="deux arcs"):
        b.validate_intervals(synthetic(WIDTHS, tuple(names)))


def test_boundaries_validator_rejects_a_gap() -> None:
    intervals = synthetic(WIDTHS)
    intervals[4] = dataclasses.replace(intervals[4], start_deg=intervals[4].start_deg + 0.5)
    with pytest.raises(b.BoundaryError, match="lacune|chevauchement"):
        b.validate_intervals(intervals)


def test_boundaries_validator_rejects_a_null_width() -> None:
    intervals = synthetic(WIDTHS)
    intervals[3] = dataclasses.replace(intervals[3], width_deg=0.0)
    with pytest.raises(b.BoundaryError, match="largeur"):
        b.validate_intervals(intervals)


def test_boundaries_validator_rejects_a_sum_different_from_a_turn() -> None:
    intervals = [dataclasses.replace(i, width_deg=i.width_deg * 0.999) for i in synthetic(WIDTHS)]
    with pytest.raises(b.BoundaryError, match="360"):
        b.validate_intervals(intervals)


def test_boundaries_no_sign_is_handled_apart() -> None:
    """Treize signes, un seul traitement : le code ne nomme aucun signe hors de l'ordre attendu."""
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(b))
    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    mentions = [value for value in literals if value in b.EXPECTED_ORDER]
    assert sorted(mentions) == sorted(b.EXPECTED_ORDER)  # une fois chacun : dans EXPECTED_ORDER


# --- Conditions d'arrêt de l'annexe D1, une à une ------------------------------------------


def test_boundaries_neighbour_check_stops_on_a_wrong_classification() -> None:
    """Classement erroné juste avant ou après une frontière : arrêt."""
    intervals = synthetic(WIDTHS)
    with pytest.raises(b.BoundaryError, match="classement erroné"):
        b._check_neighbours(intervals, lambda longitude: "Ari")


def test_boundaries_neighbour_check_accepts_a_consistent_lookup() -> None:
    intervals = synthetic(WIDTHS)

    def lookup(longitude: float) -> str:
        return next(i.sign_id for i in intervals if c.wrap(longitude - i.start_deg) < i.width_deg)

    b._check_neighbours(intervals, lookup)


def test_boundaries_dense_sampling_stops_on_a_contradiction() -> None:
    """Sondage dense contradictoire : des frontières synthétiques ne sont pas celles du ciel."""
    with pytest.raises(b.BoundaryError, match="sondage dense contradictoire"):
        b._check_dense_sampling(synthetic(WIDTHS))


def test_boundaries_merge_stops_without_any_change(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(b, "constellations_at", lambda longitudes: ["Ari"] * len(longitudes))
    with pytest.raises(b.BoundaryError, match="aucun changement"):
        b._merge(b._candidate_cuts())


# --- Intersections analytiques -------------------------------------------------------------


def test_boundaries_every_candidate_lies_on_its_grid_line() -> None:
    """Chaque coupure candidate, réinjectée dans le repère de la grille, est sur sa ligne."""
    matrix = b._ecliptic_to_b1875()
    for cut in b._candidate_cuts():
        x, y, z = (float(v) for v in matrix @ c.ecliptic_direction(cut.longitude_deg))
        if cut.kind == "right_ascension_hours":
            residual = c.signed_wrap(math.degrees(math.atan2(y, x)) - cut.value * 15.0)
        else:
            residual = math.degrees(math.asin(z)) - cut.value
        assert abs(residual) < 1e-10, (cut, residual)


def test_boundaries_candidate_count_matches_the_grid() -> None:
    """Une coupure par ligne d'ascension droite, couture comprise ; deux par déclinaison atteinte."""
    grid = b._grid()
    reached = [
        ratio for _, ratio in b._declination_ratios(b._ecliptic_to_b1875()) if abs(ratio) < 1.0
    ]
    expected = len(grid.right_ascension_hours) + 1 + 2 * len(reached)
    assert len(b._candidate_cuts()) == expected == model().certification["candidate_cuts"]


def test_boundaries_no_grid_line_is_tangent_to_the_circle() -> None:
    assert model().certification["tangent_lines"] == 0


# --- Sensibilité à la convention d'équateur (décision 0008) --------------------------------


def test_boundaries_mean_equator_shifts_have_the_size_of_nutation() -> None:
    """Lire la grille à l'équateur moyen de B1875 déplace chaque frontière de quelques secondes
    d'arc : l'ordre de grandeur de la nutation, jamais nul, jamais un degré."""
    shifts = b.mean_equator_shifts(model())
    assert len(shifts) == 13
    for shift in shifts:
        assert 1.0 / 3600.0 < abs(shift) < 60.0 / 3600.0


def test_boundaries_mean_equator_matrix_differs_from_the_true_one_by_nutation_only() -> None:
    true_matrix, mean_matrix = b._ecliptic_to_b1875(), b._ecliptic_to_mean_b1875()
    assert np.abs(mean_matrix @ mean_matrix.T - np.eye(3)).max() < 1e-12
    rotation = true_matrix @ mean_matrix.T
    angle_arcsec = (
        math.degrees(math.acos(min(1.0, (float(np.trace(rotation)) - 1.0) / 2.0))) * 3600.0
    )
    assert 1.0 < angle_arcsec < 20.0


def test_boundaries_the_model_itself_uses_the_true_equator() -> None:
    """Le PRD prescrit la matrice Time.M de Skyfield : la variante moyenne ne sert qu'à mesurer."""
    assert np.array_equal(b._ecliptic_to_b1875(), np.asarray(b._b1875().M) @ c.frame_matrix().T)
