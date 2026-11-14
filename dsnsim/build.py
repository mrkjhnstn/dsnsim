"""Build static JSON for the viewer.

    python -m dsnsim.build --out site/data            # normal hourly run
    python -m dsnsim.build --out site/data --check    # also print a source report
    python -m dsnsim.build --out site/data --schedule-file docs/example-schedule-json.json \
        --now 2026-11-02T00:00:00Z                     # offline schedule, fixed time

Outputs: schedule.json, ephem.json, meta.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import ephem as eph
from . import schedule as sched
from .config import ANTENNAS, BODIES, COMPLEXES, MISSIONS, STEP_SECONDS
from .geometry import elevation_deg, interp

UTC = timezone.utc
BACK_DAYS, FWD_DAYS = 1, 7      # range the viewer needs
PAD_BACK, PAD_FWD = 2, 9        # range fetched, so cached data stays valid between refreshes


def _parse_now(s: str | None) -> datetime:
    if not s:
        return datetime.now(UTC)
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)


def _covers(track: dict, start: datetime, stop: datetime) -> bool:
    t_end = track["t0"] + track["step"] * (len(track["pos"]) - 1)
    return track["t0"] <= start.timestamp() and t_end >= stop.timestamp()


def _fetch_object(cfg: dict, start: datetime, stop: datetime) -> tuple[dict, str]:
    step = STEP_SECONDS[cfg.get("step", "deep")]
    if "tle" in cfg:
        return eph.fetch_tle(cfg["tle"], start, stop, step), f"tle:{cfg['tle']}"
    return eph.fetch_horizons(cfg["horizons"], start, stop, step), f"horizons:{cfg['horizons']}"


def build_ephem(now: datetime, old: dict, max_age_h: float, users: set[str], pause: float = 0.5):
    """Return (objects, status). Reuses cached tracks that are fresh and cover the window."""
    grid_start = (now - timedelta(days=PAD_BACK)).replace(hour=0, minute=0, second=0, microsecond=0)
    grid_stop = grid_start + timedelta(days=PAD_BACK + PAD_FWD + 1)
    need_start, need_stop = now - timedelta(days=BACK_DAYS), now + timedelta(days=FWD_DAYS)
    old_objs = old.get("objects", {})
    objects: dict[str, dict] = {}
    status: dict[str, dict] = {}

    def resolve(key: str, cfg: dict) -> None:
        if "alias" in cfg:
            objects[key] = {"alias": cfg["alias"]}
            status[key] = {"source": f"stand-in:{cfg['alias']}", "ok": True}
            return
        src = f"tle:{cfg['tle']}" if "tle" in cfg else f"horizons:{cfg['horizons']}"
        cached = old_objs.get(key)
        if (
            cached
            and cached.get("source") == src
            and "pos" in cached
            and now.timestamp() - cached.get("fetched", 0) < max_age_h * 3600
            and _covers(cached, need_start, need_stop)
        ):
            objects[key] = cached
            status[key] = {"source": src, "ok": True, "cached": True}
            return
        try:
            track, src = _fetch_object(cfg, grid_start, grid_stop)
            time.sleep(pause)
            if not _covers(track, need_start, need_stop):
                raise eph.EphemError("trajectory does not cover the display window")
            objects[key] = {**track, "source": src, "fetched": round(now.timestamp())}
            status[key] = {"source": src, "ok": True}
        except Exception as exc:  # one bad source must not stop the build
            fb = cfg.get("fallback")
            status[key] = {"source": src, "ok": False, "error": str(exc)[:600]}
            if fb:
                objects[key] = {"alias": fb}
                status[key]["fallback"] = fb

    for key, cfg in BODIES.items():
        resolve(key, cfg)
    for key, cfg in MISSIONS.items():
        if key in users:
            resolve(key, cfg)
    return objects, status


def _track_for(objects: dict, key: str) -> dict | None:
    obj = objects.get(key)
    if obj and "alias" in obj:
        obj = objects.get(obj["alias"])
    return obj if obj and "pos" in obj else None


def elevation_report(activities: list[dict], objects: dict) -> list[dict]:
    """Add mid-track elevation to each track; list those below the horizon."""
    low = []
    for a in activities:
        if a["kind"] != "track":
            continue
        track = _track_for(objects, a["user"])
        if not track:
            continue
        bot = datetime.fromisoformat(a["bot"].replace("Z", "+00:00")).timestamp()
        eot = datetime.fromisoformat(a["eot"].replace("Z", "+00:00")).timestamp()
        ant = ANTENNAS[a["dss"]]
        els = []
        for t in (bot, (bot + eot) / 2, eot):
            pos = interp(track, t)
            els.append(None if pos is None else round(elevation_deg(pos, t, ant["lat"], ant["lon"], ant["alt_m"]), 1))
        if els[1] is None:
            continue
        a["el"] = els  # elevation (deg) at BOT, mid-track, EOT
        if els[1] < 0:
            low.append({k: a[k] for k in ("id", "user", "dss", "activity", "bot", "eot", "assoc_type", "el")})
    return low


def write_json(path: Path, obj) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, separators=(",", ":")))
    tmp.replace(path)  # atomic, so the viewer never reads a half-written file


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="site/data", help="output folder")
    ap.add_argument("--now", help="override current time (ISO, UTC)")
    ap.add_argument("--schedule-file", help="read schedule JSON from a file instead of the endpoint")
    ap.add_argument("--skip-ephem", action="store_true", help="schedule only; keep existing ephem.json")
    ap.add_argument("--ephem-max-age-hours", type=float, default=24)
    ap.add_argument("--check", action="store_true", help="print a per-mission source report")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    now = _parse_now(args.now)
    win_start, win_stop = now - timedelta(days=PAD_BACK), now + timedelta(days=PAD_FWD)

    # Schedule
    if args.schedule_file:
        raw = json.loads(Path(args.schedule_file).read_text())
    else:
        raw = sched.fetch_schedule(win_start, win_stop)
    activities = sched.process(raw)
    users = {a["user"] for a in activities if a["kind"] == "track"}
    unknown = sorted(users - set(MISSIONS))

    # Trajectories
    ephem_path = out / "ephem.json"
    old = json.loads(ephem_path.read_text()) if ephem_path.exists() else {}
    if args.skip_ephem:
        objects, status = old.get("objects", {}), {}
    else:
        objects, status = build_ephem(now, old, args.ephem_max_age_hours, users)
    low = elevation_report(activities, objects)

    generated = sched.iso(now)
    write_json(
        out / "schedule.json",
        {
            "generated": generated,
            "window": {"start": sched.iso(win_start), "end": sched.iso(win_stop)},
            "complexes": COMPLEXES,
            "antennas": {str(k): v for k, v in ANTENNAS.items()},
            "activities": activities,
        },
    )
    if not args.skip_ephem:
        write_json(
            ephem_path,
            {
                "generated": generated,
                "frame": "geocentric ICRF/J2000 equatorial, km; t0 unix seconds UTC; step seconds",
                "missions": {k: {"name": v["name"], "region": v["region"]} for k, v in MISSIONS.items()},
                "bodies": {k: {"name": v["name"]} for k, v in BODIES.items()},
                "objects": objects,
            },
        )
    failed = {k: v for k, v in status.items() if not v["ok"]}
    write_json(
        out / "meta.json",
        {
            "generated": generated,
            "counts": {
                "activities": len(activities),
                "tracks": sum(a["kind"] == "track" for a in activities),
                "busy": sum(a["kind"] == "busy" for a in activities),
            },
            "unknown_users": unknown,
            "ephem_status": status,
            "below_horizon_tracks": low,
        },
    )

    n_track = sum(a["kind"] == "track" for a in activities)
    print(f"{generated}: {len(activities)} activities ({n_track} tracks), "
          f"{len(objects)} trajectories, {len(failed)} source failures, "
          f"{len(low)} tracks below horizon")
    if unknown:
        print("Users with no mission config:", ", ".join(unknown))
    if low:
        print("Tracks below the horizon at mid-track (el at BOT, mid, EOT):")
        for t in low:
            print(f"  {t['user']:5s} DSS-{t['dss']} {t['bot']} to {t['eot']} {t['activity']!r} {t['assoc_type']} el={t['el']}")
    if args.check:
        print("Mid-track elevation by mission (tracks, min, median):")
        by_user: dict[str, list[float]] = {}
        for a in activities:
            if "el" in a:
                by_user.setdefault(a["user"], []).append(a["el"][1])
        for user, els in sorted(by_user.items()):
            els.sort()
            print(f"  {user:5s} {len(els):3d}  {els[0]:6.1f}  {els[len(els) // 2]:6.1f}")
    if args.check or failed:
        for key, st in sorted(status.items()):
            if args.check or not st["ok"]:
                tag = "ok  " if st["ok"] else "FAIL"
                extra = " (cached)" if st.get("cached") else ""
                if not st["ok"]:
                    extra = f" -> stand-in {st['fallback']}" if st.get("fallback") else " -> not shown"
                    extra += f"\n       {st['error']}"
                print(f"  {tag} {key:8s} {st['source']}{extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
