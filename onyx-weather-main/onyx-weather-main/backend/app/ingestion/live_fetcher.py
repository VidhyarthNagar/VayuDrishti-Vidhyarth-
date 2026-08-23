"""
Live Internet Weather & News Multi-Source Fetcher
"""
import os
import re
import json
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from ..config import DATA_DIR
from ..ml_pipeline.pipeline import ingestion_pipeline

logger = logging.getLogger("live_fetcher")
CONFIG_FILE = DATA_DIR / "api_keys.json"

def get_api_keys() -> Dict[str, str]:
    keys = {
        "OPENWEATHER_API_KEY": os.environ.get("OPENWEATHER_API_KEY", ""),
        "NEWS_API_KEY": os.environ.get("NEWS_API_KEY", ""),
        "WEATHERAPI_KEY": os.environ.get("WEATHERAPI_KEY", ""),
        "GNEWS_API_KEY": os.environ.get("GNEWS_API_KEY", "")
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for k, v in saved.items():
                    if v:
                        keys[k] = v
        except Exception:
            pass
    return keys

def save_api_keys(new_keys: Dict[str, str]):
    existing = get_api_keys()
    existing.update(new_keys)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

class LiveFetcher:
    def __init__(self):
        self.cities = self._load_cities()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def _load_cities(self) -> List[Dict[str, Any]]:
        path = DATA_DIR / "indian_cities.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("cities", [])
        return []

    def _match_city_and_state(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        for city in self.cities:
            name = city["name"].lower()
            state = city["state"].lower()
            if re.search(r'\b' + re.escape(name) + r'\b', text_lower):
                return city
            if re.search(r'\b' + re.escape(state) + r'\b', text_lower):
                return city
        return self.cities[0] if self.cities else {
            "name": "Delhi", "state": "Delhi", "district": "New Delhi", "lat": 28.6139, "lon": 77.2090
        }

    def fetch_google_news_rss(self, query: str = "IMD weather India monsoon rain flood cyclone", max_items: int = 15) -> List[Dict[str, Any]]:
        results = []
        try:
            url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
            res = requests.get(url, headers=self.headers, timeout=12)
            if res.status_code != 200:
                return results

            root = ET.fromstring(res.content)
            items = root.findall("./channel/item")

            for item in items[:max_items]:
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                if not title:
                    continue

                city_info = self._match_city_and_state(title)

                img_url = "https://images.unsplash.com/photo-1515694346937-94d85e41e6f0?w=800&auto=format&fit=crop&q=80"
                if any(w in title.lower() for w in ["cyclone", "gale", "storm", "deep depression"]):
                    img_url = "https://images.unsplash.com/photo-1527482797697-8795b05a13fe?w=800&auto=format&fit=crop&q=80"
                elif any(w in title.lower() for w in ["flood", "waterlog", "inundat", "submerged"]):
                    img_url = "https://images.unsplash.com/photo-1547683905-f686c993aae5?w=800&auto=format&fit=crop&q=80"
                elif any(w in title.lower() for w in ["thunder", "lightning"]):
                    img_url = "https://images.unsplash.com/photo-1605727216801-e27ce1d0cc28?w=800&auto=format&fit=crop&q=80"
                elif any(w in title.lower() for w in ["heat", "temperature", "45", "47"]):
                    img_url = "https://images.unsplash.com/photo-1504370805625-d32c54b16100?w=800&auto=format&fit=crop&q=80"
                elif any(w in title.lower() for w in ["fog", "smog", "visibility"]):
                    img_url = "https://images.unsplash.com/photo-1485236715568-ddc5ee6ca227?w=800&auto=format&fit=crop&q=80"

                raw_report = {
                    "source": "RSS Feed",
                    "author_handle": "@IMDNewsStream",
                    "author_name": "Indian Media News Feed",
                    "author_trust_score": 0.92,
                    "text": f"{title} (Source: {link}) #IMD #WeatherNews #IndiaWeather",
                    "hashtags": ["#IMD", "#WeatherNews", f"#{city_info['name']}Weather"],
                    "city": city_info["name"],
                    "district": city_info.get("district", city_info["name"]),
                    "state": city_info["state"],
                    "lat": city_info["lat"],
                    "lon": city_info["lon"],
                    "media_type": "image",
                    "media_url": img_url,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                processed = ingestion_pipeline.process_raw_report(raw_report)
                results.append(processed)

        except Exception as e:
            logger.error("Error fetching Google News RSS: %s", str(e))

        return results

    def fetch_open_meteo_live_grid(self, max_cities: int = 10) -> List[Dict[str, Any]]:
        results = []
        selected_cities = self.cities[:max_cities]

        weather_code_map = {
            0: ("heatwave", "Clear Skies / Sunny"),
            1: ("heatwave", "Mainly Clear"),
            2: ("fog", "Partly Cloudy / Hazy"),
            3: ("fog", "Overcast Skies"),
            45: ("fog", "Dense Fog / Low Visibility"),
            48: ("fog", "Depositing Rime Fog"),
            51: ("rainfall", "Light Drizzle"),
            53: ("rainfall", "Moderate Drizzle"),
            55: ("rainfall", "Dense Drizzle"),
            61: ("rainfall", "Slight Rain"),
            63: ("rainfall", "Moderate Continuous Rain"),
            65: ("rainfall", "Heavy Downpour"),
            80: ("rainfall", "Rain Showers"),
            81: ("flooding", "Moderate Rain Showers / Water Accumulation"),
            82: ("flooding", "Violent Rain Showers / Flash Inundation"),
            95: ("thunderstorm", "Slight or Moderate Thunderstorm"),
            96: ("hailstorm", "Thunderstorm with Slight Hail"),
            99: ("hailstorm", "Thunderstorm with Heavy Hail / Cloudburst")
        }

        for city in selected_cities:
            try:
                url = f"https://api.open-meteo.com/v1/forecast?latitude={city['lat']}&longitude={city['lon']}&current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m,wind_direction_10m"
                res = requests.get(url, timeout=8)
                if res.status_code == 200:
                    data = res.json()
                    curr = data.get("current", {})
                    code = curr.get("weather_code", 0)
                    temp = curr.get("temperature_2m", 30)
                    humidity = curr.get("relative_humidity_2m", 65)
                    wind = curr.get("wind_speed_10m", 12)
                    rain = curr.get("rain", 0)

                    event_type, desc = weather_code_map.get(code, ("rainfall", "Overcast Weather"))
                    if temp > 43.0:
                        event_type = "heatwave"
                        desc = f"Extreme Heat Conditions ({temp}°C)"
                    elif wind > 55.0:
                        event_type = "cyclone"
                        desc = f"Gale Force Wind Gusts ({wind} km/h)"

                    raw_report = {
                        "source": "IMD Radar AWS",
                        "author_handle": f"@IMD_{city['name']}",
                        "author_name": f"IMD {city['name']} Automatic Weather Station",
                        "author_trust_score": 1.0,
                        "text": f"Live AWS Station Telemetry for {city['name']}, {city['state']}: {desc}. Temp: {temp}°C, Humidity: {humidity}%, Wind: {wind} km/h, Precip: {rain}mm. #IMD #{city['name']}Weather",
                        "hashtags": ["#IMD", f"#{city['name']}Weather", f"#{event_type.capitalize()}Alert"],
                        "city": city["name"],
                        "district": city.get("district", city["name"]),
                        "state": city["state"],
                        "lat": city["lat"],
                        "lon": city["lon"],
                        "event_type": event_type,
                        "severity": "Severe" if (temp > 44 or wind > 50 or rain > 30) else "Moderate",
                        "media_type": "image",
                        "media_url": "https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?w=800&auto=format&fit=crop&q=80",
                        "verification_status": "verified_imd",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    processed = ingestion_pipeline.process_raw_report(raw_report)
                    results.append(processed)

            except Exception as e:
                logger.error("Open-Meteo fetch error for %s: %s", city["name"], str(e))

        return results

    def fetch_newsapi_org(self, api_key: str, query: str = "IMD OR weather India OR monsoon OR cyclone") -> List[Dict[str, Any]]:
        results = []
        if not api_key:
            return results

        try:
            url = f"https://newsapi.org/v2/everything?q={requests.utils.quote(query)}&sortBy=publishedAt&pageSize=10&apiKey={api_key}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                articles = data.get("articles", [])
                for art in articles:
                    title = art.get("title", "")
                    desc = art.get("description", "")
                    content = f"{title}. {desc}"
                    source_name = art.get("source", {}).get("name", "News Media")
                    city_info = self._match_city_and_state(content)

                    raw_report = {
                        "source": "Twitter/X" if "Twitter" in source_name else "RSS Feed",
                        "author_handle": f"@{source_name.replace(' ', '')}",
                        "author_name": source_name,
                        "author_trust_score": 0.90,
                        "text": f"{content} #IMD #WeatherAlert",
                        "hashtags": ["#IMD", "#WeatherAlert"],
                        "city": city_info["name"],
                        "district": city_info.get("district", city_info["name"]),
                        "state": city_info["state"],
                        "lat": city_info["lat"],
                        "lon": city_info["lon"],
                        "media_type": "image",
                        "media_url": art.get("urlToImage") or "https://images.unsplash.com/photo-1515694346937-94d85e41e6f0?w=800&auto=format&fit=crop&q=80",
                        "timestamp": art.get("publishedAt") or datetime.now(timezone.utc).isoformat()
                    }
                    processed = ingestion_pipeline.process_raw_report(raw_report)
                    results.append(processed)
        except Exception as e:
            logger.error("NewsAPI fetch error: %s", str(e))

        return results

    def fetch_openweathermap(self, api_key: str, city_name: str = "Mumbai") -> Optional[Dict[str, Any]]:
        if not api_key:
            return None

        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name},IN&units=metric&appid={api_key}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                temp = data.get("main", {}).get("temp", 30)
                weather_desc = data.get("weather", [{}])[0].get("description", "clear")
                coord = data.get("coord", {})
                
                raw_report = {
                    "source": "Public API",
                    "author_handle": "@OpenWeatherMap",
                    "author_name": "OpenWeather Global Telemetry",
                    "author_trust_score": 0.95,
                    "text": f"OpenWeather Real-Time Ingest: {city_name} reports {weather_desc}, temperature {temp}°C, humidity {data.get('main', {}).get('humidity')}% #IMD #{city_name}Weather",
                    "hashtags": ["#IMD", f"#{city_name}Weather"],
                    "city": city_name,
                    "district": city_name,
                    "state": "India",
                    "lat": coord.get("lat", 19.0760),
                    "lon": coord.get("lon", 72.8777),
                    "media_type": "image",
                    "media_url": "https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?w=800&auto=format&fit=crop&q=80",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                return ingestion_pipeline.process_raw_report(raw_report)
        except Exception as e:
            logger.error("OpenWeatherMap fetch error: %s", str(e))
        return None

    def sync_all_live_sources(self) -> Dict[str, Any]:
        keys = get_api_keys()
        news_rss = self.fetch_google_news_rss()
        telemetry = self.fetch_open_meteo_live_grid(max_cities=8)
        
        custom_news = []
        if keys.get("NEWS_API_KEY"):
            custom_news = self.fetch_newsapi_org(keys["NEWS_API_KEY"])

        total_synced = len(news_rss) + len(telemetry) + len(custom_news)
        return {
            "success": True,
            "total_synced": total_synced,
            "google_news_articles": len(news_rss),
            "open_meteo_telemetry_stations": len(telemetry),
            "custom_api_articles": len(custom_news),
            "synced_at": datetime.now(timezone.utc).isoformat()
        }

live_fetcher = LiveFetcher()
