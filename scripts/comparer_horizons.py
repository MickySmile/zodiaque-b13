"""Confronte la chaîne de calcul du modèle B à JPL Horizons, aux 13 frontières.

Usage :
    uv run python scripts/comparer_horizons.py               rejoue hors ligne les dernières réponses
                                                             archivées dans tests/fixtures/horizons/
    uv run python scripts/comparer_horizons.py --interroger  interroge l'API de Horizons, archive
                                                             les réponses brutes, puis compare
    uv run python scripts/comparer_horizons.py --tableau     ajoute les tableaux au format Markdown

Pour chaque frontière, on cherche l'instant de l'année de référence où la longitude astrométrique
géocentrique du Soleil, dans le repère B, égale la frontière (DE440s, méthode de Brent en TT).
À ces 13 instants, deux réponses de Horizons sont archivées (annexe technique § B, « Contrôle
externe ») :

1. Vecteurs dans l'ICRF, corrigés du temps de lumière. Comparés à ceux du moteur au même instant,
   ils contrôlent la **chaîne de positions** : éphéméride, temps de lumière, échelles de temps.
   La matrice R étant appliquée aux deux chaînes, ce contrôle ne dit rien de R.
2. Les mêmes vecteurs dans le repère écliptique J2000 de Horizons. Comparés aux vecteurs ICRF
   de Horizons transformés par R, ils contrôlent le **repère R** contre une définition écrite
   ailleurs. L'écart attendu est connu : Horizons prend l'obliquité IAU 1976 et l'axe x de
   l'ICRF, le modèle B prend 84 381,406″ et le biais de repère.

Ce que ces contrôles n'établissent pas : la position des frontières. La grille des constellations
vient de Skyfield (Roman 1987) dans tout le calcul ; Horizons ne fournit ici que des positions du
Soleil. La colonne 31 de Horizons (longitude apparente de date) n'est pas utilisée : elle n'est
pas comparable telle quelle.

Aucune donnée personnelle ne part vers Horizons : les requêtes ne contiennent que des instants.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import urllib.parse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

# Décision 0007 : `moteur` n'est pas installé ; un script lancé par son chemin ajoute la racine.
RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import brentq
from skyfield.api import load, load_file

from moteur.boundaries import BoundaryModel, construct
from moteur.coordinates import frame_matrix, longitude_latitude_deg, signed_wrap
from scripts.telecharger import (
    ErreurRegistre,
    ErreurTelechargement,
    dossier_donnees,
    recuperer_https,
)

FIXTURES = RACINE / "tests" / "fixtures" / "horizons"
API = "https://ssd.jpl.nasa.gov/api/horizons.api"
EPHEMERIS_FILE = "de440s.bsp"
REFERENCE_YEAR = 2026

BRENT_TOLERANCE_SECONDS = 0.01
SECONDS_PER_DAY = 86400.0
TIME_MATCH_DAYS = 2e-9

# Tolérances déclarées avant le calcul.
# Positions : la recherche de Brent s'arrête à 0,01 s près, soit environ 1,2 × 10⁻⁷° de longitude
# solaire ; les instants sont transmis à 10⁻⁹ jour près ; DE440s et DE441 s'accordent bien en
# deçà de la milliseconde d'arc sur la période. 10⁻⁶° (3,6 mas) couvre l'ensemble avec une marge.
CHAIN_TOLERANCE_DEG = 1e-6
BOUNDARY_TOLERANCE_DEG = 1e-6
# Repère : entre R et l'écliptique J2000 de Horizons, on attend l'écart d'obliquité
# (84 381,448″ − 84 381,406″ = 0,042″) et le biais de repère de l'ICRS (au plus 0,023″).
FRAME_TOLERANCE_ARCSEC = 0.1
# Une fois l'obliquité de Horizons et l'absence de biais prises en compte, il ne doit rester que
# l'arrondi des 16 chiffres imprimés.
EXPLAINED_TOLERANCE_ARCSEC = 1e-6

Plane = Literal["FRAME", "ECLIPTIC"]
Vector = NDArray[np.float64]
ARCHIVE_PREFIX: dict[Plane, str] = {"FRAME": "sun-boundaries", "ECLIPTIC": "sun-ecliptic"}
FRAME_HEADER: dict[Plane, str] = {
    "FRAME": "Reference frame : ICRF",
    "ECLIPTIC": "Reference frame : Ecliptic of J2000.0",
}
COMMON_HEADERS = (
    "Target body name: Sun (10)",
    "Center body name: Earth (399)",
    "Output units    : AU-D",
    "Output type     : LT CORRECTED cartesian states",
    "JDTDB",
)
OBLIQUITY_PATTERN = re.compile(r"obliquity of ([0-9]+\.[0-9]+) arcseconds wrt ICRF X-Y plane")


class ComparisonError(Exception):
    """La comparaison ne peut pas être menée : réponse inattendue, archive périmée, donnée absente."""


@dataclass(frozen=True)
class Crossing:
    """Instant où le Soleil atteint une frontière, selon la chaîne du moteur."""

    sign_id: str
    boundary_deg: float
    tt_jd: float
    tdb_jd: float
    residual_deg: float


@dataclass(frozen=True)
class Row:
    """Chaîne de positions : une frontière, le moteur et Horizons au même instant."""

    sign_id: str
    boundary_deg: float
    tdb_jd: float
    chain_difference_deg: float
    separation_arcsec: float
    boundary_difference_deg: float
    sun_latitude_deg: float  # le Soleil n'est pas sur le cercle B


@dataclass(frozen=True)
class FrameRow:
    """Repère : R appliquée au vecteur ICRF de Horizons, contre son vecteur écliptique J2000."""

    sign_id: str
    tdb_jd: float
    separation_arcsec: float
    longitude_difference_deg: float
    latitude_difference_deg: float
    explained_residual_arcsec: float


class SunChain:
    """Soleil astrométrique géocentrique dans le repère B : `.observe()` sans `.apparent()`."""

    def __init__(self, ephemeris: Path) -> None:
        if not ephemeris.is_file():
            raise ComparisonError(f"{ephemeris} absent : lance /donnees")
        self._timescale = load.timescale(builtin=True)
        kernel = load_file(str(ephemeris))
        self._earth, self._sun = kernel["earth"], kernel["sun"]
        self._matrix = frame_matrix()

    def vector_b(self, *, tt_jd: float | None = None, tdb_jd: float | None = None) -> Vector:
        if tt_jd is not None:
            time = self._timescale.tt_jd(tt_jd)
        elif tdb_jd is not None:
            time = self._timescale.tdb_jd(tdb_jd)
        else:
            raise ValueError("un instant est attendu")
        vector_icrs = np.asarray(self._earth.at(time).observe(self._sun).xyz.au, dtype=np.float64)
        result: Vector = self._matrix @ vector_icrs
        return result

    def longitude_deg(self, tt_jd: float) -> float:
        longitude, _ = longitude_latitude_deg(self.vector_b(tt_jd=tt_jd))
        if longitude is None:
            raise ComparisonError("longitude solaire indéfinie")
        return longitude

    def tt_to_tdb(self, tt_jd: float) -> float:
        return float(self._timescale.tt_jd(tt_jd).tdb)

    def tt_of_year_start(self, year: int) -> float:
        return float(self._timescale.tt(year, 1, 1).tt)


def sun_crossings(model: BoundaryModel, chain: SunChain, year: int) -> list[Crossing]:
    """Instants de l'année où la longitude solaire égale chaque frontière (Brent, échelle TT)."""
    start, end = chain.tt_of_year_start(year), chain.tt_of_year_start(year + 1)
    days = [start + offset for offset in range(math.ceil(end - start) + 1)]
    longitudes = [chain.longitude_deg(day) for day in days]
    second = 1.0 / SECONDS_PER_DAY
    crossings: list[Crossing] = []
    for interval in model.intervals:
        boundary = interval.start_deg

        def gap(tt_jd: float, target: float = boundary) -> float:
            return signed_wrap(chain.longitude_deg(tt_jd) - target)

        offsets = [signed_wrap(longitude - boundary) for longitude in longitudes]
        brackets = [
            index
            for index in range(len(days) - 1)
            # Passage par zéro en montant ; l'écart borné écarte le saut de ±180° à l'opposé.
            if offsets[index] < 0.0 <= offsets[index + 1]
            and offsets[index + 1] - offsets[index] < 5.0
        ]
        if len(brackets) != 1:
            raise ComparisonError(
                f"{interval.sign_id} : {len(brackets)} passages du Soleil trouvés en {year}, "
                "1 attendu"
            )
        low, high = days[brackets[0]], days[brackets[0] + 1]
        root = float(brentq(gap, low, high, xtol=BRENT_TOLERANCE_SECONDS * second))
        # Annexe D2, étape 7 : une seconde avant et après, de part et d'autre de la frontière.
        if not gap(root - second) < 0.0 < gap(root + second):
            raise ComparisonError(f"{interval.sign_id} : le Soleil ne franchit pas la frontière")
        crossings.append(
            Crossing(interval.sign_id, boundary, root, chain.tt_to_tdb(root), gap(root))
        )
    return crossings


def build_query(tdb_jds: Sequence[float], plane: Plane = "FRAME") -> str:
    """URL de l'API : vecteurs géocentriques du Soleil, corrigés du temps de lumière.

    `plane` choisit le repère de sortie de Horizons : l'ICRF, ou son écliptique J2000.
    """
    parameters = {
        "format": "text",
        "COMMAND": "'10'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'VECTORS'",
        "CENTER": "'500@399'",
        "REF_PLANE": f"'{plane}'",
        "REF_SYSTEM": "'ICRF'",
        "VEC_CORR": "'LT'",
        "VEC_TABLE": "'1'",
        "OUT_UNITS": "'AU-D'",
        "CSV_FORMAT": "'YES'",
        "VEC_LABELS": "'NO'",
        "TLIST_TYPE": "'JD'",
        "TIME_TYPE": "'TDB'",
        "TLIST": "'" + " ".join(f"{jd:.9f}" for jd in tdb_jds) + "'",
    }
    return API + "?" + urllib.parse.urlencode(parameters)


def parse_vectors(text: str, plane: Plane = "FRAME") -> list[tuple[float, Vector]]:
    """Lit les lignes de vecteurs d'une réponse brute, après avoir contrôlé ses en-têtes."""
    for header in (*COMMON_HEADERS, FRAME_HEADER[plane]):
        if header not in text:
            raise ComparisonError(f"réponse de Horizons inattendue : « {header} » absent")
    if "$$SOE" not in text or "$$EOE" not in text:
        raise ComparisonError("réponse de Horizons sans table de vecteurs")
    body = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    vectors: list[tuple[float, Vector]] = []
    for line in body.strip().splitlines():
        fields = [field.strip() for field in line.split(",")]
        try:
            jd, x, y, z = float(fields[0]), float(fields[2]), float(fields[3]), float(fields[4])
        except (IndexError, ValueError) as error:
            raise ComparisonError(f"ligne de vecteur illisible : {line!r}") from error
        vectors.append((jd, np.array([x, y, z])))
    return vectors


def horizons_obliquity_arcsec(ecliptic_text: str) -> float:
    """Obliquité que Horizons déclare pour son écliptique J2000, lue dans sa réponse."""
    match = OBLIQUITY_PATTERN.search(ecliptic_text)
    if match is None:
        raise ComparisonError("réponse de Horizons : obliquité de son écliptique J2000 introuvable")
    return float(match.group(1))


def _separation_arcsec(first: Vector, second: Vector) -> float:
    norms = float(np.linalg.norm(first) * np.linalg.norm(second))
    sine = float(np.linalg.norm(np.cross(first, second))) / norms
    cosine = float(np.dot(first, second)) / norms
    return math.degrees(math.atan2(sine, cosine)) * 3600.0


def _vector_at(vectors: Sequence[tuple[float, Vector]], crossing: Crossing) -> tuple[float, Vector]:
    jd, vector = min(vectors, key=lambda item: abs(item[0] - crossing.tdb_jd))
    if abs(jd - crossing.tdb_jd) > TIME_MATCH_DAYS:
        raise ComparisonError(
            f"{crossing.sign_id} : aucun vecteur archivé à l'instant du passage ; les frontières "
            "ont changé depuis l'archive, relance avec --interroger"
        )
    return jd, vector


def _check_count(vectors: Sequence[object], crossings: Sequence[Crossing]) -> None:
    if len(vectors) != len(crossings):
        raise ComparisonError(
            f"{len(vectors)} vecteurs archivés pour {len(crossings)} frontières : archive périmée"
        )


def compare(
    crossings: Sequence[Crossing], vectors: Sequence[tuple[float, Vector]], chain: SunChain
) -> list[Row]:
    """Chaîne de positions : le moteur et Horizons au même instant, par la même matrice R."""
    _check_count(vectors, crossings)
    matrix = frame_matrix()
    rows: list[Row] = []
    for crossing in crossings:
        jd, vector_icrs = _vector_at(vectors, crossing)
        horizons_b = matrix @ vector_icrs
        engine_b = chain.vector_b(tdb_jd=jd)
        longitude_horizons, _ = longitude_latitude_deg(horizons_b)
        longitude_engine, latitude_engine = longitude_latitude_deg(engine_b)
        if longitude_horizons is None or longitude_engine is None:
            raise ComparisonError(f"{crossing.sign_id} : longitude indéfinie")
        rows.append(
            Row(
                sign_id=crossing.sign_id,
                boundary_deg=crossing.boundary_deg,
                tdb_jd=jd,
                chain_difference_deg=signed_wrap(longitude_horizons - longitude_engine),
                separation_arcsec=_separation_arcsec(horizons_b, engine_b),
                boundary_difference_deg=signed_wrap(longitude_horizons - crossing.boundary_deg),
                sun_latitude_deg=latitude_engine,
            )
        )
    return rows


def compare_frames(
    crossings: Sequence[Crossing],
    icrf_vectors: Sequence[tuple[float, Vector]],
    ecliptic_vectors: Sequence[tuple[float, Vector]],
    horizons_obliquity: float,
) -> list[FrameRow]:
    """Repère : R contre l'écliptique J2000 de Horizons, sur les seuls vecteurs de Horizons.

    `explained_residual_arcsec` refait le calcul avec la définition que Horizons donne de son
    repère (rotation de son obliquité autour de l'axe x de l'ICRF, sans biais) : s'il est nul à
    l'arrondi près, tout l'écart entre R et Horizons vient de ces deux conventions connues.
    """
    _check_count(icrf_vectors, crossings)
    _check_count(ecliptic_vectors, crossings)
    matrix = frame_matrix()
    epsilon = math.radians(horizons_obliquity / 3600.0)
    cos_e, sin_e = math.cos(epsilon), math.sin(epsilon)
    horizons_matrix = np.array([[1.0, 0.0, 0.0], [0.0, cos_e, sin_e], [0.0, -sin_e, cos_e]])
    rows: list[FrameRow] = []
    for crossing in crossings:
        jd, vector_icrs = _vector_at(icrf_vectors, crossing)
        _, vector_ecliptic = _vector_at(ecliptic_vectors, crossing)
        ours = matrix @ vector_icrs
        longitude_ours, latitude_ours = longitude_latitude_deg(ours)
        longitude_theirs, latitude_theirs = longitude_latitude_deg(vector_ecliptic)
        if longitude_ours is None or longitude_theirs is None:
            raise ComparisonError(f"{crossing.sign_id} : longitude indéfinie")
        rows.append(
            FrameRow(
                sign_id=crossing.sign_id,
                tdb_jd=jd,
                separation_arcsec=_separation_arcsec(ours, vector_ecliptic),
                longitude_difference_deg=signed_wrap(longitude_ours - longitude_theirs),
                latitude_difference_deg=latitude_ours - latitude_theirs,
                explained_residual_arcsec=_separation_arcsec(
                    horizons_matrix @ vector_icrs, vector_ecliptic
                ),
            )
        )
    return rows


def archive(url: str, folder: Path, plane: Plane, year: int, now: datetime) -> Path:
    """Interroge Horizons et garde la réponse brute, avec sa date et son empreinte."""
    folder.mkdir(parents=True, exist_ok=True)
    stamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    response = folder / f"{ARCHIVE_PREFIX[plane]}-{year}_{stamp}.txt"
    recuperer_https(url, response)
    raw = response.read_bytes()
    metadata = {
        "retrieved_at": now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "url": url,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "reference_year": year,
        "content": f"JPL Horizons API, Sun geocentric vectors, light-time corrected, {plane}",
    }
    response.with_suffix(".json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return response


def latest_archive(folder: Path, year: int, plane: Plane = "FRAME") -> Path:
    """Dernière réponse archivée, après contrôle de son empreinte."""
    pattern = f"{ARCHIVE_PREFIX[plane]}-{year}_*.txt"
    candidates = sorted(folder.glob(pattern)) if folder.is_dir() else []
    if not candidates:
        raise ComparisonError(f"aucune réponse archivée dans {folder} : lance avec --interroger")
    response = candidates[-1]
    metadata = response.with_suffix(".json")
    if not metadata.is_file():
        raise ComparisonError(f"{response.name} : fiche d'archive absente, empreinte invérifiable")
    declared = json.loads(metadata.read_text(encoding="utf-8")).get("sha256")
    if declared != hashlib.sha256(response.read_bytes()).hexdigest():
        raise ComparisonError(f"{response.name} : empreinte différente de celle de son archive")
    return response


def markdown_table(rows: Sequence[Row]) -> str:
    lines = [
        (
            "| Signe | Frontière (°) | Instant du passage (JD TDB) | Écart entre chaînes (°) "
            "| Séparation (″) | Écart à la frontière (°) | Tolérance (°) "
            "| Latitude du Soleil (°) |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {row.sign_id} | {row.boundary_deg!r} | {row.tdb_jd:.9f} | "
        f"{row.chain_difference_deg:+.3e} | {row.separation_arcsec:.3e} | "
        f"{row.boundary_difference_deg:+.3e} | {BOUNDARY_TOLERANCE_DEG:.0e} | "
        f"{row.sun_latitude_deg:+.6f} |"
        for row in rows
    ]
    return "\n".join(lines)


def markdown_frame_table(rows: Sequence[FrameRow]) -> str:
    lines = [
        (
            "| Signe | Instant (JD TDB) | Séparation R / Horizons (″) | Tolérance (″) "
            "| Écart en longitude (°) | Écart en latitude (°) | Résidu expliqué (″) |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {row.sign_id} | {row.tdb_jd:.9f} | {row.separation_arcsec:.6f} | "
        f"{FRAME_TOLERANCE_ARCSEC} | {row.longitude_difference_deg:+.3e} | "
        f"{row.latitude_difference_deg:+.3e} | {row.explained_residual_arcsec:.3e} |"
        for row in rows
    ]
    return "\n".join(lines)


def main(
    argv: Sequence[str] | None = None,
    *,
    fixtures: Path = FIXTURES,
    ephemeris: Path | None = None,
    now: datetime | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--interroger", action="store_true", help="interroger Horizons et archiver les réponses"
    )
    parser.add_argument("--tableau", action="store_true", help="afficher les tableaux en Markdown")
    options = parser.parse_args(argv)
    try:
        chain = SunChain(ephemeris if ephemeris is not None else dossier_donnees() / EPHEMERIS_FILE)
        crossings = sun_crossings(construct(), chain, REFERENCE_YEAR)
        responses: dict[Plane, Path] = {}
        instants = [crossing.tdb_jd for crossing in crossings]
        moment = now or datetime.now(UTC)
        planes: tuple[Plane, ...] = ("FRAME", "ECLIPTIC")
        for plane in planes:
            if options.interroger:
                responses[plane] = archive(
                    build_query(instants, plane), fixtures, plane, REFERENCE_YEAR, moment
                )
                print(f"  Réponse archivée : {responses[plane].name}")
            else:
                responses[plane] = latest_archive(fixtures, REFERENCE_YEAR, plane)
        icrf_text = responses["FRAME"].read_text(encoding="utf-8")
        ecliptic_text = responses["ECLIPTIC"].read_text(encoding="utf-8")
        icrf_vectors = parse_vectors(icrf_text, "FRAME")
        obliquity = horizons_obliquity_arcsec(ecliptic_text)
        rows = compare(crossings, icrf_vectors, chain)
        frame_rows = compare_frames(
            crossings, icrf_vectors, parse_vectors(ecliptic_text, "ECLIPTIC"), obliquity
        )
    except (ComparisonError, ErreurTelechargement, ErreurRegistre) as error:
        print(f"  ✘ {error}", file=sys.stderr)
        return 1

    worst_chain = max(abs(row.chain_difference_deg) for row in rows)
    worst_boundary = max(abs(row.boundary_difference_deg) for row in rows)
    worst_separation = max(row.separation_arcsec for row in rows)
    worst_frame = max(row.separation_arcsec for row in frame_rows)
    worst_explained = max(row.explained_residual_arcsec for row in frame_rows)

    print(f"1. Chaîne de positions, archive {responses['FRAME'].name}")
    for row in rows:
        print(
            f"  {row.sign_id}  frontière {row.boundary_deg!r:>20}  "
            f"entre chaînes {row.chain_difference_deg:+.3e}°  "
            f"séparation {row.separation_arcsec:.3e}″  "
            f"à la frontière {row.boundary_difference_deg:+.3e}°"
        )
    print(
        f"  Écart maximal entre chaînes   : {worst_chain:.3e}°  (tolérance {CHAIN_TOLERANCE_DEG}°)"
    )
    print(f"  Séparation angulaire maximale : {worst_separation:.3e}″")
    print(
        f"  Écart maximal à la frontière  : {worst_boundary:.3e}°  "
        f"(tolérance {BOUNDARY_TOLERANCE_DEG}°)"
    )
    print(f"2. Repère R, archive {responses['ECLIPTIC'].name}")
    print(f"  Obliquité déclarée par Horizons : {obliquity}″")
    for frame_row in frame_rows:
        print(
            f"  {frame_row.sign_id}  séparation {frame_row.separation_arcsec:.6f}″  "
            f"longitude {frame_row.longitude_difference_deg:+.3e}°  "
            f"latitude {frame_row.latitude_difference_deg:+.3e}°  "
            f"résidu expliqué {frame_row.explained_residual_arcsec:.3e}″"
        )
    print(
        f"  Séparation maximale R / Horizons : {worst_frame:.6f}″  "
        f"(tolérance {FRAME_TOLERANCE_ARCSEC}″)"
    )
    print(
        f"  Résidu maximal une fois les conventions de Horizons appliquées : "
        f"{worst_explained:.3e}″  (tolérance {EXPLAINED_TOLERANCE_ARCSEC}″)"
    )
    if options.tableau:
        print()
        print(markdown_table(rows))
        print()
        print(markdown_frame_table(frame_rows))
    within = (
        worst_chain <= CHAIN_TOLERANCE_DEG
        and worst_boundary <= BOUNDARY_TOLERANCE_DEG
        and worst_frame <= FRAME_TOLERANCE_ARCSEC
        and worst_explained <= EXPLAINED_TOLERANCE_ARCSEC
    )
    if not within:
        print("  ✘ tolérance dépassée", file=sys.stderr)
    return 0 if within else 1


if __name__ == "__main__":
    sys.exit(main())
