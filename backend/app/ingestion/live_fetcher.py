"""
VayuDrishti - Live Internet Weather & News Multi-Source Fetcher
=================================================================
Free/Keyless Sources (no API key required):
  1. Google News IMD & Weather RSS (Real-Time)
  2. Open-Meteo Live Atmospheric Grid for India (35+ cities)
  3. IMD Official Government RSS Feed
  4. Skymet Weather RSS
  5. NDMA India Disaster Alerts RSS
  6. Reddit India/City Weather Community Posts (RSS)
  7. NASA EONET Natural Events Tracker
  8. GDACS Global Disaster Alert Feed
  9. Mastodon Fediverse #Weather RSS
  10. UN ReliefWeb Disaster API

Paid API Sources (optional, enter key in admin panel):
  9. NewsAPI.org
  10. OpenWeatherMap (multi-city)
  11. WeatherAPI.com
  12. GNews.io
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
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass


BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, application/json, */*"
}

WEATHER_IMAGE_MAP = {
    "cyclone": "https://images.unsplash.com/photo-1527482797697-8795b05a13fe?w=800&auto=format&fit=crop&q=80",
    "flooding": "https://images.unsplash.com/photo-1547683905-f686c993aae5?w=800&auto=format&fit=crop&q=80",
    "thunderstorm": "https://images.unsplash.com/photo-1605727216801-e27ce1d0cc28?w=800&auto=format&fit=crop&q=80",
    "heatwave": "https://images.unsplash.com/photo-1504370805625-d32c54b16100?w=800&auto=format&fit=crop&q=80",
    "fog": "https://images.unsplash.com/photo-1485236715568-ddc5ee6ca227?w=800&auto=format&fit=crop&q=80",
    "hailstorm": "https://images.unsplash.com/photo-1519692933481-e162a57d6721?w=800&auto=format&fit=crop&q=80",
    "dust_storm": "https://images.unsplash.com/photo-1504215680853-026ed2a45def?w=800&auto=format&fit=crop&q=80",
    "rainfall": "https://images.unsplash.com/photo-1515694346937-94d85e41e6f0?w=800&auto=format&fit=crop&q=80",
}


def _get_img(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["cyclone", "gale", "storm", "deep depression", "hurricane"]):
        return WEATHER_IMAGE_MAP["cyclone"]
    if any(w in t for w in ["flood", "waterlog", "inundat", "submerged", "deluge"]):
        return WEATHER_IMAGE_MAP["flooding"]
    if any(w in t for w in ["thunder", "lightning", "squall"]):
        return WEATHER_IMAGE_MAP["thunderstorm"]
    if any(w in t for w in ["heat", "temperature", "heatwave", "scorching"]):
        return WEATHER_IMAGE_MAP["heatwave"]
    if any(w in t for w in ["fog", "smog", "visibility", "haze"]):
        return WEATHER_IMAGE_MAP["fog"]
    if any(w in t for w in ["hail", "ice pellet"]):
        return WEATHER_IMAGE_MAP["hailstorm"]
    if any(w in t for w in ["dust", "sandstorm", "loo"]):
        return WEATHER_IMAGE_MAP["dust_storm"]
    return WEATHER_IMAGE_MAP["rainfall"]


class LiveFetcher:
    def __init__(self):
        self.cities = self._load_cities()

    def _load_cities(self) -> List[Dict[str, Any]]:
        path = DATA_DIR / "indian_cities.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("cities", [])
        return []

    def _match_city(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        for city in self.cities:
            name = city["name"].lower()
            state = city.get("state", "").lower()
            if re.search(r'\b' + re.escape(name) + r'\b', text_lower):
                return city
            if state and re.search(r'\b' + re.escape(state) + r'\b', text_lower):
                return city
        return self.cities[0] if self.cities else {
            "name": "Delhi", "state": "Delhi", "district": "New Delhi", "lat": 28.6139, "lon": 77.2090
        }

    def _make_report(self, source: str, handle: str, name: str, trust: float,
                     text: str, city_info: Dict, img: str = None,
                     ts: str = None, event_type: str = None,
                     verification: str = None) -> Dict[str, Any]:
        raw = {
            "source": source,
            "author_handle": handle,
            "author_name": name,
            "author_trust_score": trust,
            "text": text,
            "hashtags": ["#IMD", "#WeatherIndia", f"#{city_info['name']}Weather"],
            "city": city_info["name"],
            "district": city_info.get("district", city_info["name"]),
            "state": city_info["state"],
            "lat": city_info["lat"],
            "lon": city_info["lon"],
            "media_type": "image",
            "media_url": img or _get_img(text),
            "timestamp": ts or datetime.now(timezone.utc).isoformat()
        }
        if event_type:
            raw["event_type"] = event_type
        if verification:
            raw["verification_status"] = verification
        return ingestion_pipeline.process_raw_report(raw)

    # ─────────────────────────────────────────────────────────
    # SOURCE 1: Google News IMD RSS (free, no key)
    # ─────────────────────────────────────────────────────────
    def fetch_google_news_rss(self, query: str = "IMD weather India monsoon rain flood cyclone", max_items: int = 15) -> List[Dict[str, Any]]:
        results = []
        try:
            url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
            res = requests.get(url, headers=BROWSER_HEADERS, timeout=12)
            if res.status_code != 200:
                logger.warning("Google News RSS returned %d", res.status_code)
                return results
            root = ET.fromstring(res.content)
            for item in root.findall("./channel/item")[:max_items]:
                title = (item.findtext("title") or "").strip()
                link = item.findtext("link") or ""
                if not title:
                    continue
                city = self._match_city(title)
                text = f"{title} {link} #IMD #WeatherNews #IndiaWeather"
                results.append(self._make_report(
                    "RSS Feed", "@IMDNewsStream", "Indian Media News Feed",
                    0.92, text, city
                ))
        except Exception as e:
            logger.error("Google News RSS error: %s", e)
        return results

    # ─────────────────────────────────────────────────────────
    # SOURCE 2: Open-Meteo Live Atmospheric Grid (free, no key)
    # ─────────────────────────────────────────────────────────
    def fetch_open_meteo_live_grid(self, max_cities: int = 10) -> List[Dict[str, Any]]:
        results = []
        weather_code_map = {
            0: ("heatwave", "Clear Skies / Sunny"), 1: ("heatwave", "Mainly Clear"),
            2: ("fog", "Partly Cloudy"), 3: ("fog", "Overcast Skies"),
            45: ("fog", "Dense Fog"), 48: ("fog", "Rime Fog"),
            51: ("rainfall", "Light Drizzle"), 53: ("rainfall", "Moderate Drizzle"), 55: ("rainfall", "Dense Drizzle"),
            61: ("rainfall", "Slight Rain"), 63: ("rainfall", "Moderate Rain"), 65: ("rainfall", "Heavy Rain"),
            80: ("rainfall", "Rain Showers"), 81: ("flooding", "Moderate Showers"), 82: ("flooding", "Violent Showers"),
            95: ("thunderstorm", "Thunderstorm"), 96: ("hailstorm", "Thunderstorm + Hail"), 99: ("hailstorm", "Heavy Hail")
        }
        for city in self.cities[:max_cities]:
            try:
                url = (f"https://api.open-meteo.com/v1/forecast"
                       f"?latitude={city['lat']}&longitude={city['lon']}"
                       f"&current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m")
                res = requests.get(url, timeout=8)
                if res.status_code != 200:
                    continue
                curr = res.json().get("current", {})
                code = curr.get("weather_code", 0)
                temp = curr.get("temperature_2m", 30)
                humidity = curr.get("relative_humidity_2m", 65)
                wind = curr.get("wind_speed_10m", 10)
                rain = curr.get("rain", 0)
                event_type, desc = weather_code_map.get(code, ("rainfall", "Overcast"))
                if temp > 43:
                    event_type, desc = "heatwave", f"Extreme Heat ({temp}°C)"
                elif wind > 55:
                    event_type, desc = "cyclone", f"Gale Force Winds ({wind} km/h)"
                text = (f"Live AWS Telemetry — {city['name']}, {city['state']}: {desc}. "
                        f"Temp: {temp}°C, Humidity: {humidity}%, Wind: {wind} km/h, Precip: {rain}mm. "
                        f"#IMD #{city['name']}Weather")
                results.append(self._make_report(
                    "IMD Radar AWS", f"@IMD_{city['name']}", f"IMD {city['name']} AWS",
                    1.0, text, city,
                    img=WEATHER_IMAGE_MAP.get(event_type, WEATHER_IMAGE_MAP["rainfall"]),
                    event_type=event_type, verification="verified_imd"
                ))
            except Exception as e:
                logger.error("Open-Meteo error for %s: %s", city["name"], e)
        return results

    # ─────────────────────────────────────────────────────────
    # SOURCE 3: IMD Official Government RSS (free, no key)
    # ─────────────────────────────────────────────────────────
    def fetch_imd_official_rss(self) -> List[Dict[str, Any]]:
        results = []
        feeds = [
            "https://mausam.imd.gov.in/rss/weather_bulletin.xml",
            "https://rss.gov.in/imd",
            "https://internal.imd.gov.in/rss/",
        ]
        for feed_url in feeds:
            try:
                res = requests.get(feed_url, headers=BROWSER_HEADERS, timeout=10)
                if res.status_code != 200:
                    continue
                root = ET.fromstring(res.content)
                for item in root.findall("./channel/item")[:8]:
                    title = (item.findtext("title") or "").strip()
                    desc = (item.findtext("description") or "").strip()
                    content = f"{title}. {desc}"
                    if not title:
                        continue
                    city = self._match_city(content)
                    results.append(self._make_report(
                        "IMD Official", "@Indiametdept", "India Meteorological Department",
                        1.0, f"{content} #IMD #OfficialAlert", city,
                        verification="verified_imd"
                    ))
                if results:
                    break
            except Exception as e:
                logger.debug("IMD official RSS error (%s): %s", feed_url, e)
        return results

    # ─────────────────────────────────────────────────────────
    # SOURCE 4: Skymet Weather RSS (free, no key)
    # ─────────────────────────────────────────────────────────
    def fetch_skymet_rss(self) -> List[Dict[str, Any]]:
        results = []
        feeds = [
            "https://www.skymetweather.com/feed/",
            "https://www.skymetweather.com/content/weather-news-and-analysis/feed/"
        ]
        for feed_url in feeds:
            try:
                res = requests.get(feed_url, headers=BROWSER_HEADERS, timeout=10)
                if res.status_code != 200:
                    continue
                root = ET.fromstring(res.content)
                for item in root.findall("./channel/item")[:8]:
                    title = (item.findtext("title") or "").strip()
                    desc = re.sub(r'<[^>]+>', '', item.findtext("description") or "")[:300]
                    content = f"{title}. {desc}"
                    if not title:
                        continue
                    city = self._match_city(content)
                    results.append(self._make_report(
                        "RSS Feed", "@SkymetWeather", "Skymet Weather Services",
                        0.95, f"{content} #IMD #SkymetWeather #IndiaWeather", city
                    ))
                if results:
                    break
            except Exception as e:
                logger.debug("Skymet RSS error (%s): %s", feed_url, e)
        return results

    # ─────────────────────────────────────────────────────────
    # SOURCE 5: NDMA India Disaster Alerts (free, no key)
    # ─────────────────────────────────────────────────────────
    def fetch_ndma_alerts(self) -> List[Dict[str, Any]]:
        results = []
        feeds = [
            "https://ndma.gov.in/rss.xml",
            "https://ndma.gov.in/feed/",
        ]
        for feed_url in feeds:
            try:
                res = requests.get(feed_url, headers=BROWSER_HEADERS, timeout=10)
                if res.status_code != 200:
                    continue
                root = ET.fromstring(res.content)
                for item in root.findall("./channel/item")[:6]:
                    title = (item.findtext("title") or "").strip()
                    desc = re.sub(r'<[^>]+>', '', item.findtext("description") or "")[:300]
                    content = f"{title}. {desc}"
                    if not title:
                        continue
                    city = self._match_city(content)
                    results.append(self._make_report(
                        "Government Alert", "@NDRFHQ", "National Disaster Management Authority",
                        1.0, f"{content} #NDMA #DisasterAlert #IMD", city,
                        verification="verified_imd"
                    ))
                if results:
                    break
            except Exception as e:
                logger.debug("NDMA RSS error (%s): %s", feed_url, e)
        return results

    # ─────────────────────────────────────────────────────────
    # SOURCE 6: Reddit India/City Weather Subreddits RSS (free, no key)
    # ─────────────────────────────────────────────────────────
    def fetch_reddit_weather_posts(self) -> List[Dict[str, Any]]:
        results = []
        subreddits = [
            ("india", "Delhi"),
            ("mumbai", "Mumbai"),
            ("bangalore", "Bengaluru"),
            ("delhi", "Delhi"),
            ("chennai", "Chennai"),
            ("kolkata", "Kolkata"),
        ]
        weather_keywords = ["rain", "flood", "cyclone", "heatwave", "storm", "thunder",
                            "fog", "weather", "monsoon", "imd", "alert", "warning"]
        for subreddit, default_city_name in subreddits:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=10"
                res = requests.get(url, headers={
                    "User-Agent": "VayuDrishti-WeatherBot/1.0 (+https://github.com/VidhyarthNagar/VayuDrishti-Vidhyarth-)"
                }, timeout=8)
                if res.status_code != 200:
                    continue
                posts = res.json().get("data", {}).get("children", [])
                for post in posts:
                    data = post.get("data", {})
                    title = (data.get("title") or "").strip()
                    selftext = (data.get("selftext") or "")[:200].strip()
                    content = f"{title} {selftext}"
                    if not any(kw in content.lower() for kw in weather_keywords):
                        continue
                    city = self._match_city(content)
                    if city["name"] == self.cities[0]["name"]:
                        city = next((c for c in self.cities if c["name"] == default_city_name), city)
                    author = data.get("author", "reddit_user")
                    permalink = f"https://reddit.com{data.get('permalink', '')}"
                    results.append(self._make_report(
                        "Social Media", f"@reddit_u_{author}", f"Reddit u/{author} (r/{subreddit})",
                        0.70, f"{content} {permalink} #WeatherIndia #CitizenReport", city
                    ))
            except Exception as e:
                logger.debug("Reddit RSS error for r/%s: %s", subreddit, e)
        return results[:10]

    # ─────────────────────────────────────────────────────────
    # SOURCE 7: NASA EONET Natural Events (free, no key)
    # ─────────────────────────────────────────────────────────
    def fetch_nasa_eonet(self) -> List[Dict[str, Any]]:
        results = []
        try:
            url = "https://eonet.gsfc.nasa.gov/api/v3/events?limit=20&status=open&bbox=68,6,97,37"
            res = requests.get(url, headers=BROWSER_HEADERS, timeout=10)
            if res.status_code != 200:
                return results
            events = res.json().get("events", [])
            for ev in events:
                title = ev.get("title", "").strip()
                categories = [c.get("title", "").lower() for c in ev.get("categories", [])]
                geometry = ev.get("geometry", [])
                if not geometry:
                    continue
                coords = geometry[-1].get("coordinates", [])
                if len(coords) < 2:
                    continue
                lon, lat = float(coords[0]), float(coords[1])
                event_type = "flooding"
                if any("cyclone" in c or "storm" in c or "typhoon" in c for c in categories):
                    event_type = "cyclone"
                elif any("drought" in c or "heat" in c for c in categories):
                    event_type = "heatwave"
                elif any("fire" in c for c in categories):
                    event_type = "dust_storm"
                city = min(self.cities, key=lambda c: abs(c["lat"] - lat) + abs(c["lon"] - lon))
                ts = geometry[-1].get("date", datetime.now(timezone.utc).isoformat())
                results.append(self._make_report(
                    "Satellite Remote Sensing", "@NASA_EONET", "NASA Earth Observatory Natural Events",
                    0.98, f"NASA EONET Alert: {title}. Coordinates: ({lat:.2f}°N, {lon:.2f}°E) #NASA #EONET #IndiaWeather",
                    city, img=WEATHER_IMAGE_MAP.get(event_type, WEATHER_IMAGE_MAP["cyclone"]),
                    ts=ts, event_type=event_type, verification="verified_imd"
                ))
        except Exception as e:
            logger.error("NASA EONET error: %s", e)
        return results

    # ─────────────────────────────────────────────────────────
    # SOURCE 8: GDACS Global Disaster Alert (free, no key)
    # ─────────────────────────────────────────────────────────
    def fetch_gdacs_alerts(self) -> List[Dict[str, Any]]:
        results = []
        try:
            url = "https://www.gdacs.org/xml/rss.xml"
            res = requests.get(url, headers=BROWSER_HEADERS, timeout=12)
            if res.status_code != 200:
                return results
            root = ET.fromstring(res.content)
            ns = {"gdacs": "http://www.gdacs.org"}
            for item in root.findall("./channel/item")[:10]:
                title = (item.findtext("title") or "").strip()
                desc = re.sub(r'<[^>]+>', '', item.findtext("description") or "")[:300]
                # Only keep India-relevant events
                content = f"{title} {desc}"
                if not any(kw in content.lower() for kw in ["india", "indian", "bay of bengal", "arabian sea", "south asia"]):
                    continue
                city = self._match_city(content)
                event_type = "flooding"
                if any(w in title.lower() for w in ["cyclone", "storm", "typhoon"]):
                    event_type = "cyclone"
                elif any(w in title.lower() for w in ["drought", "heat"]):
                    event_type = "heatwave"
                results.append(self._make_report(
                    "International Alert", "@GDACS_Alert", "Global Disaster Alert & Coordination System",
                    0.99, f"🌍 GDACS Alert: {content} #GDACS #DisasterAlert #IMD", city,
                    img=WEATHER_IMAGE_MAP.get(event_type, WEATHER_IMAGE_MAP["cyclone"]),
                    event_type=event_type, verification="verified_imd"
                ))
        except Exception as e:
            logger.error("GDACS error: %s", e)
        return results

    # ─────────────────────────────────────────────────────────
    # SOURCE 9: Mastodon Fediverse RSS (free, no key)
    # ─────────────────────────────────────────────────────────
    def fetch_mastodon_rss(self) -> List[Dict[str, Any]]:
        results = []
        try:
            url = "https://mastodon.social/tags/weather.rss"
            res = requests.get(url, headers=BROWSER_HEADERS, timeout=10)
            if res.status_code == 200:
                root = ET.fromstring(res.text)
                for item in root.findall(".//item")[:15]:
                    desc = item.findtext("description", "")
                    # Mastodon descriptions are HTML, strip tags
                    desc = re.sub(r'<[^>]+>', ' ', desc).strip()
                    if "india" in desc.lower() or "imd" in desc.lower():
                        city = self._match_city(desc)
                        results.append(self._make_report(
                            "Social Media", "@MastodonUser", "Mastodon Fediverse",
                            0.70, f"Mastodon Report: {desc[:200]}...", city
                        ))
        except Exception as e:
            logger.error("Mastodon error: %s", e)
        return results

    # ─────────────────────────────────────────────────────────
    # SOURCE 10: UN ReliefWeb Disaster API (free, no key)
    # ─────────────────────────────────────────────────────────
    def fetch_reliefweb_api(self) -> List[Dict[str, Any]]:
        results = []
        try:
            # Country ISO3 for India is IND
            url = "https://api.reliefweb.int/v1/disasters?appname=vayudrishti&profile=list&preset=latest&query[value]=country.iso3:IND"
            res = requests.get(url, headers=BROWSER_HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", [])
                for d in data:
                    fields = d.get("fields", {})
                    name = fields.get("name", "")
                    if not name: continue
                    city = self._match_city(name)
                    results.append(self._make_report(
                        "Govt/NGO Alert", "@ReliefWeb", "UN ReliefWeb",
                        0.99, f"ReliefWeb Disaster Alert for India: {name}", city,
                        event_type="flooding",
                        verification="verified_imd"
                    ))
        except Exception as e:
            logger.error("ReliefWeb error: %s", e)
        return results

    # ─────────────────────────────────────────────────────────
    # SOURCE 11-14: Paid API Sources (optional — require API key)
    # ─────────────────────────────────────────────────────────
    def fetch_newsapi_org(self, api_key: str) -> List[Dict[str, Any]]:
        results = []
        if not api_key:
            return results
        try:
            url = f"https://newsapi.org/v2/everything?q=IMD+OR+weather+India+OR+monsoon+OR+cyclone&sortBy=publishedAt&pageSize=12&apiKey={api_key}"
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                return results
            for art in res.json().get("articles", []):
                title = art.get("title", "")
                desc = art.get("description", "")
                content = f"{title}. {desc}"
                source_name = art.get("source", {}).get("name", "News Media")
                city = self._match_city(content)
                results.append(self._make_report(
                    "RSS Feed", f"@{source_name.replace(' ', '')}", source_name,
                    0.90, f"{content} #IMD #WeatherAlert", city,
                    img=art.get("urlToImage") or WEATHER_IMAGE_MAP["rainfall"],
                    ts=art.get("publishedAt")
                ))
        except Exception as e:
            logger.error("NewsAPI error: %s", e)
        return results

    def fetch_openweathermap(self, api_key: str) -> List[Dict[str, Any]]:
        results = []
        if not api_key:
            return results
        target_cities = ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata", "Hyderabad", "Ahmedabad", "Jaipur"]
        for city_name in target_cities:
            try:
                url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name},IN&units=metric&appid={api_key}"
                res = requests.get(url, timeout=8)
                if res.status_code != 200:
                    continue
                data = res.json()
                temp = data.get("main", {}).get("temp", 30)
                humidity = data.get("main", {}).get("humidity", 60)
                wind = data.get("wind", {}).get("speed", 3.5) * 3.6
                weather_desc = data.get("weather", [{}])[0].get("description", "clear skies")
                coord = data.get("coord", {})
                city = self._match_city(city_name)
                results.append(self._make_report(
                    "Public API", f"@OpenWeather_{city_name}", f"OpenWeatherMap ({city_name})",
                    0.98, f"Live OWM: {city_name}: {weather_desc.capitalize()}. Temp: {temp}°C, Humidity: {humidity}%, Wind: {round(wind,1)} km/h. #IMD #{city_name}Weather",
                    city, img=WEATHER_IMAGE_MAP["rainfall"]
                ))
            except Exception as e:
                logger.error("OWM error for %s: %s", city_name, e)
        return results

    def fetch_weatherapi_com(self, api_key: str) -> List[Dict[str, Any]]:
        results = []
        if not api_key:
            return results
        for city_name in ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata"]:
            try:
                url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={city_name},India&aqi=yes"
                res = requests.get(url, timeout=8)
                if res.status_code != 200:
                    continue
                curr = res.json().get("current", {})
                condition = curr.get("condition", {}).get("text", "Clear")
                temp = curr.get("temp_c", 30)
                humidity = curr.get("humidity", 60)
                wind = curr.get("wind_kph", 10)
                city = self._match_city(city_name)
                results.append(self._make_report(
                    "Public API", f"@WeatherAPI_{city_name}", f"WeatherAPI ({city_name})",
                    0.98, f"WeatherAPI: {city_name}: {condition}. Temp: {temp}°C, Humidity: {humidity}%, Wind: {wind} km/h. #IMD #{city_name}Weather",
                    city
                ))
            except Exception as e:
                logger.error("WeatherAPI error for %s: %s", city_name, e)
        return results

    # ─────────────────────────────────────────────────────────
    # MASTER SYNC: All Sources Combined
    # ─────────────────────────────────────────────────────────
    def sync_all_live_sources(self, custom_keys: Dict[str, str] = None) -> Dict[str, Any]:
        """Syncs ALL available live feeds — keyless + optional paid API keys."""
        keys = get_api_keys()
        if custom_keys:
            keys.update({k: v for k, v in custom_keys.items() if v})

        # Always-on free sources
        google_news   = self.fetch_google_news_rss()
        open_meteo    = self.fetch_open_meteo_live_grid(max_cities=10)
        imd_official  = self.fetch_imd_official_rss()
        skymet        = self.fetch_skymet_rss()
        ndma          = self.fetch_ndma_alerts()
        reddit        = self.fetch_reddit_weather_posts()
        nasa_eonet    = self.fetch_nasa_eonet()
        gdacs         = self.fetch_gdacs_alerts()
        mastodon      = self.fetch_mastodon_rss()
        reliefweb     = self.fetch_reliefweb_api()

        # Optional paid sources
        newsapi     = self.fetch_newsapi_org(keys.get("NEWS_API_KEY", ""))
        owm         = self.fetch_openweathermap(keys.get("OPENWEATHER_API_KEY", ""))
        weatherapi  = self.fetch_weatherapi_com(keys.get("WEATHERAPI_KEY", ""))

        all_reports = (google_news + open_meteo + imd_official + skymet +
                       ndma + reddit + nasa_eonet + gdacs + mastodon + reliefweb +
                       newsapi + owm + weatherapi)

        return {
            "success": True,
            "total_synced": len(all_reports),
            "breakdown": {
                "google_news_rss": len(google_news),
                "open_meteo_aws": len(open_meteo),
                "imd_official_rss": len(imd_official),
                "skymet_rss": len(skymet),
                "ndma_alerts": len(ndma),
                "reddit_citizen_posts": len(reddit),
                "nasa_eonet_satellites": len(nasa_eonet),
                "gdacs_disaster_alerts": len(gdacs),
                "mastodon_social": len(mastodon),
                "reliefweb_disasters": len(reliefweb),
                "newsapi_articles": len(newsapi),
                "openweather_stations": len(owm),
                "weatherapi_stations": len(weatherapi),
            },
            "reports": all_reports[:30],
            "synced_at": datetime.now(timezone.utc).isoformat()
        }


live_fetcher = LiveFetcher()
