import os, json, requests, pandas as pd
from datetime import datetime, timedelta
from .config import FIRMS_API_KEY, DATASET, DAYS, BBOX, RAW_DIR

def _url_area_wsen():
    w, s, e, n = BBOX
    day = max(1, min(int(DAYS), 10))
    return f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_API_KEY}/{DATASET}/{w},{s},{e},{n}/{day}"

def _url_area_swne():
    w, s, e, n = BBOX
    day = max(1, min(int(DAYS), 10))
    return f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_API_KEY}/{DATASET}/{s},{w},{n},{e}/{day}"

def _url_country_can():
    day = max(1, min(int(DAYS), 10))
    return f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{FIRMS_API_KEY}/{DATASET}/CAN/{day}"

def _try_fetch(url):
    print(f"[FIRMS] GET {url}")
    r = requests.get(url, timeout=120)
    return r, r.text[:160].lower()

def fetch_firms_csv():
    os.makedirs(RAW_DIR, exist_ok=True)
    start_date = (datetime.utcnow() - timedelta(days=max(1, min(int(DAYS), 10)))).strftime("%Y-%m-%d")
    out_path = os.path.join(RAW_DIR, f"firms_{DATASET}_{start_date}.csv")

    r, head = _try_fetch(_url_area_wsen())
    if r.status_code == 200 and "invalid" not in head and "error" not in head:
        open(out_path, "wb").write(r.content); return out_path

    print("…area (WSEN) failed. Trying area (SWNE)…")
    r2, head2 = _try_fetch(_url_area_swne())
    if r2.status_code == 200 and "invalid" not in head2 and "error" not in head2:
        open(out_path, "wb").write(r2.content); return out_path

    print("…area failed both orders. Falling back to country=CAN and clipping locally…")
    r3, head3 = _try_fetch(_url_country_can())
    if r3.status_code == 200 and "invalid" not in head3 and "error" not in head3:
        open(out_path, "wb").write(r3.content); return out_path

    raise RuntimeError(
        "FIRMS requests failed.\n"
        f"Area WSEN: {head.strip()}\nArea SWNE: {head2.strip()}\nCountry CAN: {head3.strip()}"
    )

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
    return df

def save_geojson_points(df, out_path, popup_cols=None):
    popup_cols = popup_cols or [c for c in ["acq_date","acq_time","satellite","frp","brightness","confidence"] if c in df.columns]
    feats = []
    for _, r in df.iterrows():
        props = {c: r[c] for c in popup_cols if c in df.columns}
        feats.append({
            "type":"Feature",
            "geometry":{"type":"Point","coordinates":[float(r["lon"]), float(r["lat"])]},
            "properties": props
        })
    fc = {"type":"FeatureCollection","features":feats}
    with open(out_path, "w", encoding="utf-8") as f: json.dump(fc, f)
    return out_path
