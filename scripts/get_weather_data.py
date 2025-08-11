import os, math, time, requests, geopandas as gpd, pandas as pd
from shapely.geometry import box, Point
from datetime import datetime, timezone
from src.utils.config import BBOX, RAW_DIR, PROCESSED_DIR

OPEN_METEO_URL = ("https://api.open-meteo.com/v1/forecast"
                  "?latitude={lat}&longitude={lon}"
                  "&hourly=temperature_2m,relative_humidity_2m,windspeed_10m,winddirection_10m"
                  "&forecast_days=2&timezone=UTC")

def make_grid(bbox, cell_km=5.0):
    w,s,e,n = bbox
    mid = (s+n)/2.0
    km_lat, km_lon = 111.0, 111.320*math.cos(math.radians(mid))
    dlat, dlon = cell_km/km_lat, cell_km/km_lon
    cols, rows = int(max(1, math.ceil((e-w)/dlon))), int(max(1, math.ceil((n-s)/dlat)))
    cells=[]
    for i in range(cols):
        for j in range(rows):
            x1=w+i*dlon; y1=s+j*dlat; x2=min(e,x1+dlon); y2=min(n,y1+dlat)
            cells.append(box(x1,y1,x2,y2))
    return gpd.GeoDataFrame(geometry=cells, crs="EPSG:4326")

def fetch(lat, lon, retries=2, backoff=1.3):
    url = OPEN_METEO_URL.format(lat=lat, lon=lon)
    for a in range(retries+1):
        r = requests.get(url, timeout=20)
        if r.status_code==200:
            return r.json()
        if a<retries:
            time.sleep(backoff**a)
    raise RuntimeError(f"Open-Meteo error {r.status_code}: {r.text[:200]}")

def latest_hour(payload):
    h = payload.get("hourly", {})
    times = h.get("time", [])
    if not times:
        return None
    i = len(times) - 1

    def gv(key):
        arr = h.get(key, [])
        return arr[i] if i < len(arr) else None

    return {
        "timestamp": times[i],
        "temperature_2m": gv("temperature_2m"),
        "relative_humidity_2m": gv("relative_humidity_2m"),
        "windspeed_10m": gv("windspeed_10m"),
        "winddirection_10m": gv("winddirection_10m"),
    }

def main():
    print("▶ Building 5km grid...")
    grid = make_grid(BBOX, 5.0)
    target=300; step=max(1, math.ceil(len(grid)/target))
    grid_s = grid.iloc[::step].copy()
    grid_s["centroid"]=grid_s.geometry.centroid  # OK for sampling

    print(f"▶ Fetching Open-Meteo weather for {len(grid_s)} grid centroids (step={step})...")
    rows=[]
    for _, r in grid_s.iterrows():
        c=r["centroid"]; lat,lon=float(c.y), float(c.x)
        try:
            p = fetch(lat,lon)
            lh = latest_hour(p)
            if not lh:
                continue
            lh["lat"]=lat; lh["lon"]=lon
            rows.append(lh)
        except Exception as e:
            print(f"⚠ Weather fetch failed for {lat:.4f},{lon:.4f}: {e}")
    if not rows:
        print("⚠ No weather rows fetched.")
        return

    df = pd.DataFrame(rows)
    gdf = gpd.GeoDataFrame(df, geometry=[Point(xy) for xy in zip(df["lon"], df["lat"])], crs="EPSG:4326")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(RAW_DIR, exist_ok=True); os.makedirs(PROCESSED_DIR, exist_ok=True)
    gdf.to_csv(os.path.join(RAW_DIR, f"weather_grid_{date_str}.csv"), index=False)
    gdf.to_file(os.path.join(PROCESSED_DIR, f"weather_grid_{date_str}.geojson"), driver="GeoJSON")
    print("🎉 Weather grid ready.")
if __name__ == "__main__":
    main()
