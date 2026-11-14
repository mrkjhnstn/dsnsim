# dsnsim — Feasibility Notes

Status: feasibility investigation, nothing built yet. Last updated 2026-11-14.

## Concept

A dynamic view from space of Earth that shows the three DSN complexes and the spacecraft each one is communicating with, driven by the DSN schedule. Visualization only, so high accuracy is not needed. Time span: from now to a few weeks or months ahead. About 40 objects: HEO, lunar, and deep space.

## Schedule input

Public endpoint (example for Nov 1–5, 2026):

```
https://spsweb.fltops.jpl.nasa.gov/rest/ops/schedules/activity/json?startTime=2026-11-01T00:00:00&endTime=2026-11-05T00:00:00
```

| Field | Use |
|---|---|
| `projuser` | Mission abbreviation (see table below) |
| `facility` | DSS antenna number (e.g. 14, 23, 55, 65) |
| Activity times | Setup start, BOT (beginning of track), EOT (end of track), teardown end. Exact field names still to confirm. |
| `segservicealias` | Service/link description (e.g. "XR TTC v3", "DDOR GLD/MAD v3") |

Facility to complex mapping (from the DSS number):

| DSS | Complex |
|---|---|
| 1x, 2x | Goldstone |
| 3x, 4x | Canberra |
| 5x, 6x | Madrid |

Display states for each link: setup → tracking (BOT to EOT) → teardown.

To confirm the full user list for a period: `jq '[.[].projuser] | unique'`.

## Mission inventory and ephemeris sources

Users seen in the Nov 1–5, 2026 schedule.

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

- Exact schedule field names for setup / BOT / EOT / teardown times.
- Horizons predict coverage end dates for each mission over the display window.
- Source for IMAP (SSCWeb?) and whether a better CAPSTONE source exists.
- Whether THB/THC are available from SSCWeb for future dates (predicted orbits).
- Implementation platform: Python backend (Skyfield/spiceypy) feeding a browser 3D view, or fully browser-based.
- Should the tool read the schedule each time to pick its objects, or use a fixed list?
