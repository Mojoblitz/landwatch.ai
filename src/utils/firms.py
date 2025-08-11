import os, json, requests, pandas as pd
from datetime import datetime, timedelta
from .config import FIRMS_API_KEY, DATASET, DAYS, BBOX, RAW_DIR

# ---- URL builders (correct order per FIRMS docs) ----
def _url_area_wsen():
    # /api/area/csv/[MAP_KEY]/[SOURCE]/[AREA_COORDINATES]/[DAY_RANGE]
    w, s, e, n = BBOX  # [min_lon, min_lat, max_lon, max_lat]
    day = max(1, min(int(DAYS), 10))
    return f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_API_KEY}/{DATASET}/{w},{s},{e},{n}/{day}"

def _url_area_swne():
    # alt ordering (south,west,north,east)
    w, s, e, n = BBOX
    day = max(1, min(int(DAYS), 10))
    return f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_API_KEY}/{DATASET}/{s},{w},{n},{e}/{day}"

def _url_country_can():
    # /api/country/csv/[MAP_KEY]/[SOURCE]/[COUNTRY_CODE]/[DAY_RANGE]
    day = max(1, min(int(DAYS), 10))
    return f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{FIRMS_API_KEY}/{DATASET}/CAN/{day}"

def _try_fetch(url):
    print(f"[FIRMS] GET {url}")
    r = requests.get(url, timeout=120)
    head = r.text[:160].lower()
    return r, head

# ---- Download CSV with fallbacks ----
def fetch_firms_csv():
    os.makedirs(RAW_DIR, exist_ok=True)
    start_date = (datetime.utcnow() - timedelta(days=max(1, min(int(DAYS), 10)))).strftime("%Y-%m-%d")
    out_path = os.path.join(RAW_DIR, f"firms_{DATASET}_{start_date}.csv")

    # 1) area (WSEN)
    r, head = _try_fetch(_url_area_wsen())
    if r.status_code == 200 and "invalid" not in head and "error" not in head:
        with open(out_path, "wb") as f: f.write(r.content)
        return out_path

    print("…area (WSEN) failed. Trying area (SWNE)…")

    # 2) area (SWNE)
    r2, head2 = _try_fetch(_url_area_swne())
    if r2.status_code == 200 and "invalid" not in head2 and "error" not in head2:
        with open(out_path, "wb") as f: f.write(r2.content)
        return out_path

    print("…area failed both orders. Falling back to country=CAN and clipping locally…")

    # 3) country=CAN
    r3, head3 = _try_fetch(_url_country_can())
    if r3.status_code == 200 and "invalid" not in head3 and "error" not in head3:
        with open(out_path, "wb") as f: f.write(r3.content)
        return out_path

    raise RuntimeError(
        "FIRMS requests failed.\n"
        f"Area WSEN head: {head.strip()}\n"
        f"Area SWNE head: {head2.strip()}\n"
        f"Country CAN head: {head3.strip()}\n"
        "Check API key, DATASET (try MODIS_C6_1 or VIIRS_SNPP_NRT), and keep DAYS within 1..10."
    )

# ---- Load CSV, normalize, and clip to bbox ----
def load_firms_df(csv_path):
    df = pd.read_csv(csv_path, sep=None, engine="python")
    df.columns = [c.strip().lower() for c in df.columns]

    lat_candidates = ["latitude", "lat", "y", "latitud"]
    lon_candidates = ["longitude", "lon", "x", "longitud", "long"]

    lat = next((c for c in lat_candidates if c in df.columns), None)
    lon = next((c for c in lon_candidates if c in df.columns), None)

    if lat is None or lon is None:
        print("Columns in CSV:", list(df.columns))
        raise ValueError("No latitude/longitude columns found in FIRMS CSV")

    df = df.dropna(subset=[lat, lon]).copy()
    df.rename(columns={lat: "lat", lon: "lon"}, inplace=True)

    # clip to bbox (useful if we fetched by country)
    w, s, e, n = BBOX
    df = df[(df["lon"] >= w) & (df["lon"] <= e) & (df["lat"] >= s) & (df["lat"] <= n)].copy()
    return df

# ---- Save GeoJSON ----
def save_geojson_points(df, out_path, popup_cols=None):
    popup_cols = popup_cols or [c for c in ["acq_date","acq_time","satellite","frp","brightness","confidence"] if c in df.columns]
    feats = []
    for _, r in df.iterrows():
        props = {c: r[c] for c in popup_cols if c in df.columns}
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(r["lon"]), float(r["lat"])]},
            "properties": props
        })
    fc = {"type":"FeatureCollection","features":feats}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fc, f)
    return out_path