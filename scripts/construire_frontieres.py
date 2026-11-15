"""Construit les 13 frontières du modèle B et les écrit dans generes/.

Usage :
    uv run python scripts/construire_frontieres.py             écrit generes/frontieres.csv
                                                               et met à jour generes/manifest.json
    uv run python scripts/construire_frontieres.py --verifier  régénère dans un dossier temporaire
                                                               et compare, sans rien écrire

Le calcul est celui de `moteur.boundaries.construct()` ; ce script ne fait que l'écrire.
Si un contrôle du moteur échoue, rien n'est écrit. Les fichiers de generes/ ne s'éditent
jamais à la main : `--verifier` les régénère, puis compare le CSV octet par octet et le
manifeste clé par clé (la version corrective de Python et la plateforme, qui peuvent changer
d'une machine à l'autre sans changer le calcul, sont signalées et non refusées).

    uv run python scripts/construire_frontieres.py --sensibilite
        affiche le déplacement de chaque frontière si la grille était lue à l'équateur moyen
        de B1875 (décision 0008), sans rien écrire

L'état des portes est recopié de docs/portes.toml, que seul Micky modifie : tant que G1 n'est
pas franchie, les données portent le statut « candidate ».
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import tempfile
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

# Décision 0007 : `moteur` n'est pas installé ; un script lancé par son chemin ajoute la racine.
RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import moteur
from moteur.boundaries import BoundaryError, BoundaryModel, construct, mean_equator_shifts

GENERATED = RACINE / "generes"
GATES = RACINE / "docs" / "portes.toml"
CSV_NAME = "frontieres.csv"
MANIFEST_NAME = "manifest.json"
# Versions notées pour mémoire : elles décrivent la machine qui a produit les fichiers.
INFORMATIVE_VERSIONS = ("python", "platform")
CSV_HEADER = "sign_id,start_deg,end_deg,width_deg"


class ManifestError(Exception):
    """generes/manifest.json ou docs/portes.toml est illisible ou n'a pas la forme attendue."""


def render_csv(model: BoundaryModel) -> bytes:
    """Une ligne par signe, degrés décimaux en double précision, sans arrondi."""
    lines = [CSV_HEADER]
    lines += [f"{i.sign_id},{i.start_deg!r},{i.end_deg!r},{i.width_deg!r}" for i in model.intervals]
    return ("\n".join(lines) + "\n").encode("utf-8")


def read_gates(path: Path) -> dict[str, dict[str, object]]:
    """État des portes G1 à G3, recopié tel quel de docs/portes.toml."""
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ManifestError(f"{path} illisible : {error}") from error
    gates: dict[str, dict[str, object]] = {}
    for name, gate in sorted(raw.items()):
        if not isinstance(gate, dict) or not isinstance(gate.get("franchie"), bool):
            raise ManifestError(f"{path} : la porte « {name} » n'a pas de champ `franchie`")
        gates[name] = {
            "title": gate.get("intitule", ""),
            "crossed": gate["franchie"],
            "validated_by": gate.get("validee_par", ""),
            "date": gate.get("date", ""),
            "report": gate.get("rapport", ""),
        }
    if "g1" not in gates:
        raise ManifestError(f"{path} : porte « g1 » absente")
    return gates


def read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ManifestError(f"{path} illisible : {error}") from error
    if not isinstance(content, dict):
        raise ManifestError(f"{path} : un objet JSON est attendu")
    return content


def build_manifest(
    existing: dict[str, Any],
    model: BoundaryModel,
    csv: bytes,
    gates: dict[str, dict[str, object]],
) -> dict[str, Any]:
    """Manifeste mis à jour. Les clés que ce script ne gère pas (`sources`) sont conservées."""
    manifest = dict(existing)
    manifest["model"] = {
        "id": model.model_id,
        "reference_frame": model.reference_frame,
        "matrix_icrs_to_ecliptic": [list(row) for row in model.matrix_icrs_to_ecliptic],
        "boundary_source": model.boundary_source,
        "boundary_source_equinox": model.boundary_source_equinox,
        "boundary_equatorial_convention": model.boundary_equatorial_convention,
        "boundary_sha256": model.boundary_sha256,
        "interval_policy": model.interval_policy,
        "certification": dict(model.certification),
        "boundary_lines": [
            {"sign_id": interval.sign_id, "kind": line.kind, "value": line.value}
            for interval, line in zip(model.intervals, model.boundary_lines, strict=True)
        ],
    }
    manifest["versions"] = {
        "engine": moteur.__version__,
        "skyfield": model.skyfield_version,
        "numpy": model.numpy_version,
        "python": model.python_version,
        "platform": f"{platform.system()} {platform.machine()}",
    }
    manifest["gates"] = gates
    # Statut des données affiché partout : « candidate » tant que G1 n'est pas franchie.
    manifest["data_status"] = "verified" if gates["g1"]["crossed"] is True else "candidate"
    files = existing.get("files", {})
    if not isinstance(files, dict):
        raise ManifestError("manifeste : `files` doit être un objet")
    manifest["files"] = {
        **files,
        CSV_NAME: {"sha256": hashlib.sha256(csv).hexdigest(), "bytes": len(csv)},
    }
    return manifest


def render_manifest(manifest: dict[str, Any]) -> bytes:
    text = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
    return (text + "\n").encode("utf-8")


def sensitivity_table(model: BoundaryModel) -> str:
    """Tableau Markdown : frontière actuelle et déplacement à l'équateur moyen de B1875."""
    lines = [
        (
            "| Signe | Début, équateur vrai (°) | Déplacement à l'équateur moyen (°) "
            "| Déplacement (″) | Ligne de la grille |"
        ),
        "| --- | --- | --- | --- | --- |",
    ]
    rows = zip(model.intervals, model.boundary_lines, mean_equator_shifts(model), strict=True)
    for interval, line, shift in rows:
        grid_line = (
            f"ascension droite {line.value!r} h"
            if line.kind == "right_ascension_hours"
            else f"déclinaison {line.value!r}°"
        )
        lines.append(
            f"| {interval.sign_id} | {interval.start_deg!r} | {shift:+.6f} | "
            f"{shift * 3600.0:+.2f} | {grid_line} |"
        )
    return "\n".join(lines)


def _write_atomically(path: Path, content: bytes) -> None:
    temporary = path.with_name(path.name + ".partiel")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def generate(output: Path, gates_path: Path) -> tuple[bytes, bytes]:
    """Calcule les frontières et rend le CSV et le manifeste, sans rien écrire."""
    model = construct()
    csv = render_csv(model)
    manifest = build_manifest(
        read_manifest(output / MANIFEST_NAME), model, csv, read_gates(gates_path)
    )
    return csv, render_manifest(manifest)


def verify(output: Path, gates_path: Path) -> list[str]:
    """Régénère dans un dossier temporaire et compare aux fichiers présents. N'écrit rien ici."""
    findings: list[str] = []
    csv_path, manifest_path = output / CSV_NAME, output / MANIFEST_NAME
    for path in (csv_path, manifest_path):
        if not path.is_file():
            findings.append(f"{path.name} absent : lance le script sans --verifier")
    if findings:
        return findings
    csv, manifest = generate(output, gates_path)
    with tempfile.TemporaryDirectory() as folder:
        fresh_csv, fresh_manifest = Path(folder) / CSV_NAME, Path(folder) / MANIFEST_NAME
        fresh_csv.write_bytes(csv)
        fresh_manifest.write_bytes(manifest)
        if fresh_csv.read_bytes() != csv_path.read_bytes():
            findings.append(f"{CSV_NAME} : différent du fichier régénéré")
        stored = read_manifest(manifest_path)
        fresh = json.loads(fresh_manifest.read_bytes())
    # La version corrective de Python peut changer d'une machine à l'autre sans changer le
    # calcul : elle est signalée, pas refusée. Tout le reste doit être identique.
    stored_versions = stored.get("versions", {})
    for key in INFORMATIVE_VERSIONS:
        here, recorded = fresh["versions"][key], stored_versions.get(key)
        if here != recorded:
            print(f"  · {key} : {here} ici, {recorded} dans le manifeste")
            fresh["versions"][key] = recorded
    findings += [
        f"{MANIFEST_NAME} : la clé `{key}` diffère du manifeste régénéré"
        for key in sorted(set(stored) | set(fresh))
        if stored.get(key) != fresh.get(key)
    ]
    return findings


def main(
    argv: Sequence[str] | None = None,
    *,
    output: Path = GENERATED,
    gates_path: Path = GATES,
) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--verifier", action="store_true", help="régénérer et comparer, sans rien écrire"
    )
    parser.add_argument(
        "--sensibilite",
        action="store_true",
        help="afficher l'effet de l'équateur moyen de B1875, sans rien écrire",
    )
    options = parser.parse_args(argv)
    try:
        if options.sensibilite:
            print(sensitivity_table(construct()))
            return 0
        if options.verifier:
            findings = verify(output, gates_path)
            for finding in findings:
                print(f"  ✘ {finding}")
            if findings:
                print("Régénère avec le script, jamais à la main.")
                return 1
            print("  Frontières régénérées à l'identique.")
            return 0
        csv, manifest = generate(output, gates_path)
    except (BoundaryError, ManifestError) as error:
        print(f"  ✘ {error}", file=sys.stderr)
        return 1
    output.mkdir(parents=True, exist_ok=True)
    _write_atomically(output / CSV_NAME, csv)
    _write_atomically(output / MANIFEST_NAME, manifest)
    print(f"  {CSV_NAME} et {MANIFEST_NAME} écrits dans {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
