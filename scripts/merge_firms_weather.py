import os, glob, numpy as np, pandas as pd, geopandas as gpd
from datetime import datetime
from src.utils.config import PROCESSED_DIR

CRS_METERS = "EPSG:3347"
BUFFER_KM = 10.0
OUT_GEOJSON = os.path.join(PROCESSED_DIR, "risk_latest.geojson")
OUT_CSV     = os.path.join(PROCESSED_DIR, "risk_latest.csv")

def _latest(pat):
    files = glob.glob(pat)
    return max(files, key=os.path.getmtime) if files else None

def load_latest_weather():
    p = _latest(os.path.join(PROCESSED_DIR, "weather_grid_*.geojson"))
    if not p: raise FileNotFoundError("No weather_grid_*.geojson found")
    wx = gpd.read_file(p).to_crs(CRS_METERS)
    for c in ["temperature_2m","relative_humidity_2m","windspeed_10m","winddirection_10m"]:
        if c not in wx.columns: wx[c]=np.nan
    return wx, p

def load_latest_firms():
    p = _latest(os.path.join(PROCESSED_DIR, "firms_*.geojson"))
    if not p: raise FileNotFoundError("No firms_*.geojson found")
    return gpd.read_file(p).to_crs(CRS_METERS), p

def count_fires_within(wx_m, firms_m, km):
    r = km*1000.0
    wx_buf = wx_m.copy(); wx_buf["geometry"] = wx_buf.geometry.buffer(r)
    j = gpd.sjoin(firms_m, wx_buf[["geometry"]], predicate="within", how="left")
    counts = j.groupby("index_right").size()
    wx_m = wx_m.copy()
    wx_m[f"firms_count_{int(km)}km"] = wx_m.index.map(counts).fillna(0).astype(int)
    return wx_m

def minmax(s):
    s = pd.to_numeric(s, errors="coerce")
    mn, mx = s.min(), s.max()
    if not np.isfinite(mn) or not np.isfinite(mx) or mx==mn:
        return pd.Series([0.0]*len(s), index=s.index)
    return (s - mn) / (mx - mn)

def compute_risk(wx):
    temp_n = minmax(wx["temperature_2m"])
    rh_n   = minmax(wx["relative_humidity_2m"])
    wind_n = minmax(wx["windspeed_10m"])
    fire_n = minmax(wx.filter(like="firms_count_").iloc[:,0])
    risk = 0.35*temp_n + 0.25*wind_n + 0.15*(1.0 - rh_n) + 0.25*fire_n
    risk = risk.clip(0,1)
    wx = wx.copy()
    wx["risk_score"] = risk.round(3)
    wx["risk_level"] = pd.cut(wx["risk_score"], bins=[-1,0.33,0.66,1.01], labels=["Low","Medium","High"])
    return wx

def main():
    print("▶ Loading latest weather grid…")
    wx_m, wpath = load_latest_weather(); print("   ", wpath)
    print("▶ Loading latest FIRMS detections…")
    f_m, fpath = load_latest_firms(); print("   ", fpath)
    print(f"▶ Counting FIRMS within {BUFFER_KM:.0f} km…")
    wx_aug = count_fires_within(wx_m, f_m, BUFFER_KM)
    print("▶ Computing risk…")
    wx_risk = compute_risk(wx_aug).to_crs("EPSG:4326")
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    wx_risk.to_file(OUT_GEOJSON, driver="GeoJSON")
    wx_risk.drop(columns="geometry").to_csv(OUT_CSV, index=False)
    print(f"✅ Risk GeoJSON: {OUT_GEOJSON}")
    print(f"✅ Risk CSV:     {OUT_CSV}")
    print("🎉 Done.")

if __name__ == "__main__":
    main()
