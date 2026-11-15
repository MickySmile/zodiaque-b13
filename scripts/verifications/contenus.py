"""Contrôles de contenu du dépôt Zodiaque B13 (bibliothèque standard seule, Python 3.11+).

Appelé par scripts/verifier.sh. Sort en code 1 au premier constat, après les avoir tous listés.
Ces contrôles sont un plancher : la relecture du sous-agent gardien-contenus reste nécessaire.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
NOM_PROJET = "zodiaque-b13"

# A. Bibliothèques d'astrologie : elles supposent 12 × 30°, éléments, maîtrises, signe opposé par le nom.
DEPENDANCES_INTERDITES = re.compile(
    r"(astrolog|horoscop|natal[-_]?chart|swisseph|sweph|flatlib|kerykeion|immanuel|astrochart|zodiac)",
    re.IGNORECASE,
)

# B. Vocabulaire de l'interface (onglets Serpentaire et Conséquences, écarts des planches).
VOCABULAIRE_INTERDIT = [
    (re.compile(r"\b(th[eè]me|roue|mode|d[ée]coupage|signe|vue)s?\s+tropica", re.IGNORECASE),
     "le découpage de comparaison s'appelle « témoin 12 × 30° »"),
    (re.compile(r"[\"'>]\s*Tropical\s*[\"'<]"), "étiquette « Tropical » : écrire « témoin 12 × 30° »"),
    (re.compile(r"ma[iî]tre(sse)?\s+du\s+th[eè]me", re.IGNORECASE), "déduction abandonnée : maître du thème"),
    (re.compile(r"signe\s+oppos[ée]", re.IGNORECASE), "l'opposition se calcule par arcs, jamais par le nom du signe"),
    (re.compile(r"dominante\s+d'[ée]l[ée]ment", re.IGNORECASE), "catégorie héritée inactive : élément"),
    (re.compile(r"signes?\s+(de\s+feu|d'eau|de\s+terre|d'air)", re.IGNORECASE), "catégorie héritée inactive : élément"),
    (re.compile(r"zone\s+de\s+cuspide", re.IGNORECASE), "aucune zone de cuspide : début inclus, fin exclue"),
    (re.compile(r"m[êe]me\s+[ée]l[ée]ment", re.IGNORECASE), "catégorie héritée inactive : accord « par élément »"),
    (re.compile(r"vous\s+pensiez\s+[êe]tre", re.IGNORECASE), "formulation à remplacer (Conséquences § 8) : « dans le référentiel à douze signes… »"),
    (re.compile(r"compatibilit[ée]", re.IGNORECASE), "l'arc opposé n'est jamais nommé « compatibilité » (FR-11)"),
    (re.compile(r"votre\s+destin|vous\s+[êe]tes\s+destin[ée]", re.IGNORECASE), "aucune affirmation déterministe"),
    (re.compile("⛎️"), "⛎ en présentation emoji : utiliser U+FE0E ou aucun sélecteur"),
]

# B bis. Référentiel : catégories héritées seulement sous historical_correspondences (active: false).
CLE_HERITEE = re.compile(r"^(\s*)-?\s*(element|elements|modality|modalities|ruler|rulers|rulership|dignity|dignities|domicile|exaltation|detriment|fall)\s*:", re.IGNORECASE)
CLE_YAML = re.compile(r"^(\s*)-?\s*([A-Za-z_][\w-]*)\s*:")
BLOC_HISTORIQUE = "historical_correspondences"

# C. Valeurs astronomiques recopiées : largeurs fictives des planches, listes d'angles codées en dur.
LARGEUR_FICTIVE = re.compile(r"248(?:[.,]0+)?\s*°?\s*[–-]\s*267")
NOMBRE = re.compile(r"(?<![\w#.])-?\d{1,3}(?:\.\d+)?(?![\w.])")
LISTE = re.compile(r"[\[(]([^\[\]()]{20,})[\])]", re.DOTALL)
SEUIL_ANGLES = 13

SOURCES = (".py", ".ts", ".tsx", ".js", ".jsx")
IGNORES = {"node_modules", ".venv", "dist", "generes", "__pycache__", ".git", "tests", "e2e", "verifications"}


def fichiers(base: str, suffixes: tuple[str, ...]) -> list[Path]:
    racine = RACINE / base
    if not racine.exists():
        return []
    return [
        p for p in racine.rglob("*")
        if p.is_file()
        and p.suffix in suffixes
        and not IGNORES.intersection(p.relative_to(RACINE).parts)
        and ".test." not in p.name
        and ".spec." not in p.name
    ]


def ligne(texte: str, position: int) -> int:
    return texte.count("\n", 0, position) + 1


def dependances() -> list[str]:
    constats: list[str] = []
    noms: list[tuple[str, str]] = []
    pyproject = RACINE / "pyproject.toml"
    if pyproject.exists():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        projet = data.get("project", {})
        listes = [projet.get("dependencies", [])]
        listes += list(projet.get("optional-dependencies", {}).values())
        listes += list(data.get("dependency-groups", {}).values())
        for liste in listes:
            for spec in liste:
                if isinstance(spec, str):
                    noms.append((re.split(r"[\s<>=!~\[;]", spec, maxsplit=1)[0], "pyproject.toml"))
    verrou = RACINE / "uv.lock"
    if verrou.exists():
        for paquet in tomllib.loads(verrou.read_text(encoding="utf-8")).get("package", []):
            noms.append((paquet.get("name", ""), "uv.lock"))
    for chemin in ("web/package.json", "web/package-lock.json"):
        f = RACINE / chemin
        if not f.exists():
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        for cle in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            noms += [(n, chemin) for n in data.get(cle, {})]
        noms += [(k.rsplit("node_modules/", 1)[-1], chemin) for k in data.get("packages", {}) if k]
    for nom, source in noms:
        if nom and nom != NOM_PROJET and DEPENDANCES_INTERDITES.search(nom):
            constats.append(f"{source} : dépendance interdite « {nom} » (bibliothèque d'astrologie)")
    return constats


def vocabulaire() -> list[str]:
    constats: list[str] = []
    cibles = fichiers("web/src", SOURCES + (".html", ".json", ".md", ".css"))
    if (RACINE / "web/index.html").exists():
        cibles.append(RACINE / "web/index.html")
    for f in cibles:
        texte = f.read_text(encoding="utf-8", errors="replace")
        for motif, raison in VOCABULAIRE_INTERDIT:
            for m in motif.finditer(texte):
                constats.append(f"{f.relative_to(RACINE)}:{ligne(texte, m.start())} : {raison}")
    return constats


def referentiel() -> list[str]:
    """Hors du bloc historical_correspondences : ni clé de catégorie héritée, ni vocabulaire interdit."""
    constats: list[str] = []
    for f in fichiers("referentiel", (".yaml", ".yml")):
        pile: list[tuple[int, str]] = []  # (indentation, clé) des ancêtres
        for n, texte in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if not texte.strip() or texte.lstrip().startswith("#"):
                continue
            m = CLE_YAML.match(texte)
            retrait = len(texte) - len(texte.lstrip(" -"))
            while pile and pile[-1][0] >= retrait:
                pile.pop()
            historique = any(cle == BLOC_HISTORIQUE for _, cle in pile)
            if m and m.group(2) == BLOC_HISTORIQUE and "active: true" in texte:
                constats.append(f"{f.relative_to(RACINE)}:{n} : {BLOC_HISTORIQUE} doit rester inactif")
            if not historique:
                if CLE_HERITEE.match(texte):
                    constats.append(f"{f.relative_to(RACINE)}:{n} : catégorie héritée hors de {BLOC_HISTORIQUE}")
                for motif, raison in VOCABULAIRE_INTERDIT:
                    if motif.search(texte):
                        constats.append(f"{f.relative_to(RACINE)}:{n} : {raison}")
            if m:
                pile.append((retrait, m.group(2)))
    return constats


def valeurs_recopiees() -> list[str]:
    constats: list[str] = []
    for base in ("moteur", "api", "web/src", "scripts", "referentiel"):
        for f in fichiers(base, SOURCES + (".yaml", ".yml", ".json", ".csv")):
            texte = f.read_text(encoding="utf-8", errors="replace")
            rel = f.relative_to(RACINE)
            for m in LARGEUR_FICTIVE.finditer(texte):
                constats.append(f"{rel}:{ligne(texte, m.start())} : largeur fictive des planches (248°–267°)")
            if f.suffix not in SOURCES:
                continue
            for m in LISTE.finditer(texte):
                angles = [float(n) for n in NOMBRE.findall(m.group(1)) if 0 <= float(n) <= 360]
                if len(angles) >= SEUIL_ANGLES:
                    constats.append(
                        f"{rel}:{ligne(texte, m.start())} : {len(angles)} angles codés en dur ; "
                        "les frontières et longitudes viennent du moteur ou de generes/"
                    )
    return constats


def contient_cle(objet: object, cle: str) -> bool:
    if isinstance(objet, dict):
        return cle in objet or any(contient_cle(v, cle) for v in objet.values())
    if isinstance(objet, list):
        return any(contient_cle(v, cle) for v in objet)
    return False


def jeux_essai() -> list[str]:
    constats: list[str] = []
    for base in ("tests", "web/src", "web/e2e"):
        racine = RACINE / base
        if not racine.exists():
            continue
        for f in racine.rglob("*.json"):
            if "node_modules" in f.parts:
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if contient_cle(data, "birth") and not (isinstance(data, dict) and data.get("synthetic") is True):
                constats.append(f"{f.relative_to(RACINE)} : données de naissance sans \"synthetic\": true")
    return constats


def main() -> int:
    constats = dependances() + vocabulaire() + referentiel() + valeurs_recopiees() + jeux_essai()
    for c in constats:
        print(f"  ✘ {c}")
    if constats:
        print(f"{len(constats)} constat(s). Corrige la cause ; ce fichier ne se modifie pas depuis Claude Code.")
        return 1
    print("  Aucun constat.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
