import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from dsnsim import build, ephem, schedule
from dsnsim.config import ANTENNAS, MISSIONS
from dsnsim.geometry import antenna_ecef, elevation_deg, gmst_rad, interp

UTC = timezone.utc
EXAMPLE = Path(__file__).parent.parent / "docs" / "example-schedule-json.json"


@pytest.fixture(scope="module")
def activities():
    return schedule.process(json.loads(EXAMPLE.read_text()))


def test_parse_time():
    assert schedule.parse_time("2026-305T01:00:00") == datetime(2026, 11, 1, 1, tzinfo=UTC)


def test_only_dsn_antennas_and_unique_ids(activities):
    assert all(a["dss"] in ANTENNAS for a in activities)
    ids = [a["id"] for a in activities]
    assert len(ids) == len(set(ids))


def test_classification(activities):
    tracks = [a for a in activities if a["kind"] == "track"]
    busy = [a for a in activities if a["kind"] == "busy"]
    assert tracks and busy
    assert all(a["wrkcat"] in ("1A1", "1A2") and a["user"] not in ("DSN", "DSS") for a in tracks)
    assert any(a["user"] == "DSN" for a in busy)
    # every tracked user has a mission config
    assert {a["user"] for a in tracks} <= set(MISSIONS)


def test_mspa_uplink_windows(activities):
    grp = {a["user"]: a for a in activities if a["assoc_id"] == "11777924"}
    assert grp["M01O"]["assoc_type"] == "MSPA"
    assert grp["M01O"]["uplink"] == [["2026-11-02T01:00:00Z", "2026-11-02T03:20:00Z"]]
    assert grp["MRO"]["uplink"] == [["2026-11-02T10:10:00Z", "2026-11-02T13:00:00Z"]]
    assert grp["EMM"]["uplink"] == [] and grp["TGO"]["uplink"] == []


def test_array_spans_antennas(activities):
    arr = [a for a in activities if a["assoc_id"] == "11798305"]
    assert {a["dss"] for a in arr} == {24, 25, 26} and {a["user"] for a in arr} == {"VGR1"}


HORIZONS_SAMPLE = """*******
$$SOE
2461345.500800741, A.D. 2026-Nov-01 00:01:09.1840, 1.000000000000000E+05, -2.000000000000000E+05, 3.000000000000000E+04,
2461345.542467407, A.D. 2026-Nov-01 01:01:09.1840, 1.100000000000000E+05, -2.100000000000000E+05, 3.100000000000000E+04,
$$EOE
*******"""


def test_parse_horizons():
    tr = ephem.parse_horizons(HORIZONS_SAMPLE, 3600)
    assert tr["t0"] == datetime(2026, 11, 1, tzinfo=UTC).timestamp()
    assert tr["pos"][1] == [110000.0, -210000.0, 31000.0]
    with pytest.raises(ephem.EphemError):
        ephem.parse_horizons("No matches found.", 3600)


def test_horizons_url_has_tdb_shift():
    url = ephem.horizons_url("-31", datetime(2026, 11, 1, tzinfo=UTC), datetime(2026, 11, 2, tzinfo=UTC), 3600)
    assert "00%3A01%3A09.184" in url and "60+m" in url


def test_tle_propagation():
    # ISS-like TLE; checks plumbing and that radius is sensible
    l1 = "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9000"
    l2 = "2 25544  51.6400 208.9163 0006317  69.9862  25.2906 15.50000000    05"
    start = datetime(2024, 1, 1, 12, tzinfo=UTC)
    tr = ephem.propagate_tle(l1, l2, start, start + timedelta(hours=2), 600)
    assert len(tr["pos"]) == 13
    r = sum(x * x for x in tr["pos"][0]) ** 0.5
    assert 6600 < r < 6900


def test_elevation_zenith_and_interp():
    t = 1.79e9
    ant = ANTENNAS[14]
    site, up = antenna_ecef(ant["lat"], ant["lon"], ant["alt_m"])
    ecef = [site[k] + 1e6 * up[k] for k in range(3)]
    import math
    th = gmst_rad(t)
    eci = [math.cos(th) * ecef[0] - math.sin(th) * ecef[1], math.sin(th) * ecef[0] + math.cos(th) * ecef[1], ecef[2]]
    assert elevation_deg(eci, t, ant["lat"], ant["lon"], ant["alt_m"]) == pytest.approx(90, abs=1e-3)
    tr = {"t0": 0, "step": 10, "pos": [[0, 0, 0], [10, 20, 30]]}
    assert interp(tr, 5) == [5, 10, 15] and interp(tr, 11) is None


def test_build_offline(tmp_path, monkeypatch):
    """Full build with the example schedule and fake trajectory sources."""
    def fake_horizons(command, start, stop, step, get=None):
        if command == "ESCAPADE-Blue":
            raise ephem.EphemError("Multiple matches")
        n = int((stop - start).total_seconds() // step) + 1
        return {"t0": round(start.timestamp()), "step": step, "pos": [[1e6, 2e6, 3e5]] * n}

    monkeypatch.setattr(ephem, "fetch_horizons", fake_horizons)
    monkeypatch.setattr(ephem, "fetch_tle", lambda norad, start, stop, step, get=None: fake_horizons("x", start, stop, step))
    monkeypatch.setattr(build.time, "sleep", lambda s: None)
    args = ["--out", str(tmp_path), "--schedule-file", str(EXAMPLE), "--now", "2026-11-02T00:00:00Z"]
    assert build.main(args) == 0
    meta = json.loads((tmp_path / "meta.json").read_text())
    eph_out = json.loads((tmp_path / "ephem.json").read_text())
    assert meta["counts"]["tracks"] > 100
    assert meta["ephem_status"]["ESCB"]["ok"] is False and "ESCB" not in eph_out["objects"]
    assert eph_out["objects"]["CAPS"] == {"alias": "moon"}
    assert "pos" in eph_out["objects"]["VGR1"]
    # second run reuses the cache
    assert build.main(args) == 0
    meta2 = json.loads((tmp_path / "meta.json").read_text())
    assert meta2["ephem_status"]["VGR1"].get("cached") is True


def test_source_outage_keeps_previous_trajectory(tmp_path, monkeypatch):
    """A failed fetch reuses the previous trajectory if it still covers now."""
    def ok(command, start, stop, step, get=None):
        n = int((stop - start).total_seconds() // step) + 1
        return {"t0": round(start.timestamp()), "step": step, "pos": [[1e6, 2e6, 3e5]] * n}

    def down(*a, **k):
        raise ephem.EphemError("HTTP Error 503: Service Unavailable")

    monkeypatch.setattr(build.time, "sleep", lambda s: None)
    monkeypatch.setattr(ephem, "fetch_horizons", ok)
    monkeypatch.setattr(ephem, "fetch_tle", lambda norad, start, stop, step, get=None: ok("x", start, stop, step))
    base = ["--out", str(tmp_path), "--schedule-file", str(EXAMPLE)]
    assert build.main(base + ["--now", "2026-11-02T00:00:00Z"]) == 0
    # Two days later the cache is stale, and both CelesTrak and the Horizons backup are down.
    monkeypatch.setattr(ephem, "fetch_tle", down)
    monkeypatch.setattr(ephem, "fetch_horizons", down)
    assert build.main(base + ["--now", "2026-11-04T00:00:00Z"]) == 0
    meta = json.loads((tmp_path / "meta.json").read_text())
    eph_out = json.loads((tmp_path / "ephem.json").read_text())
    assert meta["ephem_status"]["CHDR"]["kept_previous"] is True
    assert "pos" in eph_out["objects"]["CHDR"]


def test_tle_outage_uses_horizons_backup(tmp_path, monkeypatch):
    def ok(command, start, stop, step, get=None):
        n = int((stop - start).total_seconds() // step) + 1
        return {"t0": round(start.timestamp()), "step": step, "pos": [[1e6, 2e6, 3e5]] * n}

    def down(*a, **k):
        raise ephem.EphemError("HTTP Error 503: Service Unavailable")

    monkeypatch.setattr(build.time, "sleep", lambda s: None)
    monkeypatch.setattr(ephem, "fetch_horizons", ok)
    monkeypatch.setattr(ephem, "fetch_tle", down)
    assert build.main(["--out", str(tmp_path), "--schedule-file", str(EXAMPLE), "--now", "2026-11-02T00:00:00Z"]) == 0
    st = json.loads((tmp_path / "meta.json").read_text())["ephem_status"]["CHDR"]
    assert st["ok"] and st["source"] == "horizons:Chandra Observatory" and st["backup_for"] == "tle:25867"
