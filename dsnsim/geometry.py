"""Small geometry helpers for sanity checks (visualization-grade accuracy)."""
from __future__ import annotations

import math

WGS84_A = 6378.137
WGS84_F = 1 / 298.257223563


def interp(track: dict, t: float) -> list[float] | None:
    """Linear interpolation of a sampled track at unix time t; None if outside."""
    pos, step = track["pos"], track["step"]
    u = (t - track["t0"]) / step
    if u < 0 or u > len(pos) - 1:
        return None
    i = min(int(u), len(pos) - 2)
    f = u - i
    a, b = pos[i], pos[i + 1]
    return [a[k] + f * (b[k] - a[k]) for k in range(3)]


def gmst_rad(t: float) -> float:
    """Greenwich mean sidereal time for unix time t (UT1 ~ UTC)."""
    d = t / 86400.0 + 2440587.5 - 2451545.0
    return math.radians((280.46061837 + 360.98564736629 * d) % 360.0)


def antenna_ecef(lat_deg: float, lon_deg: float, alt_m: float = 0.0) -> tuple[list[float], list[float]]:
    """Return (ECEF position km, local up unit vector)."""
    lat, lon, h = math.radians(lat_deg), math.radians(lon_deg), alt_m / 1000.0
    e2 = WGS84_F * (2 - WGS84_F)
    n = WGS84_A / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    up = [math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)]
    r = [(n + h) * up[0], (n + h) * up[1], (n * (1 - e2) + h) * math.sin(lat)]
    return r, up


def elevation_deg(pos_eci: list[float], t: float, lat_deg: float, lon_deg: float, alt_m: float = 0.0) -> float:
    """Elevation of an inertial position seen from a ground site.

    Ignores precession/nutation/polar motion (error well under 1 degree).
    """
    th = gmst_rad(t)
    c, s = math.cos(th), math.sin(th)
    ecef = [c * pos_eci[0] + s * pos_eci[1], -s * pos_eci[0] + c * pos_eci[1], pos_eci[2]]
    site, up = antenna_ecef(lat_deg, lon_deg, alt_m)
    d = [ecef[k] - site[k] for k in range(3)]
    rng = math.sqrt(sum(x * x for x in d))
    return math.degrees(math.asin(sum(d[k] * up[k] for k in range(3)) / rng))
