# dsnsim

A visualizer for the Deep Space Network: Earth, the three DSN complexes, and the links to scheduled tracks, driven by the public DSN schedule and spacecraft trajectories.

Status: backend pipeline and viewer in place. Published hourly to GitHub Pages: https://mrkjhnstn.github.io/dsnsim/ (once Pages is enabled, see below). See [docs/plan.md](docs/plan.md) and [docs/feasibility.md](docs/feasibility.md).

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python3 -m dsnsim.serve          # builds the data, serves http://localhost:8002, rebuilds hourly
```

Options: `--port`, `--interval MINUTES`, `--no-build`, `--host 0.0.0.0` (let other machines connect).

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

Static files in `site/`; no build step. `python3 -m dsnsim.serve` serves it and keeps the data fresh; any static web server pointed at `site/` also works after a backend run.

- **Timeline:** scrub, play/pause (space), reverse, speed steps, NOW (N). Faster than real time, playback loops: on reaching either end it returns to the current time and continues at the same speed.
- **Views:** ALL, GOLDSTONE, CANBERRA, MADRID (keys 1–4). A complex view follows the Earth's rotation and dims other links.
- **Details:** hover or click a spacecraft or antenna (or a status-board row) for a card with range, light time, current and next activity. Esc closes it.
- **Timeline context:** with a card pinned, the scrub bar shows that antenna's, spacecraft's or planet's passes (cyan tracking, blue setup, gray teardown, amber busy). PREV PASS / NEXT PASS (keys `[` and `]`) jump between them.
- **Auto-tour:** TOUR (T) cycles ALL and each complex for unattended display, showing a card for each spacecraft in contact (ALL view, expanding the Moon, Mars or Jupiter group as needed) and for each antenna (complex views); any click on the scene stops it. `?tour` in the URL starts it automatically.
- **Antenna list:** the ▸ triangle on DEEP SPACE NETWORK (key L) shows or hides it. Hidden by default on phones; the choice is remembered per device.
- **Phones:** in portrait the view buttons get their own row and the info card opens as a sheet above the controls; in landscape the top bar stays on one line and the antenna list scrolls.
- **Full screen:** F (not available in iPhone Safari, where the button is hidden).
- **URL options:** `?t=2026-11-14T12:00:00Z` starts at a fixed time; `&view=MDSCC` starts on a complex; `&rate=600` sets the speed.

The viewer reloads the data files every 5 minutes, so it picks up hourly backend runs without a refresh.

Display conventions: directions from Earth's centre are true; distance is logarithmic. The antennas of a complex are fanned out in a row so each is visible. Links leave the antenna vertically and bend toward the spacecraft. Spacecraft at the Moon, Mars and Jupiter are drawn at the body, whose label lists who is in contact; click the body to fan them out in a ring and list them in a card. During setup a blue dashed line extends from the antenna, reaching the spacecraft at BOT; during teardown a gray dotted line retracts to the antenna.

## GitHub Pages

`.github/workflows/pages.yml` builds the data every hour and publishes `site/` to GitHub Pages. One-time setup: repository **Settings → Pages → Source: GitHub Actions**. It can also be run by hand from the Actions tab.

- Trajectories are cached between runs, so Horizons is queried about once a day.
- If the schedule can't be fetched the run fails and the last published version stays up.
- GitHub treats schedules as best-effort: in practice runs start every few hours, not hourly, and schedules pause after 60 days without repository activity. The viewer shows the data's age and warns once it is over 12 hours old.

## Tests

```bash
pytest
```
