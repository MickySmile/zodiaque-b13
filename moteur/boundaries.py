"""Construction et contrôle des 13 frontières du modèle B.

Référence : `docs/prd/01-annexe-technique.md`, § B (conventions), D1 (algorithme), G (flottants).

Le cercle B (écliptique moyen J2000 fixe, latitude nulle) traverse la grille des constellations
de l'UAI telle que Skyfield la réalise d'après Roman 1987 (catalogue VI/42) : des lignes
d'ascension droite et de déclinaison constantes, à l'équinoxe B1875. Les frontières sont les
longitudes où le cercle change de constellation.

Méthode :
1. intersections analytiques du cercle avec chaque ligne de la grille ;
2. tri des longitudes candidates ;
3. constellation au milieu de chaque arc, par la fonction de Skyfield ;
4. suppression des coupures sans changement de constellation ;
5. contrôle des 13 noms et de leur ordre cyclique ;
6. sondage dense indépendant, raffiné par dichotomie.

Le calcul s'arrête par une `BoundaryError` plutôt que de corriger un résultat incohérent.
Les treize signes passent par les mêmes fonctions : aucun n'est traité à part.
"""

from __future__ import annotations

import hashlib
import math
import platform
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import cache
from pkgutil import get_data
from typing import Literal

import numpy as np
import skyfield
from numpy.typing import NDArray
from skyfield import framelib
from skyfield.api import load_constellation_map
from skyfield.functions import load_bundled_npy
from skyfield.positionlib import ICRF
from skyfield.timelib import Time, julian_date_of_besselian_epoch

from moteur import MODEL_ID
from moteur.coordinates import REFERENCE_FRAME, frame_matrix, signed_wrap, wrap

EXPECTED_ORDER = (
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
"""Ordre cyclique attendu le long du cercle B. Contrôlé après le calcul, jamais imposé."""

SUM_TOLERANCE_DEG = 1e-9
NEIGHBOUR_OFFSET_DEG = 1e-9
SAMPLING_STEP_DEG = 0.1
BISECTION_TOLERANCE_DEG = 1e-8
TANGENCY_TOLERANCE = 1e-12
CONTAINMENT_MARGIN_DEG = 1e-12

BOUNDARY_SOURCE = (
    "IAU constellation boundaries via Roman 1987 (CDS catalogue VI/42), "
    "grid bundled with Skyfield: Skyfield / Roman realisation"
)
BOUNDARY_SOURCE_EQUINOX = "B1875"
BOUNDARY_EQUATORIAL_CONVENTION = (
    "equatorial grid of equinox B1875, queried as radec(epoch=B1875) with Skyfield's "
    "Time.M matrix (precession, nutation, frame bias)"
)
INTERVAL_POLICY = "start_included_end_excluded"

LineKind = Literal["right_ascension_hours", "declination_deg"]
Lookup = Callable[[float], str]


class BoundaryError(Exception):
    """Les frontières calculées sont incohérentes : le calcul s'arrête, rien n'est corrigé."""


@dataclass(frozen=True)
class Interval:
    """Un signe sur le cercle B : début inclus, fin exclue."""

    sign_id: str
    start_deg: float
    end_deg: float
    width_deg: float


@dataclass(frozen=True)
class BoundaryLine:
    """Ligne de la grille B1875 qui porte une frontière."""

    longitude_deg: float
    kind: LineKind
    value: float  # heures d'ascension droite, ou degrés de déclinaison


@dataclass(frozen=True)
class BoundaryModel:
    """Résultat de `construct()` (annexe G, contrat du constructeur de frontières)."""

    model_id: str
    reference_frame: str
    boundary_source: str
    boundary_source_equinox: str
    boundary_equatorial_convention: str
    interval_policy: str
    skyfield_version: str
    numpy_version: str
    python_version: str
    boundary_sha256: str
    matrix_icrs_to_ecliptic: tuple[tuple[float, float, float], ...]
    certification: dict[str, float | int | str]
    intervals: tuple[Interval, ...]
    boundary_lines: tuple[BoundaryLine, ...]


@dataclass(frozen=True)
class _Grid:
    right_ascension_hours: tuple[float, ...]
    declination_deg: tuple[float, ...]
    sha256: str


@cache
def _grid() -> _Grid:
    """Lignes de la grille de Skyfield et empreinte du fichier qui les contient."""
    raw = get_data("skyfield", "data/constellations.npz")
    if raw is None:
        raise BoundaryError("grille des constellations introuvable dans Skyfield")
    arrays = load_bundled_npy("constellations.npz")
    return _Grid(
        right_ascension_hours=tuple(float(v) for v in arrays["sorted_ra"]),
        declination_deg=tuple(float(v) for v in arrays["sorted_dec"]),
        sha256=hashlib.sha256(raw).hexdigest(),
    )


@cache
def _b1875() -> Time:
    return Time(None, julian_date_of_besselian_epoch(1875))


def _ecliptic_to_b1875() -> NDArray[np.float64]:
    """Matrice qui exprime un vecteur du repère B dans le repère équatorial de la grille."""
    result: NDArray[np.float64] = np.asarray(_b1875().M, dtype=np.float64) @ frame_matrix().T
    return result


def _ecliptic_to_mean_b1875() -> NDArray[np.float64]:
    """Variante à l'équateur moyen de B1875 : précession et biais de repère, sans nutation.

    Le modèle ne l'utilise pas : elle ne sert qu'à chiffrer la sensibilité des frontières à
    cette convention (décision 0008).
    """
    mean = np.asarray(_b1875().P, dtype=np.float64) @ np.asarray(
        framelib.ICRS_to_J2000, dtype=np.float64
    )
    result: NDArray[np.float64] = mean @ frame_matrix().T
    return result


def _declination_ratios(p: NDArray[np.float64]) -> list[tuple[float, float]]:
    """Pour chaque ligne de déclinaison : sa valeur et sin δ rapporté à l'amplitude du cercle."""
    amplitude = math.hypot(float(p[2, 0]), float(p[2, 1]))
    return [
        (degrees, math.sin(math.radians(degrees)) / amplitude)
        for degrees in _grid().declination_deg
    ]


def _tangent_lines(p: NDArray[np.float64]) -> int:
    """Nombre de lignes de déclinaison que le cercle B touche sans les traverser."""
    return sum(
        1 for _, ratio in _declination_ratios(p) if abs(abs(ratio) - 1.0) <= TANGENCY_TOLERANCE
    )


@cache
def _skyfield_lookup() -> Callable[[ICRF], object]:
    lookup: Callable[[ICRF], object] = load_constellation_map()
    return lookup


def constellations_at(longitudes_deg: Sequence[float]) -> list[str]:
    """Constellation de chaque point du cercle B, par la fonction de Skyfield."""
    angles = np.radians(np.asarray(longitudes_deg, dtype=np.float64))
    directions_b = np.array([np.cos(angles), np.sin(angles), np.zeros_like(angles)])
    directions_icrs = frame_matrix().T @ directions_b
    names = np.atleast_1d(np.asarray(_skyfield_lookup()(ICRF(directions_icrs))))
    return [str(name) for name in names]


def constellation_at(longitude_deg: float) -> str:
    """Constellation d'un point du cercle B."""
    return constellations_at([longitude_deg])[0]


def _candidate_cuts(matrix: NDArray[np.float64] | None = None) -> list[BoundaryLine]:
    """Intersections du cercle B avec toutes les lignes de la grille, triées par longitude.

    Dans le repère de la grille, le cercle s'écrit v(λ) = p₁ cos λ + p₂ sin λ, où p₁ et p₂ sont
    les deux premières colonnes de la matrice de passage. Les deux familles de lignes donnent
    chacune une équation en cos λ et sin λ, résolue exactement.
    """
    p = _ecliptic_to_b1875() if matrix is None else matrix
    grid = _grid()
    cuts: list[BoundaryLine] = []

    # Lignes d'ascension droite : demi-grands cercles. La ligne 0 h est la couture de la grille.
    for hours in (0.0, *grid.right_ascension_hours):
        alpha = math.radians(hours * 15.0)
        sin_a, cos_a = math.sin(alpha), math.cos(alpha)
        a = float(p[0, 0]) * sin_a - float(p[1, 0]) * cos_a
        b = float(p[0, 1]) * sin_a - float(p[1, 1]) * cos_a
        if a == 0.0 and b == 0.0:
            raise BoundaryError(f"ligne d'ascension droite {hours} h : cas dégénéré")
        base = math.atan2(-a, b)
        solutions = []
        for angle in (base, base + math.pi):
            cos_l, sin_l = math.cos(angle), math.sin(angle)
            x = float(p[0, 0]) * cos_l + float(p[0, 1]) * sin_l
            y = float(p[1, 0]) * cos_l + float(p[1, 1]) * sin_l
            if x * cos_a + y * sin_a > 0.0:  # du côté de la ligne, pas du méridien opposé
                solutions.append(angle)
        if len(solutions) != 1:
            raise BoundaryError(f"ligne d'ascension droite {hours} h : cas dégénéré")
        cuts.append(BoundaryLine(wrap(math.degrees(solutions[0])), "right_ascension_hours", hours))

    # Lignes de déclinaison : petits cercles, jamais remplacés par des grands cercles.
    c, d = float(p[2, 0]), float(p[2, 1])
    phase = math.atan2(d, c)
    for degrees, ratio in _declination_ratios(p):
        if abs(ratio) > 1.0 + TANGENCY_TOLERANCE:
            continue  # le cercle B n'atteint pas cette déclinaison
        if abs(ratio) >= 1.0 - TANGENCY_TOLERANCE:
            # Tangence : un seul point de contact, gardé comme candidat. S'il ne sépare pas
            # deux constellations, l'étape 4 l'écarte.
            angles = [phase if ratio > 0.0 else phase + math.pi]
        else:
            half = math.acos(ratio)
            angles = [phase - half, phase + half]
        cuts.extend(
            BoundaryLine(wrap(math.degrees(angle)), "declination_deg", degrees) for angle in angles
        )

    cuts.sort(key=lambda cut: cut.longitude_deg)
    distinct: list[BoundaryLine] = []
    for cut in cuts:
        if not distinct or cut.longitude_deg != distinct[-1].longitude_deg:
            distinct.append(cut)
    return distinct


def _merge(cuts: Sequence[BoundaryLine]) -> tuple[list[Interval], list[BoundaryLine]]:
    """Garde les coupures où la constellation change et en fait des intervalles contigus."""
    count = len(cuts)
    middles = []
    for index, cut in enumerate(cuts):
        following = cuts[(index + 1) % count].longitude_deg
        middles.append(wrap(cut.longitude_deg + wrap(following - cut.longitude_deg) / 2.0))
    names = constellations_at(middles)

    changes = [index for index in range(count) if names[index] != names[index - 1]]
    if not changes:
        raise BoundaryError("aucun changement de constellation le long du cercle B")
    intervals: list[Interval] = []
    lines: list[BoundaryLine] = []
    for position, index in enumerate(changes):
        start = cuts[index].longitude_deg
        end = cuts[changes[(position + 1) % len(changes)]].longitude_deg
        intervals.append(Interval(names[index], start, end, wrap(end - start)))
        lines.append(cuts[index])

    # Présentation : la liste commence au premier signe de l'ordre attendu, s'il est là une
    # seule fois. Ce n'est qu'une rotation ; l'ordre lui-même est contrôlé ensuite.
    firsts = [i for i, interval in enumerate(intervals) if interval.sign_id == EXPECTED_ORDER[0]]
    if len(firsts) == 1:
        pivot = firsts[0]
        intervals = intervals[pivot:] + intervals[:pivot]
        lines = lines[pivot:] + lines[:pivot]
    return intervals, lines


def validate_intervals(intervals: Sequence[Interval]) -> float:
    """Contrôle la partition du cercle et rend l'écart de la somme des largeurs à 360°.

    Lève `BoundaryError` au premier défaut : nombre d'intervalles, constellation répétée,
    ordre, largeur nulle, lacune ou chevauchement, somme différente d'un tour.
    """
    expected = len(EXPECTED_ORDER)
    if len(intervals) != expected:
        found = ", ".join(interval.sign_id for interval in intervals)
        raise BoundaryError(f"{expected} intervalles attendus, {len(intervals)} trouvés : {found}")
    names = tuple(interval.sign_id for interval in intervals)
    if len(set(names)) != len(names):
        raise BoundaryError(f"une constellation occupe deux arcs distincts : {', '.join(names)}")
    if names != EXPECTED_ORDER:
        raise BoundaryError(f"ordre inattendu le long du cercle B : {', '.join(names)}")
    for interval in intervals:
        if not math.isfinite(interval.width_deg) or interval.width_deg <= 0.0:
            raise BoundaryError(f"{interval.sign_id} : largeur nulle ou invalide")
    for index, interval in enumerate(intervals):
        following = intervals[(index + 1) % expected]
        if interval.end_deg != following.start_deg:
            raise BoundaryError(
                f"lacune ou chevauchement entre {interval.sign_id} et {following.sign_id}"
            )
    error = math.fsum(interval.width_deg for interval in intervals) - 360.0
    if abs(error) >= SUM_TOLERANCE_DEG:
        raise BoundaryError(f"la somme des largeurs s'écarte de 360° de {error!r}°")
    for interval in intervals:
        if interval.width_deg != wrap(interval.end_deg - interval.start_deg):
            raise BoundaryError(f"{interval.sign_id} : largeur incohérente avec ses bornes")
    return error


def _check_neighbours(intervals: Sequence[Interval], lookup: Lookup) -> None:
    """Juste avant une frontière : le signe précédent ; juste après : le signe qui commence."""
    for index, interval in enumerate(intervals):
        previous = intervals[index - 1]
        before = lookup(wrap(interval.start_deg - NEIGHBOUR_OFFSET_DEG))
        after = lookup(wrap(interval.start_deg + NEIGHBOUR_OFFSET_DEG))
        if before != previous.sign_id or after != interval.sign_id:
            raise BoundaryError(
                f"classement erroné autour de la frontière {previous.sign_id} / "
                f"{interval.sign_id} : {before} avant, {after} après"
            )


def sample_boundaries(step_deg: float, tolerance_deg: float) -> list[tuple[float, float]]:
    """Sondage dense du cercle B : encadrements des changements de constellation.

    Échantillonne au pas donné, puis resserre chaque changement par dichotomie jusqu'à la
    tolérance. Chaîne indépendante des intersections analytiques ; elle ne prouve pas
    l'exhaustivité, une constellation plus étroite que le pas pouvant lui échapper.
    """
    count = round(360.0 / step_deg)
    samples = [index * 360.0 / count for index in range(count)]
    names = constellations_at(samples)
    brackets: list[tuple[float, float]] = []
    for index in range(count):
        if names[index] == names[(index + 1) % count]:
            continue
        low, high = samples[index], samples[index] + 360.0 / count
        while high - low > tolerance_deg:
            middle = (low + high) / 2.0
            if constellation_at(wrap(middle)) == names[index]:
                low = middle
            else:
                high = middle
        brackets.append((low, high))
    return brackets


def _check_dense_sampling(intervals: Sequence[Interval]) -> int:
    brackets = sorted(sample_boundaries(SAMPLING_STEP_DEG, BISECTION_TOLERANCE_DEG))
    starts = sorted(interval.start_deg for interval in intervals)
    if len(brackets) != len(starts):
        raise BoundaryError(
            f"sondage dense contradictoire : {len(brackets)} changements pour "
            f"{len(starts)} frontières"
        )
    for start, (low, high) in zip(starts, brackets, strict=True):
        if not low - CONTAINMENT_MARGIN_DEG <= start <= high + CONTAINMENT_MARGIN_DEG:
            raise BoundaryError(
                f"sondage dense contradictoire : frontière {start!r}° hors de "
                f"l'encadrement [{low!r}, {high!r}]"
            )
    return len(brackets)


def construct() -> BoundaryModel:
    """Calcule les 13 frontières, les contrôle et rend le modèle avec ses métadonnées."""
    cuts = _candidate_cuts()
    intervals, lines = _merge(cuts)
    sum_error = validate_intervals(intervals)
    _check_neighbours(intervals, constellation_at)
    transitions = _check_dense_sampling(intervals)

    matrix = frame_matrix()
    return BoundaryModel(
        model_id=MODEL_ID,
        reference_frame=REFERENCE_FRAME,
        boundary_source=BOUNDARY_SOURCE,
        boundary_source_equinox=BOUNDARY_SOURCE_EQUINOX,
        boundary_equatorial_convention=BOUNDARY_EQUATORIAL_CONVENTION,
        interval_policy=INTERVAL_POLICY,
        skyfield_version=str(skyfield.__version__),
        numpy_version=str(np.__version__),
        python_version=platform.python_version(),
        boundary_sha256=_grid().sha256,
        matrix_icrs_to_ecliptic=tuple(
            (float(row[0]), float(row[1]), float(row[2])) for row in matrix
        ),
        certification={
            "interval_count": len(intervals),
            "candidate_cuts": len(cuts),
            "tangent_lines": _tangent_lines(_ecliptic_to_b1875()),
            "sum_error_deg": sum_error,
            "sum_tolerance_deg": SUM_TOLERANCE_DEG,
            "neighbour_offset_deg": NEIGHBOUR_OFFSET_DEG,
            "dense_sampling_step_deg": SAMPLING_STEP_DEG,
            "dense_sampling_tolerance_deg": BISECTION_TOLERANCE_DEG,
            "dense_sampling_transitions": transitions,
            # Validation indépendante : décision humaine (porte G1), jamais déclarée ici.
            "independent_validation": "not_performed",
        },
        intervals=tuple(intervals),
        boundary_lines=tuple(lines),
    )


def mean_equator_shifts(model: BoundaryModel) -> tuple[float, ...]:
    """Déplacement de chaque frontière si la grille était lue à l'équateur moyen de B1875.

    Mêmes lignes de la grille, mêmes équations, mais sans la nutation que contient la matrice
    `Time.M` de Skyfield. Rend, dans l'ordre des intervalles, l'écart « moyen − vrai » en degrés.
    C'est une mesure de sensibilité (décision 0008), pas un second jeu de frontières : les
    constellations ne sont pas réidentifiées avec cette variante.
    """
    cuts = _candidate_cuts(_ecliptic_to_mean_b1875())
    shifts: list[float] = []
    for line in model.boundary_lines:
        same_line = [cut for cut in cuts if (cut.kind, cut.value) == (line.kind, line.value)]
        if not same_line:
            raise BoundaryError(f"ligne {line.kind} = {line.value!r} : le cercle ne la coupe plus")
        shifts.append(
            min(
                (signed_wrap(cut.longitude_deg - line.longitude_deg) for cut in same_line),
                key=abs,
            )
        )
    return tuple(shifts)
