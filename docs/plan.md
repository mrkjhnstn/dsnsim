# dsnsim — Plan

Decisions as of 2026-11-14. Background and data findings are in [feasibility.md](feasibility.md).

## Goal

A web visualizer showing Earth, the three DSN complexes, and the links to scheduled tracks, driven by the DSN schedule and spacecraft trajectories. Credible to a technical viewer; high accuracy is not required. Equally an unattended wall display and a tool one person explores.

## Decisions

| Topic | Decision |
|---|---|
| Hosting | Own machine for now. Keep it portable to GitHub Actions + Pages (static JSON + static viewer, one build command, no secrets). |
| Look | Photoreal Earth (Blue Marble, no political boundaries, night lights, atmosphere) with schematic-style labels and overlays. |
| Distance scale | Fully logarithmic radial scale, true geocentric directions. |
| Time range | About 1 day back to 7 days forward, with snap-to-now. |
| Stand-ins | IMAP → Sun–Earth L1 point. CAPS → Moon. THB/THC → Horizons if available, else Moon. Mars rovers → Mars. |
| Antennas shown | The 15 DSN antennas only (see feasibility.md). Complex-level facilities (10, 20, 40, 60) and non-DSN antennas are ignored. |

### Antenna states

| State | Rule | Display |
|---|---|---|
| Tracking | Spacecraft user, `wrkcat` 1A1 or 1A2 | Link drawn to the spacecraft |
| Busy | Any other scheduled activity on the antenna (DSN/DSS maintenance, tests, radio astronomy, other work categories) | Distinct antenna marker, activity name on its card, no link |
| Idle | Nothing scheduled | Plain marker |

## Architecture

### Backend (Python, run hourly)

One command writes static JSON to an output folder:

```
python -m dsnsim.build --out site/data
```

- **Schedule:** fetch now −2 d to now +9 d, classify each activity as track or busy, de-duplicate by `pkgid`, extract uplink windows (`UPL` in `segequipmentlist`), keep association id/type (SSPA, MSPA, ARRAY, DDOR).
- **Trajectories:** geocentric J2000 (ICRF equatorial) positions in km on a fixed time grid.
  - Horizons vectors API for most missions (hourly steps near Earth, 6 h steps for deep space).
  - TLE (CelesTrak) + SGP4 via Skyfield for CHDR and MMS1–4.
  - Sun, Moon, Mars, Jupiter and Sun–Earth L1 for context, lighting and stand-ins.
- **Caching:** trajectories are reused for 24 h; the schedule is refreshed on every run.
- **Sanity check:** elevation of the spacecraft at the antenna at mid-track; tracks below the horizon are listed in `meta.json`.
- **Failure handling:** a mission whose trajectory can't be fetched is reported in `meta.json` and does not stop the build.

Outputs: `schedule.json`, `ephem.json`, `meta.json`.

### Viewer (static web app, three.js)

- Earth rotation and day/night terminator computed from time.
- Time engine interpolates positions; playback forward and backward.
- **Timeline bar:** scrub, play/pause/reverse, speed steps, NOW button.
- **Complex buttons:** Goldstone, Canberra, Madrid, All. Camera flies to the complex; other links dim.
- **Links:** setup dashed, tracking solid, teardown fading; uplink/downlink pulses; thicker beams for 70 m; arrays converge, MSPA fans out.
- **Cards:** hover or click a spacecraft or antenna for mission, antenna, BOT/EOT, range, light time.
- **Auto-tour:** cycles through complexes for unattended display.
- Full-screen landscape layout.

## Phases

1. **Backend pipeline** and JSON format; verify Horizons coverage for all missions.
2. **Viewer core:** globe, complexes, time engine, links as direction rays.
3. **Spacecraft at log distance:** labels, distance rings, clustering around Moon and Mars.
4. **Camera views, cards, full-screen polish, auto-tour.**
5. **Automation:** hourly job locally; optional GitHub Actions + Pages.
