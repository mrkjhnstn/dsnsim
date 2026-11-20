# dsnsim — Plan

Decisions as of 2026-11-14. **Status: phases 1–5 built**; remaining work is listed at the end. Background and data findings are in [feasibility.md](feasibility.md).

## Goal

A web visualizer showing Earth, the three DSN complexes, and the links to scheduled tracks, driven by the DSN schedule and spacecraft trajectories. Credible to a technical viewer; high accuracy is not required. Equally an unattended wall display and a tool one person explores.

## Decisions

| Topic | Decision |
|---|---|
| Hosting | Own machine (`python3 -m dsnsim.serve`, port 8002) and GitHub Actions + Pages (hourly, public). Static JSON + static viewer, one build command, no secrets. |
| Look | Photoreal Earth (Blue Marble, no political boundaries, night lights, atmosphere) with schematic-style labels and overlays. |
| Distance scale | Fully logarithmic radial scale, true geocentric directions. |
| Time range | About 1 day back to 7 days forward, with snap-to-now. |
| Stand-ins | IMAP → Sun–Earth L1 point. CAPS → Moon. THB/THC → Horizons if available, else Moon. Mars rovers → Mars. |
| Antennas shown | The 15 DSN antennas only (see feasibility.md). Complex-level facilities (10, 20, 40, 60) and non-DSN antennas are ignored. |

### Antenna states

| State | Rule | Display |
|---|---|---|
| Tracking | Spacecraft user, `wrkcat` 1A1 or 1A2 | Link drawn to the spacecraft |
| Busy | Any other scheduled activity on the antenna (DSN/DSS maintenance, tests, radio astronomy, other work categories). Also a track whose spacecraft is below the horizon at mid-track (e.g. ECC connectivity tests booked under a mission), or whose mission has no trajectory (shown in use, no link). | Distinct antenna marker, activity name on its card, no link |
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

## Display conventions (as built)

- **Scale:** true directions from Earth's centre; logarithmic distance, with labeled rings (GEO, Moon, L1/L2, 1 AU, 10 AU, 100 AU) in the ecliptic plane.
- **Antennas:** the antennas of a complex are fanned out in an east–west row (about 2.4° apart, 70 m first) so each is visible.
- **Links:** leave the antenna vertically and bend toward the spacecraft, so they never cut through the Earth's limb at log scale. Cyan while tracking, with cyan pulses down and orange pulses up during uplink windows; thicker for 70 m.
- **Setup / teardown:** setup is a blue dashed line that extends from the antenna and reaches the spacecraft at BOT; teardown is a gray dotted line that retracts to the antenna.
- **Planets:** spacecraft at the Moon, Mars and Jupiter are drawn at the body; its label lists who is in contact. Clicking the body fans them out in a ring and opens a card listing them. MSPA links to a collapsed body merge into one beam.
- **Cards:** hover or click a spacecraft, antenna or planet. Pinned cards add pass marks on the timeline and PREV / NEXT PASS.
- **Complex views:** camera follows the Earth's rotation; other complexes' links are dimmed.
- **Auto-tour:** ALL view with slow rotation, showing a card for each spacecraft in setup, tracking or teardown (5 s each, inside out, expanding body groups as needed); then each complex: fly in, hold the close-up 3 s, then pull straight back (10 s) to the ALL distance, rotating slowly as in the ALL view while the camera keeps following the Earth's rotation, showing each antenna's card (6 s each).
- **Default view:** from about 60° north, so the distance rings read as rings.

## Phases

1. **Backend pipeline** and JSON format; verify Horizons coverage for all missions.
2. **Viewer core:** globe, complexes, time engine, links as direction rays.
3. **Spacecraft at log distance:** labels, distance rings, clustering around Moon and Mars.
4. **Camera views, cards, full-screen polish, auto-tour.**
5. **Automation:** hourly job locally; optional GitHub Actions + Pages.

## Remaining

- Tune the auto-tour (dwell times, camera angles, text sizes) on the wall display.
- Confirm the hourly GitHub Actions run can reach the schedule endpoint, Horizons and CelesTrak.
- B101 (Blue Origin HLS test flight) has no trajectory yet; add a source when one exists.
- Antenna coordinates are approximate; DSS-23, 53 and 56 are estimates.
