r"""
Run:
  python -m scripts.get_firms_data
"""
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.utils.config import DATASET, DAYS, RAW_DIR, PROCESSED_DIR, MAP_DIR, FIRMS_API_KEY  # type: ignore
from src.utils.firms import fetch_firms_csv, load_firms_df, save_geojson_points

try:
    import folium
    from folium.plugins import HeatMap, MarkerCluster
    FOLIUM_OK = True
except Exception:
    FOLIUM_OK = False

def build_map(df, out_html):
    if not FOLIUM_OK or df.empty: return None
    from src.utils.config import BBOX
    w,s,e,n = BBOX
    center = [(s+n)/2, (w+e)/2]
    m = folium.Map(location=center, zoom_start=5, control_scale=True)
    try: folium.Rectangle([(s,w),(n,e)], fill=False, weight=2).add_to(m)
    except: pass
    # Heatmap weights
    def weight(r):
        if "frp" in df.columns:
            try: return float(r["frp"])
            except: pass
        if "confidence" in df.columns:
            try: return float(r["confidence"])
            except:
                t=str(r["confidence"]).strip().lower()
                return {"l":0.3,"n":0.6,"h":0.9}.get(t,1.0)
        return 1.0
    heat=[]
    for _,r in df.iterrows():
        try: heat.append([float(r["lat"]), float(r["lon"]), float(weight(r))])
        except: pass
    if heat: HeatMap(heat, radius=10, blur=15, max_zoom=8).add_to(m)
    mc = MarkerCluster().add_to(m)
    popup_cols=[c for c in ["acq_date","acq_time","satellite","frp","brightness","confidence","instrument"] if c in df.columns]
    for i,(_,r) in enumerate(df.iterrows()):
        if i % max(1, len(df)//1000): continue
        html="<br>".join([f"<b>{c}:</b> {r[c]}" for c in popup_cols])
        try: folium.Marker([float(r["lat"]), float(r["lon"])], popup=folium.Popup(html, max_width=300)).add_to(mc)
        except: pass
    os.makedirs(os.path.dirname(out_html), exist_ok=True)
    m.save(out_html); return out_html

def main():
    if not FIRMS_API_KEY or FIRMS_API_KEY.strip() in {"","CHANGE_ME"}:
        print("❌ Set FIRMS_API_KEY in env or src/utils/config.py"); return
    print(f"▶ Fetching NASA FIRMS dataset={DATASET} over last {DAYS} days…")
    csv_path = fetch_firms_csv()
    print(f"✅ CSV saved: {csv_path}")
    df = load_firms_df(csv_path)
    from datetime import datetime
    print(f"ℹ Rows loaded: {len(df)}")
    from src.utils.config import PROCESSED_DIR
    date_tag = os.path.basename(csv_path).split("_")[-1].replace(".csv","")
    gj_path = os.path.join(PROCESSED_DIR, f"firms_{DATASET}_{date_tag}.geojson")
    save_geojson_points(df, gj_path)
    print(f"✅ GeoJSON saved: {gj_path}")
    from src.utils.config import MAP_DIR
    mpath = build_map(df, os.path.join(MAP_DIR, "firms_latest.html"))
    if mpath: print(f"🗺  Map saved: {mpath}")
    print("🎉 Done.")

if __name__ == "__main__":
    main()
