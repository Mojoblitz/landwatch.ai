# LandWatch.AI — Wildfire Risk Map

**Live wildfire risk monitoring for Manitoba and surrounding regions, powered by NASA FIRMS satellite data and Open-Meteo weather forecasts.**  
LandWatch.AI automatically updates daily with the latest wildfire risk levels and weather conditions.

🌐 **Live Map:** [View Here](https://mojoblitz.github.io/landwatch.ai/)

---

## 📍 Features
- **Daily updates** — pulls the latest data each night.
- **Risk levels** — low, medium, high — color-coded for quick visual scanning.
- **Weather overlays** — includes temperature, humidity, and wind speed for each point.
- **GeoJSON download** — easily grab the latest data for your own analysis.
- **Mobile-friendly** — interactive map works across devices.

---

## 🔍 How It Works
1. **Data Collection** — NASA FIRMS wildfire risk + Open-Meteo weather data.
2. **Processing Script** — `get_weather_data.py` merges location, risk score, and weather conditions into a single GeoJSON file.
3. **Automatic Deployment** — GitHub Actions runs the update script nightly and pushes new data to the site.
4. **Map Display** — The `index.html` uses Leaflet.js to render the interactive map.

---

## 📦 Data Sources
- [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) — Fire Information for Resource Management System
- [Open-Meteo](https://open-meteo.com/) — Weather forecast API

---

## 📂 Repository Structure
Add detailed README with project description and usage
