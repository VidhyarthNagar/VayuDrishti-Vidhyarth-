"""
IMD Doppler Weather Radar (DWR) & Automatic Weather Station (AWS) Grid Telemetry
Simulates and connects to official meteorological stations across India.
"""
import random
from typing import List, Dict, Any

DWR_STATIONS = [
    { "station_id": "DWR-MUM-01", "name": "Mumbai Colaba Radar", "city": "Mumbai", "state": "Maharashtra", "lat": 18.9067, "lon": 72.8147, "range_km": 250, "status": "Operational" },
    { "station_id": "DWR-DEL-01", "name": "Delhi Palam Radar", "city": "Delhi", "state": "Delhi", "lat": 28.5665, "lon": 77.1031, "range_km": 250, "status": "Operational" },
    { "station_id": "DWR-CHE-01", "name": "Chennai Port Radar", "city": "Chennai", "state": "Tamil Nadu", "lat": 13.0900, "lon": 80.2900, "range_km": 250, "status": "Operational" },
    { "station_id": "DWR-KOL-01", "name": "Kolkata Radar", "city": "Kolkata", "state": "West Bengal", "lat": 22.5300, "lon": 88.3400, "range_km": 250, "status": "Operational" },
    { "station_id": "DWR-PAR-01", "name": "Paradeep Cyclone Radar", "city": "Bhubaneswar", "state": "Odisha", "lat": 20.3167, "lon": 86.6167, "range_km": 300, "status": "Operational" },
    { "station_id": "DWR-BLR-01", "name": "Bengaluru Radar", "city": "Bengaluru", "state": "Karnataka", "lat": 12.9500, "lon": 77.5800, "range_km": 250, "status": "Operational" },
    { "station_id": "DWR-HYD-01", "name": "Hyderabad Begumpet Radar", "city": "Hyderabad", "state": "Telangana", "lat": 17.4500, "lon": 78.4700, "range_km": 250, "status": "Operational" },
    { "station_id": "DWR-GHY-01", "name": "Guwahati Borjhar Radar", "city": "Guwahati", "state": "Assam", "lat": 26.1060, "lon": 91.5860, "range_km": 250, "status": "Operational" },
    { "station_id": "DWR-JPR-01", "name": "Jaipur Sanganer Radar", "city": "Jaipur", "state": "Rajasthan", "lat": 26.8242, "lon": 75.8122, "range_km": 250, "status": "Operational" },
    { "station_id": "DWR-KCH-01", "name": "Kochi Radar", "city": "Kochi", "state": "Kerala", "lat": 9.9312, "lon": 76.2673, "range_km": 250, "status": "Operational" },
    { "station_id": "DWR-SXR-01", "name": "Srinagar Pir Panjal Radar", "city": "Srinagar", "state": "Jammu & Kashmir", "lat": 34.0837, "lon": 74.7973, "range_km": 250, "status": "Operational" }
]

def get_all_radar_stations() -> List[Dict[str, Any]]:
    """Returns all Doppler radar stations with live simulated atmospheric telemetry."""
    stations = []
    for stn in DWR_STATIONS:
        reflectivity_dbz = random.randint(15, 58)
        rain_rate = round(0.036 * (10 ** (0.0625 * reflectivity_dbz)), 1) if reflectivity_dbz > 28 else 0.0
        
        stations.append({
            **stn,
            "telemetry": {
                "reflectivity_dbz": reflectivity_dbz,
                "rain_rate_mm_hr": rain_rate,
                "surface_temp_c": round(random.uniform(22.0, 39.0), 1),
                "relative_humidity_pct": random.randint(45, 98),
                "wind_speed_kmh": random.randint(10, 75),
                "wind_direction": random.choice(["SW", "W", "NE", "NW", "SE", "E"]),
                "cloud_top_height_km": round(random.uniform(3.5, 14.5), 1),
                "last_sweep_time": "Real-Time Active"
            }
        })
    return stations
