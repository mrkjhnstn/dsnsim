"""Static configuration: antennas, context bodies and missions.

Mission trajectory sources
--------------------------
Each mission has one of:
  horizons: value passed to Horizons as COMMAND (a spacecraft ID such as "-31",
            or a name Horizons can match uniquely)
  tle:      NORAD catalog number, propagated with SGP4
  alias:    key of a context body used as a stand-in (e.g. "moon")
  (none):   no trajectory available; the antenna is shown in use, with no link
and optionally:
  fallback: context body to use if the primary source fails
  step:     "near" (hourly samples) or "deep" (6-hourly samples)

Run `python -m dsnsim.build --check` to see which sources resolve.
"""

# --- Antennas ---------------------------------------------------------------
# Geodetic coordinates are approximate (good to roughly a kilometre), which is
# ample for a globe-scale display. lon is degrees east.
COMPLEXES = {
    "GDSCC": {"name": "Goldstone, CA", "lat": 35.34, "lon": -116.87},
    "CDSCC": {"name": "Canberra, Australia", "lat": -35.40, "lon": 148.98},
    "MDSCC": {"name": "Madrid, Spain", "lat": 40.43, "lon": -4.25},
}

ANTENNAS = {
    14: {"complex": "GDSCC", "size_m": 70, "lat": 35.4259, "lon": -116.8895, "alt_m": 1000},
    23: {"complex": "GDSCC", "size_m": 34, "lat": 35.3395, "lon": -116.8730, "alt_m": 960},
    24: {"complex": "GDSCC", "size_m": 34, "lat": 35.3399, "lon": -116.8748, "alt_m": 950},
    25: {"complex": "GDSCC", "size_m": 34, "lat": 35.3376, "lon": -116.8754, "alt_m": 960},
    26: {"complex": "GDSCC", "size_m": 34, "lat": 35.3357, "lon": -116.8730, "alt_m": 970},
    43: {"complex": "CDSCC", "size_m": 70, "lat": -35.4024, "lon": 148.9813, "alt_m": 690},
    34: {"complex": "CDSCC", "size_m": 34, "lat": -35.3985, "lon": 148.9820, "alt_m": 690},
    35: {"complex": "CDSCC", "size_m": 34, "lat": -35.3958, "lon": 148.9814, "alt_m": 695},
    36: {"complex": "CDSCC", "size_m": 34, "lat": -35.3951, "lon": 148.9785, "alt_m": 685},
    63: {"complex": "MDSCC", "size_m": 70, "lat": 40.4314, "lon": -4.2480, "alt_m": 865},
    53: {"complex": "MDSCC", "size_m": 34, "lat": 40.4274, "lon": -4.2496, "alt_m": 840},
    54: {"complex": "MDSCC", "size_m": 34, "lat": 40.4256, "lon": -4.2541, "alt_m": 837},
    55: {"complex": "MDSCC", "size_m": 34, "lat": 40.4243, "lon": -4.2526, "alt_m": 819},
    56: {"complex": "MDSCC", "size_m": 34, "lat": 40.4260, "lon": -4.2520, "alt_m": 836},
    65: {"complex": "MDSCC", "size_m": 34, "lat": 40.4272, "lon": -4.2507, "alt_m": 834},
}

# --- Schedule classification -------------------------------------------------
GROUND_USERS = {"DSN", "DSS", "TEST", "GBRA", "HCRA"}
TRACK_WRKCATS = {"1A1", "1A2"}

# --- Context bodies (Horizons IDs) -------------------------------------------
BODIES = {
    "sun": {"name": "Sun", "horizons": "10", "step": "deep"},
    "moon": {"name": "Moon", "horizons": "301", "step": "near"},
    "mars": {"name": "Mars", "horizons": "499", "step": "deep"},
    "jupiter": {"name": "Jupiter", "horizons": "599", "step": "deep"},
    "sel1": {"name": "Sun-Earth L1", "horizons": "31", "step": "deep"},
}

# --- Missions ----------------------------------------------------------------
# region: heo | l1l2 | lunar | mars | helio | outer  (used by the viewer for grouping)
MISSIONS = {
    # HEO (TLE)
    "CHDR": {"name": "Chandra", "region": "heo", "tle": 25867, "step": "near"},
    "MMS1": {"name": "MMS 1", "region": "heo", "tle": 40482, "step": "near"},
    "MMS2": {"name": "MMS 2", "region": "heo", "tle": 40483, "step": "near"},
    "MMS3": {"name": "MMS 3", "region": "heo", "tle": 40484, "step": "near"},
    "MMS4": {"name": "MMS 4", "region": "heo", "tle": 40485, "step": "near"},
    "TESS": {"name": "TESS", "region": "heo", "horizons": "-95", "step": "near"},
    "XMM": {"name": "XMM-Newton", "region": "heo", "tle": 25989, "step": "near"},
    # Sun-Earth L1/L2 region
    "ACE": {"name": "ACE", "region": "l1l2", "horizons": "-92", "step": "near"},
    "SOHO": {"name": "SOHO", "region": "l1l2", "horizons": "-21", "step": "near"},
    "WIND": {"name": "Wind", "region": "l1l2", "horizons": "-8", "step": "near"},
    "SWFO": {"name": "SWFO-L1", "region": "l1l2", "horizons": "SWFO-L1", "fallback": "sel1", "step": "near"},
    "CGO": {"name": "Carruthers Geocorona Observatory", "region": "l1l2", "horizons": "Carruthers", "fallback": "sel1", "step": "near"},
    "DSCO": {"name": "DSCOVR", "region": "l1l2", "horizons": "-78", "fallback": "sel1", "step": "near"},
    "IMAP": {"name": "IMAP", "region": "l1l2", "alias": "sel1"},
    "JWST": {"name": "James Webb Space Telescope", "region": "l1l2", "horizons": "-170", "step": "near"},
    "RST": {"name": "Roman Space Telescope", "region": "l1l2", "horizons": "Roman", "step": "near"},
    # Lunar
    "LRO": {"name": "Lunar Reconnaissance Orbiter", "region": "lunar", "horizons": "-85", "fallback": "moon", "step": "near"},
    "KPLO": {"name": "KPLO (Danuri)", "region": "lunar", "horizons": "-155", "fallback": "moon", "step": "near"},
    "CAPS": {"name": "CAPSTONE", "region": "lunar", "alias": "moon"},
    "THB": {"name": "THEMIS-B (ARTEMIS P1)", "region": "lunar", "horizons": "-192", "fallback": "moon", "step": "near"},
    "THC": {"name": "THEMIS-C (ARTEMIS P2)", "region": "lunar", "horizons": "-193", "fallback": "moon", "step": "near"},
    "B101": {"name": "Blue Origin HLS test flight", "region": "lunar"},
    # Mars
    "M01O": {"name": "Mars Odyssey", "region": "mars", "horizons": "-53", "fallback": "mars", "step": "deep"},
    "MRO": {"name": "Mars Reconnaissance Orbiter", "region": "mars", "horizons": "-74", "fallback": "mars", "step": "deep"},
    "MEX": {"name": "Mars Express", "region": "mars", "horizons": "-41", "fallback": "mars", "step": "deep"},
    "TGO": {"name": "ExoMars Trace Gas Orbiter", "region": "mars", "horizons": "-143", "fallback": "mars", "step": "deep"},
    "EMM": {"name": "Emirates Mars Mission (Hope)", "region": "mars", "horizons": "-62", "fallback": "mars", "step": "deep"},
    "MSL": {"name": "Curiosity", "region": "mars", "alias": "mars"},
    "M20": {"name": "Perseverance", "region": "mars", "alias": "mars"},
    # Heliocentric / inner solar system
    "ESCB": {"name": "ESCAPADE Blue", "region": "helio", "horizons": "ESCAPADE-Blue", "step": "deep"},
    "ESCG": {"name": "ESCAPADE Gold", "region": "helio", "horizons": "ESCAPADE-Gold", "step": "deep"},
    "BIOS": {"name": "BioSentinel", "region": "helio", "horizons": "BioSentinel", "step": "deep"},
    "BEPI": {"name": "BepiColombo", "region": "helio", "horizons": "-121", "step": "deep"},
    "MMX": {"name": "Martian Moons eXploration", "region": "helio", "horizons": "MMX", "step": "deep"},
    "STA": {"name": "STEREO-A", "region": "helio", "horizons": "-234", "step": "deep"},
    "SPP": {"name": "Parker Solar Probe", "region": "helio", "horizons": "-96", "step": "deep"},
    "PSYC": {"name": "Psyche", "region": "helio", "horizons": "-255", "step": "deep"},
    "LUCY": {"name": "Lucy", "region": "helio", "horizons": "-49", "step": "deep"},
    "ORX": {"name": "OSIRIS-APEX", "region": "helio", "horizons": "-64", "step": "deep"},
    # Outer solar system
    "JNO": {"name": "Juno", "region": "outer", "horizons": "-61", "fallback": "jupiter", "step": "deep"},
    "EURC": {"name": "Europa Clipper", "region": "outer", "horizons": "-159", "step": "deep"},
    "NHPC": {"name": "New Horizons", "region": "outer", "horizons": "-98", "step": "deep"},
    "VGR1": {"name": "Voyager 1", "region": "outer", "horizons": "-31", "step": "deep"},
    "VGR2": {"name": "Voyager 2", "region": "outer", "horizons": "-32", "step": "deep"},
}

STEP_SECONDS = {"near": 3600, "deep": 6 * 3600}

SCHEDULE_URL = "https://spsweb.fltops.jpl.nasa.gov/rest/ops/schedules/activity/json"
HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php"
