"""Contrôle d'intégrité des données téléchargées et des fichiers générés (bibliothèque standard seule).

- donnees/sources.toml : chaque fichier présent doit avoir l'empreinte SHA-256 déclarée.
- generes/manifest.json : chaque fichier de generes/ doit y figurer avec son empreinte exacte.
Option --sans-donnees (CI) : ignore les fichiers de donnees/telechargees/, absents de Git.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tomllib
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
DONNEES = Path(os.environ.get("B13_DONNEES", RACINE / "donnees" / "telechargees"))
GENERES = RACINE / "generes"
HORS_MANIFESTE = {"manifest.json", "README.md", ".gitkeep"}


def sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def sources(sans_donnees: bool) -> tuple[list[str], list[str]]:
    echecs: list[str] = []
    avis: list[str] = []
    fichier = RACINE / "donnees" / "sources.toml"
    if not fichier.exists():
        return ["donnees/sources.toml manquant"], avis
    for src in tomllib.loads(fichier.read_text(encoding="utf-8")).get("source", []):
        nom = src.get("fichier")
        if not nom or src.get("type") == "paquet":
            continue
        if sans_donnees:
            continue
        chemin = DONNEES / nom
        attendu = src.get("sha256", "")
        if not chemin.exists():
            avis.append(f"{nom} : pas encore téléchargé (lance /donnees)")
        elif not attendu:
            echecs.append(
                f"{nom} : empreinte non renseignée dans donnees/sources.toml (lance /donnees, Micky valide)"
            )
        elif sha256(chemin) != attendu:
            echecs.append(
                f"{nom} : empreinte différente de donnees/sources.toml ; fichier modifié ou corrompu"
            )
    return echecs, avis


def generes() -> list[str]:
    echecs: list[str] = []
    if not GENERES.exists():
        return echecs
    presents = {
        p.relative_to(GENERES).as_posix() for p in GENERES.rglob("*") if p.is_file()
    } - HORS_MANIFESTE
    manifeste = GENERES / "manifest.json"
    if not manifeste.exists():
        return [
            f"generes/{p} : aucun generes/manifest.json pour l'attester" for p in sorted(presents)
        ]
    declares = json.loads(manifeste.read_text(encoding="utf-8")).get("files", {})
    for nom, info in declares.items():
        chemin = GENERES / nom
        if not chemin.exists():
            echecs.append(f"generes/{nom} : déclaré dans le manifeste mais absent")
        elif sha256(chemin) != info.get("sha256"):
            echecs.append(
                f"generes/{nom} : empreinte différente du manifeste ; régénère avec le script, jamais à la main"
            )
    for nom in sorted(presents - set(declares)):
        echecs.append(f"generes/{nom} : absent du manifeste")
    return echecs


def main() -> int:
    sans_donnees = "--sans-donnees" in sys.argv[1:]
    echecs, avis = sources(sans_donnees)
    echecs += generes()
    for a in avis:
        print(f"  · {a}")
    for e in echecs:
        print(f"  ✘ {e}")
    if echecs:
        return 1
    print("  Empreintes conformes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
