"""Classement d'une longitude dans un découpage du cercle B (FR-02).

Référence : PRD § 5 « Règle centrale » ; annexe technique § C (formules), G (flottants), J (tests).

    wᵢ = wrap(bᵢ₊₁ − bᵢ)    dᵢ = wrap(λ − bᵢ)    astre ∈ i ⟺ 0 ≤ dᵢ < wᵢ    pᵢ = dᵢ / wᵢ

Le signe est décidé par des comparaisons directes entre la longitude ramenée dans [0°, 360°[ et
les bornes canoniques : début inclus, fin exclue, strictement. Une soustraction arrondit, et son
arrondi pourrait faire basculer un point voisin d'une frontière dans le mauvais signe ; une
comparaison ne se trompe pas. Les degrés internes et la progression sont calculés ensuite.

Aucun signe n'est élargi d'un epsilon, aucun n'est traité à part : le découpage est une liste
d'intervalles, tous lus par le même code. Les bornes de production viennent du fichier
`generes/frontieres.csv` ; elles ne sont pas recalculées ici (décision 0009).
"""

from __future__ import annotations

import hashlib
import json
import math
from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np

from moteur import MODEL_ID
from moteur.boundaries import (
    INTERVAL_POLICY,
    SUM_TOLERANCE_DEG,
    BoundaryError,
    Interval,
    validate_intervals,
)
from moteur.coordinates import frame_matrix, wrap

GENERATED = Path(__file__).resolve().parents[1] / "generes"
BOUNDARIES_FILE = "frontieres.csv"
MANIFEST_FILE = "manifest.json"
CSV_HEADER = "sign_id,start_deg,end_deg,width_deg"
EXPECTED_COUNT = 13
# La matrice R se recalcule à l'identique ; cette marge couvre le dernier chiffre d'une autre
# machine, pas un autre repère (un écart d'obliquité d'un millième de seconde d'arc vaut 5 × 10⁻⁹).
MATRIX_TOLERANCE = 1e-14
# Arrondi admis sur les degrés internes : quelques unités du dernier chiffre d'un angle.
ROUNDING_MARGIN_DEG = 1e-12

# Un intervalle du découpage est le même objet que celui du constructeur de frontières : début
# inclus, fin exclue, bornes canoniques identiques partout (annexe G).
Sign = Interval


class ClassificationError(Exception):
    """Le classement est refusé : longitude indéfinie, découpage invalide, bornes non fiables."""


@dataclass(frozen=True)
class Provenance:
    """D'où viennent les bornes d'un découpage de production, pour le manifeste d'un résultat."""

    model_id: str
    boundaries_file_sha256: str  # empreinte de generes/frontieres.csv
    boundary_source_sha256: str  # empreinte de la grille de Skyfield
    data_status: str  # « candidate » tant que la porte G1 n'est pas franchie


@dataclass(frozen=True)
class Placement:
    """Résultat du classement d'une longitude."""

    sign_id: str
    longitude_deg: float  # ramenée dans [0°, 360°[, sans arrondi
    degrees_in_sign: float  # d : position depuis le début du signe
    fraction_in_sign: float  # p = d / w : position géométrique, pas une intensité
    sign_width_deg: float


class Zodiac:
    """Découpage contigu du cercle en intervalles, contrôlé à la construction."""

    def __init__(
        self,
        signs: Sequence[Sign],
        expected_count: int | None = EXPECTED_COUNT,
        provenance: Provenance | None = None,
    ) -> None:
        self._signs = tuple(signs)
        self._validate(expected_count)
        ordered = tuple(sorted(self._signs, key=lambda sign: sign.start_deg))
        self._starts = tuple(sign.start_deg for sign in ordered)
        self._ordered = ordered
        self.provenance = provenance

    @classmethod
    def from_boundaries(
        cls, boundaries: Sequence[tuple[str, float]], expected_count: int | None = EXPECTED_COUNT
    ) -> Zodiac:
        """Construit le découpage depuis ses débuts : la fin d'un signe est le début du suivant."""
        if any(not math.isfinite(start) for _, start in boundaries):
            raise ClassificationError("découpage invalide : borne non finie")
        signs = []
        for index, (sign_id, start) in enumerate(boundaries):
            end = boundaries[(index + 1) % len(boundaries)][1]
            signs.append(Sign(sign_id, start, end, wrap(end - start)))
        return cls(signs, expected_count)

    @property
    def signs(self) -> tuple[Sign, ...]:
        return self._signs

    def _validate(self, expected_count: int | None) -> None:
        signs = self._signs
        if expected_count is not None and len(signs) != expected_count:
            raise ClassificationError(
                f"découpage invalide : {expected_count} intervalles attendus, {len(signs)} trouvés"
            )
        if len(signs) < 2:
            raise ClassificationError("découpage invalide : au moins deux intervalles")
        if len({sign.sign_id for sign in signs}) != len(signs):
            raise ClassificationError("découpage invalide : un signe apparaît deux fois")
        for sign in signs:
            numbers = (sign.start_deg, sign.end_deg, sign.width_deg)
            if not all(math.isfinite(value) for value in numbers):
                raise ClassificationError(f"découpage invalide : {sign.sign_id}, borne non finie")
            if not (0.0 <= sign.start_deg < 360.0 and 0.0 <= sign.end_deg < 360.0):
                raise ClassificationError(
                    f"découpage invalide : {sign.sign_id}, borne hors [0, 360["
                )
            if sign.width_deg <= 0.0:
                raise ClassificationError(f"découpage invalide : {sign.sign_id}, largeur nulle")
        for index, sign in enumerate(signs):
            following = signs[(index + 1) % len(signs)]
            if sign.end_deg != following.start_deg:
                raise ClassificationError(
                    f"découpage invalide : lacune ou chevauchement entre {sign.sign_id} "
                    f"et {following.sign_id}"
                )
        error = math.fsum(sign.width_deg for sign in signs) - 360.0
        if abs(error) >= SUM_TOLERANCE_DEG:
            raise ClassificationError(
                f"découpage invalide : la somme des largeurs s'écarte de 360° de {error!r}°"
            )
        for sign in signs:
            if sign.width_deg != wrap(sign.end_deg - sign.start_deg):
                raise ClassificationError(
                    f"découpage invalide : {sign.sign_id}, largeur incohérente avec ses bornes"
                )
        # Un tour, un seul : exactement un intervalle revient vers 0°. Les contrôles précédents
        # l'impliquent déjà ; cette garde protège le classement si l'un d'eux venait à changer.
        if sum(1 for sign in signs if sign.end_deg <= sign.start_deg) != 1:
            raise ClassificationError("découpage invalide : lacune ou chevauchement autour de 0°")

    def classify(self, longitude_deg: float | None) -> Placement:
        """Signe, degrés internes et progression d'une longitude du repère B.

        Pour une longitude déjà dans [0°, 360°[, ce que rendent toutes les fonctions du moteur,
        le signe est exactement celui de la définition : bᵢ ≤ λ < bᵢ₊₁. Une longitude négative
        ou supérieure à 360° est d'abord ramenée dans l'intervalle par `wrap`, dont l'addition
        arrondit au dernier chiffre : à moins d'un demi-chiffre sous une frontière, elle peut
        être lue sur la frontière et donc dans le signe qui commence.
        """
        if longitude_deg is None:
            raise ClassificationError(
                "longitude indéfinie (pôle du repère) : aucun signe, pas de signe le plus proche"
            )
        try:
            wrapped = wrap(longitude_deg)
        except ValueError as error:
            raise ClassificationError(f"longitude invalide : {error}") from error
        # Dernier début inférieur ou égal à la longitude ; avant le premier début, c'est
        # l'intervalle qui revient vers 0°, le dernier dans l'ordre des débuts.
        sign = self._ordered[bisect_right(self._starts, wrapped) - 1]
        if wrapped >= sign.start_deg:
            degrees = wrapped - sign.start_deg
        else:
            degrees = (360.0 - sign.start_deg) + wrapped
        # L'arrondi de cette soustraction peut atteindre la largeur elle-même pour le dernier
        # nombre avant la fin du signe. Le signe est déjà décidé ; on garde d < w. Un excès
        # plus grand que l'arrondi ne peut pas venir d'un découpage valide : arrêt.
        if degrees >= sign.width_deg:
            if degrees - sign.width_deg > ROUNDING_MARGIN_DEG:
                raise ClassificationError(
                    f"{sign.sign_id} : position interne supérieure à la largeur du signe"
                )
            degrees = math.nextafter(sign.width_deg, 0.0)
        return Placement(
            sign_id=sign.sign_id,
            longitude_deg=wrapped,
            degrees_in_sign=degrees,
            fraction_in_sign=degrees / sign.width_deg,
            sign_width_deg=sign.width_deg,
        )


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ClassificationError(f"{path.name} illisible : {error}") from error
    if not isinstance(content, dict):
        raise ClassificationError(f"{path.name} : un objet JSON est attendu")
    return content


def _read_intervals(raw: bytes) -> list[Interval]:
    try:
        header, *rows = raw.decode("utf-8").splitlines()
        if header != CSV_HEADER:
            raise ValueError("en-tête inattendu")
        intervals = []
        for row in rows:
            sign_id, start, end, width = row.split(",")
            intervals.append(Interval(sign_id, float(start), float(end), float(width)))
    except (UnicodeDecodeError, ValueError) as error:
        raise ClassificationError(f"{BOUNDARIES_FILE} illisible : {error}") from error
    return intervals


def _section(manifest: dict[str, Any], key: str) -> dict[str, Any]:
    section = manifest.get(key)
    if not isinstance(section, dict):
        raise ClassificationError(f"{MANIFEST_FILE} : la clé `{key}` doit être un objet")
    return section


@cache
def load_canonical(folder: Path = GENERATED) -> Zodiac:
    """Découpage de production : les 13 bornes de generes/frontieres.csv, après contrôle.

    Refuse de classer si le fichier ne correspond pas à l'empreinte du manifeste, si le modèle
    ou la convention des bornes n'est pas celle du moteur, ou si la matrice du manifeste n'est
    pas la matrice R utilisée ici (annexe G : même repère pour les frontières et les positions).

    Le résultat est gardé en mémoire pour la durée du processus : si generes/ est régénéré en
    cours d'exécution, appeler `load_canonical.cache_clear()` pour relire et recontrôler.
    """
    csv_path, manifest_path = folder / BOUNDARIES_FILE, folder / MANIFEST_FILE
    if not csv_path.is_file() or not manifest_path.is_file():
        raise ClassificationError(
            f"{BOUNDARIES_FILE} ou {MANIFEST_FILE} absent de {folder} : "
            "lance scripts/construire_frontieres.py"
        )
    raw = csv_path.read_bytes()
    manifest = _read_manifest(manifest_path)
    entry = _section(manifest, "files").get(BOUNDARIES_FILE)
    declared = entry.get("sha256") if isinstance(entry, dict) else None
    digest = hashlib.sha256(raw).hexdigest()
    if declared != digest:
        raise ClassificationError(
            f"{BOUNDARIES_FILE} : empreinte différente de celle du manifeste ; "
            "régénère avec le script, jamais à la main"
        )
    model = _section(manifest, "model")
    if model.get("id") != MODEL_ID:
        raise ClassificationError(
            f"frontières d'un autre modèle : {model.get('id')!r}, {MODEL_ID!r} attendu"
        )
    if model.get("interval_policy") != INTERVAL_POLICY:
        raise ClassificationError(
            f"frontières d'une autre convention de bornes : {INTERVAL_POLICY!r} attendu"
        )
    try:
        recorded = np.asarray(model.get("matrix_icrs_to_ecliptic"), dtype=np.float64)
        same_frame = recorded.shape == (3, 3) and bool(
            np.abs(recorded - frame_matrix()).max() <= MATRIX_TOLERANCE
        )
    except (TypeError, ValueError):
        same_frame = False
    if not same_frame:
        raise ClassificationError(
            "la matrice du manifeste n'est pas la matrice R du moteur : frontières et positions "
            "ne seraient pas dans le même repère"
        )
    intervals = _read_intervals(raw)
    try:
        validate_intervals(intervals)  # 13 signes, ordre attendu, contiguïté, somme
    except BoundaryError as error:
        raise ClassificationError(f"découpage invalide : {error}") from error
    provenance = Provenance(
        model_id=MODEL_ID,
        boundaries_file_sha256=digest,
        boundary_source_sha256=str(model.get("boundary_sha256", "")),
        data_status=str(manifest.get("data_status", "candidate")),
    )
    return Zodiac(intervals, EXPECTED_COUNT, provenance)
