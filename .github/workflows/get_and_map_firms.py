# get_and_map_firms.py
# FIRMS (MAP_KEY-based area CSV) + Canadian weather (Meteostat) -> site/index.html for GitHub Pages

from pathlib import Path
import os
import sys
import time
from datetime import datetime, timezone

import requests
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster
from meteostat import Stations, Hourly
import pytz

# ============== Paths / Output ==============
ROOT = Path(__file__).parent
SITE_DIR = ROOT / "site"
RAW_DIR = ROOT / "data" / "raw"
SITE_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

MAP_PATH = SITE_DIR / "index.html"   # <-- GitHub Pages will serve this

# ============== Secrets / Config ==============
# IMPORTANT: Do NOT hardcode secrets. Provide them via environment / GitHub Actions.
MAP_KEY = os.getenv("ef237f447ad3d6bb05d187024f80c981")            # required for FIRMS area API
# API_KEY = os.getenv("ef237f447ad3d6bb05d187024f80c981")          # not used in this script (MAP_KEY is required)

SOURCE   = "VIIRS_NOAA20_NRT"                   # VIIRS_NOAA20_NRT | VIIRS_SNPP_NRT | MODIS_C6_1
BBOX     = [-102.0, 49.0, -95.0, 55.0]          # west, south, east, north (Manitoba-ish)
DAYS     = 7                                     # lookback days for FIRMS
HOURS_CA = 24                                    # last N hours of Canadian weather observations

# ============== FIRMS ==============
def fetch_firms_csv(map_key: str, source: str, bbox: list[float], days: int) -> Path:
    """Fetch FIRMS detections for a bbox using MAP_KEY area endpoint and save CSV."""
    if not map_key:
        raise RuntimeError("Missing FIRMS MAP_KEY. Set env var FIRMS_MAP_KEY.")

    west, south, east, north = bbox  # order required by FIRMS
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/{source}/{west},{south},{east},{north}/{days}"
    print(f"Fetching FIRMS: {url}")

    r = requests.get(url, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"FIRMS API error {r.status_code}: {r.text[:300]}")

    # Catch text errors returned as CSV/plain text
    first_line = (r.text.strip().splitlines() or [""])[0].lower()
    if first_line.startswith("invalid area") or "<html" in first_line:
        raise RuntimeError(f"FIRMS API response looks invalid:\n{r.text[:300]}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RAW_DIR / f"firms_{source}_{stamp}.csv"
    out.write_bytes(r.content)
    print(f"✅ Saved CSV: {out}")
    return out

def load_firms(csv_path: Path) -> pd.DataFrame:
    """Load FIRMS CSV and normalize columns."""
    df = pd.read_csv(csv_path)
    df.columns = [c.lower() for c in df.columns]
    if not {"latitude", "longitude"}.issubset(df.columns):
        first = open(csv_path, "r", encoding="utf-8", errors="ignore").readline().strip()
        raise RuntimeError(f"CSV missing latitude/longitude. First line: {first}")
    df = df.dropna(subset=["latitude", "longitude"]).copy()
    if "acq_date" in df.columns:
        df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce", utc=True)
    return df

# ============== Canadian Weather (Meteostat observations: last N hours) ==============
def fetch_canada_grid(bbox: list[float], hours: int) -> list[dict]:
    """Fetch hourly weather observations for stations in/near bbox and summarize last N hours."""
    west, south, east, north = bbox
    center_lat = (south + north) / 2
    center_lon = (west + east) / 2

    # Primary: stations with hourly inventory inside bbox
    stations = (
        Stations()
        .bounds((south, west), (north, east))
        .inventory("hourly", True)
        .fetch(200)
    )
    # Fallback 1: slightly expanded bbox
    if stations.empty:
        pad = 2.0
        stations = (
            Stations()
            .bounds((south - pad, west - pad), (north + pad, east + pad))
            .inventory("hourly", True)
            .fetch(200)
        )
    # Fallback 2: nearest Canadian stations to center point
    if stations.empty:
        stations = (
            Stations()
            .region("CA")
            .nearby(center_lat, center_lon)
            .inventory("hourly", True)
            .fetch(50)
        )

    results: list[dict] = []
    if stations.empty:
        print("⚠ No Canadian weather stations found near bbox.")
        return results

    now = datetime.now(pytz.UTC)
    start = now - pd.Timedelta(hours=hours)

    for _, stn in stations.iterrows():
        try:
            data = Hourly(stn["id"], start=start, end=now).fetch()
        except Exception:
            continue
        if data.empty:
            continue

        temp_mean_c = round(float(data["temp"].mean()), 1) if "temp" in data and not data["temp"].isna().all() else None
        rh_mean_pct = round(float(data["rhum"].mean()), 1) if "rhum" in data and not data["rhum"].isna().all() else None
        # Meteostat wind speed is m/s; convert to km/h
        if "wspd" in data and not data["wspd"].isna().all():
            wind_kmh = round(float(data["wspd"].iloc[-1]) * 3.6, 1)
            wind_example = f"{wind_kmh} km/h"
        else:
            wind_example = None

        results.append({
            "lat": float(stn["latitude"]),
            "lon": float(stn["longitude"]),
            "temp_mean_c": temp_mean_c,
            "rh_mean_pct": rh_mean_pct,
            "first_start": str(data.index[0]),
            "first_end": str(data.index[-1]),
            "wind_example": wind_example,
        })
        time.sleep(0.1)  # be polite

    return results

# ============== Map helpers ==============
def risk_color(row: pd.Series) -> str:
    """Green→yellow→red based on confidence (fallback to brightness)."""
    def norm(v, lo, hi):
        try:
            v = float(v)
        except Exception:
            return 0.5
        v = max(lo, min(hi, v))
        return (v - lo) / (hi - lo + 1e-9)

    x = 0.5
    conf = row.get("confidence", None)
    try:
        if conf is not None and str(conf).replace(".", "", 1).isdigit():
            x = norm(float(conf), 0, 100)
        else:
            raise Exception()
    except Exception:
        if isinstance(conf, str):
            x = {"low": 0.2, "nominal": 0.5, "high": 0.85}.get(conf.lower(), 0.5)
        else:
            x = norm(row.get("brightness", 320), 300, 420)

    if x < 0.5:
        r = int(2 * x * 255); g = 255
        return f"#{r:02x}{g:02x}00"
    else:
        r = 255; g = int((1 - (x - 0.5) * 2) * 255)
        return f"#{r:02x}{g:02x}00"

def add_footer(m: folium.Map, text: str) -> None:
    """Add a small footer overlay to the map."""
    html = f"""
    <div style="
        position: fixed;
        left: 10px;
        bottom: 10px;
        z-index: 9999;
        background: rgba(0,0,0,0.55);
        color: #fff;
        padding: 6px 10px;
        border-radius: 6px;
        font: 12px/1.2 Arial, sans-serif;
    ">{text}</div>
    """
    from folium import Element
    m.get_root().html.add_child(Element(html))

def build_map(firms_df: pd.DataFrame, wx_points: list[dict], out_html: Path) -> None:
    lat_col, lon_col = "latitude", "longitude"
    center_lat = float(firms_df[lat_col].mean()) if not firms_df.empty else (BBOX[1] + BBOX[3]) / 2
    center_lon = float(firms_df[lon_col].mean()) if not firms_df.empty else (BBOX[0] + BBOX[2]) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, control_scale=True)
    folium.TileLayer("OpenStreetMap", name="OSM").add_to(m)
    folium.TileLayer("CartoDB positron", name="Light").add_to(m)
    folium.TileLayer("CartoDB dark_matter", name="Dark").add_to(m)

    # FIRMS detections
    if not firms_df.empty:
        cluster = MarkerCluster(name="FIRMS Detections").add_to(m)
        for _, r in firms_df.iterrows():
            popup = folium.Popup(
                (f"<b>Date</b>: {r.get('acq_date','')} {r.get('acq_time','')}"
                 f"<br><b>Brightness</b>: {r.get('brightness','')}"
                 f"<br><b>FRP</b>: {r.get('frp','')}"
                 f"<br><b>Confidence</b>: {r.get('confidence','')}"
                 f"<br><b>Satellite</b>: {r.get('satellite','')}"
                 f"<br><b>Instrument</b>: {r.get('instrument','')}"),
                max_width=360
            )
            folium.CircleMarker(
                [r[lat_col], r[lon_col]],
                radius=4,
                fill=True,
                fill_opacity=0.8,
                color=risk_color(r),
                weight=0,
                popup=popup
            ).add_to(cluster)

        HeatMap(
            firms_df[[lat_col, lon_col]].values.tolist(),
            radius=12, blur=18, min_opacity=0.2, name="FIRMS Heatmap"
        ).add_to(m)

    # Canada weather overlay
    if wx_points:
        grp = folium.FeatureGroup(name=f"Canada Weather (last {HOURS_CA}h)").add_to(m)
        for p in wx_points:
            rh = p.get("rh_mean_pct")
            # color by RH (drier -> redder)
            if rh is None: color = "#888888"
            elif rh < 25:  color = "#ff3300"
            elif rh < 45:  color = "#ff9900"
            elif rh < 65:  color = "#ffd11a"
            else:          color = "#00aa00"

            label = (f"<b>ECCC/Meteostat (last {HOURS_CA}h)</b>"
                     f"<br>Temp mean: {p.get('temp_mean_c')}"
                     f"<br>RH mean: {rh}"
                     f"<br>Wind: {p.get('wind_example')}"
                     f"<br>From: {p.get('first_start')}<br>To: {p.get('first_end')}")
            folium.CircleMarker(
                [p["lat"], p["lon"]], radius=6, fill=True, fill_opacity=0.6,
                color=color, weight=1, popup=folium.Popup(label, max_width=320)
            ).add_to(grp)

    # Timestamp footer
    updated = datetime.now(timezone.utc).strftime("Last updated: %Y-%m-%d %H:%M UTC")
    add_footer(m, updated)

    folium.LayerControl(collapsed=False).add_to(m)
    m.save(str(out_html))
    print(f"✅ Map saved: {out_html}")

# ============== Main ==============
def main():
    print("Starting LandWatch.AI — FIRMS + Canada Weather…")
    csv_path = fetch_firms_csv(MAP_KEY, SOURCE, BBOX, DAYS)
    firms_df = load_firms(csv_path)
    print("Fetching Canadian hourly weather (Meteostat)…")
    wx_points = fetch_canada_grid(BBOX, HOURS_CA)
    print(f"✅ Canadian weather points: {len(wx_points)}")
    build_map(firms_df, wx_points, MAP_PATH)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n❌ Error:", e)
        sys.exit(1)
