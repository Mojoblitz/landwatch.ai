import os

# ---- NASA FIRMS API settings ----
FIRMS_API_KEY = os.getenv("FIRMS_API_KEY", "ef237f447ad3d6bb05d187024f80c981")
DATASET = "VIIRS_NOAA20_NRT"   # or: "VIIRS_SNPP_NRT", "MODIS_C6_1"
DAYS = 7                       # FIRMS area endpoints allow 1..10

# Bounding box (west, south, east, north) — MB/SK example
BBOX = (-102.0, 49.0, -95.0, 55.0)

# ---- Local data directories ----
BASE_DIR = os.path.dirname(os.path.abspath(os.path.join(__file__, "..", "..")))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
MAP_DIR = os.path.join(BASE_DIR, "maps")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(MAP_DIR, exist_ok=True)
