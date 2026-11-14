# dsnsim

A visualizer for the Deep Space Network: Earth, the three DSN complexes, and the links to scheduled tracks, driven by the public DSN schedule and spacecraft trajectories.

Status: backend pipeline and viewer in place. See [docs/plan.md](docs/plan.md) and [docs/feasibility.md](docs/feasibility.md).

## Backend

Requires Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Build the data files (fetches the schedule, Horizons vectors and TLEs)
python -m dsnsim.build --out site/data --check
```

Run it hourly (cron, launchd, etc.). The schedule is refreshed on every run; trajectories are reused for 24 hours.

| Output | Contents |
|---|---|
| `schedule.json` | Antennas, and one entry per activity: `kind` (`track` or `busy`), times, association, uplink windows |
| `ephem.json` | Geocentric J2000 positions (km) for each spacecraft and context body, on a uniform time grid |
| `meta.json` | Counts, trajectory source status, tracks whose spacecraft is below the horizon at mid-track |

Useful options:

- `--check` prints which trajectory source each mission resolved to, and any errors.
- `--schedule-file FILE --now ISO` builds from a saved schedule at a fixed time.
- `--skip-ephem` refreshes the schedule only.

Trajectory sources are set per mission in [`dsnsim/config.py`](dsnsim/config.py). A mission whose source fails is reported and either falls back to a stand-in or is left out; it never stops the build.

## Viewer

Static files in `site/`; no build step. After a backend run:

```bash
python -m http.server -d site 8000
# open http://localhost:8000
```

- **Timeline:** scrub, play/pause (space), reverse, speed steps, NOW (N).
- **Views:** ALL, GOLDSTONE, CANBERRA, MADRID (keys 1–4). A complex view follows the Earth's rotation and dims other links.
- **Details:** hover or click a spacecraft or antenna (or a status-board row) for a card with range, light time, current and next activity. Esc closes it.
- **Auto-tour:** TOUR (T) cycles ALL and each complex for unattended display; any click on the scene stops it. `?tour` in the URL starts it automatically.
- **Full screen:** F.
- **URL options:** `?t=2026-11-14T12:00:00Z` starts at a fixed time; `&view=MDSCC` starts on a complex; `&rate=600` sets the speed.

The viewer reloads the data files every 5 minutes, so it picks up hourly backend runs without a refresh.

Display conventions: directions from Earth's centre are true; distance is logarithmic. The antennas of a complex are fanned out in a row so each is visible. Links leave the antenna vertically and bend toward the spacecraft. Orbiters and landers are fanned out in a ring around the Moon, Mars and Jupiter. Setup and teardown links are dashed.

## Tests

```bash
pytest
```
