"""Trajectory sources: JPL Horizons vectors and TLE/SGP4.

All positions are geocentric, ICRF/J2000 equatorial, in km, sampled on a
uniform UTC grid: {"t0": epoch seconds, "step": seconds, "pos": [[x, y, z], ...]}.
"""
from __future__ import annotations

import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from .config import CELESTRAK_URL, HORIZONS_URL

UTC = timezone.utc
TDB_MINUS_UTC = 69.184  # seconds; TT-UTC since 2017 (TDB ~ TT to within 2 ms)
JD_UNIX_EPOCH = 2440587.5


class EphemError(Exception):
    pass


def _get(url: str, timeout: float = 90) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "dsnsim/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


# --- Horizons ----------------------------------------------------------------
def horizons_url(command: str, start: datetime, stop: datetime, step_s: int) -> str:
    fmt = "%Y-%m-%d %H:%M"
    # Horizons reads vector-table times as TDB; shift so samples land on the UTC grid.
    shift = timedelta(seconds=TDB_MINUS_UTC)
    params = {
        "format": "text",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'VECTORS'",
        "CENTER": "'500@399'",
        "REF_PLANE": "'FRAME'",
        "REF_SYSTEM": "'ICRF'",
        "OUT_UNITS": "'KM-S'",
        "VEC_TABLE": "'1'",
        "CSV_FORMAT": "'YES'",
        "START_TIME": f"'{(start + shift).strftime(fmt + ':%S.%f')[:-3]}'",
        "STOP_TIME": f"'{(stop + shift).strftime(fmt + ':%S.%f')[:-3]}'",
        "STEP_SIZE": f"'{step_s // 60} m'",
    }
    return f"{HORIZONS_URL}?{urllib.parse.urlencode(params)}"


def parse_horizons(text: str, step_s: int) -> dict:
    """Parse a Horizons CSV vector table (VEC_TABLE=1) into a sampled track."""
    if "$$SOE" not in text or "$$EOE" not in text:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        raise EphemError("Horizons returned no ephemeris: " + " | ".join(lines[:12])[:600])
    body = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    jds, pos = [], []
    for line in body.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 5:
            continue
        jds.append(float(parts[0]))
        pos.append([round(float(parts[2]), 1), round(float(parts[3]), 1), round(float(parts[4]), 1)])
    if len(pos) < 2:
        raise EphemError("Horizons returned fewer than 2 samples")
    t0 = (jds[0] - JD_UNIX_EPOCH) * 86400.0 - TDB_MINUS_UTC
    return {"t0": round(t0), "step": step_s, "pos": pos}


def fetch_horizons(command: str, start: datetime, stop: datetime, step_s: int, get=_get) -> dict:
    return parse_horizons(get(horizons_url(command, start, stop, step_s)), step_s)


# --- TLE / SGP4 --------------------------------------------------------------
def parse_tle(text: str) -> tuple[str, str]:
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    l1 = next((ln for ln in lines if ln.startswith("1 ")), None)
    l2 = next((ln for ln in lines if ln.startswith("2 ")), None)
    if not l1 or not l2:
        raise EphemError("No TLE in response: " + " | ".join(lines[:3])[:200])
    return l1, l2


def propagate_tle(l1: str, l2: str, start: datetime, stop: datetime, step_s: int) -> dict:
    """SGP4 via Skyfield, which also converts TEME to GCRS (~J2000)."""
    from skyfield.api import EarthSatellite, load

    ts = load.timescale()  # built-in data, no download
    n = int((stop - start).total_seconds() // step_s) + 1
    times = ts.from_datetimes([start + timedelta(seconds=i * step_s) for i in range(n)])
    xyz = EarthSatellite(l1, l2, ts=ts).at(times).position.km
    pos = [[round(float(xyz[0][i]), 1), round(float(xyz[1][i]), 1), round(float(xyz[2][i]), 1)] for i in range(n)]
    return {"t0": round(start.timestamp()), "step": step_s, "pos": pos}


def fetch_tle(norad: int, start: datetime, stop: datetime, step_s: int, get=_get) -> dict:
    text = get(f"{CELESTRAK_URL}?CATNR={norad}&FORMAT=TLE")
    l1, l2 = parse_tle(text)
    return propagate_tle(l1, l2, start, stop, step_s)
