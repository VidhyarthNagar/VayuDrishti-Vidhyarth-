"""
Live Event Streamer & Disaster Scenario Simulation Engine
Allows real-time streaming of incoming weather reports and triggering specific crisis scenarios.
"""
import asyncio
import random
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from .social_scraper import social_ingestor
from ..ml_pipeline.pipeline import ingestion_pipeline

logger = logging.getLogger("event_generator")

class ScenarioGenerator:
    def __init__(self):
        self.is_streaming = True
        self.stream_interval_seconds = 8.0 # generates new report every 8s

    def trigger_scenario(self, scenario_name: str) -> List[Dict[str, Any]]:
        """
        Triggers a batch of realistic reports corresponding to a major meteorological event or incident.
        """
        results = []
        now = datetime.now(timezone.utc).isoformat()

        if scenario_name == "cyclone_landfall":
            # Cyclone Dana Landfall along Odisha - West Bengal Coast
            batch = [
                {
                    "source": "IMD Radar AWS",
                    "author_handle": "@Indiametdept",
                    "author_trust_score": 1.0,
                    "text": "IMD BULLETIN #14: Severe Cyclonic Storm 'DANA' centered 80km off Dhamra Port. Sustained winds 110-120 kmph gusting to 135 kmph. Landfall process commencing. Red Alert in Bhadrak, Kendrapara, Balasore. #IMD #CycloneDana #Odisha",
                    "city": "Bhubaneswar",
                    "district": "Bhadrak",
                    "state": "Odisha",
                    "lat": 20.9000,
                    "lon": 86.5100,
                    "event_type": "cyclone",
                    "severity": "Severe Cyclonic Storm",
                    "media_url": "https://images.unsplash.com/photo-1527482797697-8795b05a13fe?w=800&auto=format&fit=crop&q=80"
                },
                {
                    "source": "Citizen Report",
                    "author_handle": "Citizen-App#9031",
                    "author_trust_score": 0.88,
                    "text": "Heavy storm surge and crashing waves breached embankment near Dhamra port. NDRF boats active. Electricity cut off. #CycloneDana #IMD",
                    "city": "Bhubaneswar",
                    "district": "Bhadrak",
                    "state": "Odisha",
                    "lat": 20.8950,
                    "lon": 86.5150,
                    "event_type": "cyclone",
                    "severity": "Severe Cyclonic Storm",
                    "media_url": "https://images.unsplash.com/photo-1508873696983-2df5293cb32b?w=800&auto=format&fit=crop&q=80"
                },
                {
                    "source": "Twitter/X",
                    "author_handle": "@HoaxBuster_Fail",
                    "author_trust_score": 0.15,
                    "text": "GOVERNMENT IS CONCEALING: Cyclone Dana is a Category 6 nuclear storm that will obliterate Kolkata and Dhaka! Evacuate to Himalayas! #CycloneDana #IMD #Doomsday",
                    "city": "Kolkata",
                    "district": "Kolkata",
                    "state": "West Bengal",
                    "lat": 22.5726,
                    "lon": 88.3639,
                    "event_type": "cyclone",
                    "severity": "Catastrophic (Hoax)",
                    "media_url": "https://images.unsplash.com/photo-1509114397022-ed747cca3f65?w=800&auto=format&fit=crop&q=80"
                }
            ]
        elif scenario_name == "mumbai_cloudburst":
            # Extreme Cloudburst in Mumbai
            batch = [
                {
                    "source": "IMD Radar AWS",
                    "author_handle": "@IMDMumbai",
                    "author_trust_score": 1.0,
                    "text": "NOWCAST WARNING: Extremely intense precipitation spells (80-100mm/hr) occurring over Mumbai Suburban and Thane. Doppler radar shows heavy convective cloud tops at 14km. Red Alert. #IMD #MumbaiRains",
                    "city": "Mumbai",
                    "district": "Mumbai Suburban",
                    "state": "Maharashtra",
                    "lat": 19.1136,
                    "lon": 72.8697,
                    "event_type": "rainfall",
                    "severity": "Torrential / Cloudburst",
                    "media_url": "https://images.unsplash.com/photo-1515694346937-94d85e41e6f0?w=800&auto=format&fit=crop&q=80"
                },
                {
                    "source": "Twitter/X",
                    "author_handle": "@AndheriTrafficLive",
                    "author_trust_score": 0.90,
                    "text": "Andheri Subway and Milan Subway completely closed for traffic due to 4 feet water accumulation. Pumps working at full capacity. #MumbaiRains #IMD #Waterlogging",
                    "city": "Mumbai",
                    "district": "Mumbai Suburban",
                    "state": "Maharashtra",
                    "lat": 19.1197,
                    "lon": 72.8464,
                    "event_type": "flooding",
                    "severity": "Severe Inundation",
                    "media_url": "https://images.unsplash.com/photo-1547683905-f686c993aae5?w=800&auto=format&fit=crop&q=80"
                }
            ]
        elif scenario_name == "delhi_severe_smog":
            # Severe Winter Smog & Zero Visibility in Delhi-NCR
            batch = [
                {
                    "source": "Twitter/X",
                    "author_handle": "@DelhiAirWatch",
                    "author_trust_score": 0.93,
                    "text": "AQI crosses 495 (Severe Plus) across Anand Vihar and ITO. Dense toxic smog envelope reduces visibility below 40 meters. Emergency measures GRAP Stage 4 enforced. #IMD #DelhiSmog #DenseFog #AQI",
                    "city": "Delhi",
                    "district": "East Delhi",
                    "state": "Delhi",
                    "lat": 28.6500,
                    "lon": 77.3000,
                    "event_type": "fog",
                    "severity": "Zero Visibility Fog (<50m)",
                    "media_url": "https://images.unsplash.com/photo-1485236715568-ddc5ee6ca227?w=800&auto=format&fit=crop&q=80"
                }
            ]
        else:
            # Random synthetic single report
            batch = [social_ingestor.fetch_synthetic_post()]

        for item in batch:
            item["timestamp"] = now
            processed = ingestion_pipeline.process_raw_report(item)
            results.append(processed)

        return results

    def generate_single_live_stream_report(self) -> Dict[str, Any]:
        """Generates one realistic stream event and processes it through the pipeline."""
        raw = social_ingestor.fetch_synthetic_post()
        return ingestion_pipeline.process_raw_report(raw)

scenario_generator = ScenarioGenerator()
