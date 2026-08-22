"""
VAYU - Automated Live Hourly Pipeline Execution Engine
High-performance batch execution integrating multi-source sensor telemetry,
staleness guardrails, Dynamic Climatological Estimator (DCME), H3 spatial grid mesh,
IDW spatial interpolation, Open-Meteo 72h meteorology, self-correcting adaptive recalibration,
vectorized XGBoost rolling inference, Gemini multilingual advisories, and static snapshot export.
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
from backend.ingestion.fetch_waqi import fetch_live_waqi_telemetry, get_telemetry_status
from backend.ingestion.fetch_weather import fetch_72h_weather_forecast
from backend.advisory import generate_gemini_advisories, calculate_source_attribution
from backend.models.train_model import FEATURE_COLUMNS, train_aqi_model, MODEL_OUTPUT_PATH
from backend.models.adaptive_calibration import AdaptiveCalibrationEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

FRONTEND_DATA_OUTPUT = "frontend/public/data/delhi_current_grid.json"
BACKEND_DATA_OUTPUT = "backend/data/delhi_current_grid.json"


def get_aqi_rgba(aqi: float, alpha: int = 65) -> list:
    """Returns RGBA tuple based on CPCB AQI color scale with refined translucency."""
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
    Executes end-to-end VAYU batch pipeline with continuous error adaptation,
    staleness remediation, and calibrated XGBoost 72-hour forecasting.
    """
    logger.info("=" * 60)
    logger.info("STARTING CALIBRATED VAYU INGESTION & FORECASTING PIPELINE")
    logger.info("=" * 60)

    now_dt = datetime.datetime.now()
    now_iso = now_dt.isoformat()

    # 1. Fetch 72-Hour Weather Forecast First (needed for meteorological baseline conditioning)
    logger.info("1. Querying Open-Meteo 72-hour forecast vectors...")
    weather = fetch_72h_weather_forecast()
    forecast_times = weather.get("times", [])
    temps = weather["temperatures"]
    rhs = weather["humidity"]
    ws = weather["wind_speeds"]
    wdirs = weather["wind_dirs"]
    u_winds = weather["u_winds"]
    v_winds = weather["v_winds"]
    pressures = weather["pressures"]
    blhs = weather["blh"]

    weather_summary = {
        "temp": temps[0] if temps else 25.0,
        "humidity": rhs[0] if rhs else 55.0,
        "wind_speed": ws[0] if ws else 6.0,
        "wind_dir": wdirs[0] if wdirs else 280.0,
        "blh": blhs[0] if blhs else 450.0
    }

    # 2. Generate H3 Spatial Grid (~1,500 hexagons)
    logger.info("2. Generating Uber H3 spatial grid for NCT Delhi...")
    grid = generate_delhi_h3_grid(resolution=8)
    n_hex = len(grid)
    target_points = [tuple(hex_data["centroid"]) for hex_data in grid]

    # 3. Ingest Telemetry with Staleness Detection & DCME Fallback
    logger.info("3. Ingesting live CPCB / OpenAQ / WAQI station telemetry...")
    station_points = fetch_live_waqi_telemetry(weather_summary=weather_summary)
    telemetry_health = get_telemetry_status()
    logger.info(f"Ingested {len(station_points)} ground station feeds (Mode: {telemetry_health.get('ingestion_mode')}).")

    # 4. IDW Spatial Interpolation for Current Hour AQI
    logger.info("4. Running Inverse Distance Weighting (IDW) spatial interpolation...")
    current_aqis = np.array(idw_interpolation(target_points, station_points, power=2.0), dtype=float)
    city_mean_current = float(np.mean(current_aqis))
    logger.info(f"IDW spatial range: Min={np.min(current_aqis):.1f}, Max={np.max(current_aqis):.1f}, Mean={city_mean_current:.1f}")

    # 5. Continuous Self-Correction & Adaptive Recalibration Loop
    logger.info("5. Executing Adaptive Self-Correction & Error Recalibration Loop...")
    cal_engine = AdaptiveCalibrationEngine()
    eval_result = cal_engine.evaluate_ground_truth(now_iso, city_mean_current)
    calibration_metrics = cal_engine.get_metrics_summary()
    logger.info(f"Calibration metrics: Rolling Accuracy = {calibration_metrics['forecast_accuracy_pct']}%, MBE = {calibration_metrics['mean_bias_error']:+.2f}")

    # Compute forward feedback correction vector across 72h horizon
    num_hours = min(72, len(forecast_times))
    correction_vector = cal_engine.get_forward_correction_vector(num_hours)

    # 6. Load Pre-Trained XGBoost AQI Model
    logger.info("6. Loading pre-trained XGBoost model artifact...")
    if not os.path.exists(MODEL_OUTPUT_PATH):
        logger.warning(f"Model {MODEL_OUTPUT_PATH} not found. Training model now...")
        model = train_aqi_model()
    else:
        model = xgb.XGBRegressor()
        model.load_model(MODEL_OUTPUT_PATH)
        logger.info(f"Loaded XGBoost model from {MODEL_OUTPUT_PATH}")

    # 7. Pre-calculate zone average AQI for Gemini advisories
    zone_aqi_map = {}
    zone_count_map = {}
    for hex_data, cur_aqi in zip(grid, current_aqis):
        z_name = hex_data["zone_name"]
        zone_aqi_map[z_name] = zone_aqi_map.get(z_name, 0.0) + cur_aqi
        zone_count_map[z_name] = zone_count_map.get(z_name, 0) + 1

    zone_avg_aqi = {z: zone_aqi_map[z] / max(1, zone_count_map[z]) for z in zone_aqi_map}

    # 8. Generate Gemini AI Multilingual Advisories for 12 Municipal Zones
    logger.info("8. Generating Gemini AI health advisories for municipal zones...")
    zones_input = {}
    for z_name, avg_val in zone_avg_aqi.items():
        zones_input[z_name] = {
            "current_aqi": avg_val,
            "dominant_source": "Vehicular Traffic" if avg_val < 150 else "Industrial & Vehicular Emissions"
        }

    advisories = generate_gemini_advisories(zones_input)

    # 9. Autoregressive 72-Hour Forward Forecasting with Adaptive Feedback
    logger.info(f"9. Running calibrated 72-hour forward forecasting across {n_hex} spatial hexagons...")
    forecast_matrix = np.zeros((n_hex, num_hours), dtype=float)
    forecast_matrix[:, 0] = current_aqis

    # We evaluate forward atmospheric trajectory per zone/hexagon autoregressively
    # Build initial lag buffers for each hexagon
    hex_lags_1h = current_aqis.copy()
    hex_lags_2h = current_aqis.copy()
    hex_lags_3h = current_aqis.copy()
    hex_lags_24h = current_aqis.copy()

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

        h_sin = np.sin(2 * np.pi * t_hour / 24.0)
        h_cos = np.cos(2 * np.pi * t_hour / 24.0)
        d_sin = np.sin(2 * np.pi * t_doy / 365.25)
        d_cos = np.cos(2 * np.pi * t_doy / 365.25)

        # Vectorized batch prediction for all hexagons at step h
        batch_df = pd.DataFrame({
            "aqi_lag_1h": hex_lags_1h,
            "aqi_lag_2h": hex_lags_2h,
            "aqi_lag_3h": hex_lags_3h,
            "aqi_lag_24h": hex_lags_24h,
            "station_base": current_aqis, # Microclimate anchor
            "temperature_2m": temp_h,
            "relative_humidity_2m": rh_h,
            "wind_speed_10m": ws_h,
            "wind_direction_10m": wdir_h,
            "wind_u": u_h,
            "wind_v": v_h,
            "surface_pressure": press_h,
            "boundary_layer_height": blh_h,
            "inversion_factor": inv_fac,
            "hour": t_hour,
            "dayofweek": t_dow,
            "month": t_month,
            "hour_sin": h_sin,
            "hour_cos": h_cos,
            "doy_sin": d_sin,
            "doy_cos": d_cos,
        })

        pred_batch = model.predict(batch_df[FEATURE_COLUMNS])

        # Apply continuous adaptive error feedback compensation C_h
        c_val = float(correction_vector[h])
        adjusted_batch = pred_batch + c_val

        # Strict physical boundaries [20.0, 480.0]
        bounded_batch = np.clip(adjusted_batch, 20.0, 480.0)

        # Store in forecast matrix
        forecast_matrix[:, h] = np.round(bounded_batch, 1)

        # Update autoregressive lag buffers
        hex_lags_24h = hex_lags_3h.copy() if h >= 24 else current_aqis.copy()
        hex_lags_3h = hex_lags_2h.copy()
        hex_lags_2h = hex_lags_1h.copy()
        hex_lags_1h = bounded_batch.copy()

    # 10. Register Issued Forward Forecast with Adaptive Calibration Engine
    city_forecast_series = [float(np.mean(forecast_matrix[:, h])) for h in range(num_hours)]
    cal_engine.register_forecast(forecast_times[:num_hours], city_forecast_series, now_dt)

    # 11. Assemble Hexagon Payloads with Source Attribution & Translucent Color
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
            "color_rgb": get_aqi_rgba(base_cur_aqi, alpha=65),
            "source_attribution": attr,
            "advisory_en": zone_adv["en"],
            "advisory_hi": zone_adv["hi"],
            "forecast_72h": f_72h
        })

    avg_nct_aqi = round(float(total_nct_aqi / max(1, n_hex)), 1)
    nct_category = get_category_name(avg_nct_aqi)

    # 12. Build Master Grid Payload
    zones_summary = {}
    for z_name, avg_val in zone_avg_aqi.items():
        adv = advisories.get(z_name, {"en": "", "hi": ""})
        zones_summary[z_name] = {
            "current_aqi": round(avg_val),
            "category": get_category_name(avg_val),
            "dominant_source": "Vehicular Traffic" if avg_val < 150 else "Industrial & Vehicular Emissions",
            "advisory_en": adv.get("en", ""),
            "advisory_hi": adv.get("hi", "")
        }

    full_payload = {
        "timestamp": now_iso,
        "generated_at": now_dt.strftime("%Y-%m-%d %H:%M:%S IST"),
        "nct_average_aqi": avg_nct_aqi,
        "nct_category": nct_category,
        "dominant_pollutant": "PM2.5",
        "active_stations_count": len(station_points),
        "total_hexagons": len(hexagons_payload),
        "telemetry_health": telemetry_health,
        "calibration_metrics": calibration_metrics,
        "forecast_timestamps": forecast_times[:num_hours],
        "weather_summary": weather_summary,
        "zones_summary": zones_summary,
        "hexagons": hexagons_payload
    }

    # 13. Export Static Snapshots
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
    logger.info(f"Telemetry Status: {telemetry_health.get('source')} (Stale: {telemetry_health.get('is_stale')})")
    logger.info(f"Forecast Accuracy: {calibration_metrics['forecast_accuracy_pct']}% | MBE: {calibration_metrics['mean_bias_error']:+.2f}")
    logger.info("=" * 60)

    return full_payload


if __name__ == "__main__":
    run_pipeline()
