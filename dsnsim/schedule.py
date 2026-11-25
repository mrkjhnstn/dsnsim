"""Fetch the DSN schedule and reduce it to per-antenna activities."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .config import ANTENNAS, GROUND_USERS, PRELAUNCH_USERS, SCHEDULE_URL, TRACK_WRKCATS

UTC = timezone.utc


def parse_time(s: str) -> datetime:
    """Parse schedule day-of-year time, e.g. '2026-305T01:00:00' (UTC)."""
    return datetime.strptime(s.strip(), "%Y-%jT%H:%M:%S").replace(tzinfo=UTC)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_schedule(start: datetime, end: datetime, timeout: float = 60) -> dict:
    fmt = "%Y-%m-%dT%H:%M:%S"
    query = urllib.parse.urlencode(
        {"startTime": start.astimezone(UTC).strftime(fmt), "endTime": end.astimezone(UTC).strftime(fmt)}
    )
    with urllib.request.urlopen(f"{SCHEDULE_URL}?{query}", timeout=timeout) as resp:
        return json.load(resp)


def _merge(windows: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    out: list[tuple[datetime, datetime]] = []
    for s, e in sorted(windows):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def process(raw: dict) -> list[dict]:
    """Turn raw schedule JSON into one entry per activity on a DSN antenna.

    kind = 'track': spacecraft user with a committed work category -> link drawn
    kind = 'busy':  any other scheduled activity on the antenna
    """
    items = (raw.get("result") or {}).get("item") or []
    if isinstance(items, dict):  # a single record may come back unwrapped
        items = [items]

    by_pkg: dict[int, list[dict]] = {}
    for rec in items:
        if rec.get("facility") in ANTENNAS:
            by_pkg.setdefault(rec["pkgid"], []).append(rec)

    activities = []
    for pkgid, segs in by_pkg.items():
        first = segs[0]
        user = first["projuser"].strip()
        wrkcat = first["wrkcat"].strip()
        is_track = user not in GROUND_USERS and user not in PRELAUNCH_USERS and wrkcat in TRACK_WRKCATS
        assoc = first.get("associations", "").strip()
        assoc_id, _, assoc_type = assoc.partition(":")
        uplink = _merge(
            [
                (parse_time(s["segbot"]), parse_time(s["segeot"]))
                for s in segs
                if "UPL" in [e.strip() for e in s.get("segequipmentlist", "").split(",")]
            ]
        )
        activities.append(
            {
                "id": pkgid,
                "dss": first["facility"],
                "user": user,
                "kind": "track" if is_track else "busy",
                "activity": first["activity"].strip(),
                "wrkcat": wrkcat,
                "start": iso(parse_time(first["starttime"])),
                "bot": iso(parse_time(first["bot"])),
                "eot": iso(parse_time(first["eot"])),
                "end": iso(parse_time(first["endtime"])),
                "assoc_id": assoc_id or None,
                "assoc_type": assoc_type or None,
                "uplink": [[iso(s), iso(e)] for s, e in uplink] if is_track else [],
                "services": sorted({s["segservicealias"].strip() for s in segs}),
            }
        )
    activities.sort(key=lambda a: (a["start"], a["dss"], a["id"]))
    return activities
