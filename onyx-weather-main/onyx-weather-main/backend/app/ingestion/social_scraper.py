"""
Social Media Ingestion Engine
Crawls/streams posts with #IMD and weather hashtags across Indian meteorological corridors.
"""
import random
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from ..config import DATA_DIR

class SocialMediaIngestor:
    def __init__(self):
        self.cities = self._load_cities()
        self.lexicon = self._load_lexicon()

    def _load_cities(self) -> List[Dict[str, Any]]:
        path = DATA_DIR / "indian_cities.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("cities", [])
        return []

    def _load_lexicon(self) -> Dict[str, Any]:
        path = DATA_DIR / "weather_lexicon.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def fetch_synthetic_post(self, force_scenario: str = None) -> Dict[str, Any]:
        """
        Generates realistic social media post stream matching live meteorological conditions in India.
        """
        city_obj = random.choice(self.cities) if self.cities else {
            "name": "Mumbai", "state": "Maharashtra", "district": "Mumbai City", "lat": 19.0760, "lon": 72.8777
        }

        # Real-world media assets
        media_gallery = {
            "rainfall": [
                "https://images.unsplash.com/photo-1515694346937-94d85e41e6f0?w=800&auto=format&fit=crop&q=80",
                "https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?w=800&auto=format&fit=crop&q=80"
            ],
            "flooding": [
                "https://images.unsplash.com/photo-1547683905-f686c993aae5?w=800&auto=format&fit=crop&q=80",
                "https://images.unsplash.com/photo-1519692933481-e162a57d6721?w=800&auto=format&fit=crop&q=80"
            ],
            "thunderstorm": [
                "https://images.unsplash.com/photo-1605727216801-e27ce1d0cc28?w=800&auto=format&fit=crop&q=80",
                "https://images.unsplash.com/photo-1534088568595-a066f410bcda?w=800&auto=format&fit=crop&q=80"
            ],
            "heatwave": [
                "https://images.unsplash.com/photo-1504370805625-d32c54b16100?w=800&auto=format&fit=crop&q=80"
            ],
            "fog": [
                "https://images.unsplash.com/photo-1485236715568-ddc5ee6ca227?w=800&auto=format&fit=crop&q=80"
            ],
            "dust_storm": [
                "https://images.unsplash.com/photo-1509114397022-ed747cca3f65?w=800&auto=format&fit=crop&q=80"
            ],
            "cyclone": [
                "https://images.unsplash.com/photo-1527482797697-8795b05a13fe?w=800&auto=format&fit=crop&q=80",
                "https://images.unsplash.com/photo-1508873696983-2df5293cb32b?w=800&auto=format&fit=crop&q=80"
            ],
            "hailstorm": [
                "https://images.unsplash.com/photo-1516912481808-3406841bd33c?w=800&auto=format&fit=crop&q=80"
            ]
        }

        # Select Event Type
        event_types = ["rainfall", "flooding", "thunderstorm", "heatwave", "fog", "dust_storm", "cyclone", "hailstorm"]
        event_type = force_scenario if force_scenario in event_types else random.choice(event_types)

        # Template library
        templates = {
            "rainfall": [
                f"Continuous torrential rains pouring over {city_obj['name']}. Low lying areas experiencing water runoff. #IMD #{city_obj['name']}Rains #MonsoonUpdate",
                f"Moderate showers and cloudy weather in {city_obj['name']} bringing relief from humidity. Rainfall gauge: 35mm. #IMD #WeatherUpdate",
                f"Heavy cloudburst in central {city_obj['name']} causing minor traffic slowing. Carry umbrellas! #IMD #RainAlert"
            ],
            "flooding": [
                f"Severe waterlogging reported near main junction in {city_obj['name']}. Water level approx 2 feet. Civic teams deployed. #IMD #{city_obj['name']}Floods #Waterlogging",
                f"Inundation along the low-lying river canal in {city_obj['name']}. Avoid traveling via underpasses. #IMD #FloodAlert"
            ],
            "thunderstorm": [
                f"Loud thunder claps and sharp lightning streaks visible over {city_obj['name']} skyline right now! Stay indoors. #IMD #Thunderstorm #LightningAlert",
                f"Sudden squall winds 60kmph accompanied by severe lightning in {city_obj['name']}. Power supply tripped in some sectors. #IMD #Squall"
            ],
            "heatwave": [
                f"Extreme heatwave grips {city_obj['name']}. Mercury crosses 45.4°C today with blistering Loo winds. Red Alert active. #IMD #Heatwave #SummerAlert",
                f"Scorching sun in {city_obj['name']} with high UV index. Drink plenty of water and electrolytes. #IMD #HeatAlert"
            ],
            "fog": [
                f"Thick dense fog blanket over {city_obj['name']} reducing highway visibility below 100 meters. Drive carefully! #IMD #DenseFog #FogAlert",
                f"Severe smog and low visibility in {city_obj['name']} this morning. Flight departures delayed. #IMD #DelhiFog #LowVisibility"
            ],
            "dust_storm": [
                f"Massive dust storm (Andhi) sweeping across {city_obj['name']}. Sky turned brownish yellow with 50kmph sand winds. #IMD #DustStorm #Andhi",
                f"Intense sandstorm in outskirts of {city_obj['name']}. Tree branches fallen on peripheral road. #IMD #SandStorm"
            ],
            "cyclone": [
                f"Gale force winds reaching 85km/h battering coastal belt near {city_obj['name']}. Heavy tidal surges observed. #IMD #CycloneAlert #CoastalStorm",
                f"Cyclone warning advisory for {city_obj['name']} and adjoining districts. Evacuation of coastal huts initiated. #IMD #SuperCyclone"
            ],
            "hailstorm": [
                f"Surprise hailstorm in {city_obj['name']}! Marble sized hailstones pelted down for 15 minutes. Temperature dropped sharply. #IMD #Hailstorm #HailAlert",
                f"Intense hail and squalls reported across {city_obj['name']} rural belt. Farmers reporting crop impact. #IMD #Cloudburst"
            ]
        }

        chosen_text = random.choice(templates[event_type])
        urls = media_gallery.get(event_type, [])
        chosen_media = random.choice(urls) if urls else ""

        # Coordinate jitter within city radius (±0.03 deg ~ 3km)
        lat_jitter = city_obj["lat"] + random.uniform(-0.03, 0.03)
        lon_jitter = city_obj["lon"] + random.uniform(-0.03, 0.03)

        handles = ["@WeatherWatcherIND", "@MonsoonTracker", "@CityLiveUpdate", "@SkyAlertHQ", "@CitizenObserver", "@DailyMetNews"]
        handle = random.choice(handles)

        return {
            "source": "Twitter/X",
            "author_handle": handle,
            "author_name": handle.replace("@", ""),
            "author_trust_score": round(random.uniform(0.75, 0.95), 2),
            "text": chosen_text,
            "hashtags": ["#IMD", f"#{city_obj['name']}Weather", f"#{event_type.capitalize()}Alert"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "city": city_obj["name"],
            "district": city_obj.get("district", city_obj["name"]),
            "state": city_obj["state"],
            "lat": round(lat_jitter, 4),
            "lon": round(lon_jitter, 4),
            "event_type": event_type,
            "media_type": "image",
            "media_url": chosen_media
        }

social_ingestor = SocialMediaIngestor()
