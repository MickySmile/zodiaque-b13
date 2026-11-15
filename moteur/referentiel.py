"""Référentiel symbolique B13 : lecture et contrôle des 13 fiches de signe (FR-15).

Référence : PRD § 6 (FR-15) ; annexe technique § I ; onglets Serpentaire (§ 1, 6, 9, 11) et
Conséquences (§ 3, 4, 5, 7) ; décision 0013 (schéma des fiches).

Régime « interprétation » : les textes sont transcrits du PRD, jamais rédigés ici. Ce module ne
fait que lire `referentiel/` et refuser ce qui sort du schéma. Une rubrique que le PRD ne
remplit pas reste `missing` : rien n'est écrit à sa place.

Le calcul alimente l'interprétation, jamais l'inverse : aucun module de calcul n'importe celui-ci,
et rien ici ne lit les correspondances historiques pour classer ou interpréter. Elles sont
transportées telles quelles, marquées inactives.

Empreinte : `python -m moteur.referentiel` affiche la ligne attendue dans `referentiel/EMPREINTE`.
Elle lie la version au contenu : une fiche modifiée sans que la version change est refusée.
"""

from __future__ import annotations

import hashlib
import json
from functools import cache
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import AfterValidator, BaseModel, ConfigDict, ValidationError, model_validator

from moteur.boundaries import EXPECTED_ORDER

ROOT = Path(__file__).resolve().parents[1]
REFERENTIEL = ROOT / "referentiel"
SHEETS = "signes"
VERSION_FILE = "VERSION"
DIGEST_FILE = "EMPREINTE"
SCHEMA_FILE = Path("schema") / "fiche.schema.json"
RULES_FILE = "regles.yaml"

Provenance = Literal[
    "H", "M", "C"
]  # héritage documenté, référence mythologique, choix contemporain


def _meaningful(value: str) -> str:
    """Un texte transcrit n'est ni vide, ni fait d'espaces, ni bordé d'espaces."""
    if not value or value != value.strip():
        raise ValueError("texte vide ou bordé d'espaces")
    if not any(char.isalnum() for char in value):
        raise ValueError("texte sans aucune lettre ni chiffre")
    return value


Text = Annotated[str, AfterValidator(_meaningful)]


class ReferentielError(Exception):
    """Le référentiel est absent ou ne respecte pas son schéma : aucune fiche n'est rendue."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _not_empty[T](values: tuple[T, ...]) -> tuple[T, ...]:
    if not values:
        raise ValueError("liste vide")
    return values


class Table(_Strict):
    """Tableau transcrit : ses colonnes et ses lignes, cellule par cellule."""

    columns: Annotated[tuple[Text, ...], AfterValidator(_not_empty)]
    rows: Annotated[tuple[tuple[Text, ...], ...], AfterValidator(_not_empty)]

    @model_validator(mode="after")
    def _same_width(self) -> Table:
        if len(self.columns) < 2 or any(len(row) != len(self.columns) for row in self.rows):
            raise ValueError("au moins deux colonnes, et autant de cellules par ligne")
        return self


class Entry(_Strict):
    """Une rubrique : un texte transcrit du PRD avec sa source et sa provenance, ou `missing`."""

    status: Literal["transcribed", "missing"]
    text: Text | None = None
    items: Annotated[tuple[Text, ...], AfterValidator(_not_empty)] | None = None
    table: Table | None = None
    # Ce que le PRD écrit autour de la rubrique et qui en règle la lecture : la réserve placée
    # à côté de son titre (« jamais des diagnostics »), la phrase qui la clôt. Les omettre
    # changerait le sens du texte transcrit.
    caveat: Text | None = None
    closing: Text | None = None
    source: Text | None = None
    provenance: Annotated[tuple[Provenance, ...], AfterValidator(_not_empty)] | None = None

    @model_validator(mode="after")
    def _coherent(self) -> Entry:
        contents = [value for value in (self.text, self.items, self.table) if value is not None]
        if self.status == "missing":
            around = (self.caveat, self.closing, self.source, self.provenance)
            if contents or any(value is not None for value in around):
                raise ValueError(
                    "une rubrique manquante ne porte ni texte, ni source, ni provenance"
                )
        elif len(contents) != 1 or self.source is None or self.provenance is None:
            raise ValueError(
                "une rubrique transcrite porte un seul contenu, sa source et sa provenance"
            )
        return self

    def strings(self) -> list[str]:
        """Tous les textes de la rubrique, pour les contrôles de transcription."""
        found: list[str] = [value for value in (self.caveat, self.closing) if value is not None]
        if self.text is not None:
            found.append(self.text)
        if self.items is not None:
            found += self.items
        if self.table is not None:
            found += [*self.table.columns, *(cell for row in self.table.rows for cell in row)]
        return found


class Section(Entry):
    """Rubrique complémentaire : une rubrique du PRD hors des quatre de FR-15, sous son nom."""

    label: Text
    status: Literal["transcribed"]


class HistoricalCorrespondences(_Strict):
    """Catégories héritées, consultables et inactives : aucun code ne les lit pour interpréter.

    Tout ou rien : un signe a ses trois correspondances documentées, ou n'en a aucune.
    """

    active: Literal[False]
    element: Text | None
    modality: Text | None
    domicile: Text | None
    source: Text
    provenance: Annotated[tuple[Provenance, ...], AfterValidator(_not_empty)]

    @model_validator(mode="after")
    def _all_or_none(self) -> HistoricalCorrespondences:
        given = [value is not None for value in (self.element, self.modality, self.domicile)]
        if any(given) and not all(given):
            raise ValueError("correspondances historiques : les trois valeurs, ou aucune")
        return self


class SignSheet(_Strict):
    """Fiche d'un signe. Le même schéma pour les 13 : aucun champ propre à un signe."""

    schema_version: Literal[1]
    sign_id: Text
    name: Text
    operation: Entry
    archetype: Entry
    resources: Entry
    tensions: Entry
    introspection_question: Entry
    forbidden_inferences: Entry
    additional_sections: tuple[Section, ...]
    historical_correspondences: HistoricalCorrespondences

    @model_validator(mode="after")
    def _distinct_labels(self) -> SignSheet:
        labels = [section.label for section in self.additional_sections]
        if len(labels) != len(set(labels)):
            raise ValueError("deux rubriques complémentaires portent le même nom")
        return self

    def core(self) -> dict[str, Entry]:
        """Les rubriques communes, par nom de champ."""
        return {
            "operation": self.operation,
            "archetype": self.archetype,
            "resources": self.resources,
            "tensions": self.tensions,
            "introspection_question": self.introspection_question,
            "forbidden_inferences": self.forbidden_inferences,
        }

    def missing(self) -> tuple[str, ...]:
        """Rubriques communes que le PRD ne remplit pas pour ce signe."""
        return tuple(name for name, entry in self.core().items() if entry.status == "missing")


class CommonRules(_Strict):
    """Règles et statuts qui valent pour les 13 signes, transcrits du PRD."""

    schema_version: Literal[1]
    common_rules: Entry
    general_policy: Entry
    inherited_categories_decision: Entry
    historical_heritage: Entry


class Referentiel(_Strict):
    """Le référentiel chargé : sa version, ses 13 fiches dans l'ordre du cercle, ses règles."""

    version: Text
    sha256: Text
    sheets: tuple[SignSheet, ...]
    rules: CommonRules

    def sheet(self, sign_id: str) -> SignSheet:
        for sheet in self.sheets:
            if sheet.sign_id == sign_id:
                return sheet
        raise ReferentielError(f"aucune fiche pour le signe {sign_id!r}")

    def missing(self) -> dict[str, tuple[str, ...]]:
        """Rubriques manquantes par signe : la liste à transmettre au rédacteur."""
        return {sheet.sign_id: sheet.missing() for sheet in self.sheets if sheet.missing()}


def sheet_json_schema() -> dict[str, Any]:
    """Schéma JSON d'une fiche, dérivé du modèle : `referentiel/schema/fiche.schema.json`.

    Il décrit les champs et leurs types ; les contrôles de cohérence (un seul contenu par
    rubrique, tout ou rien pour les correspondances) sont dans les modèles ci-dessus.
    """
    return SignSheet.model_json_schema()


class _UniqueKeys(yaml.SafeLoader):  # type: ignore[misc]  # PyYAML est livré sans annotations
    """Lecteur YAML qui refuse une clé écrite deux fois, au lieu de garder la dernière."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        keys = [self.construct_object(key, deep=deep) for key, _ in node.value]
        if len(keys) != len(set(keys)):
            raise yaml.YAMLError("clé écrite deux fois")
        mapping: dict[Any, Any] = super().construct_mapping(node, deep=deep)
        return mapping


def _read_yaml(path: Path) -> object:
    try:
        # Lecteur dérivé de SafeLoader : aucune construction d'objet arbitraire.
        return yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeys)
    except (OSError, UnicodeError, TypeError, yaml.YAMLError) as error:
        raise ReferentielError(f"{path.name} illisible") from error


def _sheet_files(folder: Path) -> list[Path]:
    """Fichiers de `signes/`, triés. Les fichiers cachés du système (« .DS_Store ») sont ignorés :
    ils ne sont ni des fiches ni du contenu."""
    return sorted(path for path in (folder / SHEETS).glob("*") if not path.name.startswith("."))


def _content_files(folder: Path) -> list[Path]:
    """Les fichiers dont le contenu fait le référentiel : les fiches et les règles."""
    return [*_sheet_files(folder), folder / RULES_FILE]


def digest(folder: Path = REFERENTIEL) -> str:
    """Empreinte SHA-256 des fiches et des règles, noms de fichiers compris."""
    sha = hashlib.sha256()
    try:
        for path in _content_files(folder):
            sha.update(path.name.encode("utf-8") + b"\0" + path.read_bytes() + b"\0")
    except OSError as error:
        raise ReferentielError("fichier du référentiel illisible") from error
    return sha.hexdigest()


def load(folder: Path = REFERENTIEL) -> Referentiel:
    """Lit et contrôle le référentiel : 13 fiches, une par signe du moteur, au même schéma."""
    try:
        version = (folder / VERSION_FILE).read_text(encoding="utf-8").strip()
        recorded = (folder / DIGEST_FILE).read_text(encoding="utf-8").split()
        declared = json.loads((folder / SCHEMA_FILE).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReferentielError("version, empreinte ou schéma absents ou illisibles") from error
    if declared != sheet_json_schema():
        raise ReferentielError("le schéma des fiches ne correspond plus au modèle qui les lit")
    # Un fichier par signe, nommé par son identifiant en minuscules : même règle pour les 13.
    expected = sorted(f"{sign_id.lower()}.yaml" for sign_id in EXPECTED_ORDER)
    present = [path.name for path in _sheet_files(folder)]
    if present != expected:
        raise ReferentielError("referentiel/signes/ doit contenir exactement les 13 fiches")
    sha256 = digest(folder)
    if recorded != [version, sha256]:
        raise ReferentielError(
            "le contenu du référentiel ne correspond plus à son empreinte : toute modification "
            "change referentiel/VERSION, puis referentiel/EMPREINTE"
        )
    sheets: list[SignSheet] = []
    try:
        for sign_id in EXPECTED_ORDER:
            path = folder / SHEETS / f"{sign_id.lower()}.yaml"
            sheet = SignSheet.model_validate(_read_yaml(path))
            if sheet.sign_id != sign_id:
                raise ReferentielError(f"{path.name} : identifiant de signe inattendu")
            sheets.append(sheet)
        rules = CommonRules.model_validate(_read_yaml(folder / RULES_FILE))
        return Referentiel(version=version, sha256=sha256, sheets=tuple(sheets), rules=rules)
    except ValidationError as error:
        # Seul le nombre de défauts sort : le détail reste dans l'exception d'origine.
        raise ReferentielError(f"fiche hors schéma : {error.error_count()} défaut(s)") from error


@cache
def load_canonical() -> Referentiel:
    """Référentiel du dépôt, lu et contrôlé une fois par processus.

    Une fiche modifiée pendant que le serveur tourne n'est lue qu'à son redémarrage.
    """
    return load()


if __name__ == "__main__":
    print((REFERENTIEL / VERSION_FILE).read_text(encoding="utf-8").strip(), digest())
