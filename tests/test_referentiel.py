"""Référentiel B13 — 13 fiches de signe au même schéma, transcrites du PRD (FR-15).

Référence : PRD § 6 (FR-15 : « archétype, ressources, tensions, question d'introspection et
provenance de chaque règle (H, M ou C) ») ; onglets Serpentaire (§ 1, 6, 9, 11) et Conséquences
(§ 3, 4, 5, 7, 9) ; annexe technique § I ; décision 0013 ; règle `.claude/rules/referentiel.md`.

Le contrôle central : chaque texte d'une fiche est une cellule entière, une ligne entière ou une
puce entière de la section du PRD qu'il cite, et, dans un tableau, de la ligne de son propre
signe ou de sa propre rubrique. Rien n'est rédigé dans `referentiel/` ; ce que le PRD ne dit pas
reste `missing`.
"""

from __future__ import annotations

import json
import re
import shutil
from functools import cache
from pathlib import Path

import pytest
import yaml

from api.catalogue import SIGN_LABELS
from moteur import referentiel
from moteur.boundaries import EXPECTED_ORDER
from moteur.referentiel import Entry, ReferentielError, Section, SignSheet

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "referentiel"
SOURCE = re.compile(r"^(docs/prd/[\w.-]+\.md) § (\d+|[A-K])$")
CORE = (
    "operation",
    "archetype",
    "resources",
    "tensions",
    "introspection_question",
    "forbidden_inferences",
)
# Décision 0013 : de quelle colonne (tableau rangé par signe) ou de quelle ligne (tableau rangé
# par rubrique) du PRD vient chaque rubrique commune. Une rubrique complémentaire vient de la
# colonne ou de la ligne qui porte son libellé.
DECLARED_COLUMNS = {
    "operation": "Opération B13 (active)",
    "tensions": "Tension",
    "introspection_question": "Question",
}
DECLARED_ROWS = {
    "operation": "Opération centrale",
    "archetype": "Archétype",
    "resources": "Ressources",
    "tensions": "Tension distinctive",
    "introspection_question": "Question d'introspection",
}
SIGN_COLUMN = "Signe"


def normalise(text: str) -> str:
    """Texte sans marques d'emphase Markdown, espaces réduits : la forme comparée au PRD."""
    return " ".join(text.replace("**", "").replace("*", "").split())


def cells(line: str) -> list[str]:
    return [normalise(cell) for cell in line.strip().strip("|").split("|")]


class Cited:
    """Une section du PRD : ses lignes, ses titres en gras, ses listes à puces, ses tableaux."""

    def __init__(self, path: str, number: str) -> None:
        lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
        start = next(
            index
            for index, line in enumerate(lines)
            if re.match(rf"^## {re.escape(number)}\. ", line)
        )
        end = next(
            (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
            len(lines),
        )
        body = lines[start:end]
        self.text = normalise("\n".join(body))
        self.lines = [normalise(line) for line in body if line.strip()]
        # Titres en gras en début de ligne : « **Excès possibles** — … ».
        self.bold_titles = {
            normalise(found.group(1))
            for line in body
            if (found := re.match(r"^\*\*([^*]+)\*\*", line))
        }
        # Listes à puces, chacune sous la dernière ligne de texte qui la précède.
        self.bullet_lists: list[tuple[str, list[str]]] = []
        # Tableaux : la ligne d'en-tête (celle que suit la ligne de tirets), puis les lignes.
        self.tables: list[tuple[list[str], list[list[str]]]] = []
        previous = ""
        for index, line in enumerate(body):
            if line.startswith("- "):
                if not self.bullet_lists or self.bullet_lists[-1][0] != previous:
                    self.bullet_lists.append((previous, []))
                self.bullet_lists[-1][1].append(normalise(line[2:]))
                continue
            if line.startswith("|"):
                separator = set(line) <= set("|- :")
                following = body[index + 1] if index + 1 < len(body) else ""
                if not separator and set(following) <= set("|- :") and following.startswith("|"):
                    self.tables.append((cells(line), []))
                elif not separator and self.tables:
                    self.tables[-1][1].append(cells(line))
                continue
            if line.strip():
                previous = normalise(line)

    def cell(self, key: str, column: str) -> list[str]:
        """Cellules de la colonne `column` sur les lignes dont la première cellule est `key`
        (ou « key — … »), dans les tableaux rangés par signe."""
        found = []
        for header, rows in self.tables:
            if header[0] != SIGN_COLUMN or column not in header:
                continue
            found += [
                row[header.index(column)]
                for row in rows
                if row[0] == key or row[0].startswith(f"{key} — ")
            ]
        return found

    def value(self, rubric: str) -> list[str]:
        """Valeur (deuxième cellule) des lignes nommées `rubric`, dans les tableaux rangés par
        rubrique."""
        return [
            row[1]
            for header, rows in self.tables
            if header[0] != SIGN_COLUMN
            for row in rows
            if row[0] == rubric
        ]

    def rubric_names(self) -> set[str]:
        """Intitulés de rubrique de la section : en-têtes de colonne des tableaux rangés par
        signe, premières cellules des autres tableaux, titres en gras."""
        names = set(self.bold_titles)
        for header, rows in self.tables:
            names |= set(header[1:]) if header[0] == SIGN_COLUMN else {row[0] for row in rows}
        return names


@cache
def section(path: str, number: str) -> Cited:
    return Cited(path, number)


def cited(source: str | None) -> Cited:
    match = SOURCE.match(source or "")
    assert match, f"source mal formée : {source!r}"
    return section(match.group(1), match.group(2))


def entries(sheet: SignSheet) -> list[tuple[str, Entry]]:
    named: list[tuple[str, Entry]] = list(sheet.core().items())
    named += [(item.label, item) for item in sheet.additional_sections]
    return named


@cache
def loaded() -> referentiel.Referentiel:
    return referentiel.load()


def raw(sign_id: str) -> dict[str, object]:
    data = yaml.safe_load((FOLDER / "signes" / f"{sign_id.lower()}.yaml").read_text("utf-8"))
    assert isinstance(data, dict)
    return data


def allowed_texts(sheet: SignSheet, name: str, entry: Entry, source: Cited) -> list[str]:
    """Les seuls textes que le PRD donne à cette rubrique de ce signe : la cellule de sa colonne
    sur la ligne du signe, la valeur de sa ligne dans un tableau par rubrique, ou la ligne de
    texte qui commence par son libellé."""
    label = normalise(entry.label) if isinstance(entry, Section) else None
    column = label or DECLARED_COLUMNS.get(name)
    rubric = label or DECLARED_ROWS.get(name)
    found: list[str] = []
    if column is not None:
        found += source.cell(normalise(sheet.name), column)
    if rubric is not None:
        found += source.value(normalise(rubric))
    if label is not None:
        found += [line for line in source.lines if line.startswith(f"{label}, ")]
    return found


# --- Treize fiches, un seul schéma ---------------------------------------------------------------


def test_fr_15_thirteen_sheets_one_per_engine_sign_in_circle_order() -> None:
    sheets = loaded().sheets
    assert [sheet.sign_id for sheet in sheets] == list(EXPECTED_ORDER)
    assert len(sheets) == 13
    for sheet in sheets:
        assert sheet.name == SIGN_LABELS[sheet.sign_id].name


def test_fr_15_the_thirteen_sheets_share_one_schema() -> None:
    shapes = {tuple(raw(sign_id)) for sign_id in EXPECTED_ORDER}
    assert len(shapes) == 1  # mêmes champs, dans le même ordre : aucun en plus, aucun en moins
    assert set(next(iter(shapes))) == set(SignSheet.model_fields)
    historical = {
        tuple(raw(sign_id)["historical_correspondences"])  # type: ignore[arg-type]
        for sign_id in EXPECTED_ORDER
    }
    assert len(historical) == 1


def test_fr_15_schema_file_is_the_model_that_reads_the_sheets() -> None:
    declared = json.loads((FOLDER / "schema" / "fiche.schema.json").read_text(encoding="utf-8"))
    assert declared == referentiel.sheet_json_schema()


def test_referentiel_reader_has_no_sign_specific_branch() -> None:
    source = (ROOT / "moteur" / "referentiel.py").read_text(encoding="utf-8")
    for sign_id in EXPECTED_ORDER:
        assert f'"{sign_id}"' not in source and f"'{sign_id}'" not in source
    assert "erpentaire" not in source.split('"""', 2)[2]


def test_calculation_never_reads_the_symbolic_referentiel() -> None:
    """Le calcul alimente l'interprétation, jamais l'inverse (PRD § 5)."""
    for module in (ROOT / "moteur").glob("*.py"):
        if module.name == "referentiel.py":
            continue
        assert "referentiel" not in module.read_text(encoding="utf-8"), module.name


# --- Transcrire, jamais rédiger -------------------------------------------------------------------


@pytest.mark.parametrize("sign_id", EXPECTED_ORDER)
def test_fr_15_every_text_comes_from_its_own_cell_of_the_cited_section(sign_id: str) -> None:
    """Chaque texte est la cellule de sa propre colonne sur la ligne de son propre signe (ou la
    valeur de sa propre ligne dans un tableau par rubrique) : jamais un fragment, jamais la
    cellule d'une autre rubrique ni celle d'un autre signe. Une liste est reprise en entier."""
    sheet = loaded().sheet(sign_id)
    checked = 0
    for name, entry in entries(sheet):
        if entry.status == "missing":
            continue
        source = cited(entry.source)
        where = f"{sign_id} · {name} ({entry.source})"
        label = normalise(entry.label) if isinstance(entry, Section) else None
        if entry.text is not None:
            assert normalise(entry.text) in allowed_texts(sheet, name, entry, source), where
            checked += 1
        if entry.items is not None:
            listed = [normalise(item) for item in entry.items]
            under_title = [
                bullets
                for title, bullets in source.bullet_lists
                if label is not None and title.startswith(label)
            ]
            # La liste à puces entière placée sous le titre de la rubrique, sans puce en moins ;
            # ou la liste telle qu'elle est écrite dans une phrase, close par un point.
            assert listed in under_title or f") : {', '.join(listed)}." in source.text, where
            checked += len(listed)
        if entry.table is not None:
            columns = [normalise(cell) for cell in entry.table.columns]
            rows = [[normalise(cell) for cell in row] for row in entry.table.rows]
            # Le tableau entier : son en-tête et toutes ses lignes, dans l'ordre.
            assert (columns, rows) in source.tables, where
            checked += len(rows)
    assert checked >= 10  # une fiche vide ne passerait pas pour une fiche transcrite


@pytest.mark.parametrize("sign_id", EXPECTED_ORDER)
def test_fr_15_section_labels_are_rubric_names_of_the_prd(sign_id: str) -> None:
    """Un libellé de rubrique complémentaire est un intitulé du PRD : un en-tête de colonne, le
    nom d'une ligne dans un tableau par rubrique, ou un titre en gras. Jamais un nom inventé."""
    for item in loaded().sheet(sign_id).additional_sections:
        names = cited(item.source).rubric_names()
        assert normalise(item.label) in names, (
            f"{sign_id} · libellé « {item.label} » absent de {item.source}"
        )


@pytest.mark.parametrize("sign_id", EXPECTED_ORDER)
def test_fr_15_caveats_and_closing_sentences_are_kept_whole_with_their_rubric(sign_id: str) -> None:
    """La réserve que le PRD place à côté d'un titre, entière, et la phrase qui clôt la rubrique."""
    for name, entry in entries(loaded().sheet(sign_id)):
        if entry.status == "missing":
            continue
        source = cited(entry.source)
        if entry.caveat is not None:
            # La ligne du titre, entière : « Titre — réserve : ». Une réserve tronquée ne passe pas.
            assert f"{normalise(name)} — {normalise(entry.caveat)} :" in source.lines, name
        if entry.closing is not None:
            assert normalise(entry.closing) in source.lines, name


def test_fr_15_no_caveat_of_the_cited_sections_is_dropped() -> None:
    """Toute rubrique transcrite dont le titre porte une réserve dans le PRD (« Titre — … : »)
    la reprend : l'omettre changerait la lecture du texte."""
    found = 0
    for sheet in loaded().sheets:
        for item in sheet.additional_sections:
            source = cited(item.source)
            label = normalise(item.label)
            if any(line.startswith(f"{label} — ") for line in source.lines):
                assert item.caveat is not None, (sheet.sign_id, item.label)
                found += 1
    assert found >= 2  # le contrôle porte bien sur des rubriques réelles


@pytest.mark.parametrize("sign_id", EXPECTED_ORDER)
def test_fr_15_every_transcribed_entry_names_its_source_and_provenance(sign_id: str) -> None:
    for name, entry in entries(loaded().sheet(sign_id)):
        if entry.status == "missing":
            assert entry.strings() == [] and entry.source is None and entry.provenance is None
            continue
        assert SOURCE.match(entry.source or ""), name
        assert entry.provenance and set(entry.provenance) <= {"H", "M", "C"}, name


def test_fr_15_serpentaire_sheet_shows_the_four_rubrics_of_the_requirement() -> None:
    sheet = loaded().sheet("Oph")
    assert sheet.archetype.text == "Le praticien qui reste apprenant"
    for name in ("archetype", "resources", "tensions", "introspection_question"):
        assert sheet.core()[name].status == "transcribed", name
    assert sheet.missing() == ()


def test_fr_15_every_sheet_has_its_operation_tension_and_question() -> None:
    for sheet in loaded().sheets:
        for name in ("operation", "tensions", "introspection_question"):
            assert sheet.core()[name].status == "transcribed", (sheet.sign_id, name)
        assert sheet.additional_sections, sheet.sign_id


def test_fr_15_the_operations_are_the_thirteen_of_the_circle_sequence() -> None:
    """Treize opérations distinctes, une par signe (onglet Conséquences § 7)."""
    operations = [sheet.operation.text for sheet in loaded().sheets]
    assert len(set(operations)) == 13 and None not in operations


def test_fr_15_missing_rubrics_are_listed_never_filled() -> None:
    """Décision 0013 : le PRD ne donne ni archétype, ni ressources, ni inférences interdites
    aux douze signes révisés. Ces rubriques restent vides ; la liste va au rédacteur."""
    missing = loaded().missing()
    assert set(missing) == set(EXPECTED_ORDER) - {"Oph"}
    for fields in missing.values():
        assert fields == ("archetype", "resources", "forbidden_inferences")
    listing = (ROOT / "docs" / "referentiel" / "champs-manquants.md").read_text(encoding="utf-8")
    for sign_id in missing:
        assert f"| {SIGN_LABELS[sign_id].name} | manquant | manquant | manquant |" in listing
    assert f"**{sum(len(fields) for fields in missing.values())} rubriques**" in listing
    assert loaded().version in listing


def test_forbidden_inferences_of_the_serpentaire_are_the_five_of_the_prd() -> None:
    entry = loaded().sheet("Oph").forbidden_inferences
    assert entry.items is not None
    sentence = cited(entry.source).text
    assert f") : {', '.join(entry.items)}." in sentence
    # La règle structurée du § 12 en liste autant.
    block = section("docs/prd/02-serpentaire.md", "12").text
    structured = block.split('"forbidden_inferences": [', 1)[1].split("]", 1)[0]
    assert len(re.findall(r'"\w+"', structured)) == len(entry.items) == 5


# --- Catégories héritées : consultables, inactives ------------------------------------------------


def test_historical_correspondences_come_from_the_row_of_their_own_sign() -> None:
    inherited = section("docs/prd/03-consequences.md", "3")
    column = "Élément · modalité (inactifs)"
    for sheet in loaded().sheets:
        block = sheet.historical_correspondences
        source = cited(block.source)
        assert block.provenance == ("H",)
        documented = inherited.cell(sheet.name, column)
        if block.element is None:
            # Aucune catégorie héritée : seulement pour un signe que le tableau des catégories
            # héritées ne connaît pas, et la section citée le dit pour chacune.
            assert documented == [], f"{sheet.sign_id} : catégories documentées, non transcrites"
            assert block.modality is None and block.domicile is None
            assert source.value("Élément, modalité, polarité") == ["Aucune"]
            assert source.value("Domicile, exaltation, exil, chute") == ["Aucun"]
            continue
        assert source is inherited, sheet.sign_id
        assert documented == [f"{block.element} · {block.modality}"], sheet.sign_id
        assert source.cell(sheet.name, "Domicile ancien (inactif)") == [block.domicile]


def test_historical_words_are_only_keys_of_the_inactive_block() -> None:
    inherited = {"element", "modality", "polarity", "ruler", "domicile", "dignity", "exaltation"}
    for sign_id in EXPECTED_ORDER:
        text = (FOLDER / "signes" / f"{sign_id.lower()}.yaml").read_text(encoding="utf-8")
        in_block = False
        for line in text.splitlines():
            if not line.startswith(" "):
                in_block = line.startswith("historical_correspondences:")
            key = line.strip().split(":", 1)[0]
            assert key not in inherited or in_block, f"{sign_id} : « {key} » hors du bloc inactif"


# --- Le lecteur refuse ce qui sort du schéma -----------------------------------------------------


@pytest.fixture
def copy(tmp_path: Path) -> Path:
    target = tmp_path / "referentiel"
    shutil.copytree(FOLDER, target)
    return target


def reseal(folder: Path) -> None:
    """Remet l'empreinte à jour, pour éprouver un autre contrôle que celui de l'empreinte."""
    version = (folder / "VERSION").read_text(encoding="utf-8").strip()
    (folder / "EMPREINTE").write_text(f"{version} {referentiel.digest(folder)}\n", "utf-8")


def rewrite(folder: Path, sign_id: str, change: dict[str, object]) -> None:
    path = folder / "signes" / f"{sign_id.lower()}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data.update(change)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    reseal(folder)


def entry_of(sign_id: str, name: str) -> dict[str, object]:
    return dict(raw(sign_id)[name])  # type: ignore[call-overload]


def test_loader_reads_an_untouched_copy(copy: Path) -> None:
    assert len(referentiel.load(copy).sheets) == 13


def test_loader_reads_a_resealed_copy(copy: Path) -> None:
    reseal(copy)
    assert referentiel.load(copy).sha256 == loaded().sha256


def test_loader_refuses_a_field_proper_to_one_sign(copy: Path) -> None:
    rewrite(copy, "Oph", {"special_power": "aucun signe n'a de champ en plus"})
    with pytest.raises(ReferentielError):
        referentiel.load(copy)


def test_loader_refuses_an_active_inherited_category(copy: Path) -> None:
    block = entry_of("Ari", "historical_correspondences")
    rewrite(copy, "Ari", {"historical_correspondences": {**block, "active": True}})
    with pytest.raises(ReferentielError):
        referentiel.load(copy)


def test_loader_refuses_partial_historical_correspondences(copy: Path) -> None:
    block = entry_of("Ari", "historical_correspondences")
    rewrite(copy, "Ari", {"historical_correspondences": {**block, "modality": None}})
    with pytest.raises(ReferentielError):
        referentiel.load(copy)


def test_loader_refuses_a_text_without_source(copy: Path) -> None:
    rewrite(copy, "Tau", {"archetype": {"status": "transcribed", "text": "Texte sans source"}})
    with pytest.raises(ReferentielError):
        referentiel.load(copy)


@pytest.mark.parametrize("field", ["text", "caveat", "closing", "source"])
def test_loader_refuses_a_missing_rubric_that_carries_anything(copy: Path, field: str) -> None:
    rewrite(copy, "Tau", {"archetype": {"status": "missing", field: "Texte glissé là"}})
    with pytest.raises(ReferentielError):
        referentiel.load(copy)


def test_loader_ignores_hidden_system_files(copy: Path) -> None:
    """Un « .DS_Store » posé par le Finder n'est ni une fiche ni du contenu."""
    (copy / "signes" / ".DS_Store").write_bytes(b"\x00\x01")
    loaded_copy = referentiel.load(copy)
    assert len(loaded_copy.sheets) == 13 and loaded_copy.sha256 == loaded().sha256


@pytest.mark.parametrize("text", ["", " ", "*", "—", " Texte bordé d'espaces "])
def test_loader_refuses_an_empty_or_meaningless_text(copy: Path, text: str) -> None:
    rewrite(copy, "Tau", {"tensions": {**entry_of("Tau", "tensions"), "text": text}})
    with pytest.raises(ReferentielError):
        referentiel.load(copy)


def test_loader_refuses_a_section_without_source_or_with_a_duplicate_label(copy: Path) -> None:
    sections = list(raw("Gem")["additional_sections"])  # type: ignore[call-overload]
    without_source = {key: value for key, value in sections[0].items() if key != "source"}
    rewrite(copy, "Gem", {"additional_sections": [without_source, *sections[1:]]})
    with pytest.raises(ReferentielError):
        referentiel.load(copy)
    rewrite(copy, "Gem", {"additional_sections": [sections[0], sections[0]]})
    with pytest.raises(ReferentielError):
        referentiel.load(copy)


def test_loader_refuses_a_missing_sheet(copy: Path) -> None:
    (copy / "signes" / "gem.yaml").unlink()
    reseal(copy)
    with pytest.raises(ReferentielError):
        referentiel.load(copy)


def test_loader_refuses_a_fourteenth_file(copy: Path) -> None:
    shutil.copy(copy / "signes" / "gem.yaml", copy / "signes" / "quatorzieme.yaml")
    reseal(copy)
    with pytest.raises(ReferentielError):
        referentiel.load(copy)
    (copy / "signes" / "quatorzieme.yaml").rename(copy / "signes" / "notes.txt")
    reseal(copy)
    with pytest.raises(ReferentielError):
        referentiel.load(copy)


def test_loader_refuses_a_sheet_under_the_wrong_name(copy: Path) -> None:
    rewrite(copy, "Leo", {"sign_id": "Vir"})
    with pytest.raises(ReferentielError):
        referentiel.load(copy)


def test_loader_refuses_a_schema_file_that_drifted(copy: Path) -> None:
    (copy / "schema" / "fiche.schema.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ReferentielError):
        referentiel.load(copy)


def test_loader_refuses_a_key_written_twice(copy: Path) -> None:
    path = copy / "signes" / "vir.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "name: Autre nom\n", encoding="utf-8")
    reseal(copy)
    with pytest.raises(ReferentielError):
        referentiel.load(copy)


def test_loader_refuses_a_file_that_is_not_utf8(copy: Path) -> None:
    (copy / "signes" / "lib.yaml").write_bytes(b"name: \xff\xfe\n")
    reseal(copy)
    with pytest.raises(ReferentielError):
        referentiel.load(copy)


# --- Version liée au contenu ----------------------------------------------------------------------


def test_referentiel_version_names_the_ruleset_of_the_prd() -> None:
    version = loaded().version
    assert version == (FOLDER / "VERSION").read_text(encoding="utf-8").strip()
    assert version.startswith("b13_symbolic_v1")  # identifiant du jeu de règles, annexe § F


def test_referentiel_digest_is_recorded_beside_its_version() -> None:
    recorded = (FOLDER / "EMPREINTE").read_text(encoding="utf-8").split()
    assert recorded == [loaded().version, referentiel.digest()]
    assert loaded().sha256 == recorded[1] and len(recorded[1]) == 64


@pytest.mark.parametrize("target", ["signes/sgr.yaml", "regles.yaml"])
def test_an_unsealed_change_is_refused(copy: Path, target: str) -> None:
    """Une fiche ou une règle retouchée sans que l'empreinte soit refaite ne se charge pas. (Le
    contrôle ne peut pas voir une retouche rescellée sous le même nom de version : l'empreinte,
    rendue par l'API avec la version, distingue alors les deux contenus.)"""
    path = copy / target
    path.write_text(path.read_text(encoding="utf-8") + "# retouche\n", encoding="utf-8")
    with pytest.raises(ReferentielError):
        referentiel.load(copy)


def test_common_rules_are_whole_units_of_the_prd() -> None:
    rules = loaded().rules
    common = cited(rules.common_rules.source)
    listed = [normalise(item) for item in rules.common_rules.items or ()]
    # Les six puces placées sous « Règles communes obligatoires », toutes, dans l'ordre.
    assert ("Règles communes obligatoires", listed) in common.bullet_lists and len(listed) == 6
    policy = cited(rules.general_policy.source)
    line = f"Politique générale pour les 12 signes : {normalise(rules.general_policy.text or '')}"
    assert line in policy.lines
    decision = cited(rules.inherited_categories_decision.source)
    assert normalise(rules.inherited_categories_decision.text or "") in decision.lines
    heritage = cited(rules.historical_heritage.source)
    assert heritage.value("Héritage historique") == [
        normalise(rules.historical_heritage.text or "")
    ]


# --- Jeu F8 : phrases à remplacer (onglet Conséquences § 9 et § 3) -----------------------------


def plain(text: str) -> str:
    """Forme de comparaison du jeu F8 : apostrophes ramenées à « ' », espaces réduits."""
    return normalise(text).replace("’", "'").replace(" ", " ")


def quoted(text: str) -> list[str]:
    return [plain(found) for found in re.findall(r"« ([^»]+) »", text)]


def phrases_to_replace() -> list[str]:
    """Colonne « Ne plus écrire » du § 9 et « Règles devenues inapplicables » du § 3."""
    lines = (ROOT / "docs/prd/03-consequences.md").read_text(encoding="utf-8").splitlines()
    start = lines.index("| Ne plus écrire | Écrire plutôt |")
    banned: list[str] = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        banned += quoted(line.split("|")[1])
    start = next(i for i, line in enumerate(lines) if line.startswith("**Règles devenues inapp"))
    for line in lines[start + 1 :]:
        if line.startswith("- "):
            banned += quoted(line)
        elif line.strip() and banned:
            break
    return banned


def visible_files() -> list[Path]:
    """Ce qui peut arriver à l'écran : référentiel, API, messages du moteur, interface."""
    files = [*FOLDER.rglob("*.yaml"), *(ROOT / "api").glob("*.py"), *(ROOT / "moteur").glob("*.py")]
    files += [
        path
        for path in (ROOT / "web" / "src").rglob("*")
        if path.suffix in {".ts", ".tsx", ".css"} and ".test." not in path.name
    ]
    return files


def test_f8_the_prd_lists_phrases_to_replace() -> None:
    banned = phrases_to_replace()
    assert len(banned) == 9  # trois phrases du § 9, six règles inapplicables du § 3
    assert all(len(phrase) > 20 for phrase in banned)


def test_f8_phrases_to_replace_are_absent_from_interface_and_referentiel() -> None:
    banned = phrases_to_replace()
    files = visible_files()
    assert len(files) > 30
    for path in files:
        content = plain(path.read_text(encoding="utf-8"))
        for phrase in banned:
            # Avec ou sans la ponctuation finale, quelle que soit l'apostrophe employée.
            assert phrase.rstrip(".") not in content, f"{path.relative_to(ROOT)} : {phrase!r}"


def test_f8_the_check_sees_a_banned_phrase_whatever_its_apostrophe() -> None:
    banned = phrases_to_replace()
    typographic = next(phrase for phrase in banned if "'" in phrase).replace("'", "’")
    assert any(phrase.rstrip(".") in plain(f"Texte : « {typographic} »") for phrase in banned)
