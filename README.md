# dsnsim

A visualizer for the Deep Space Network: Earth, the three DSN complexes, and the links to scheduled tracks, driven by the public DSN schedule and spacecraft trajectories.

Status: backend pipeline in place; viewer not started. See [docs/plan.md](docs/plan.md) and [docs/feasibility.md](docs/feasibility.md).

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

## Tests

```bash
pytest
```
