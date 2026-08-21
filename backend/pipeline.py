"""
VAYU - Automated Live Hourly Pipeline Execution Engine
High-performance batch execution integrating WAQI telemetry, H3 spatial grid mesh,
IDW spatial interpolation, Open-Meteo 72h meteorology, vectorized XGBoost rolling inference,
Gemini multilingual health advisories, and static snapshot export.
"""

import os
import sys
import json
import logging
import datetime
import numpy as np
import pandas as pd
import xgboost as xgb

# Ensure project root is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.ingestion.grid_builder import generate_delhi_h3_grid, idw_interpolation
from backend.ingestion.fetch_waqi import fetch_live_waqi_telemetry
from backend.ingestion.fetch_weather import fetch_72h_weather_forecast
from backend.advisory import generate_gemini_advisories, calculate_source_attribution
from backend.models.train_model import FEATURE_COLUMNS, train_aqi_model, MODEL_OUTPUT_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

FRONTEND_DATA_OUTPUT = "frontend/public/data/delhi_current_grid.json"
BACKEND_DATA_OUTPUT = "backend/data/delhi_current_grid.json"


def get_aqi_rgba(aqi: float, alpha: int = 180) -> list:
    """Returns RGBA tuple based on CPCB AQI color scale."""
    val = round(aqi)
    if val <= 50:
        return [0, 228, 0, alpha]         # Good (#00E400)
    elif val <= 100:
        return [255, 255, 0, alpha]       # Moderate (#FFFF00)
    elif val <= 150:
        return [255, 126, 0, alpha]       # Sensitive (#FF7E00)
    elif val <= 200:
        return [255, 0, 0, alpha]         # Unhealthy (#FF0000)
    elif val <= 300:
        return [143, 63, 151, alpha]      # Very Unhealthy (#8F3F97)
    else:
        return [126, 0, 35, alpha + 15]   # Hazardous (#7E0023)


def get_category_name(aqi: float) -> str:
    val = round(aqi)
    if val <= 50: return "Good"
    if val <= 100: return "Moderate"
    if val <= 150: return "Unhealthy for Sensitive Groups"
    if val <= 200: return "Unhealthy"
    if val <= 300: return "Very Unhealthy"
    return "Hazardous"


def run_pipeline() -> dict:
    """
    Executes end-to-end VAYU batch pipeline with vectorized batch inference
    and produces the static JSON payload.
    """
    logger.info("=" * 60)
    logger.info("STARTING VAYU LIVE INGESTION & FORECASTING PIPELINE")
    logger.info("=" * 60)

    # 1. Generate H3 Spatial Grid (~1,500 hexagons)
    logger.info("1. Generating Uber H3 spatial grid for NCT Delhi...")
    grid = generate_delhi_h3_grid(resolution=8)
    n_hex = len(grid)
    target_points = [tuple(hex_data["centroid"]) for hex_data in grid]

    # 2. Fetch Live Ground Station Telemetry
    logger.info("2. Ingesting live CPCB / WAQI station telemetry...")
    station_points = fetch_live_waqi_telemetry()
    logger.info(f"Ingested {len(station_points)} ground station feeds.")

    # 3. IDW Spatial Interpolation for Current Hour AQI
    logger.info("3. Running Inverse Distance Weighting (IDW) spatial interpolation...")
    current_aqis = np.array(idw_interpolation(target_points, station_points, power=2.0), dtype=float)

    # 4. Fetch 72-Hour Weather Forecast
    logger.info("4. Querying Open-Meteo 72-hour forecast vectors...")
    weather = fetch_72h_weather_forecast()
    forecast_times = weather.get("times", [])

    # 5. Load or Train XGBoost AQI Model
    logger.info("5. Loading pre-trained XGBoost model artifact...")
    if not os.path.exists(MODEL_OUTPUT_PATH):
        logger.warning(f"Model {MODEL_OUTPUT_PATH} not found. Training model now...")
        model = train_aqi_model()
    else:
        model = xgb.XGBRegressor()
        model.load_model(MODEL_OUTPUT_PATH)
        logger.info(f"Loaded XGBoost model from {MODEL_OUTPUT_PATH}")

    # 6. Pre-calculate zone average AQI for Gemini advisories
    now_dt = datetime.datetime.now()
    zone_aqi_map = {}
    zone_count_map = {}

    for hex_data, cur_aqi in zip(grid, current_aqis):
        z_name = hex_data["zone_name"]
        zone_aqi_map[z_name] = zone_aqi_map.get(z_name, 0.0) + cur_aqi
        zone_count_map[z_name] = zone_count_map.get(z_name, 0) + 1

    zone_avg_aqi = {z: zone_aqi_map[z] / max(1, zone_count_map[z]) for z in zone_aqi_map}

    # 7. Generate Gemini AI Multilingual Advisories for 12 Zones
    logger.info("7. Generating Gemini AI health advisories for municipal zones...")
    zones_input = {}
    for z_name, avg_val in zone_avg_aqi.items():
        zones_input[z_name] = {
            "current_aqi": avg_val,
            "dominant_source": "Vehicular Traffic & Stubble" if avg_val > 250 else "Traffic & Dust"
        }

    advisories = generate_gemini_advisories(zones_input)

    # 8. High-Performance Vectorized Batch Inference across all Hexagons for 72 Hours
    logger.info(f"8. Running vectorized 72-hour batch inference for all {n_hex} hexagons...")
    temps = weather["temperatures"]
    rhs = weather["humidity"]
    ws = weather["wind_speeds"]
    wdirs = weather["wind_dirs"]
    u_winds = weather["u_winds"]
    v_winds = weather["v_winds"]
    pressures = weather["pressures"]
    blhs = weather["blh"]

    num_hours = min(72, len(forecast_times))
    forecast_matrix = np.zeros((n_hex, num_hours), dtype=float)
    forecast_matrix[:, 0] = current_aqis

    # Lags matrix tracking
    lag_1 = current_aqis.copy()
    lag_3 = current_aqis.copy()
    lag_24 = current_aqis.copy()

    for h in range(1, num_hours):
        t_hour = (now_dt.hour + h) % 24
        t_month = now_dt.month
        t_doy = (now_dt.timetuple().tm_yday + (h // 24)) % 365
        t_dow = (now_dt.weekday() + (h // 24)) % 7

        h_idx = min(h, len(temps) - 1)
        temp_h = temps[h_idx]
        rh_h = rhs[h_idx]
        ws_h = ws[h_idx]
        wdir_h = wdirs[h_idx]
        u_h = u_winds[h_idx]
        v_h = v_winds[h_idx]
        press_h = pressures[h_idx]
        blh_h = blhs[h_idx]
        inv_fac = 1000.0 / max(100.0, blh_h)

        # Build batch array of shape (n_hex, n_features)
        batch_dict = {
            "aqi_lag_1h": lag_1,
            "aqi_lag_3h": lag_3,
            "aqi_lag_24h": lag_24,
            "temperature_2m": np.full(n_hex, temp_h),
            "relative_humidity_2m": np.full(n_hex, rh_h),
            "wind_speed_10m": np.full(n_hex, ws_h),
            "wind_direction_10m": np.full(n_hex, wdir_h),
            "wind_u": np.full(n_hex, u_h),
            "wind_v": np.full(n_hex, v_h),
            "surface_pressure": np.full(n_hex, press_h),
            "boundary_layer_height": np.full(n_hex, blh_h),
            "inversion_factor": np.full(n_hex, inv_fac),
            "hour": np.full(n_hex, t_hour),
            "dayofweek": np.full(n_hex, t_dow),
            "month": np.full(n_hex, t_month),
            "hour_sin": np.full(n_hex, np.sin(2 * np.pi * t_hour / 24.0)),
            "hour_cos": np.full(n_hex, np.cos(2 * np.pi * t_hour / 24.0)),
            "doy_sin": np.full(n_hex, np.sin(2 * np.pi * t_doy / 365.25)),
            "doy_cos": np.full(n_hex, np.cos(2 * np.pi * t_doy / 365.25)),
        }

        batch_df = pd.DataFrame(batch_dict)[FEATURE_COLUMNS]
        preds = model.predict(batch_df)
        preds = np.clip(preds, 20.0, 750.0)
        forecast_matrix[:, h] = preds

        # Update rolling state
        lag_24 = lag_3 if h >= 24 else current_aqis
        lag_3 = lag_1 if h >= 3 else current_aqis
        lag_1 = preds.copy()

    # 9. Assemble Hexagon Payloads
    hexagons_payload = []
    total_nct_aqi = 0.0

    for hex_idx, hex_data in enumerate(grid):
        hex_id = hex_data["hex_id"]
        c_lat, c_lon = hex_data["centroid"]
        z_name = hex_data["zone_name"]
        base_cur_aqi = float(current_aqis[hex_idx])
        total_nct_aqi += base_cur_aqi

        # 72h forecast integers
        f_72h = [int(round(x)) for x in forecast_matrix[hex_idx, :]]

        attr = calculate_source_attribution(
            zone_name=z_name,
            hour=now_dt.hour,
            wind_speed=ws[0] if ws else 6.0,
            wind_dir=wdirs[0] if wdirs else 290.0,
            month=now_dt.month
        )

        zone_adv = advisories.get(z_name, {
            "en": "Air quality is monitored continuously. Maintain standard precautions.",
            "hi": "वायु गुणवत्ता की निरंतर निगरानी की जा रही है। मानक सावधानियां बरतें।"
        })

        hexagons_payload.append({
            "hex_id": hex_id,
            "centroid": [c_lat, c_lon],
            "zone_name": z_name,
            "aqi": int(round(base_cur_aqi)),
            "color_rgb": get_aqi_rgba(base_cur_aqi),
            "source_attribution": attr,
            "advisory_en": zone_adv["en"],
            "advisory_hi": zone_adv["hi"],
            "forecast_72h": f_72h
        })

    avg_nct_aqi = round(float(total_nct_aqi / max(1, n_hex)), 1)
    nct_category = get_category_name(avg_nct_aqi)

    # 10. Build Master Grid Payload
    zones_summary = {}
    for z_name, avg_val in zone_avg_aqi.items():
        adv = advisories.get(z_name, {"en": "", "hi": ""})
        zones_summary[z_name] = {
            "current_aqi": round(avg_val),
            "category": get_category_name(avg_val),
            "dominant_source": "Vehicular Traffic" if avg_val < 200 else "Stubble & Vehicular Emissions",
            "advisory_en": adv.get("en", ""),
            "advisory_hi": adv.get("hi", "")
        }

    full_payload = {
        "timestamp": now_dt.isoformat(),
        "generated_at": now_dt.strftime("%Y-%m-%d %H:%M:%S IST"),
        "nct_average_aqi": avg_nct_aqi,
        "nct_category": nct_category,
        "dominant_pollutant": "PM2.5",
        "active_stations_count": len(station_points),
        "total_hexagons": len(hexagons_payload),
        "forecast_timestamps": forecast_times[:num_hours],
        "weather_summary": {
            "temp": temps[0] if temps else 25.0,
            "humidity": rhs[0] if rhs else 55.0,
            "wind_speed": ws[0] if ws else 6.0,
            "wind_dir": wdirs[0] if wdirs else 280.0,
            "blh": blhs[0] if blhs else 450.0
        },
        "zones_summary": zones_summary,
        "hexagons": hexagons_payload
    }

    # 11. Write to static JSON files
    os.makedirs(os.path.dirname(FRONTEND_DATA_OUTPUT), exist_ok=True)
    os.makedirs(os.path.dirname(BACKEND_DATA_OUTPUT), exist_ok=True)

    with open(FRONTEND_DATA_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(full_payload, f, ensure_ascii=False, indent=2)

    with open(BACKEND_DATA_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(full_payload, f, ensure_ascii=False, indent=2)

    file_size_kb = os.path.getsize(FRONTEND_DATA_OUTPUT) / 1024
    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETE: Exported {len(hexagons_payload)} hexagons to {FRONTEND_DATA_OUTPUT} ({file_size_kb:.1f} KB)")
    logger.info(f"NCT Delhi Average AQI: {avg_nct_aqi} ({nct_category})")
    logger.info("=" * 60)

    return full_payload


if __name__ == "__main__":
    run_pipeline()
