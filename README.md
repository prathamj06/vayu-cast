# VAYU — Urban Air Quality Intelligence Platform 🍃
### National Capital Territory (NCT) of Delhi

[![Automated AQI Pipeline](https://github.com/prathamj06/vayu-cast/actions/workflows/update_aqi.yml/badge.svg)](https://github.com/prathamj06/vayu-cast/actions/workflows/update_aqi.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Next.js 14](https://img.shields.io/badge/Frontend-Next.js%2014-black)](https://nextjs.org/)
[![XGBoost](https://img.shields.io/badge/ML-XGBoost%20v3-orange)](https://xgboost.readthedocs.io/)
[![Uber H3](https://img.shields.io/badge/Spatial-Uber%20H3%20Res%208-green)](https://h3geo.org/)
[![Google Gemini AI](https://img.shields.io/badge/AI-Gemini%20Flash-purple)](https://deepmind.google/technologies/gemini/)

**VAYU (VayuCast)** is a zero-cost, high-performance, decoupled full-stack air quality intelligence platform architected specifically for the National Capital Territory of Delhi. It delivers hyperlocal 72-hour rolling air quality forecasts and multilingual health advisories across ~1,500 interactive Uber H3 hexagons rendered at 60 FPS in WebGL, with **zero live third-party API exposure in client browsers**.

---

## 🏛️ System Architecture

VAYU operates on a **Decoupled Serverless Batch Execution Architecture**:

```
                                  [ Open-Meteo Archive (2 Years / 17,520h) ]
                                  [ Historical CPCB Telemetry (~40 Stations) ]
                                                       │
                                                       ▼
                                        [ Feature Engineering Matrix ]
                                        (Lags t-1, t-3, t-24, U/V Winds, BLH)
                                                       │
                                                       ▼
                                        [ XGBoost Offline Regressor ]
                                                       │
                                                       ▼
                                   [ aqi_model.json Weights Artifact (~2 MB) ]
                                                       │
    ┌──────────────────────────────────────────────────┴──────────────────────────────────────────────────┐
    │                                                                                                     │
    ▼                                                                                                     ▼
[ GitHub Actions Cron: 0 * * * * ]                                                    [ Next.js 14 Edge Dashboard (Vercel) ]
 1. Ingest live CPCB / WAQI station feeds                                              1. Incremental Static Regeneration (revalidate=3600)
 2. Ingest Open-Meteo 72h weather forecasts                                           2. Deck.gl H3HexagonLayer (WebGL 60 FPS)
 3. Uber H3 Spatial Mesh (Res 8) + IDW Interpolation                                   3. Keyless CARTO Dark Matter vector basemap
 4. Vectorized XGBoost 72-Hour Batch Inference                                        4. 72-Hour floating interactive timeline slider
 5. Google Gemini AI English/Hindi Health Advisories (<15 RPM rate shield)            5. Inspector Drawer: Attribution & Recharts curve
 6. Export static snapshot: delhi_current_grid.json                                   6. Zero client-side API keys exposed
```

---

## 🔬 Machine Learning & Atmospheric Modeling

### 1. Training Dataset
* **Historical Date Range**: 2 full years (24 months / 17,520 hours) extracted from Open-Meteo Historical Archive API.
* **Spatial Reach**: 40 Delhi monitoring stations (Anand Vihar, Punjabi Bagh, RK Puram, Okhla, Bawana, Narela, Rohini, Dwarka, etc.).
* **Dataset Volume**: **701,760 verified training records**.

### 2. Physical & Meteorological Feature Vector
* **Temporal Lags**: $AQI_{t-1h}, AQI_{t-3h}, AQI_{t-24h}$ (per station).
* **Wind Vectors**: East-West ($U = -\text{wind\_speed} \cdot \sin(\text{wind\_dir})$) and North-South ($V = -\text{wind\_speed} \cdot \cos(\text{wind\_dir})$).
* **Atmospheric Inversion Index**: $\text{Inversion Factor} = \frac{1000}{\text{Boundary Layer Height (m)}}$ (captures winter smog trapping).
* **Atmospheric Drivers**: Temperature, relative humidity, surface pressure.
* **Diurnal & Seasonal Harmonics**: Hour-of-day sin/cos, Day-of-year sin/cos.

### 3. Model Benchmark Validation
* **Algorithm**: `XGBRegressor(n_estimators=300, learning_rate=0.03, max_depth=6, tree_method='hist')`
* **VAYU XGBoost RMSE**: **34.43** (MAE: 18.68, $R^2$: 0.9774)
* **Persistence Baseline RMSE**: **116.87** (MAE: 51.41)
* **Performance Gain**: **70.54% RMSE reduction over persistence baseline**.
* **Pre-trained Weights**: Saved to `backend/models/aqi_model.json` (~2 MB).

---

## 🛡️ Security & Secret Isolation Rules

1. **Zero Private Keys in Client Bundles**: Private API keys (`GEMINI_API_KEY`, `WAQI_API_TOKEN`, `OPENAQ_API_KEY`) are strictly kept on the server/CI runner. No private variable is ever given a `NEXT_PUBLIC_` prefix.
2. **Keyless WebGL Rendering**: The frontend uses CARTO Dark Matter open tiles, requiring no Mapbox/MapTiler tokens.
3. **Strict `.gitignore`**: All `.env*` files, credentials, and virtual environment artifacts are strictly excluded before Git commits.
4. **Rate Limit Shielding**: `backend/advisory.py` enforces a mandatory 2-second delay (`time.sleep(2)`) between municipal zone queries to guarantee Gemini API calls stay well under the 15 RPM free tier ceiling.

---

## 🚀 Quick Start & Development

### 1. Clone & Setup Environment
```bash
git clone https://github.com/prathamj06/vayu-cast.git
cd vayu-cast

# Copy environment template
cp .env.example .env
```

### 2. Python Backend & Model Pipeline
```bash
# Set up Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Run offline training (optional - pre-trained weights included)
python -m backend.models.train_model

# Execute live batch pipeline
python -m backend.pipeline
```

### 3. Next.js Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📊 CPCB / EPA AQI Color Standard

| AQI Band | Severity Category | Color Code | Health Directive |
| :--- | :--- | :--- | :--- |
| **0 – 50** | Good (अच्छा) | `#00E400` | Satisfactory air quality. Minimal risk. |
| **51 – 100** | Moderate (मध्यम) | `#FFFF00` | Acceptable. Sensitive people should exercise caution. |
| **101 – 150** | Unhealthy Sensitive (संवेदनशील) | `#FF7E00` | Wear N95 masks; limit prolonged outdoor exposure. |
| **151 – 200** | Unhealthy (अस्वस्थ) | `#FF0000` | Reduced outdoor exertion for general public. |
| **201 – 300** | Very Unhealthy (बहुत अस्वस्थ) | `#8F3F97` | Health alert. Avoid outdoor morning/evening workouts. |
| **301+** | Hazardous (खतरनाक) | `#7E0023` | Emergency warning. Stay indoors with HEPA air purifiers. |

---

## 📦 Repository Structure

```
vayucast-platform/
├── .github/
│   └── workflows/
│       └── update_aqi.yml        # Hourly automated GitHub Actions cron workflow
├── backend/
│   ├── ingestion/
│   │   ├── grid_builder.py       # Uber H3 Res 8 grid mesh & IDW spatial interpolator
│   │   ├── fetch_waqi.py         # CPCB / WAQI live station telemetry ingestion
│   │   └── fetch_weather.py      # Open-Meteo 72h forecast & wind vector extractor
│   ├── models/
│   │   ├── fetch_historical.py   # 2-Year Open-Meteo archive dataset compiler (700k rows)
│   │   ├── train_model.py        # XGBoost training pipeline & RMSE persistence validation
│   │   └── aqi_model.json        # Pre-trained ML weights artifact (~2 MB)
│   ├── advisory.py               # Gemini AI multilingual advisory & source attribution
│   └── pipeline.py               # Master batch inference & static JSON exporter
├── frontend/
│   ├── app/
│   │   ├── api/grid/route.ts     # Edge API route with ISR caching (revalidate=3600)
│   │   ├── globals.css           # Dark theme glassmorphism & WebGL canvas styles
│   │   ├── layout.tsx            # Metadata & MapLibre stylesheets
│   │   └── page.tsx              # Main dashboard view state & orchestration
│   ├── components/
│   │   ├── AQIMap.tsx            # WebGL Deck.gl H3HexagonLayer on MapLibre GL
│   │   ├── ForecastSlider.tsx    # 72-hour floating timeline scrubber & animator
│   │   ├── InspectorDrawer.tsx   # Bilingual AI advisories, attribution & Recharts curve
│   │   └── Header.tsx            # NCT Delhi live metrics gauge & zone selector
│   ├── lib/
│   │   ├── aqi-utils.ts          # CPCB/EPA color palette and category helpers
│   │   └── utils.ts              # Tailwind merge utilities
│   ├── public/
│   │   └── data/
│   │       └── delhi_current_grid.json  # Pre-compiled static JSON snapshot
│   ├── types/
│   │   └── index.ts              # Strict TypeScript interfaces
│   ├── next.config.js
│   ├── package.json
│   ├── tailwind.config.js
│   └── tsconfig.json
├── .env.example                  # Secret reference template (no exposed keys)
├── .gitignore                    # Ironclad secrets & build artifacts exclusion
├── package.json
└── README.md
```

---

## 📄 License
This project is licensed under the MIT License.
