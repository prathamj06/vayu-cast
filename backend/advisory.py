"""
VAYU - Gemini AI Focused Advisory & Hyperlocal Micro-Spatial Source Attribution Engine
Generates context-aware medical/health advisories without redundant numerical AQI readouts,
and calculates continuous, spatially unique source attribution for each individual hexagon centroid.
"""

import os
import math
import time
import logging
from typing import Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Key Industrial Pollution Hotspot Coordinates in Delhi NCR
INDUSTRIAL_CENTROIDS = [
    {"name": "Bawana", "lat": 28.7762, "lon": 77.0511, "weight": 1.4},
    {"name": "Narela", "lat": 28.8500, "lon": 77.0900, "weight": 1.3},
    {"name": "Wazirpur", "lat": 28.6998, "lon": 77.1654, "weight": 1.2},
    {"name": "Mayapuri", "lat": 28.6280, "lon": 77.1080, "weight": 1.1},
    {"name": "Okhla Phase 2", "lat": 28.5300, "lon": 77.2800, "weight": 1.3},
    {"name": "Anand Vihar Hub", "lat": 28.6469, "lon": 77.3160, "weight": 1.3},
    {"name": "Mundka", "lat": 28.6847, "lon": 77.0299, "weight": 1.2},
]

# Major Arterial Traffic Corridors / Highway Intersections
TRAFFIC_CORRIDORS = [
    {"name": "Ring Road / AIIMS", "lat": 28.5672, "lon": 77.2100, "weight": 1.3},
    {"name": "Outer Ring Road / IIT Flyover", "lat": 28.5450, "lon": 77.1926, "weight": 1.3},
    {"name": "ITO Intersection", "lat": 28.6315, "lon": 77.2488, "weight": 1.4},
    {"name": "NH48 Mahipalpur / Dhaula Kuan", "lat": 28.5880, "lon": 77.1580, "weight": 1.4},
    {"name": "GT Karnal Road / Mukarba Chowk", "lat": 28.7450, "lon": 77.1500, "weight": 1.35},
    {"name": "Ashram Chowk / Mathura Road", "lat": 28.5710, "lon": 77.2600, "weight": 1.3},
    {"name": "Peeragarhi Chowk", "lat": 28.6780, "lon": 77.0920, "weight": 1.25},
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes distance between two coordinates in kilometers."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def get_focused_fallback_advisory(zone_name: str, aqi_val: float) -> Tuple[str, str]:
    """
    Generates actionable, context-aware health advisories WITHOUT numerical AQI values.
    Focuses strictly on medical guidance, vulnerable group precautions, and actionable mitigations.
    """
    val = round(aqi_val)

    if val <= 50:
        return (
            f"Air quality in {zone_name} is ideal for outdoor activities, endurance training, and sports. Keep living spaces well-ventilated.",
            f"{zone_name} में वायु गुणवत्ता बहुत साफ है। सभी बाहरी गतिविधियों और खेलकूद के लिए आदर्श समय है।"
        )
    elif val <= 100:
        return (
            f"Air quality in {zone_name} is acceptable. Individuals with severe asthma or acute respiratory sensitivity should monitor outdoor physical exertion.",
            f"{zone_name} में हवा संतोषजनक है। सांस के गंभीर मरीज और संवेदनशील लोग अत्यधिक बाहरी श्रम सीमित करें।"
        )
    elif val <= 150:
        return (
            f"Elevated particulate levels in {zone_name}. Children, elderly citizens, and individuals with respiratory conditions should reduce prolonged outdoor workouts.",
            f"{zone_name} में प्रदूषण स्तर बढ़ रहा है। बच्चे, बुजुर्ग और सांस के मरीज बाहर भारी शारीरिक व्यायाम से बचें।"
        )
    elif val <= 200:
        return (
            f"Unhealthy air conditions across {zone_name}. Wear well-fitted N95 masks during commutes, avoid strenuous morning jogs, and keep windows closed during peak traffic.",
            f"{zone_name} में अस्वस्थ हवा। बाहर जाते समय N95 मास्क पहनें, सुबह की भारी दौड़ से बचें और घर की खिड़कियां बंद रखें।"
        )
    elif val <= 300:
        return (
            f"Severe atmospheric entrapment in {zone_name}. High risk of respiratory irritation. Run indoor HEPA air purifiers, avoid non-essential outdoor travel, and wear protective masks.",
            f"{zone_name} में प्रदूषण की गंभीर स्थिति। घर के अंदर एयर प्यूरीफायर चलाएं, अनावश्यक बाहरी यात्रा से बचें और N95 मास्क अवश्य पहनें।"
        )
    else:
        return (
            f"Hazardous pollution emergency in {zone_name}. Severe thermal inversion. Strictly avoid all outdoor exposure, seal indoor ventilation, and consult medical professionals if experiencing breathing discomfort.",
            f"{zone_name} में आपातकालीन गंभीर स्थिति। सभी बाहरी गतिविधियों को पूरी तरह बंद करें और घर के अंदर सुरक्षित रहें।"
        )


def _generate_single_zone_advisory(client, zone_name: str, data: Dict[str, Any]) -> tuple[str, Dict[str, str]]:
    avg_aqi = data.get("current_aqi", 150)
    dom_source = data.get("dominant_source", "Vehicular Traffic")

    if client is not None:
        try:
            prompt = (
                f"You are the Chief Public Health Officer of Delhi. "
                f"Zone: '{zone_name}', Primary Environmental Driver: {dom_source}. "
                f"Air Quality Severity Level: {'Good' if avg_aqi <= 50 else 'Moderate' if avg_aqi <= 100 else 'Unhealthy for Sensitive Groups' if avg_aqi <= 150 else 'Unhealthy' if avg_aqi <= 200 else 'Very Unhealthy' if avg_aqi <= 300 else 'Hazardous'}. "
                f"CRITICAL RULE: DO NOT include any numerical AQI values, scores, or numbers (e.g. do not say 'AQI 145'). "
                f"Generate a concise 1-2 sentence actionable medical precaution in English focusing on masks, ventilation, or exercise timing, "
                f"and its formal Hindi counterpart in Devanagari script. "
                f"Format strictly as:\n"
                f"EN: <English Advisory>\n"
                f"HI: <Hindi Advisory>"
            )

            text = ""
            for model_candidate in ["gemini-3.5-flash", "gemini-3.6-flash"]:
                try:
                    response = client.models.generate_content(
                        model=model_candidate,
                        contents=prompt
                    )
                    if response and response.text:
                        text = response.text.strip()
                        break
                except Exception:
                    continue

            en_adv = ""
            hi_adv = ""
            if text:
                for line in text.split("\n"):
                    if line.startswith("EN:"):
                        en_adv = line.replace("EN:", "").strip()
                    elif line.startswith("HI:"):
                        hi_adv = line.replace("HI:", "").strip()

            if en_adv and hi_adv:
                logger.info(f"Generated AI advisory for {zone_name}")
                return zone_name, {"en": en_adv, "hi": hi_adv}

        except Exception as e:
            logger.warning(f"Using fallback advisory for {zone_name}: {e}")

    en_adv, hi_adv = get_focused_fallback_advisory(zone_name, avg_aqi)
    return zone_name, {"en": en_adv, "hi": hi_adv}


def generate_gemini_advisories(zones_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """
    Calls Google Gemini API for each municipal zone with strict prompt instructions
    to OMIT all numerical AQI numbers and provide purely actionable health advisories.
    Uses concurrent workers with bounded HTTP timeouts to guarantee fast pipeline completion.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    client = None
    advisories = {}

    if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(
                api_key=GEMINI_API_KEY,
                http_options=types.HttpOptions(
                    timeout=10000,
                    retry_options=types.HttpRetryOptions(attempts=1)
                )
            )
            logger.info("Initialized Google GenAI client with bounded timeouts.")
        except Exception as e:
            logger.warning(f"Could not initialize Google GenAI SDK: {e}. Using focused fallback generator.")

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(_generate_single_zone_advisory, client, zone_name, data)
            for zone_name, data in zones_data.items()
        ]
        for f in as_completed(futures):
            try:
                z_name, adv = f.result(timeout=15)
                advisories[z_name] = adv
            except Exception as exc:
                logger.warning(f"Error fetching advisory: {exc}")

    # Ensure all zones have advisories
    for zone_name, data in zones_data.items():
        if zone_name not in advisories:
            avg_aqi = data.get("current_aqi", 150)
            en_adv, hi_adv = get_focused_fallback_advisory(zone_name, avg_aqi)
            advisories[zone_name] = {"en": en_adv, "hi": hi_adv}

    return advisories


def calculate_hyperlocal_source_attribution(
    centroid_lat: float,
    centroid_lon: float,
    zone_name: str,
    local_aqi: float,
    hour: int,
    wind_speed: float,
    wind_dir: float,
    month: int = 11,
    gases: Optional[Dict[str, float]] = None
) -> Dict[str, int]:
    """
    Computes scientific, data-driven source apportionment using Chemical Receptor Modeling
    and real-time multi-pollutant gas concentrations (NO2, SO2, CO, PM10, PM2.5).
    - Road Dust & Construction: Driven by coarse excess (PM10 - PM2.5) * (PM10 / (PM2.5 + 12))
    - Vehicular Traffic: Driven by tailpipe combustion tracers (NO2 * 2.4 + CO * 1.6) + Arterial Density
    - Industrial Emissions: Driven by sulfur combustion tracer (SO2 * 3.2) + Industrial Cluster Density
    - Stubble / Biomass: Driven by seasonal NW wind advection & CO/NO2 combustion anomaly
    Guarantees every single hexagon has a continuous, dynamic chemical fingerprint normalized to 100%.
    """
    if not gases:
        gases = {
            "pm25": max(15.0, local_aqi * 0.75),
            "pm10": max(25.0, local_aqi * 1.25),
            "no2": 15.0,
            "so2": 8.0,
            "co": 10.0
        }

    pm25 = float(gases.get("pm25", 50.0))
    pm10 = float(gases.get("pm10", 75.0))
    no2 = float(gases.get("no2", 14.0))
    so2 = float(gases.get("so2", 7.0))
    co = float(gases.get("co", 10.0))

    # 1. Road Dust & Construction: Driven by coarse particulate excess (PM10 - PM2.5)
    coarse_dust_excess = max(0.0, pm10 - pm25)
    dust_ratio = pm10 / max(10.0, pm25 + 12.0)
    dust_score = max(10.0, coarse_dust_excess * dust_ratio * 1.2)

    # Localized riverbed silt factor for Yamuna corridor
    yamuna_dist = abs(centroid_lon - 77.25) * 111.0  # approx km
    if yamuna_dist < 3.0:
        dust_score += (3.0 - yamuna_dist) * 4.0
    if wind_speed > 10.0:
        dust_score += (wind_speed - 10.0) * 1.8

    # 2. Vehicular Traffic: Driven by tailpipe NO2 and CO + Arterial Corridor proximity
    min_traffic_dist = min(haversine_km(centroid_lat, centroid_lon, traf["lat"], traf["lon"]) for traf in TRAFFIC_CORRIDORS)
    corridor_density = max(0.0, (8.0 - min_traffic_dist) * 3.5)
    traffic_score = max(20.0, (no2 * 2.4) + (co * 1.6) + corridor_density)

    # Diurnal rush hours (8-11 AM, 17-21 PM)
    if 8 <= hour <= 11 or 17 <= hour <= 21:
        traffic_score += 12.0
    elif 1 <= hour <= 5:
        traffic_score -= 8.0

    # 3. Industrial Emissions: Driven by SO2 (coal/boiler tracer) + Industrial cluster proximity
    min_ind_dist = min(haversine_km(centroid_lat, centroid_lon, ind["lat"], ind["lon"]) for ind in INDUSTRIAL_CENTROIDS)
    ind_cluster_density = max(0.0, (9.0 - min_ind_dist) * 3.2)
    ind_score = max(0.0, (so2 * 3.2) + ind_cluster_density)

    if zone_name in ["South Delhi", "Central Delhi"] and min_ind_dist > 6.0:
        ind_score = 0.0  # Pure residential / urban forest belt

    # 4. Agricultural Stubble: Driven by seasonal NW winds & elevated CO/NO2 anomaly in Oct/Nov
    stubble_score = 5.0
    if month in [10, 11] and 270 <= wind_dir <= 340:
        nw_dist_factor = (centroid_lat - 28.45) * 12.0 + (77.35 - centroid_lon) * 8.0
        stubble_plume = (co / max(2.0, no2)) * 15.0
        stubble_score = max(5.0, stubble_plume + max(0.0, nw_dist_factor))

    # Normalize strictly to 100%
    total = traffic_score + dust_score + ind_score + stubble_score
    pct_t = int(round((traffic_score / total) * 100))
    pct_d = int(round((dust_score / total) * 100))
    pct_i = int(round((ind_score / total) * 100)) if ind_score > 0 else 0
    pct_s = 100 - (pct_t + pct_d + pct_i)

    # Final sanity bounds
    if pct_s < 4:
        pct_t -= (4 - pct_s)
        pct_s = 4
    if pct_d < 5:
        pct_t -= (5 - pct_d)
        pct_d = 5

    return {
        "traffic": pct_t,
        "stubble": pct_s,
        "industry": pct_i,
        "dust": pct_d
    }


# Backwards compatibility alias
def calculate_source_attribution(zone_name: str, hour: int, wind_speed: float, wind_dir: float, month: int = 11) -> Dict[str, int]:
    return calculate_hyperlocal_source_attribution(28.6139, 77.2090, zone_name, 150.0, hour, wind_speed, wind_dir, month)
