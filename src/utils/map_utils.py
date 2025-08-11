import os, folium
from folium.plugins import HeatMap, MarkerCluster
from .config import MAP_DIR, BBOX

def make_firms_map(df, map_name="firms_latest"):
    south, west, north, east = BBOX[1], BBOX[0], BBOX[3], BBOX[2]
    m = folium.Map(location=[(south+north)/2, (west+east)/2], zoom_start=5, control_scale=True)
    folium.Rectangle([(south, west), (north, east)], fill=False, weight=2).add_to(m)

    weight_col = "confidence" if "confidence" in df.columns else ("frp" if "frp" in df.columns else None)
    heat = [[r["lat"], r["lon"], float(r.get(weight_col, 1.0))] for _, r in df.iterrows()]
    if heat:
        HeatMap(heat, radius=10, blur=15, max_zoom=8).add_to(m)

    mc = MarkerCluster().add_to(m)
    popup_cols = [c for c in ["acq_date","acq_time","satellite","frp","brightness","confidence","instrument"] if c in df.columns]
    for _, r in df.iterrows():
        html = "<br>".join([f"<b>{c}:</b> {r[c]}" for c in popup_cols])
        folium.Marker([r["lat"], r["lon"]], popup=folium.Popup(html, max_width=300)).add_to(mc)

    os.makedirs(MAP_DIR, exist_ok=True)
    out = f"{MAP_DIR}/{map_name}.html"
    m.save(out)
    return out