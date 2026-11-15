"""Socle de la phase 2 : les paquets s'importent, l'API répond, l'outillage est déclaré."""

from __future__ import annotations

import ast
import importlib
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]


def test_socle_moteur_importable() -> None:
    moteur = importlib.import_module("moteur")
    assert moteur.MODEL_ID == "model_b_iau_ecliptic_j2000_v1"


def test_socle_moteur_ne_depend_ni_de_l_api_ni_du_web() -> None:
    """Contrôle statique : aucun fichier de moteur/ n'importe l'API, le front ou leur outillage."""
    interdits = {"api", "web", "fastapi", "starlette", "uvicorn"}
    fautifs: list[str] = []
    fichiers = sorted((RACINE / "moteur").rglob("*.py"))
    assert fichiers, "moteur/ ne contient aucun fichier Python"
    for fichier in fichiers:
        arbre = ast.parse(fichier.read_text(encoding="utf-8"), filename=str(fichier))
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.Import):
                modules = [alias.name for alias in noeud.names]
            elif isinstance(noeud, ast.ImportFrom) and noeud.level == 0:
                modules = [noeud.module or ""]
            else:
                continue
            for module in modules:
                if module.split(".")[0] in interdits:
                    fautifs.append(f"{fichier.relative_to(RACINE)}:{noeud.lineno} importe {module}")
    assert fautifs == []


def test_socle_version_unique() -> None:
    """La version vit dans moteur/ ; pyproject.toml et l'API la reprennent sans la réécrire."""
    import moteur
    from api.main import app

    projet = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert projet["version"] == moteur.__version__
    assert app.version == moteur.__version__


def test_socle_api_route_health() -> None:
    from api.main import HealthResponse, app, health

    chemins = {getattr(route, "path", None) for route in app.routes}
    assert "/health" in chemins
    reponse = health()
    assert isinstance(reponse, HealthResponse)
    assert reponse.status == "ok"


def test_socle_api_sans_page_servie_par_un_tiers() -> None:
    """Les pages /docs et /redoc de FastAPI chargent leurs scripts depuis un CDN : désactivées."""
    from api.main import app

    assert app.docs_url is None
    assert app.redoc_url is None


SCRIPTS = sorted(p for p in (RACINE / "scripts").glob("*.py") if not p.name.startswith("_"))


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_socle_script_lancable_par_son_chemin(script: Path, tmp_path: Path) -> None:
    """Décision 0007 : lancé par son chemin, depuis un autre dossier, un script trouve ses imports.

    `scripts/verifier.sh` lance les scripts ainsi ; `moteur` n'étant pas installé, un script qui
    l'importe doit ajouter lui-même la racine du dépôt à son chemin.
    """
    resultat = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert resultat.returncode == 0, resultat.stderr


def test_socle_marqueur_donnees_declare(pytestconfig: pytest.Config) -> None:
    marqueurs = pytestconfig.getini("markers")
    assert any(str(m).startswith("donnees") for m in marqueurs)


@pytest.mark.parametrize(
    "module",
    [
        "skyfield",
        "numpy",
        "scipy",
        "tzdata",
        "timezonefinder",
        "fastapi",
        "pydantic",
        "uvicorn",
        "hypothesis",
    ],
)
def test_socle_dependances_importables(module: str) -> None:
    assert importlib.import_module(module) is not None
