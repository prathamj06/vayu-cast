"""
VAYU - Real-Time Telemetry Ingestion & Dynamic Climatological Estimator (DCME)
Integrates live CPCB / OpenAQ / WAQI sensor telemetry across NCT Delhi,
detects stale data / ingestion interruptions, and provides a continuous,
meteorology- and season-grounded dynamic estimation engine.
"""

import os
import time
import math
import logging
import datetime
import requests
from typing import List, Tuple, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WAQI_API_TOKEN = os.getenv("WAQI_API_TOKEN", "")
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "")

# Comprehensive Delhi CPCB/DPCC Ground Station Network with Reference Microclimate Baselines
# Reference base is calibrated against winter peak load (DOY ~325); DCME scales dynamically by season & meteorology.
DELHI_STATIONS_BASELINE = [
    # Heavy Industrial & Interstate Transport Nodes (North / Northwest / East)
    {"name": "Anand Vihar, Delhi", "lat": 28.6469, "lon": 77.3160, "base_aqi": 240, "type": "industrial_transport"},
    {"name": "Bawana Industrial Area, Delhi", "lat": 28.7762, "lon": 77.0511, "base_aqi": 250, "type": "heavy_industrial"},
    {"name": "Narela Industrial Area, Delhi", "lat": 28.8500, "lon": 77.0900, "base_aqi": 240, "type": "industrial_border"},
    {"name": "Jahangirpuri, Delhi", "lat": 28.7328, "lon": 77.1706, "base_aqi": 230, "type": "industrial_mixed"},
    {"name": "Wazirpur Industrial Area, Delhi", "lat": 28.6998, "lon": 77.1654, "base_aqi": 235, "type": "industrial"},
    {"name": "Mundka, Delhi", "lat": 28.6847, "lon": 77.0299, "base_aqi": 240, "type": "industrial_west"},
    {"name": "Okhla Phase 2, Delhi", "lat": 28.5300, "lon": 77.2800, "base_aqi": 225, "type": "industrial_south"},

    # High-Density Commercial & Heavy Traffic Corridors
    {"name": "ITO Junction, Delhi", "lat": 28.6315, "lon": 77.2488, "base_aqi": 195, "type": "heavy_traffic"},
    {"name": "Punjabi Bagh, Delhi", "lat": 28.6720, "lon": 77.1310, "base_aqi": 185, "type": "traffic_corridor"},
    {"name": "Shadipur, Delhi", "lat": 28.6515, "lon": 77.1581, "base_aqi": 180, "type": "commercial_traffic"},
    {"name": "Chandni Chowk, Delhi", "lat": 28.6562, "lon": 77.2300, "base_aqi": 175, "type": "high_density_heritage"},
    {"name": "Vivek Vihar, Delhi", "lat": 28.6720, "lon": 77.3150, "base_aqi": 195, "type": "east_residential_traffic"},

    # High-Density Mixed Residential (East / North / West)
    {"name": "Patparganj, Delhi", "lat": 28.6237, "lon": 77.2872, "base_aqi": 175, "type": "residential_east"},
    {"name": "Sonia Vihar, Delhi", "lat": 28.7105, "lon": 77.2494, "base_aqi": 180, "type": "riverbed_mixed"},
    {"name": "Ashok Vihar, Delhi", "lat": 28.6954, "lon": 77.1817, "base_aqi": 175, "type": "residential_north"},
    {"name": "Rohini Sector 16, Delhi", "lat": 28.7495, "lon": 77.0565, "base_aqi": 185, "type": "suburban_northwest"},
    {"name": "Burari Crossing, Delhi", "lat": 28.7256, "lon": 77.2012, "base_aqi": 190, "type": "north_highway"},
    {"name": "Alipur, Delhi", "lat": 28.7971, "lon": 77.1331, "base_aqi": 195, "type": "north_corridor"},
    {"name": "Shahdara, Delhi", "lat": 28.6738, "lon": 77.2915, "base_aqi": 190, "type": "east_mixed"},

    # Suburban & Institutional Sectors
    {"name": "Dwarka Sector 8, Delhi", "lat": 28.5823, "lon": 77.0500, "base_aqi": 135, "type": "suburban_planned"},
    {"name": "IGI Airport T3, Delhi", "lat": 28.5562, "lon": 77.1000, "base_aqi": 140, "type": "aviation_open"},
    {"name": "North Campus DU, Delhi", "lat": 28.6900, "lon": 77.2100, "base_aqi": 135, "type": "university_green"},
    {"name": "Pusa Campus, Delhi", "lat": 28.6366, "lon": 77.1567, "base_aqi": 125, "type": "institutional_forest"},
    {"name": "Najafgarh, Delhi", "lat": 28.6090, "lon": 76.9790, "base_aqi": 145, "type": "rural_west"},
    {"name": "Mandir Marg, Delhi", "lat": 28.6360, "lon": 77.2010, "base_aqi": 130, "type": "central_mixed"},

    # Low-Density, Forest Canopy, Green Belts & South Delhi Residential
    {"name": "Lodhi Road, Delhi", "lat": 28.5880, "lon": 77.2210, "base_aqi": 95, "type": "central_green_canopy"},
    {"name": "Major Dhyan Chand Stadium, Delhi", "lat": 28.6120, "lon": 77.2370, "base_aqi": 105, "type": "central_green"},
    {"name": "Jawaharlal Nehru Stadium, Delhi", "lat": 28.5802, "lon": 77.2338, "base_aqi": 110, "type": "south_central"},
    {"name": "Sri Aurobindo Marg (Hauz Khas), Delhi", "lat": 28.5313, "lon": 77.1901, "base_aqi": 115, "type": "south_corridor"},
    {"name": "Sirifort, Delhi", "lat": 28.5504, "lon": 77.2159, "base_aqi": 100, "type": "south_green_residential"},
    {"name": "R K Puram, Delhi", "lat": 28.5630, "lon": 77.1860, "base_aqi": 120, "type": "south_residential"},
    {"name": "Dr. Karni Singh Range (Asola), Delhi", "lat": 28.4986, "lon": 77.2648, "base_aqi": 85, "type": "southern_sanctuary"},
    {"name": "Aya Nagar (Ridge Border), Delhi", "lat": 28.4700, "lon": 77.1100, "base_aqi": 80, "type": "south_ridge_forest"},
]

# Telemetry status cache for observability
_latest_telemetry_status: Dict[str, Any] = {
    "is_stale": False,
    "source": "none",
    "active_count": 0,
    "ingestion_mode": "uninitialized",
    "timestamp": None,
}


def pm25_to_aqi(pm25: float) -> float:
    """
    Converts PM2.5 concentration (ug/m3) to Indian National AQI (CPCB standard).
    """
    if pm25 <= 0:
        return 10.0
    elif pm25 <= 30.0:
        return (pm25 / 30.0) * 50.0
    elif pm25 <= 60.0:
        return 50.0 + ((pm25 - 30.0) / 30.0) * 50.0
    elif pm25 <= 90.0:
        return 100.0 + ((pm25 - 60.0) / 30.0) * 100.0
    elif pm25 <= 120.0:
        return 200.0 + ((pm25 - 90.0) / 30.0) * 100.0
    elif pm25 <= 250.0:
        return 300.0 + ((pm25 - 120.0) / 130.0) * 100.0
    else:
        return min(500.0, 400.0 + ((pm25 - 250.0) / 130.0) * 100.0)


def calculate_seasonal_baseline_factor(dt: Optional[datetime.datetime] = None) -> float:
    """
    Calculates the climatological seasonal harmonic scaling factor for Delhi NCT.
    - Winter peak (Nov-Jan, DOY ~325): factor 1.30 - 1.75 (severe smog, low BLH, stubble)
    - Monsoon low (July-Sept, DOY ~230): factor 0.35 - 0.50 (rain washout, clean air)
    - Pre-monsoon/Summer (April-June, DOY ~130): factor 0.80 - 1.05 (convective mixing, dust)
    - Post-winter/Spring (Feb-March, DOY ~75): factor 0.70 - 0.90
    """
    if dt is None:
        dt = datetime.datetime.now()
    doy = dt.timetuple().tm_yday

    f_winter = math.exp(-((doy - 325) / 45.0) ** 2) + math.exp(-((doy - (325 - 365)) / 45.0) ** 2) + math.exp(-((doy - (325 + 365)) / 45.0) ** 2)
    f_monsoon = math.exp(-((doy - 230) / 40.0) ** 2)
    f_summer = math.exp(-((doy - 130) / 35.0) ** 2)

    factor = 0.85 + 0.80 * f_winter - 0.45 * f_monsoon + 0.10 * f_summer
    return float(max(0.35, min(1.75, factor)))


def dynamic_climatological_meteorological_estimate(
    weather_summary: Optional[Dict[str, float]] = None,
    dt: Optional[datetime.datetime] = None
) -> List[Tuple[float, float, float]]:
    """
    Dynamic Climatological & Meteorological Estimator (DCME).
    Provides physics-grounded, microclimate-differentiated baseline AQI values
    during sensor feed interruptions, eliminating ungrounded drift.
    """
    if dt is None:
        dt = datetime.datetime.now()
    
    season_factor = calculate_seasonal_baseline_factor(dt)
    hour = dt.hour

    # Diurnal rush hour harmonic
    if 8 <= hour <= 11 or 18 <= hour <= 22:
        rush_mod = 1.12
    elif 1 <= hour <= 5:
        rush_mod = 0.88
    else:
        rush_mod = 1.0

    # Meteorological modulation from live Open-Meteo parameters
    meteo_mod = 1.0
    if weather_summary:
        wind_speed = weather_summary.get("wind_speed", 6.0)
        blh = weather_summary.get("blh", 500.0)
        humidity = weather_summary.get("humidity", 55.0)

        # High wind speed dilutes pollution; stagnant air accumulates
        wind_factor = (6.0 / max(2.0, wind_speed)) ** 0.35
        # Low boundary layer height traps pollutants (inversion)
        blh_factor = (600.0 / max(150.0, blh)) ** 0.25
        # High humidity during monsoon promotes wet deposition/washout
        rh_factor = 0.90 if (humidity > 75.0 and 6 <= dt.month <= 9) else 1.0

        meteo_mod = max(0.70, min(1.40, wind_factor * blh_factor * rh_factor))

    points = []
    for st in DELHI_STATIONS_BASELINE:
        # Base emission load scaled by season, meteorology, and diurnal cycle
        est_aqi = st["base_aqi"] * season_factor * meteo_mod * rush_mod
        # Bound strictly within realistic physical range
        est_aqi = max(25.0, min(450.0, est_aqi))
        points.append((st["lat"], st["lon"], round(est_aqi, 1)))

    return points


def fetch_openaq_telemetry() -> List[Tuple[float, float, float]]:
    """
    Fetches real-time sensor measurements from OpenAQ v3 API for Delhi stations.
    Returns valid [(lat, lon, aqi), ...] points.
    """
    points: List[Tuple[float, float, float]] = []
    if not OPENAQ_API_KEY or OPENAQ_API_KEY == "your_openaq_api_key_here":
        return points

    headers = {"X-API-Key": OPENAQ_API_KEY}
    bbox_url = "https://api.openaq.org/v3/locations?bbox=76.84,28.40,77.35,28.88&limit=25"

    try:
        resp = requests.get(bbox_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            locations = resp.json().get("results", [])
            logger.info(f"OpenAQ returned {len(locations)} monitoring locations in Delhi NCR.")

            now_utc = datetime.datetime.now(datetime.timezone.utc)

            for loc in locations:
                loc_id = loc.get("id")
                coords = loc.get("coordinates", {})
                lat = coords.get("latitude")
                lon = coords.get("longitude")
                if not lat or not lon:
                    continue

                try:
                    latest_url = f"https://api.openaq.org/v3/locations/{loc_id}/latest"
                    l_resp = requests.get(latest_url, headers=headers, timeout=6)
                    if l_resp.status_code == 200:
                        measurements = l_resp.json().get("results", [])
                        for m in measurements:
                            # Check timestamp freshness (within 24 hours)
                            dt_str = m.get("datetime", {}).get("utc")
                            val = m.get("value")
                            if val is not None and dt_str:
                                dt_meas = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                                age_hours = (now_utc - dt_meas).total_seconds() / 3600.0

                                if age_hours <= 18.0:
                                    # Convert PM2.5/PM10 measurement to CPCB AQI
                                    # OpenAQ typically measures in ug/m3
                                    aqi_val = pm25_to_aqi(float(val)) if val < 300 else float(val)
                                    if 15.0 <= aqi_val <= 600.0:
                                        points.append((float(lat), float(lon), round(aqi_val, 1)))
                                        break
                except Exception:
                    continue

    except Exception as e:
        logger.warning(f"OpenAQ live query encountered error: {e}")

    return points


def fetch_live_waqi_telemetry(weather_summary: Optional[Dict[str, float]] = None) -> List[Tuple[float, float, float]]:
    """
    Fetches real-time AQI readings across Delhi NCT from WAQI & OpenAQ APIs.
    Detects data stream staleness and seamlessly switches to the Dynamic
    Climatological & Meteorological Estimator (DCME) to prevent drift.
    """
    global _latest_telemetry_status
    points: List[Tuple[float, float, float]] = []
    now_dt = datetime.datetime.now()

    # 1. Try WAQI API
    if WAQI_API_TOKEN and WAQI_API_TOKEN != "your_waqi_api_token_here":
        try:
            url = f"https://api.waqi.info/map/bounds/?latlng=28.40,76.84,28.88,77.35&token={WAQI_API_TOKEN}"
            logger.info("Requesting live CPCB station data from WAQI API...")
            resp = requests.get(url, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "ok":
                    stations = data.get("data", [])
                    logger.info(f"Received {len(stations)} stations from WAQI.")

                    for st in stations:
                        try:
                            lat = float(st.get("lat"))
                            lon = float(st.get("lon"))
                            raw_aqi = st.get("aqi")

                            if raw_aqi is not None and raw_aqi != "-" and raw_aqi != "":
                                aqi = float(raw_aqi)
                                if 10.0 <= aqi <= 750.0:
                                    points.append((lat, lon, aqi))
                        except (ValueError, TypeError):
                            continue

                    if len(points) >= 8:
                        logger.info(f"Successfully ingested {len(points)} fresh live WAQI stations.")
                        _latest_telemetry_status = {
                            "is_stale": False,
                            "source": "WAQI_Live",
                            "active_count": len(points),
                            "ingestion_mode": "live_telemetry",
                            "timestamp": now_dt.isoformat()
                        }
                        return points
                    else:
                        logger.warning(f"WAQI returned only {len(points)} valid non-empty station feeds (stale/missing).")
        except Exception as e:
            logger.error(f"Error fetching from WAQI API: {e}.")

    # 2. Try OpenAQ live telemetry as high-fidelity fallback
    if len(points) < 8 and OPENAQ_API_KEY:
        logger.info("Attempting secondary live ingestion via OpenAQ API...")
        openaq_points = fetch_openaq_telemetry()
        if len(openaq_points) >= 4:
            logger.info(f"Successfully ingested {len(openaq_points)} fresh OpenAQ stations.")
            points.extend(openaq_points)

    if len(points) >= 6:
        _latest_telemetry_status = {
            "is_stale": False,
            "source": "OpenAQ_Live",
            "active_count": len(points),
            "ingestion_mode": "live_telemetry",
            "timestamp": now_dt.isoformat()
        }
        return points

    # 3. Dynamic Climatological & Meteorological Estimator (DCME) Fallback
    logger.info("Upstream sensor feeds are stale or interrupted. Activating Dynamic Climatological & Meteorological Estimator (DCME)...")
    points = dynamic_climatological_meteorological_estimate(weather_summary=weather_summary, dt=now_dt)

    _latest_telemetry_status = {
        "is_stale": True,
        "source": "DCME_Climatological_Physics",
        "active_count": len(points),
        "ingestion_mode": "adaptive_climatological_fallback",
        "staleness_reason": "Upstream feeds unavailable or returning '-'",
        "timestamp": now_dt.isoformat(),
        "seasonal_factor": round(calculate_seasonal_baseline_factor(now_dt), 3)
    }

    mean_aqi = sum(p[2] for p in points) / len(points)
    logger.info(f"DCME generated {len(points)} meteorology-calibrated station readings (Mean NCT AQI: {mean_aqi:.1f}).")
    return points


def get_telemetry_status() -> Dict[str, Any]:
    """Returns the health and staleness metadata of the latest ingestion cycle."""
    return _latest_telemetry_status
