"""Position astrométrique géocentrique du Soleil dans le repère B.

Référence : annexe technique § B (observateur, positions, éphéméride, échelles de temps), E
(cibles) ; règle « Positions astrométriques géocentriques : `.observe()` sans `.apparent()` ».

- Éphéméride JPL DE440s, fichier figé : son empreinte est comparée à `donnees/sources.toml`
  avant tout calcul. Hors de sa période (26/12/1849 – 22/01/2150), erreur explicite, jamais de
  valeur approchée.
- Échelles de temps (décision 0010) : UTC à partir de 1972, temps universel avant ; l'échelle
  est indiquée avec chaque instant. Au-delà des tables de temps de Skyfield, l'instant est
  marqué « conditionnel » : les secondes intercalaires à venir ne sont pas connues.
- Les tables de temps sont celles que Skyfield embarque : aucun téléchargement à l'exécution.
"""

from __future__ import annotations

import hashlib
import os
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Literal

import numpy as np
import skyfield
from skyfield.api import load, load_file

from moteur.coordinates import frame_matrix, longitude_latitude_deg

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "donnees" / "sources.toml"
EPHEMERIS_ID = "de440s"
SUN, EARTH = 10, 399
SUN_TARGET_KIND = "center"
UTC_ERA_START = datetime(1972, 1, 1, tzinfo=UTC)
SECONDS_PER_DAY = 86400.0

TimeScale = Literal["utc", "ut1_before_1972"]


class PositionError(Exception):
    """La position ne peut pas être calculée. Le message est destiné à la personne."""


class EphemerisUnavailable(PositionError):
    """Le fichier d'éphéméride est absent ou ne correspond pas à son empreinte."""


class OutOfEphemerisRange(PositionError):
    """L'instant est hors de la période couverte par l'éphéméride."""


@dataclass(frozen=True, repr=False)
class Instant:
    """Un instant, dans l'échelle des éphémérides, avec la façon dont il a été obtenu."""

    tt_jd: float
    time_scale: TimeScale
    conditional: bool  # vrai au-delà des tables de temps : secondes intercalaires inconnues

    def __repr__(self) -> str:
        return "Instant(<données personnelles masquées>)"


def data_directory() -> Path:
    """Dossier des fichiers téléchargés : $B13_DONNEES, sinon donnees/telechargees/."""
    variable = os.environ.get("B13_DONNEES")
    if variable is None:
        return ROOT / "donnees" / "telechargees"
    if not variable.strip():
        raise EphemerisUnavailable("B13_DONNEES est définie mais vide")
    return Path(variable)


def _declared_source() -> tuple[str, str]:
    """Nom du fichier d'éphéméride et empreinte déclarée dans donnees/sources.toml."""
    try:
        registry = tomllib.loads(SOURCES.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        # Le détail technique (chemin du serveur) reste dans l'exception d'origine.
        raise EphemerisUnavailable("donnees/sources.toml illisible") from error
    for source in registry.get("source", []):
        if source.get("id") == EPHEMERIS_ID:
            return str(source.get("fichier", "")), str(source.get("sha256", ""))
    raise EphemerisUnavailable(f"source « {EPHEMERIS_ID} » absente de donnees/sources.toml")


class SunEphemeris:
    """Chaîne de calcul du Soleil : éphéméride contrôlée, tables de temps, matrice R."""

    def __init__(self, path: Path, expected_sha256: str) -> None:
        if not path.is_file():
            raise EphemerisUnavailable(
                "éphéméride DE440s absente : lance /donnees pour la télécharger"
            )
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                digest.update(block)
        self.sha256 = digest.hexdigest()
        if not expected_sha256 or self.sha256 != expected_sha256:
            raise EphemerisUnavailable(
                "éphéméride DE440s : empreinte différente de celle de donnees/sources.toml"
            )
        self.file_name = path.name
        self._timescale = load.timescale(builtin=True)
        kernel = load_file(str(path))
        self._earth, self._sun = kernel["earth"], kernel["sun"]
        self._matrix = frame_matrix()
        # Période commune aux segments utilisés (Terre et Soleil), en jours juliens TDB.
        used = [s for s in kernel.segments if s.target in (SUN, EARTH, 3)]
        self.start_tdb_jd = max(float(s.spk_segment.start_jd) for s in used)
        self.end_tdb_jd = min(float(s.spk_segment.end_jd) for s in used)
        # Dernière date des tables de temps : au-delà, ΔT et secondes intercalaires sont prédits.
        self.time_data_end_tt_jd = float(np.asarray(self._timescale.delta_t_table[0])[-1])
        self.last_leap_second_tai_minus_utc = float(self._timescale.leap_offsets[-1])
        # Jonction de la décision 0010, exprimée en TT : un seul critère dans les deux sens.
        self._utc_era_start_tt_jd = float(self._timescale.utc(1972, 1, 1).tt)

    # --- Temps -----------------------------------------------------------------------------

    def instant(self, moment: datetime) -> Instant:
        """Convertit un instant civil daté en UTC vers l'échelle des éphémérides (décision 0010)."""
        if moment.tzinfo is None:
            raise ValueError("un instant avec fuseau est attendu")
        moment = moment.astimezone(UTC)
        seconds = moment.second + moment.microsecond / 1e6
        fields = (moment.year, moment.month, moment.day, moment.hour, moment.minute, seconds)
        scale: TimeScale
        if moment >= UTC_ERA_START:
            time, scale = self._timescale.utc(*fields), "utc"
        else:
            time, scale = self._timescale.ut1(*fields), "ut1_before_1972"
        tt_jd = float(time.tt)
        self._check_range(float(time.tdb))
        return Instant(tt_jd, scale, tt_jd > self.time_data_end_tt_jd)

    def utc_datetime(self, tt_jd: float) -> datetime:
        """Instant civil correspondant à une date TT, dans l'échelle de la décision 0010."""
        time = self._timescale.tt_jd(tt_jd)
        if tt_jd >= self._utc_era_start_tt_jd:
            moment: datetime = time.utc_datetime()
            return moment
        # Avant 1972 : temps universel. Jour julien UT1 converti en date grégorienne.
        ut1_jd = float(time.ut1)
        return datetime(2000, 1, 1, 12, tzinfo=UTC) + timedelta(days=ut1_jd - 2451545.0)

    def is_conditional(self, tt_jd: float) -> bool:
        return tt_jd > self.time_data_end_tt_jd

    def coverage(self) -> tuple[datetime, datetime]:
        """Premier et dernier instants couverts par l'éphéméride, lus dans le fichier."""
        origin = datetime(2000, 1, 1, 12, tzinfo=UTC)
        return (
            origin + timedelta(days=self.start_tdb_jd - 2451545.0),
            origin + timedelta(days=self.end_tdb_jd - 2451545.0),
        )

    def _out_of_range(self) -> OutOfEphemerisRange:
        first, last = self.coverage()
        return OutOfEphemerisRange(
            "date hors de la période couverte par l'éphéméride DE440s "
            f"(du {first:%d/%m/%Y} au {last:%d/%m/%Y}) : aucune position n'est calculée"
        )

    def _check_range(self, tdb_jd: float) -> None:
        if not self.start_tdb_jd <= tdb_jd <= self.end_tdb_jd:
            raise self._out_of_range()

    # --- Position --------------------------------------------------------------------------

    def sun_longitude_latitude(self, tt_jd: float) -> tuple[float, float]:
        """Longitude et latitude astrométriques géocentriques du Soleil, repère B, en degrés."""
        time = self._timescale.tt_jd(tt_jd)
        self._check_range(float(time.tdb))
        try:
            astrometric = self._earth.at(time).observe(self._sun)
        except ValueError as error:
            # Tout au début de la période, la lumière est partie avant le premier instant couvert.
            raise self._out_of_range() from error
        vector_icrs = np.asarray(astrometric.xyz.au, dtype=np.float64)
        longitude, latitude = longitude_latitude_deg(self._matrix @ vector_icrs)
        if longitude is None:
            raise PositionError("longitude du Soleil indéfinie")
        return longitude, latitude

    def sun_longitude(self, tt_jd: float) -> float:
        return self.sun_longitude_latitude(tt_jd)[0]

    # --- Manifeste -------------------------------------------------------------------------

    def manifest(self) -> dict[str, object]:
        """Ce qui identifie cette chaîne de calcul, pour le manifeste d'un résultat."""
        return {
            "ephemeris": self.file_name,
            "ephemeris_sha256": self.sha256,
            "observer": "geocentric",
            "position_type": "astrometric",
            "time_data": f"Skyfield {skyfield.__version__} bundled tables",
            "time_data_last_leap_second_tai_minus_utc": self.last_leap_second_tai_minus_utc,
            # Au-delà de cette date, un instant est « conditionnel » : secondes intercalaires et
            # règles d'heure légale à venir ne sont pas connues.
            "time_data_end_utc": self.utc_datetime(self.time_data_end_tt_jd).date().isoformat(),
            "time_scale_policy": "utc_from_1972_ut1_before",
        }


@cache
def _load(path: Path, expected_sha256: str) -> SunEphemeris:
    return SunEphemeris(path, expected_sha256)


def load_ephemeris() -> SunEphemeris:
    """Éphéméride de production, contrôlée contre donnees/sources.toml, chargée une fois."""
    file_name, expected = _declared_source()
    return _load(data_directory() / file_name, expected)
