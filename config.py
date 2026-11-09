from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "exoplanets.db"
PLOTS_DIR = BASE_DIR / "plots"
RAW_SNAPSHOT_PATH = BASE_DIR / "data" / "raw" / "pscomppars.json"
TABLE_NAME = "exoplanets"

NASA_TAP_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
# One row per planet. The "ps" table has several rows per planet.
NASA_SOURCE_TABLE = "pscomppars"

ID_COLUMN = "pl_name"
HOST_COLUMN = "hostname"
METHOD_COLUMN = "discoverymethod"
YEAR_COLUMN = "disc_year"
RADIUS_COLUMN = "pl_rade"
TARGET_COLUMN = "is_terrestrial"
FEATURE_COLUMNS = [
    "pl_bmasse",
    "pl_orbper",
    "pl_orbsmax",
    "pl_insol",
    "pl_eqt",
    "st_teff",
    "st_rad",
    "st_mass",
    "st_met",
]

# Machine learning uses transit planets only. Other methods mostly find giant
# planets, and their radii are probably derived from mass rather than measured.
TRAINING_METHOD = "Transit"

# Planets smaller than this radius (in Earth radii) are labelled terrestrial.
RADIUS_THRESHOLD = 2.0

# NASA estimates many missing masses from the planet radius. Those values
# would leak the target into the features, so they are discarded.
MASS_PROVENANCE_COLUMN = "pl_bmassprov"
ESTIMATED_MASS_KEYWORD = "relationship"

RANDOM_STATE = 42
TEST_SIZE = 0.2
