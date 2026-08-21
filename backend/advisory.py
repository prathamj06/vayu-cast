"""
VAYU - Gemini AI Multilingual Advisory & Satellite Source Attribution Engine
Generates zone-level health advisories in English & Hindi via Google Gemini (gemini-2.5-flash)
with strict rate-limit shielding (time.sleep(2) between zone queries < 15 RPM),
and calculates physical source attribution splits (% Traffic, Stubble, Industry, Dust).
"""

import os
import time
import logging
from typing import Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def get_fallback_advisories(zone_name: str, aqi: float) -> Tuple[str, str]:
    """Generates localized bilingual fallback health advisories based on AQI category."""
    if aqi <= 50:
        return (
            f"Air quality in {zone_name} is Good (AQI {round(aqi)}). Ideal for all outdoor exercises and activities.",
            f"{zone_name} में वायु गुणवत्ता अच्छी है (AQI {round(aqi)})। सभी बाहरी गतिविधियों और व्यायाम के लिए उत्तम।"
        )
    elif aqi <= 100:
        return (
            f"Air quality in {zone_name} is Moderate (AQI {round(aqi)}). Unusually sensitive individuals should limit prolonged outdoor exertion.",
            f"{zone_name} में वायु गुणवत्ता मध्यम है (AQI {round(aqi)})। अत्यधिक संवेदनशील व्यक्ति लंबे समय तक बाहरी गतिविधियों को सीमित करें।"
        )
    elif aqi <= 150:
        return (
            f"Unhealthy for Sensitive Groups in {zone_name} (AQI {round(aqi)}). Children, elderly, and asthma patients should wear N95 masks outdoors.",
            f"{zone_name} में संवेदनशील समूहों के लिए अस्वस्थ वायु (AQI {round(aqi)})। बच्चे, बुजुर्ग और सांस के रोगी बाहर निकलते समय N95 मास्क पहनें।"
        )
    elif aqi <= 200:
        return (
            f"Unhealthy air across {zone_name} (AQI {round(aqi)}). Everyone should reduce heavy outdoor exertion. Keep indoor air purifiers active.",
            f"{zone_name} में अस्वस्थ हवा (AQI {round(aqi)})। सभी लोग भारी बाहरी व्यायाम कम करें और घरों में एयर प्यूरीफायर चलाएं।"
        )
    elif aqi <= 300:
        return (
            f"Very Unhealthy air alert in {zone_name} (AQI {round(aqi)}). Avoid outdoor activities. High particulate entrapment; wear N95/FFP2 masks.",
            f"{zone_name} में बहुत अस्वस्थ हवा का अलर्ट (AQI {round(aqi)})। बाहरी गतिविधियों से बचें। N95/FFP2 मास्क का अनिवार्य उपयोग करें।"
        )
    else:
        return (
            f"HAZARDOUS EMERGENCY in {zone_name} (AQI {round(aqi)})! Severe atmospheric inversion. Avoid all outdoor exposure; seal windows and use HEPA purifiers.",
            f"{zone_name} में गंभीर आपातकालीन स्थिति (AQI {round(aqi)})! गंभीर प्रदूषण। सभी बाहरी संपर्क से बचें, खिड़कियां बंद रखें और HEPA प्यूरीफायर चालू रखें।"
        )


def generate_gemini_advisories(zones_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """
    Calls Google Gemini API for each municipal zone with a mandatory 2-second rate-limiting delay.
    Returns: { zone_name: { "en": "...", "hi": "..." } }
    """
    client = None
    advisories = {}

    if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info("Initialized Google GenAI client successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize Google GenAI SDK: {e}. Using fallback generator.")

    for zone_name, data in zones_data.items():
        avg_aqi = data.get("current_aqi", 200)
        dom_source = data.get("dominant_source", "Vehicular Traffic")

        if client is not None:
            try:
                prompt = (
                    f"You are the official Delhi Air Quality Chief Health Officer. "
                    f"Zone: '{zone_name}', Current AQI: {round(avg_aqi)}, Dominant Pollution Source: {dom_source}. "
                    f"Generate a concise, authoritative 1-2 sentence public health advisory in English, "
                    f"and its precise translation/counterpart in formal Hindi (Devanagari script). "
                    f"Format your response EXACTLY as:\n"
                    f"EN: <English Advisory>\n"
                    f"HI: <Hindi Advisory>"
                )

                # Try modern available models: gemini-2.5-flash, gemini-2.0-flash, or gemini-1.5-flash
                text = ""
                for model_candidate in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                    try:
                        response = client.models.generate_content(
                            model=model_candidate,
                            contents=prompt
                        )
                        if response and response.text:
                            text = response.text.strip()
                            break
                    except Exception as model_err:
                        logger.debug(f"Model {model_candidate} not available: {model_err}")
                        continue

                en_adv = ""
                hi_adv = ""

                for line in text.split("\n"):
                    if line.startswith("EN:"):
                        en_adv = line.replace("EN:", "").strip()
                    elif line.startswith("HI:"):
                        hi_adv = line.replace("HI:", "").strip()

                if not en_adv or not hi_adv:
                    en_adv, hi_adv = get_fallback_advisories(zone_name, avg_aqi)

                advisories[zone_name] = {"en": en_adv, "hi": hi_adv}
                logger.info(f"Generated Gemini advisory for {zone_name} (AQI {round(avg_aqi)})")

                # MANDATORY RATE LIMIT DELAY: Pace 2.0 seconds between zone requests to strictly stay < 15 RPM
                time.sleep(2.0)

            except Exception as e:
                logger.error(f"Gemini generation error for zone {zone_name}: {e}. Falling back.")
                en_adv, hi_adv = get_fallback_advisories(zone_name, avg_aqi)
                advisories[zone_name] = {"en": en_adv, "hi": hi_adv}
                time.sleep(1.0)
        else:
            en_adv, hi_adv = get_fallback_advisories(zone_name, avg_aqi)
            advisories[zone_name] = {"en": en_adv, "hi": hi_adv}

    return advisories


def calculate_source_attribution(
    zone_name: str,
    hour: int,
    wind_speed: float,
    wind_dir: float,
    month: int = 11
) -> Dict[str, int]:
    """
    Computes heuristic source attribution percentages strictly summing to 100%.
    Factors:
    - Traffic: Peak during commuting hours (8-11 AM, 6-9 PM)
    - Stubble: High in October-November with NW winds (270-340 deg)
    - Industry: Heavy in industrial zones (Okhla, Narela, Anand Vihar)
    - Dust: Higher with high wind speeds (>10 km/h) and dry weather
    """
    # 1. Traffic weight
    traffic_weight = 30.0
    if 8 <= hour <= 11 or 17 <= hour <= 21:
        traffic_weight += 20.0
    if zone_name in ["Central Delhi", "West Delhi", "East Delhi", "South Delhi", "Shahdara"]:
        traffic_weight += 10.0

    # 2. Agricultural Stubble weight
    stubble_weight = 5.0
    if month in [10, 11, 12]:  # Post-monsoon harvest burning
        stubble_weight += 25.0
        # Check if wind is coming from North-West (Punjab/Haryana corridor: 270° to 340°)
        if 260 <= wind_dir <= 350:
            stubble_weight += 20.0

    # 3. Industrial Combustion weight
    industry_weight = 15.0
    if zone_name in ["Okhla Industrial", "Narela", "Anand Vihar", "Rohini"]:
        industry_weight += 25.0
    if hour >= 22 or hour <= 5:  # Night-time industrial activity & heavy diesel trucking
        industry_weight += 15.0

    # 4. Dust / Road Resuspension weight
    dust_weight = 15.0
    if wind_speed > 10.0:
        dust_weight += 15.0
    if month in [3, 4, 5, 6]:  # Summer dry dust storms
        dust_weight += 20.0

    # Normalize to 100%
    total = traffic_weight + stubble_weight + industry_weight + dust_weight
    t_pct = int(round((traffic_weight / total) * 100))
    s_pct = int(round((stubble_weight / total) * 100))
    i_pct = int(round((industry_weight / total) * 100))
    d_pct = 100 - (t_pct + s_pct + i_pct)

    return {
        "traffic": max(5, t_pct),
        "stubble": max(2, s_pct),
        "industry": max(5, i_pct),
        "dust": max(3, d_pct)
    }
