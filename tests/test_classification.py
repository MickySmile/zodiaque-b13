"""FR-02 — signe B13 d'une longitude (PRD § 5 « Règle centrale », § 6 ; annexe § C, G, J).

Critère d'acceptation : étant donné λ = bᵢ, le signe i est retourné (début inclus, fin exclue) ;
λ = 365° est classé comme 5°. Cas limites : signe qui traverse 0°, longitude négative ou
supérieure à 360°, astre exactement au début ou à la fin d'un signe, longitude indéfinie aux
pôles, découpage invalide.

Les découpages écrits à la main dans ce fichier sont synthétiques. L'annexe J illustre ses tests
avec l'intervalle fictif des planches ; ni ses bornes ni sa largeur ne sont reprises ici (règle
« aucune valeur recopiée des planches »), mais chaque cas de l'annexe a son équivalent.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from fractions import Fraction
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from moteur import MODEL_ID, boundaries
from moteur import classification as k
from moteur import coordinates as c

GENERATED = Path(__file__).resolve().parents[1] / "generes"

# Découpage synthétique : cinq intervalles, dont un de 17° et un qui traverse 0°.
SYNTHETIC = [("a", 20.0), ("b", 100.0), ("c", 117.0), ("d", 200.0), ("e", 350.0)]


def synthetic() -> k.Zodiac:
    return k.Zodiac.from_boundaries(SYNTHETIC, expected_count=None)


def canonical() -> k.Zodiac:
    return k.load_canonical()


def crossing_sign(zodiac: k.Zodiac) -> k.Sign:
    return next(sign for sign in zodiac.signs if sign.end_deg < sign.start_deg)


# --- Critère d'acceptation -----------------------------------------------------------------


def test_fr_02_boundary_longitude_returns_the_sign_that_starts() -> None:
    """Étant donné λ = bᵢ, le signe i est retourné : début inclus. Vrai pour les 13 frontières."""
    zodiac = canonical()
    for sign in zodiac.signs:
        placement = zodiac.classify(sign.start_deg)
        assert placement.sign_id == sign.sign_id
        assert placement.degrees_in_sign == 0.0
        assert placement.fraction_in_sign == 0.0


def test_fr_02_just_before_a_boundary_is_still_the_previous_sign() -> None:
    """Fin exclue, sans zone de cuspide : le dernier nombre avant bᵢ appartient au signe d'avant.

    Voisins testés avec `math.nextafter()` (annexe G), sur les 13 frontières réelles.
    """
    zodiac = canonical()
    signs = zodiac.signs
    for previous, sign in zip(signs[-1:] + signs[:-1], signs, strict=True):
        before = zodiac.classify(math.nextafter(sign.start_deg, -math.inf))
        after = zodiac.classify(math.nextafter(sign.start_deg, math.inf))
        assert before.sign_id == previous.sign_id
        assert after.sign_id == sign.sign_id
        assert 0.0 <= before.degrees_in_sign < previous.width_deg
        assert 0.0 <= before.fraction_in_sign < 1.0


def test_fr_02_end_of_a_sign_belongs_to_the_next_one() -> None:
    zodiac = canonical()
    signs = zodiac.signs
    for sign, following in zip(signs, signs[1:] + signs[:1], strict=True):
        assert zodiac.classify(sign.end_deg).sign_id == following.sign_id


def test_fr_02_365_degrees_is_classified_as_5_degrees() -> None:
    for zodiac in (canonical(), synthetic()):
        assert zodiac.classify(365.0) == zodiac.classify(5.0)


# --- Cas limites du PRD --------------------------------------------------------------------


def test_fr_02_sign_crossing_zero() -> None:
    """Début 350°, fin 20°, astre à 5° : w = 30°, d = 15°, p = 0,5 (jeu F2)."""
    placement = synthetic().classify(5.0)
    assert placement.sign_id == "e"
    assert placement.sign_width_deg == 30.0
    assert placement.degrees_in_sign == 15.0
    assert placement.fraction_in_sign == 0.5


def test_fr_02_negative_longitude_and_whole_turns() -> None:
    """λ = −355° ou 365° : même résultat que 5° ; 0° et 360° : résultats identiques (jeu F3)."""
    zodiac = synthetic()
    assert zodiac.classify(-355.0) == zodiac.classify(5.0)
    assert zodiac.classify(0.0) == zodiac.classify(360.0)
    assert zodiac.classify(-0.0) == zodiac.classify(0.0)
    assert zodiac.classify(725.0) == zodiac.classify(5.0)


def test_fr_02_inside_start_and_end_of_an_interval() -> None:
    """Équivalent des cas de l'annexe J sur un intervalle synthétique de 17° (100° à 117°)."""
    zodiac = synthetic()
    inside = zodiac.classify(108.0)
    assert (inside.sign_id, inside.degrees_in_sign) == ("b", 8.0)
    assert inside.fraction_in_sign == pytest.approx(8.0 / 17.0, abs=1e-15)
    assert zodiac.classify(100.0).sign_id == "b"  # début inclus
    assert zodiac.classify(math.nextafter(117.0, -math.inf)).sign_id == "b"
    assert zodiac.classify(117.0).sign_id == "c"  # fin exclue : signe suivant


def test_fr_02_undefined_longitude_is_rejected() -> None:
    """Pôle écliptique : rejet, jamais de signe « le plus proche »."""
    for zodiac in (canonical(), synthetic()):
        with pytest.raises(k.ClassificationError, match="indéfinie"):
            zodiac.classify(None)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_fr_02_non_finite_longitude_is_rejected(value: float) -> None:
    with pytest.raises(k.ClassificationError, match="longitude invalide"):
        synthetic().classify(value)


# --- Flottants : arrondis connus, figés par des tests --------------------------------------


def test_fr_02_position_in_sign_stays_below_the_width() -> None:
    """Dernier nombre avant la fin du signe qui traverse 0° : l'arrondi de la soustraction peut
    atteindre la largeur. Le signe reste celui-là, et d reste strictement sous w."""
    zodiac = canonical()
    sign = crossing_sign(zodiac)
    last = math.nextafter(sign.end_deg, -math.inf)
    placement = zodiac.classify(last)
    assert placement.sign_id == sign.sign_id
    assert placement.degrees_in_sign < sign.width_deg
    assert placement.fraction_in_sign < 1.0
    raw = (360.0 - sign.start_deg) + last
    if raw >= sign.width_deg:
        assert placement.degrees_in_sign == math.nextafter(sign.width_deg, 0.0)


def test_fr_02_negative_longitude_half_a_digit_below_a_boundary() -> None:
    """Limite documentée : une longitude négative est d'abord ramenée dans [0°, 360°[, et cette
    addition arrondit. Le résultat reste celui de la longitude ramenée, à un demi-chiffre près."""
    zodiac = canonical()
    for sign in zodiac.signs:
        longitude = math.nextafter(sign.start_deg - 360.0, -math.inf)
        assert zodiac.classify(longitude) == zodiac.classify(c.wrap(longitude))
        assert abs(c.signed_wrap(c.wrap(longitude) - sign.start_deg)) < 1e-12


# --- Découpage invalide : classement refusé ------------------------------------------------


def signs(*rows: tuple[str, float, float]) -> list[k.Sign]:
    return [k.Sign(name, start, end, c.wrap(end - start)) for name, start, end in rows]


def test_fr_02_partition_with_a_gap_is_refused() -> None:
    with pytest.raises(k.ClassificationError, match="lacune ou chevauchement"):
        k.Zodiac(signs(("a", 0.0, 100.0), ("b", 110.0, 200.0), ("c", 200.0, 0.0)), None)


def test_fr_02_partition_with_an_overlap_is_refused() -> None:
    with pytest.raises(k.ClassificationError, match="lacune ou chevauchement"):
        k.Zodiac(signs(("a", 0.0, 120.0), ("b", 100.0, 200.0), ("c", 200.0, 0.0)), None)


def test_fr_02_partition_whose_widths_do_not_sum_to_a_turn_is_refused() -> None:
    rows = signs(("a", 0.0, 100.0), ("b", 100.0, 200.0), ("c", 200.0, 0.0))
    rows[1] = k.Sign("b", 100.0, 200.0, 99.0)
    with pytest.raises(k.ClassificationError, match="somme des largeurs"):
        k.Zodiac(rows, None)


def test_fr_02_partition_going_twice_around_is_refused() -> None:
    rows = signs(("a", 0.0, 200.0), ("b", 200.0, 100.0), ("c", 100.0, 300.0), ("d", 300.0, 0.0))
    with pytest.raises(k.ClassificationError, match="somme des largeurs"):
        k.Zodiac(rows, None)


def test_fr_02_partition_with_a_width_inconsistent_with_its_bounds_is_refused() -> None:
    """Somme juste, mais deux largeurs échangées : chaque largeur doit être celle de ses bornes."""
    rows = signs(("a", 0.0, 100.0), ("b", 100.0, 220.0), ("c", 220.0, 0.0))
    rows[0] = k.Sign("a", 0.0, 100.0, 120.0)
    rows[1] = k.Sign("b", 100.0, 220.0, 100.0)
    with pytest.raises(k.ClassificationError, match="largeur incohérente"):
        k.Zodiac(rows, None)


def test_fr_02_partition_with_a_null_width_is_refused() -> None:
    with pytest.raises(k.ClassificationError, match="largeur nulle"):
        k.Zodiac(signs(("a", 0.0, 100.0), ("b", 100.0, 100.0), ("c", 100.0, 0.0)), None)


def test_fr_02_partition_with_a_non_finite_bound_is_refused() -> None:
    with pytest.raises(k.ClassificationError, match="borne non finie"):
        k.Zodiac.from_boundaries([("a", 0.0), ("b", math.nan), ("c", 200.0)], None)


def test_fr_02_partition_with_a_bound_outside_the_circle_is_refused() -> None:
    with pytest.raises(k.ClassificationError, match="hors"):
        k.Zodiac(signs(("a", 0.0, 100.0), ("b", 100.0, 400.0), ("c", 400.0, 0.0)), None)


def test_fr_02_partition_with_a_repeated_sign_is_refused() -> None:
    with pytest.raises(k.ClassificationError, match="deux fois"):
        k.Zodiac.from_boundaries([("a", 0.0), ("b", 100.0), ("a", 200.0)], None)


def test_fr_02_production_partition_must_have_thirteen_signs() -> None:
    """En production `expected_count = 13` (annexe J) : un découpage à 5 intervalles est refusé."""
    with pytest.raises(k.ClassificationError, match="13 intervalles attendus"):
        k.Zodiac.from_boundaries(SYNTHETIC)


# --- Bornes canoniques ---------------------------------------------------------------------


def test_fr_02_canonical_zodiac_reads_the_generated_boundaries() -> None:
    """Le classement lit generes/frontieres.csv ; il ne recalcule pas les frontières (0009)."""
    zodiac = canonical()
    lines = (GENERATED / "frontieres.csv").read_text(encoding="utf-8").splitlines()[1:]
    assert len(zodiac.signs) == 13
    assert tuple(sign.sign_id for sign in zodiac.signs) == boundaries.EXPECTED_ORDER
    for sign, line in zip(zodiac.signs, lines, strict=True):
        name, start, end, width = line.split(",")
        assert (sign.sign_id, sign.start_deg, sign.end_deg, sign.width_deg) == (
            name,
            float(start),
            float(end),
            float(width),
        )


def test_fr_02_canonical_zodiac_carries_its_provenance() -> None:
    """De quoi écrire le manifeste d'un résultat et afficher le statut des données."""
    provenance = canonical().provenance
    assert provenance is not None
    assert provenance.model_id == MODEL_ID
    raw = (GENERATED / "frontieres.csv").read_bytes()
    assert provenance.boundaries_file_sha256 == hashlib.sha256(raw).hexdigest()
    assert len(provenance.boundary_source_sha256) == 64
    assert provenance.data_status == "candidate"  # la porte G1 n'est pas franchie


def test_fr_02_every_canonical_midpoint_is_in_its_sign() -> None:
    zodiac = canonical()
    for sign in zodiac.signs:
        middle = zodiac.classify(c.wrap(sign.start_deg + sign.width_deg / 2.0))
        assert middle.sign_id == sign.sign_id
        assert middle.fraction_in_sign == pytest.approx(0.5, abs=1e-12)


def copy_generated(tmp_path: Path) -> Path:
    target = tmp_path / "generes"
    target.mkdir()
    for name in ("frontieres.csv", "manifest.json"):
        shutil.copy(GENERATED / name, target / name)
    return target


def rewrite_manifest(folder: Path, change) -> None:  # type: ignore[no-untyped-def]
    path = folder / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    change(manifest)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def test_fr_02_edited_boundary_file_is_refused(tmp_path: Path) -> None:
    """Un fichier de frontières qui ne correspond plus à son empreinte ne sert pas à classer."""
    folder = copy_generated(tmp_path)
    path = folder / "frontieres.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    last = lines[1][-1]
    lines[1] = lines[1][:-1] + ("1" if last != "1" else "2")  # un seul chiffre change
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(k.ClassificationError, match="empreinte"):
        k.load_canonical(folder)


def test_fr_02_boundary_file_in_another_order_is_refused_even_with_a_matching_fingerprint(
    tmp_path: Path,
) -> None:
    """Empreinte refaite, mais découpage faux : le contrôle des 13 signes s'applique encore."""
    folder = copy_generated(tmp_path)
    path = folder / "frontieres.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[3], lines[4] = lines[4], lines[3]
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(raw)

    def refresh(manifest: dict) -> None:  # type: ignore[type-arg]
        manifest["files"]["frontieres.csv"]["sha256"] = hashlib.sha256(raw).hexdigest()

    rewrite_manifest(folder, refresh)
    with pytest.raises(k.ClassificationError, match="découpage invalide"):
        k.load_canonical(folder)


def test_fr_02_boundaries_of_another_frame_are_refused(tmp_path: Path) -> None:
    """Annexe G : le moteur vérifie que la matrice du manifeste est celle qu'il utilise."""
    folder = copy_generated(tmp_path)

    def shift(manifest: dict) -> None:  # type: ignore[type-arg]
        manifest["model"]["matrix_icrs_to_ecliptic"][1][1] += 1e-6

    rewrite_manifest(folder, shift)
    with pytest.raises(k.ClassificationError, match="matrice"):
        k.load_canonical(folder)


def test_fr_02_boundaries_of_another_model_are_refused(tmp_path: Path) -> None:
    folder = copy_generated(tmp_path)
    rewrite_manifest(folder, lambda manifest: manifest["model"].update(id="another_model"))
    with pytest.raises(k.ClassificationError, match="autre modèle"):
        k.load_canonical(folder)


def test_fr_02_boundaries_with_another_interval_policy_are_refused(tmp_path: Path) -> None:
    folder = copy_generated(tmp_path)
    rewrite_manifest(
        folder, lambda manifest: manifest["model"].update(interval_policy="start_excluded")
    )
    with pytest.raises(k.ClassificationError, match="convention de bornes"):
        k.load_canonical(folder)


@pytest.mark.parametrize("key", ["files", "model"])
def test_fr_02_malformed_manifest_is_an_explicit_error(tmp_path: Path, key: str) -> None:
    folder = copy_generated(tmp_path)
    rewrite_manifest(folder, lambda manifest: manifest.update({key: None}))
    with pytest.raises(k.ClassificationError, match="doit être un objet"):
        k.load_canonical(folder)


def test_fr_02_missing_boundary_files_are_an_explicit_error(tmp_path: Path) -> None:
    with pytest.raises(k.ClassificationError, match="frontieres"):
        k.load_canonical(tmp_path)


# --- Propriétés ----------------------------------------------------------------------------

LONGITUDES = st.floats(min_value=-1e5, max_value=1e5, allow_nan=False, allow_infinity=False)
WRAPPED = st.floats(min_value=0.0, max_value=360.0, exclude_max=True)
PARTITIONS = st.lists(WRAPPED, min_size=2, max_size=15, unique=True).filter(
    lambda starts: min(b - a for a, b in zip(sorted(starts), sorted(starts)[1:])) > 1e-6
)


def exact_sign(zodiac: k.Zodiac, longitude: float) -> str:
    """Oracle : la définition du PRD, 0 ≤ wrap(λ − bᵢ) < wᵢ, en arithmétique exacte."""
    turn = Fraction(360)
    value = Fraction(longitude)
    matches = [
        sign.sign_id
        for sign in zodiac.signs
        if (value - Fraction(sign.start_deg)) % turn
        < (Fraction(sign.end_deg) - Fraction(sign.start_deg)) % turn
    ]
    assert len(matches) == 1
    return matches[0]


@given(WRAPPED)
def test_fr_02_sign_matches_the_exact_definition(longitude: float) -> None:
    zodiac = canonical()
    placement = zodiac.classify(longitude)
    assert placement.sign_id == exact_sign(zodiac, longitude)
    assert placement.longitude_deg == longitude
    assert 0.0 <= placement.degrees_in_sign < placement.sign_width_deg
    assert 0.0 <= placement.fraction_in_sign < 1.0


@given(LONGITUDES)
def test_fr_02_any_longitude_is_classified_as_its_wrapped_value(longitude: float) -> None:
    zodiac = canonical()
    assert zodiac.classify(longitude) == zodiac.classify(c.wrap(longitude))


@given(PARTITIONS, WRAPPED)
def test_fr_02_any_valid_partition_matches_the_exact_definition(
    starts: list[float], longitude: float
) -> None:
    ordered = sorted(starts)
    zodiac = k.Zodiac.from_boundaries(
        [(f"s{rank}", start) for rank, start in enumerate(ordered)], expected_count=None
    )
    assert zodiac.classify(longitude).sign_id == exact_sign(zodiac, longitude)
    names = [sign.sign_id for sign in zodiac.signs]
    for rank, start in enumerate(ordered):
        at_start = zodiac.classify(start)
        assert (at_start.sign_id, at_start.degrees_in_sign) == (names[rank], 0.0)  # début inclus
        just_before = zodiac.classify(math.nextafter(start, -math.inf) if start > 0.0 else 360.0)
        if start > 0.0:
            assert just_before.sign_id == names[rank - 1]  # fin exclue


# --- Treize signes, un seul traitement -----------------------------------------------------


def test_fr_02_no_sign_is_named_in_the_classification_code() -> None:
    import ast
    import inspect

    literals = {
        node.value
        for node in ast.walk(ast.parse(inspect.getsource(k)))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert literals.isdisjoint(boundaries.EXPECTED_ORDER)
