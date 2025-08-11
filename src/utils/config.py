import os

# ---- NASA FIRMS API settings ----
# Prefer env var; fallback to literal for now
FIRMS_API_KEY = os.getenv("FIRMS_API_KEY", "ef237f447ad3d6bb05d187024f80c981")

# Dataset options: "VIIRS_NOAA20_NRT", "VIIRS_SNPP_NRT", "MODIS_C6_1"
DATASET = "VIIRS_NOAA20_NRT"

# FIRMS allows 1..10 for these endpoints
DAYS = 7

# Bounding box (west, south, east, north)
# Covers Manitoba/Saskatchewan example
BBOX = (-102.0, 49.0, -95.0, 55.0)

# ---- Local data directories ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
MAP_DIR = os.path.join(BASE_DIR, "maps")

# Ensure directories exist
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(MAP_DIR, exist_ok=True)