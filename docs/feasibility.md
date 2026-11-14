# dsnsim — Feasibility Notes

Status: feasibility investigation, completed 2026-11-14. The project has since been built; see [plan.md](plan.md) and the README. A section at the end records what the first live runs showed.

## Concept

A dynamic view from space of Earth that shows the three DSN complexes and the spacecraft each one is communicating with, driven by the DSN schedule. Visualization only, so high accuracy is not needed. Time span: from now to a few weeks or months ahead. About 40 objects: HEO, lunar, and deep space.

## Schedule input

Public endpoint (example for Nov 1–5, 2026):

```
https://spsweb.fltops.jpl.nasa.gov/rest/ops/schedules/activity/json?startTime=2026-11-01T00:00:00&endTime=2026-11-05T00:00:00
```

Sample response: [`example-schedule-json.json`](example-schedule-json.json) (Nov 1–5, 2026; 343 records).

### Structure

Records are in `result.item[]`. Each record is one **service segment** of an activity:

- `pkgid` identifies the activity. One activity often has several records (e.g. a downlink segment and an uplink segment) with the same activity-level fields. Remove duplicates by `pkgid` for the link display.
- `segid` is unique per record.
- Fields without the `seg` prefix describe the whole activity; `seg*` fields describe the segment and can cover a shorter window.

All times are **UTC**, in day-of-year format: `YYYY-DDDThh:mm:ss` (e.g. `2026-305T01:00:00`).

### Fields used

| Field | Use |
|---|---|
| `projuser` | Mission abbreviation (see inventory below) |
| `facility` | DSS antenna number (integer) |
| `starttime` | Setup start |
| `bot` | BOT (beginning of track) |
| `eot` | EOT (end of track) |
| `endtime` | Teardown end |
| `wrkcat` | Work category (filter, see below) |
| `associations` | `<id>:<type>` grouping (see below) |
| `segbot`, `segeot`, `segequipmentlist` | Segment window and equipment; used to find the uplink |
| `segservicealias` | Service/link description (e.g. "34M/70M U/L v5", "D/L Only v2") |
| `activity` | Activity description (e.g. "TKG PASS", "SSR DUMP/UNATT") |

Other fields (`week`, `year`, `version`, `nib`, `configcode`, `soecode`, `equipmentlist`, `segactivity`, etc.) are not needed for now.

### Filters

Show a record as a spacecraft link only if all of these hold:

1. `wrkcat` is `1A1` (committed tracking pass) or `1A2`. Other categories (tests, maintenance, etc.) are omitted.
2. `facility` is one of the DSN antennas below.
3. `projuser` is a spacecraft (not DSN, DSS, TEST, GBRA, HCRA).

In the Nov 1–5 sample, facilities removed by the antenna filter were DSS-13 (GAVRT, debris detection, LRO Mini-RF), 10, 20, 28, 40, 60 (network/complex maintenance) and 38 (a JAXA SOHO pass).

### Associations

`associations` has the form `<id>:<type>`. Records with the same id belong together.

| Type | Meaning | Example in sample |
|---|---|---|
| SSPA | Single spacecraft per aperture | Most records (292) |
| MSPA | Multiple spacecraft per aperture | DSS-53: M01O, MSL, MRO, M20, EMM, TGO under one id |
| ARRAY | One spacecraft on several antennas | VGR1 on DSS-24, 25, 26 |
| DDOR | Two complexes track one spacecraft at once | PSYC on DSS-24 and DSS-65 |

### Uplink in MSPA passes

In an MSPA, the segment whose `segequipmentlist` contains `UPL` is the uplink; its `segbot`–`segeot` is the uplink window. Usually only one spacecraft has the uplink at a time; the others are downlink only. Use the **segment** equipment list, not the activity-level `equipmentlist` (e.g. the MRO activity on DSS-53 has no `UPL` at activity level, but its U/L segment does).

Sample (DSS-53, association 11777924, DOY 306), uplinks in sequence:

| Spacecraft | Uplink (segment) |
|---|---|
| M01O | 01:00–03:20 |
| MSL | 03:50–06:00 |
| M20 | 07:40–09:40 |
| MRO | 10:10–13:00 |

EMM and TGO are downlink only in that pass.

### DSN antennas

Facility to complex mapping. Show only these DSN antennas; activities on any other `facility` value (control center, non-DSN antennas) are excluded.

| Complex | 70m | 34m |
|---|---|---|
| Goldstone, CA | DSS-14 | DSS-23, 24, 25, 26 |
| Canberra, Australia | DSS-43 | DSS-34, 35, 36 |
| Madrid, Spain | DSS-63 | DSS-53, 54, 55, 56, 65 |

### Display states

For each link: setup (`starttime`–`bot`) → tracking (`bot`–`eot`) → teardown (`eot`–`endtime`). During tracking, show uplink vs downlink-only using the UPL segment window. MSPA, ARRAY and DDOR groups can be drawn as one antenna to many spacecraft, or many antennas to one spacecraft.

To list the users for a period: `jq '[.result.item[].projuser] | unique'`.

## Mission inventory and ephemeris sources

Users in the Nov 1–5, 2026 schedule (44 distinct, confirmed from the full sample file).

### Not spacecraft (exclude)

| projuser | Meaning |
|---|---|
| DSN, DSS | Ground activities |
| TEST | Test |
| GBRA | Ground-based radio astronomy |
| HCRA | Host country radio astronomy (DSN foreign sites) |

### TLE / SGP4 (HEO)

| projuser | Mission | Notes |
|---|---|---|
| CHDR | Chandra X-ray Observatory | TLE OK for visualization |
| MMS1–MMS4 | Magnetospheric Multiscale | TLE OK; SSCWeb also has them |

TESS has TLEs, but its lunar-resonant orbit makes SGP4 drift. Use Horizons.

### Horizons — Earth / Sun–Earth L1/L2 region

| projuser | Mission | Horizons check |
|---|---|---|
| ACE | Advanced Composition Explorer | — |
| SOHO | SOHO | — |
| WIND | Wind | — |
| SWFO | SWFO-L1 | OK |
| CGO | Carruthers Geocorona Observatory | OK |
| IMAP | Interstellar Mapping and Acceleration Probe | **Not found.** Use Horizons Sun–Earth L1 point as a stand-in, or try SSCWeb |
| JWST | James Webb Space Telescope | — |
| RST | Nancy Grace Roman Space Telescope | OK. Launched 2026-08-30; transfer to L2 (~3 months) |
| TESS | TESS | — |

### Lunar

| projuser | Mission | Source / notes |
|---|---|---|
| LRO | Lunar Reconnaissance Orbiter | Horizons |
| KPLO | Korea Pathfinder Lunar Orbiter (Danuri) | Horizons |
| CAPS | CAPSTONE (NRHO) | **Not found in Horizons.** Pin to Moon or draw a generic 9:2 NRHO path |
| THB, THC | THEMIS-B/C (ARTEMIS P1/P2) | Probably not in Horizons; use NASA SSCWeb. SGP4 not valid in lunar orbit |

### Mars

| projuser | Mission | Notes |
|---|---|---|
| M01O | Mars Odyssey | Horizons |
| MRO | Mars Reconnaissance Orbiter | Horizons |
| MEX | Mars Express | Horizons |
| TGO | ExoMars Trace Gas Orbiter | Horizons |
| EMM | Emirates Mars Mission (Hope) | Horizons |
| MSL | Curiosity (surface) | Mars center or landing site is enough |
| M20 | Perseverance (surface) | Mars center or landing site is enough |

### Interplanetary / heliocentric

| projuser | Mission | Horizons check |
|---|---|---|
| ESCB, ESCG | ESCAPADE Blue / Gold | OK |
| BIOS | BioSentinel | OK |
| STA | STEREO-A | — |
| SPP | Parker Solar Probe | — |
| PSYC | Psyche | — |
| LUCY | Lucy | — |
| ORX | OSIRIS-APEX | — |
| JNO | Juno | — |
| EURC | Europa Clipper | — |
| NHPC | New Horizons | — |
| VGR1, VGR2 | Voyager 1 / 2 | — |

"—" = expected to be in Horizons, not yet checked. When checking, confirm predict coverage extends over the full display window (predicts often end shortly after the latest nav delivery).

### Checking Horizons

- Web app: https://ssd.jpl.nasa.gov/horizons/app.html → Target Body search → Vector Table over the window. An out-of-coverage span returns an error naming the coverage limits.
- API lookup: `https://ssd.jpl.nasa.gov/api/horizons_lookup.api?sstr=<name>`
- Major-body list: `https://ssd.jpl.nasa.gov/api/horizons.api?format=text&COMMAND='MB'`

## Propagation approach

- **Earth orbiters:** TLE/OMM from CelesTrak or Space-Track, propagated with SGP4 (`sgp4` or Skyfield). Accuracy ~1 km at epoch, growing ~1–3 km/day. Refresh TLEs for longer spans.
- **Everything else:** Horizons vectors (API or `astroquery.jplhorizons`), or SPICE SPKs via `spiceypy`. Skyfield's SPK reader only handles segment types 2/3; spacecraft kernels are often 13/21.
- **Frames/time:** SGP4 outputs TEME; convert to GCRS/J2000 before combining with Horizons/SPICE positions. Use one time scale throughout.
- **Fetching:** cache Horizons results locally (daily or hourly steps, interpolated) rather than querying at render time.

## Display concept

### Log radial distance scale

Keep each object's true geocentric direction; compress only distance:

```
r' = R_E_display + k * log10(r / R_E)
```

The offset keeps Earth at a fixed visible size with the three complexes on it.

| Range | Distance (km) | Objects |
|---|---|---|
| HEO | 1e4–1e5 | MMS, CHDR, TESS |
| Moon | ~4e5 | LRO, KPLO, THB/THC, CAPS |
| L1/L2 | ~1.5e6 | ACE, SOHO, WIND, IMAP, SWFO, CGO, JWST, RST |
| Inner solar system | 1e7–1e8 | ESCB/ESCG, BIOS, STA, SPP, Mars group, PSYC, LUCY, ORX |
| Jupiter | ~8e8 | JNO, EURC |
| Kuiper Belt / interstellar | 1e9–1e10 | NHPC, VGR1, VGR2 |

Roughly 6–7 decades, spread fairly evenly.

### Gotchas

- **Clustering around planets:** orbiters collapse onto their primary (all Mars assets at one point; lunar orbiters inside the Moon's marker). Use grouped labels with fan-out, or local magnified views around the Moon and Mars.
- **Shapes distort:** circular orbits around Earth stay circular; straight trajectories bend; orbits around the Moon or Mars get warped. Acceptable for a link display.
- **Link lines:** a line from a complex to a scaled position is not the true pointing direction for nearby (HEO, lunar) objects. Calculate visibility (elevation above horizon) in true coordinates; use scaled coordinates only for drawing.
- **Readability:** labeled distance rings (GEO, Moon, L1/L2, 1 AU, Jupiter, 100 AU).
- **Hybrid option:** linear scale out to ~2e6 km, log beyond. Keeps cislunar geometry intuitive.

### Frame

Earth-centered inertial (GCRS): Earth rotates under a mostly fixed set of spacecraft directions, so each complex visibly rotates into view of its spacecraft as the schedule plays.

## Open questions

- Horizons predict coverage end dates for each mission over the display window.
- Source for IMAP (SSCWeb?) and whether a better CAPSTONE source exists.
- Whether THB/THC are available from SSCWeb for future dates (predicted orbits).
- Implementation platform: Python backend (Skyfield/spiceypy) feeding a browser 3D view, or fully browser-based.
- Should the tool read the schedule each time to pick its objects, or use a fixed list?

## Results from the first live runs (2026-11-14)

- **Pipeline validated:** over a 9-day window, 713 tracks; every mission's mid-track elevation is above the horizon (minimums mostly 10–30°). This confirms frames, timing and Earth rotation, including for the stand-ins.
- **Horizons IDs confirmed:** all numeric IDs in `dsnsim/config.py` resolve, including THB/THC (−192/−193). Name searches work for `SWFO-L1`, `Carruthers`, `Roman`, `BioSentinel`, `MMX`, `ESCAPADE-Blue` and `ESCAPADE-Gold` (hyphenated; with a space Horizons falls through to a small-body search and fails).
- **Additional users** outside the Nov 1–5 sample: BEPI (BepiColombo), DSCO (DSCOVR), XMM (XMM-Newton, TLE), MMX, and B101 (Blue Origin HLS test flight, no trajectory yet).
- **Below-horizon tracks:** the only two were ECC (Emergency Control Center) data connectivity tests booked under THB and LUCY, which do not involve the spacecraft. General rule adopted: a track whose spacecraft is below the horizon at mid-track is shown as busy.
- **Antenna count:** 15 DSN antennas (5 Goldstone, 4 Canberra, 6 Madrid).
- **Work categories:** 1A1 and 1A2 are links; any other scheduled activity on an antenna is busy.
