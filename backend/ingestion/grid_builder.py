"""
VAYU - Spatial Grid Mesh & IDW Interpolation Engine
Constructs Delhi's Uber H3 Resolution 8 Spatial Grid (~1,500 hexagons)
and maps non-uniform CPCB telemetry points onto hexagon centroids via IDW.
"""

import math
import logging
from typing import List, Dict, Tuple, Any
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# H3 compatibility wrapper (supports both h3-py v3 and v4)
try:
    import h3
    def geo_to_hex(lat: float, lon: float, res: int = 8) -> str:
        if hasattr(h3, 'geo_to_h3'):
            return h3.geo_to_h3(lat, lon, res)
        elif hasattr(h3, 'latlng_to_cell'):
            return h3.latlng_to_cell(lat, lon, res)
        raise AttributeError("No valid h3 geo-to-cell function found")

    def hex_to_geo(hex_id: str) -> Tuple[float, float]:
        if hasattr(h3, 'h3_to_geo'):
            return h3.h3_to_geo(hex_id)
        elif hasattr(h3, 'cell_to_latlng'):
            return h3.cell_to_latlng(hex_id)
        raise AttributeError("No valid h3 cell-to-latlng function found")
except ImportError:
    logger.warning("h3 module not installed. Using fallback synthetic hex generator.")
    h3 = None

# Delhi NCT Bounding Box & Municipal Zones
DELHI_BBOX = {
    "min_lat": 28.40,
    "max_lat": 28.88,
    "min_lon": 76.84,
    "max_lon": 77.35
}

DELHI_MUNICIPAL_ZONES = [
    {"name": "Anand Vihar", "lat": 28.6469, "lon": 77.3160, "type": "Transport/Industrial Hub"},
    {"name": "Rohini", "lat": 28.7495, "lon": 77.0565, "type": "Residential/Commercial"},
    {"name": "Dwarka", "lat": 28.5823, "lon": 77.0500, "type": "Suburban Hub"},
    {"name": "South Delhi", "lat": 28.5400, "lon": 77.2100, "type": "Urban Forest/Residential"},
    {"name": "Central Delhi", "lat": 28.6304, "lon": 77.2177, "type": "Commercial Core"},
    {"name": "North Delhi", "lat": 28.7100, "lon": 77.1800, "type": "University/Mixed Area"},
    {"name": "East Delhi", "lat": 28.6280, "lon": 77.2950, "type": "High Density Residential"},
    {"name": "West Delhi", "lat": 28.6500, "lon": 77.1200, "type": "Commercial/Industrial"},
    {"name": "Okhla Industrial", "lat": 28.5300, "lon": 77.2800, "type": "Heavy Industrial"},
    {"name": "IGI Airport", "lat": 28.5562, "lon": 77.1000, "type": "Aviation Zone"},
    {"name": "Narela", "lat": 28.8500, "lon": 77.0900, "type": "Border/Industrial Zone"},
    {"name": "Shahdara", "lat": 28.6738, "lon": 77.2915, "type": "High Density Mixed"},
]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def assign_zone(lat: float, lon: float) -> str:
    """Assigns the closest municipal zone name to a coordinate."""
    best_zone = DELHI_MUNICIPAL_ZONES[0]["name"]
    min_dist = float("inf")
    for zone in DELHI_MUNICIPAL_ZONES:
        dist = haversine_distance(lat, lon, zone["lat"], zone["lon"])
        if dist < min_dist:
            min_dist = dist
            best_zone = zone["name"]
    return best_zone


def generate_delhi_h3_grid(resolution: int = 8) -> List[Dict[str, Any]]:
    """
    Generates approx 1,500 Uber H3 hexagons covering NCT Delhi.
    Returns a list of dicts with hex_id, centroid [lat, lon], and zone_name.
    """
    hex_set = set()
    grid = []

    # Step sampling points within the Delhi bounding box
    lat_step = 0.008
    lon_step = 0.009

    lat_coords = np.arange(DELHI_BBOX["min_lat"], DELHI_BBOX["max_lat"], lat_step)
    lon_coords = np.arange(DELHI_BBOX["min_lon"], DELHI_BBOX["max_lon"], lon_step)

    for lat in lat_coords:
        for lon in lon_coords:
            if h3 is not None:
                try:
                    h_id = geo_to_hex(float(lat), float(lon), resolution)
                    if h_id not in hex_set:
                        hex_set.add(h_id)
                        c_lat, c_lon = hex_to_geo(h_id)
                        grid.append({
                            "hex_id": h_id,
                            "centroid": [round(float(c_lat), 5), round(float(c_lon), 5)],
                            "zone_name": assign_zone(c_lat, c_lon)
                        })
                except Exception as e:
                    logger.debug(f"H3 conversion error: {e}")
            else:
                # Fallback synthetic hex IDs
                fake_id = f"88{abs(int(lat*1000))}{abs(int(lon*1000))}ffff"
                if fake_id not in hex_set:
                    hex_set.add(fake_id)
                    grid.append({
                        "hex_id": fake_id,
                        "centroid": [round(float(lat), 5), round(float(lon), 5)],
                        "zone_name": assign_zone(lat, lon)
                    })

    logger.info(f"Generated {len(grid)} H3 Resolution {resolution} hexagons for Delhi NCR.")
    return grid


def idw_interpolation(
    target_points: List[Tuple[float, float]],
    station_points: List[Tuple[float, float, float]],
    power: float = 2.0
) -> List[float]:
    """
    Inverse Distance Weighting (IDW) interpolation.
    target_points: List of (lat, lon)
    station_points: List of (lat, lon, aqi_value)
    power: Distance weighting power (default p=2)
    Returns: List of interpolated AQI values for each target point.
    """
    if not station_points:
        return [150.0 for _ in target_points]

    results = []
    for t_lat, t_lon in target_points:
        weights_sum = 0.0
        weighted_val_sum = 0.0
        exact_match = None

        for s_lat, s_lon, val in station_points:
            dist = haversine_distance(t_lat, t_lon, s_lat, s_lon)
            if dist < 0.05:  # within 50m, direct match
                exact_match = val
                break
            w = 1.0 / (dist ** power)
            weights_sum += w
            weighted_val_sum += w * val

        if exact_match is not None:
            results.append(round(exact_match, 1))
        elif weights_sum > 0:
            results.append(round(weighted_val_sum / weights_sum, 1))
        else:
            results.append(150.0)

    return results
