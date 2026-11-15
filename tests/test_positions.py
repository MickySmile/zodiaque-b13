"""Positions du Soleil et échelles de temps (annexe technique § B, E ; décision 0010).

Les tests marqués `donnees` exigent l'éphéméride DE440s téléchargée.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from moteur import coordinates as c
from moteur import positions as p

J2000 = datetime(2000, 1, 1, 12, tzinfo=UTC)


def tt_minus_civil_seconds(instant: p.Instant, moment: datetime) -> float:
    return (instant.tt_jd - (2451545.0 + (moment - J2000).total_seconds() / 86400.0)) * 86400.0


# --- Éphéméride absente ou non fiable (sans données) ---------------------------------------


def test_positions_missing_ephemeris_is_an_explicit_error(tmp_path: Path) -> None:
    with pytest.raises(p.EphemerisUnavailable, match="/donnees"):
        p.SunEphemeris(tmp_path / "absent.bsp", "0" * 64)


def test_positions_ephemeris_with_another_fingerprint_is_refused(tmp_path: Path) -> None:
    fake = tmp_path / "de440s.bsp"
    fake.write_bytes(b"ce fichier n'est pas une ephemeride")
    with pytest.raises(p.EphemerisUnavailable, match="empreinte"):
        p.SunEphemeris(fake, "0" * 64)


def test_positions_ephemeris_without_declared_fingerprint_is_refused(tmp_path: Path) -> None:
    """Pas d'empreinte déclarée, pas de calcul : le contrôle échoue fermé."""
    fake = tmp_path / "de440s.bsp"
    fake.write_bytes(b"contenu quelconque")
    with pytest.raises(p.EphemerisUnavailable, match="empreinte"):
        p.SunEphemeris(fake, "")


def test_positions_empty_data_directory_variable_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("B13_DONNEES", "")
    with pytest.raises(p.EphemerisUnavailable):
        p.data_directory()


def test_positions_data_directory_follows_the_variable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("B13_DONNEES", raising=False)
    assert p.data_directory() == p.ROOT / "donnees" / "telechargees"
    monkeypatch.setenv("B13_DONNEES", str(tmp_path))
    assert p.data_directory() == tmp_path


def test_positions_error_messages_do_not_leak_server_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(p, "SOURCES", tmp_path / "absent.toml")
    with pytest.raises(p.EphemerisUnavailable) as raised:
        p._declared_source()
    assert str(tmp_path) not in str(raised.value)


def test_positions_instant_representation_shows_nothing() -> None:
    assert "2461" not in repr(p.Instant(2461000.5, "utc", False))


# --- Échelles de temps (décision 0010) -----------------------------------------------------


@pytest.fixture(scope="module")
def chain() -> p.SunEphemeris:
    return p.load_ephemeris()


@pytest.mark.donnees
def test_positions_utc_from_1972_uses_leap_seconds(chain: p.SunEphemeris) -> None:
    """TT − UTC = 32,184 s + (TAI − UTC) : 42,184 s au 1ᵉʳ janvier 1972, 69,184 s en 2026."""
    first = datetime(1972, 1, 1, tzinfo=UTC)
    recent = datetime(2026, 6, 1, 10, tzinfo=UTC)
    assert chain.instant(first).time_scale == "utc"
    assert tt_minus_civil_seconds(chain.instant(first), first) == pytest.approx(42.184, abs=1e-3)
    assert tt_minus_civil_seconds(chain.instant(recent), recent) == pytest.approx(69.184, abs=1e-3)


@pytest.mark.donnees
def test_positions_before_1972_civil_time_is_universal_time(chain: p.SunEphemeris) -> None:
    eve = datetime(1971, 12, 31, 23, 59, 59, tzinfo=UTC)
    old = datetime(1900, 6, 1, 12, tzinfo=UTC)
    assert chain.instant(eve).time_scale == "ut1_before_1972"
    assert chain.instant(old).time_scale == "ut1_before_1972"
    # ΔT = TT − UT1 : quelques secondes négatives vers 1900, une quarantaine en 1971.
    assert -10.0 < tt_minus_civil_seconds(chain.instant(old), old) < 0.0
    assert 41.0 < tt_minus_civil_seconds(chain.instant(eve), eve) < 43.0


@pytest.mark.donnees
def test_positions_junction_of_the_two_scales_is_within_a_tenth_of_a_second(
    chain: p.SunEphemeris,
) -> None:
    before = chain.instant(datetime(1971, 12, 31, 23, 59, 59, tzinfo=UTC))
    after = chain.instant(datetime(1972, 1, 1, tzinfo=UTC))
    assert abs((after.tt_jd - before.tt_jd) * 86400.0 - 1.0) < 0.1


@pytest.mark.donnees
@pytest.mark.parametrize(
    "moment",
    [
        datetime(1850, 3, 1, 6, 30, tzinfo=UTC),
        datetime(1900, 6, 1, 12, tzinfo=UTC),
        datetime(1971, 12, 31, 23, 59, 59, tzinfo=UTC),
        datetime(1972, 1, 1, 0, 0, 1, tzinfo=UTC),
        datetime(2026, 6, 1, 10, tzinfo=UTC),
        datetime(2100, 1, 1, tzinfo=UTC),
    ],
)
def test_positions_instant_and_civil_date_are_inverse(
    chain: p.SunEphemeris, moment: datetime
) -> None:
    """Le même seuil sert dans les deux sens : l'aller-retour redonne l'instant, à 1 ms près."""
    back = chain.utc_datetime(chain.instant(moment).tt_jd)
    assert abs((back - moment).total_seconds()) < 1e-3


@pytest.mark.donnees
def test_positions_naive_datetime_is_refused(chain: p.SunEphemeris) -> None:
    with pytest.raises(ValueError, match="fuseau"):
        chain.instant(datetime(2026, 6, 1, 10))


@pytest.mark.donnees
def test_positions_future_instants_are_conditional(chain: p.SunEphemeris) -> None:
    """PRD § 7 : au-delà des tables de temps, secondes intercalaires et heure légale inconnues."""
    assert chain.instant(datetime(2000, 1, 1, tzinfo=UTC)).conditional is False
    assert chain.instant(datetime(2100, 1, 1, tzinfo=UTC)).conditional is True
    threshold = chain.time_data_end_tt_jd
    assert chain.is_conditional(threshold) is False
    assert chain.is_conditional(math.nextafter(threshold, math.inf)) is True
    assert chain.manifest()["time_data_end_utc"] == chain.utc_datetime(threshold).date().isoformat()


# --- Position du Soleil --------------------------------------------------------------------


@pytest.mark.donnees
def test_positions_sun_is_astrometric_not_apparent(chain: p.SunEphemeris) -> None:
    """Annexe B : `.observe()` sans `.apparent()`. L'aberration vaut une vingtaine de secondes
    d'arc ; la longitude rendue doit être celle de la position astrométrique."""
    instant = chain.instant(datetime(2026, 6, 1, 10, tzinfo=UTC))
    time = chain._timescale.tt_jd(instant.tt_jd)
    astrometric = chain._earth.at(time).observe(chain._sun)
    expected, _ = c.longitude_latitude_deg(c.frame_matrix() @ np.asarray(astrometric.xyz.au))
    apparent, _ = c.longitude_latitude_deg(
        c.frame_matrix() @ np.asarray(astrometric.apparent().xyz.au)
    )
    assert expected is not None and apparent is not None
    assert chain.sun_longitude(instant.tt_jd) == expected
    difference_arcsec = abs(c.signed_wrap(apparent - expected)) * 3600.0
    assert 15.0 < difference_arcsec < 25.0


@pytest.mark.donnees
def test_positions_sun_stays_close_to_the_circle_and_moves_forward(chain: p.SunEphemeris) -> None:
    start = chain.instant(datetime(2026, 1, 1, tzinfo=UTC)).tt_jd
    previous = chain.sun_longitude(start)
    for day in range(1, 366):
        longitude, latitude = chain.sun_longitude_latitude(start + day)
        assert 0.0 <= longitude < 360.0
        assert abs(latitude) < 0.01  # le Soleil reste à quelques secondes d'arc du cercle B
        assert 0.9 < c.signed_wrap(longitude - previous) < 1.1  # y compris au passage par 0°
        previous = longitude


@pytest.mark.donnees
def test_positions_outside_the_ephemeris_is_an_explicit_error(chain: p.SunEphemeris) -> None:
    """Jeu F6 : aucune position approchée hors de DE440s, et un message qui donne la période."""
    first, last = chain.coverage()
    for moment in (
        datetime(1849, 6, 1, tzinfo=UTC),
        datetime(2150, 6, 1, tzinfo=UTC),
        first - timedelta(days=1),
        last + timedelta(days=1),
    ):
        with pytest.raises(p.OutOfEphemerisRange) as raised:
            chain.instant(moment)
        message = str(raised.value)
        assert f"{first:%d/%m/%Y}" in message and f"{last:%d/%m/%Y}" in message


@pytest.mark.donnees
def test_positions_very_first_minutes_of_the_ephemeris_are_an_explicit_error(
    chain: p.SunEphemeris,
) -> None:
    """La lumière reçue au tout début de la période est partie avant : même erreur explicite."""
    with pytest.raises(p.OutOfEphemerisRange, match="DE440s"):
        chain.sun_longitude(chain.start_tdb_jd + 1e-4)
    assert 0.0 <= chain.sun_longitude(chain.start_tdb_jd + 1.0) < 360.0
    assert 0.0 <= chain.sun_longitude(chain.end_tdb_jd - 1.0) < 360.0


@pytest.mark.donnees
def test_positions_manifest_identifies_the_chain(chain: p.SunEphemeris) -> None:
    manifest = chain.manifest()
    assert manifest["ephemeris"] == "de440s.bsp"
    assert manifest["ephemeris_sha256"] == chain.sha256 and len(chain.sha256) == 64
    assert manifest["observer"] == "geocentric"
    assert manifest["position_type"] == "astrometric"
    assert manifest["time_scale_policy"] == "utc_from_1972_ut1_before"
    assert "Skyfield" in str(manifest["time_data"])
