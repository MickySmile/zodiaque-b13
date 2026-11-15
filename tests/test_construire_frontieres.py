"""Écriture et vérification des frontières générées (skill `frontieres`, étapes 1 et 2)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from moteur import MODEL_ID, boundaries
from moteur import coordinates as c
from scripts import construire_frontieres as s

GATES_CLOSED = """
[g1]
intitule = "porte synthétique"
franchie = false
validee_par = ""
date = ""
rapport = ""

[g2]
intitule = "porte synthétique"
franchie = false
"""


@pytest.fixture
def gates(tmp_path: Path) -> Path:
    path = tmp_path / "portes.toml"
    path.write_text(GATES_CLOSED, encoding="utf-8")
    return path


@pytest.fixture
def output(tmp_path: Path) -> Path:
    return tmp_path / "generes"


def run(arguments: list[str], output: Path, gates: Path) -> int:
    return s.main(arguments, output=output, gates_path=gates)


# --- Écriture ------------------------------------------------------------------------------


def test_construire_writes_thirteen_rows_in_double_precision(output: Path, gates: Path) -> None:
    assert run([], output, gates) == 0
    text = (output / "frontieres.csv").read_text(encoding="utf-8")
    assert text.endswith("\n")
    header, *rows = text.splitlines()
    assert header == "sign_id,start_deg,end_deg,width_deg"
    assert len(rows) == 13
    model = boundaries.construct()
    for row, interval in zip(rows, model.intervals, strict=True):
        sign, start, end, width = row.split(",")
        # Aucun arrondi : la valeur relue est exactement celle du moteur.
        assert (sign, float(start), float(end), float(width)) == (
            interval.sign_id,
            interval.start_deg,
            interval.end_deg,
            interval.width_deg,
        )


def test_construire_manifest_describes_the_model(output: Path, gates: Path) -> None:
    run([], output, gates)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    model = manifest["model"]
    assert model["id"] == MODEL_ID
    assert model["reference_frame"] == c.REFERENCE_FRAME
    assert np.array_equal(np.array(model["matrix_icrs_to_ecliptic"]), c.frame_matrix())
    assert model["boundary_source_equinox"] == "B1875"
    assert model["interval_policy"] == "start_included_end_excluded"
    assert len(model["boundary_sha256"]) == 64
    assert model["certification"]["independent_validation"] == "not_performed"
    assert [line["sign_id"] for line in model["boundary_lines"]] == list(boundaries.EXPECTED_ORDER)
    assert set(manifest["versions"]) == {"engine", "skyfield", "numpy", "python", "platform"}


def test_construire_manifest_attests_the_csv(output: Path, gates: Path) -> None:
    run([], output, gates)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    csv = (output / "frontieres.csv").read_bytes()
    assert manifest["files"]["frontieres.csv"] == {
        "sha256": hashlib.sha256(csv).hexdigest(),
        "bytes": len(csv),
    }


def test_construire_manifest_copies_the_gates_and_stays_candidate(
    output: Path, gates: Path
) -> None:
    run([], output, gates)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["gates"]["g1"]["crossed"] is False
    assert set(manifest["gates"]) == {"g1", "g2"}
    assert manifest["data_status"] == "candidate"


def test_construire_keeps_the_keys_it_does_not_manage(output: Path, gates: Path) -> None:
    output.mkdir()
    existing = {"sources": {"essai": {"sha256": "abc"}}, "files": {"autre.csv": {"sha256": "def"}}}
    (output / "manifest.json").write_text(json.dumps(existing), encoding="utf-8")
    run([], output, gates)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sources"] == existing["sources"]
    assert manifest["files"]["autre.csv"] == {"sha256": "def"}
    assert "frontieres.csv" in manifest["files"]


def test_construire_is_idempotent(output: Path, gates: Path) -> None:
    run([], output, gates)
    first = {p.name: p.read_bytes() for p in output.iterdir()}
    run([], output, gates)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == first
    assert sorted(first) == ["frontieres.csv", "manifest.json"]  # aucun fichier temporaire


def test_construire_writes_nothing_when_the_engine_stops(
    output: Path, gates: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def failing() -> boundaries.BoundaryModel:
        raise boundaries.BoundaryError("contrôle en échec (simulé)")

    monkeypatch.setattr(s, "construct", failing)
    assert run([], output, gates) == 1
    assert not output.exists()
    assert "contrôle en échec" in capsys.readouterr().err


def test_construire_refuses_an_unreadable_gates_file(output: Path, tmp_path: Path) -> None:
    broken = tmp_path / "portes.toml"
    broken.write_text('[g1]\nintitule = "sans champ franchie"\n', encoding="utf-8")
    assert run([], output, broken) == 1
    assert not output.exists()


# --- Vérification --------------------------------------------------------------------------


def test_construire_verify_accepts_what_it_generated_and_writes_nothing(
    output: Path, gates: Path
) -> None:
    run([], output, gates)
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()}
    assert run(["--verifier"], output, gates) == 0
    assert {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()} == before


def test_construire_verify_refuses_an_edited_csv(output: Path, gates: Path) -> None:
    run([], output, gates)
    path = output / "frontieres.csv"
    path.write_bytes(path.read_bytes().replace(b"Oph,", b"Oph ,"))
    edited = path.read_bytes()
    assert run(["--verifier"], output, gates) == 1
    assert path.read_bytes() == edited  # la vérification ne répare rien


def test_construire_verify_refuses_an_edited_manifest(output: Path, gates: Path) -> None:
    run([], output, gates)
    path = output / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["data_status"] = "verified"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert run(["--verifier"], output, gates) == 1


def test_construire_verify_refuses_missing_files(output: Path, gates: Path) -> None:
    assert run(["--verifier"], output, gates) == 1
    assert not output.exists()


def test_construire_verify_notices_a_change_of_gate(
    output: Path, gates: Path, tmp_path: Path
) -> None:
    """Si l'état d'une porte change dans portes.toml, le manifeste recopié n'est plus à jour."""
    run([], output, gates)
    other = tmp_path / "portes-modifiees.toml"
    other.write_text(GATES_CLOSED.replace("franchie = false", "franchie = true", 1), "utf-8")
    assert run(["--verifier"], output, other) == 1


def test_construire_verify_tolerates_another_python_patch_version(
    output: Path, gates: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run([], output, gates)
    path = output / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["versions"]["python"] = "0.0.0"
    path.write_bytes(s.render_manifest(manifest))
    assert run(["--verifier"], output, gates) == 0
    assert "0.0.0" in capsys.readouterr().out


# --- État du dépôt -------------------------------------------------------------------------


def test_construire_repository_files_are_up_to_date() -> None:
    """Ce que rejoue scripts/verifier.sh : generes/ correspond au calcul et aux portes."""
    assert s.main(["--verifier"]) == 0


def test_construire_repository_gate_g1_is_closed() -> None:
    manifest = json.loads((s.GENERATED / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["gates"]["g1"]["crossed"] is False
    assert manifest["data_status"] == "candidate"


def test_construire_verify_tolerates_another_platform(
    output: Path, gates: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """La plateforme décrit la machine qui a produit les fichiers : signalée, pas refusée."""
    run([], output, gates)
    path = output / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["versions"]["platform"] = "autre machine"
    path.write_bytes(s.render_manifest(manifest))
    assert run(["--verifier"], output, gates) == 0
    assert "autre machine" in capsys.readouterr().out


def test_construire_verify_refuses_another_skyfield_version(output: Path, gates: Path) -> None:
    """Skyfield porte la grille : une autre version n'est pas un détail de machine."""
    run([], output, gates)
    path = output / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["versions"]["skyfield"] = "0.0"
    path.write_bytes(s.render_manifest(manifest))
    assert run(["--verifier"], output, gates) == 1


def test_construire_sensitivity_table_writes_nothing(
    output: Path, gates: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(["--sensibilite"], output, gates) == 0
    assert not output.exists()
    table = capsys.readouterr().out
    assert table.count("\n| ") == 14  # séparateur et 13 signes, sous l'en-tête
    for sign in boundaries.EXPECTED_ORDER:
        assert f"| {sign} |" in table


# --- Hors de la machine de référence (décision 0009) ---------------------------------------


def as_if_produced_elsewhere(output: Path, shift: float) -> None:
    """Décale une borne du fichier présent, comme le ferait le dernier chiffre d'une autre
    machine, et remet l'empreinte du manifeste en accord avec ce fichier."""
    csv_path, manifest_path = output / "frontieres.csv", output / "manifest.json"
    text = csv_path.read_text(encoding="utf-8")
    start = text.splitlines()[5].split(",")[1]
    moved = repr(float(start) + shift)
    assert moved != start
    text = text.replace(start, moved)
    assert text.count(moved) == 2  # début d'un signe et fin du précédent : la même borne
    csv_path.write_text(text, encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = text.encode("utf-8")
    manifest["files"]["frontieres.csv"] = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    manifest_path.write_bytes(s.render_manifest(manifest))


@pytest.fixture
def elsewhere(monkeypatch: pytest.MonkeyPatch) -> Callable[[], None]:
    """Rend une fonction qui déplace la vérification sur une autre machine que celle qui a
    produit les fichiers : à appeler après la génération."""

    def move() -> None:
        monkeypatch.setattr(s, "current_platform", lambda: "Autre machine")

    return move


def test_construire_cross_platform_tolerance_is_declared() -> None:
    assert s.CROSS_PLATFORM_TOLERANCE_DEG == 1e-11


def test_construire_reference_machine_stays_byte_exact(output: Path, gates: Path) -> None:
    """Sur la machine notée au manifeste, un seul chiffre de différence est refusé."""
    run([], output, gates)
    as_if_produced_elsewhere(output, 1e-13)
    assert run(["--verifier"], output, gates) == 1


def test_construire_elsewhere_accepts_identical_files(
    output: Path, gates: Path, elsewhere: Callable[[], None], capsys: pytest.CaptureFixture[str]
) -> None:
    run([], output, gates)
    elsewhere()
    capsys.readouterr()
    assert run(["--verifier"], output, gates) == 0
    assert "écart maximal 0.000e+00°" in capsys.readouterr().out


def test_construire_elsewhere_accepts_a_last_digit_difference(
    output: Path, gates: Path, elsewhere: Callable[[], None], capsys: pytest.CaptureFixture[str]
) -> None:
    run([], output, gates)
    elsewhere()
    as_if_produced_elsewhere(output, 1e-13)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    capsys.readouterr()
    assert run(["--verifier"], output, gates) == 0
    assert "comparaison numérique" in capsys.readouterr().out
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before  # rien n'est réécrit


def test_construire_elsewhere_refuses_a_difference_above_the_tolerance(
    output: Path, gates: Path, elsewhere: Callable[[], None]
) -> None:
    run([], output, gates)
    elsewhere()
    as_if_produced_elsewhere(output, 1e-9)
    assert run(["--verifier"], output, gates) == 1


def test_construire_elsewhere_refuses_another_order_of_signs(
    output: Path, gates: Path, elsewhere: Callable[[], None]
) -> None:
    run([], output, gates)
    elsewhere()
    path = output / "frontieres.csv"
    path.write_text(
        path.read_text(encoding="utf-8").replace("Oph,", "Xxx,").replace("Sco,", "Oph,"),
        encoding="utf-8",
    )
    assert run(["--verifier"], output, gates) == 1


def test_construire_elsewhere_refuses_a_missing_row(
    output: Path, gates: Path, elsewhere: Callable[[], None]
) -> None:
    run([], output, gates)
    elsewhere()
    path = output / "frontieres.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    assert run(["--verifier"], output, gates) == 1


def test_construire_elsewhere_refuses_an_unreadable_value(
    output: Path, gates: Path, elsewhere: Callable[[], None]
) -> None:
    run([], output, gates)
    elsewhere()
    path = output / "frontieres.csv"
    path.write_text(path.read_text(encoding="utf-8").replace("Gem,9", "Gem,x9"), encoding="utf-8")
    assert run(["--verifier"], output, gates) == 1


def test_construire_elsewhere_keeps_the_rest_of_the_manifest_exact(
    output: Path, gates: Path, elsewhere: Callable[[], None]
) -> None:
    """La tolérance ne porte que sur les bornes : le reste du manifeste reste comparé tel quel."""
    run([], output, gates)
    elsewhere()
    path = output / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["data_status"] = "verified"
    path.write_bytes(s.render_manifest(manifest))
    assert run(["--verifier"], output, gates) == 1
