# 🌍 LandWatch.AI — Wildfire Risk Map

[![Pages Build](https://github.com/Mojoblitz/landwatch.ai/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/Mojoblitz/landwatch.ai/actions)
![Last Updated](https://img.shields.io/github/last-commit/Mojoblitz/landwatch.ai?label=Last%20Update)
![License](https://img.shields.io/github/license/Mojoblitz/landwatch.ai)

An interactive map that visualizes **wildfire risk levels** across Manitoba, Canada, using real-time weather data and AI-driven risk scoring.

🔗 **Live Map:** [https://mojoblitz.github.io/landwatch.ai/](https://mojoblitz.github.io/landwatch.ai/)

---

## 📍 Features
- **Interactive wildfire risk map** with zoom & pan  
- Color-coded **risk levels** (Low 🟢, Medium 🟡, High 🔴)  
- Popups showing:
  - Risk score
  - Temperature
  - Relative humidity
  - Wind speed  
- Built with [Leaflet.js](https://leafletjs.com/) for smooth rendering
- Automated updates via GitHub Actions

---

## 🛠 How It Works
1. **Data Fetching:** Weather data is fetched from the [Open-Meteo API](https://open-meteo.com/) and processed with Python.
2. **Risk Scoring:** A simple model assigns each point a *risk score* and *risk level*.
3. **GeoJSON Output:** Data is saved as `geo/risk_latest.geojson`.
4. **Visualization:** Leaflet renders the points on the live map with color & size encoding.

---

## 🚀 Running Locally

Clone the repository:
```bash
git clone https://github.com/Mojoblitz/landwatch.ai.git
cd landwatch.ai
