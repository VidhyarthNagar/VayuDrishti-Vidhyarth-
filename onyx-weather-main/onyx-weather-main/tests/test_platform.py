"""
Automated Test Suite for National Weather Big Data Analytics Platform
Verifies NLP classification, fake detection, deduplication, and database pipelines.
"""
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.ml_pipeline.classifier import weather_classifier
from backend.app.ml_pipeline.fake_detector import fake_detector
from backend.app.ml_pipeline.deduplicator import deduplication_engine
from backend.app.ml_pipeline.pipeline import ingestion_pipeline
from backend.app.database import init_db, get_db_connection

class TestWeatherBigDataPlatform(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_classifier_rainfall(self):
        text = "Continuous heavy rainfall in Mumbai suburbs causing minor water stagnation #IMD #MumbaiRains"
        event, conf, sev = weather_classifier.classify(text)
        self.assertEqual(event, "rainfall")
        self.assertGreater(conf, 0.7)

    def test_classifier_thunderstorm(self):
        text = "Loud thunder and dangerous lightning strikes in Delhi NCR Damini alert #Thunderstorm"
        event, conf, sev = weather_classifier.classify(text)
        self.assertEqual(event, "thunderstorm")
        self.assertGreater(conf, 0.7)

    def test_classifier_heatwave(self):
        text = "Severe loo conditions with scorching 47 degrees temperature in Jodhpur red alert"
        event, conf, sev = weather_classifier.classify(text)
        self.assertEqual(event, "heatwave")
        self.assertGreater(conf, 0.7)

    def test_classifier_cyclone(self):
        text = "Super cyclonic storm landfall near Odisha coast with 130 kmph destructive gale winds"
        event, conf, sev = weather_classifier.classify(text)
        self.assertEqual(event, "cyclone")
        self.assertGreater(conf, 0.7)

    def test_fake_detector_hoax(self):
        hoax_text = "EMERGENCY: Secret 100m tsunami hitting New Delhi right now! All will die! Unofficial NASA leak run for life!"
        res = fake_detector.evaluate(hoax_text, author_handle="@ScamBot", author_trust=0.1, city="Delhi")
        self.assertTrue(res["is_fake_flagged"])
        self.assertGreaterEqual(res["fake_probability"], 0.75)
        self.assertEqual(res["recommended_status"], "fake_misleading")
        self.assertTrue(len(res["explanation_reasons"]) > 0)

    def test_fake_detector_climatological_anomaly(self):
        snow_in_chennai = "Heavy 4 feet snowfall on Marina Beach in Chennai right now!"
        res = fake_detector.evaluate(snow_in_chennai, author_handle="@WeatherUser", author_trust=0.8, city="Chennai")
        self.assertTrue(res["is_fake_flagged"])
        self.assertGreaterEqual(res["fake_probability"], 0.8)

    def test_fake_detector_official_source(self):
        official_text = "Heavy rainfall warning issued for Konkan and Goa coast during next 24 hours #IMD"
        res = fake_detector.evaluate(official_text, author_handle="@Indiametdept", author_trust=1.0, city="Mumbai")
        self.assertFalse(res["is_fake_flagged"])
        self.assertLess(res["fake_probability"], 0.15)
        self.assertEqual(res["recommended_status"], "verified_imd")

    def test_deduplicator_clusters_close_events(self):
        recent = [{
            "id": "RPT-001",
            "lat": 19.0760,
            "lon": 72.8777,
            "timestamp": "2026-08-23T12:00:00Z",
            "event_type": "flooding",
            "text": "Waterlogging in Dadar TT circle completely submerged under water",
            "duplicate_cluster_id": "CLUS-MUM-TEST",
            "cluster_size": 1
        }]

        new_rep = {
            "id": "RPT-002",
            "lat": 19.0770, # ~100m away
            "lon": 72.8780,
            "timestamp": "2026-08-23T12:05:00Z", # 5 mins later
            "event_type": "flooding",
            "text": "Dadar TT circle submerged under deep waterlogging avoid area"
        }

        res = deduplication_engine.process_new_report(new_rep, recent)
        self.assertEqual(res["duplicate_cluster_id"], "CLUS-MUM-TEST")
        self.assertFalse(res["is_cluster_primary"])
        self.assertEqual(res["cluster_size"], 2)

    def test_pipeline_end_to_end(self):
        raw = {
            "source": "Citizen Report",
            "author_name": "Test User",
            "author_handle": "@TestUser",
            "author_trust_score": 0.85,
            "text": "Moderate rain showers and cloudy weather in Pune #IMD #WeatherUpdate",
            "city": "Pune",
            "district": "Pune",
            "state": "Maharashtra",
            "lat": 18.5204,
            "lon": 73.8567
        }
        processed = ingestion_pipeline.process_raw_report(raw)
        self.assertIn("id", processed)
        self.assertEqual(processed["event_type"], "rainfall")
        self.assertIn(processed["verification_status"], ["verified_ai", "verified_imd", "citizen_corroborated"])

        # Check in DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM weather_reports WHERE id = ?", (processed["id"],))
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["city"], "Pune")

if __name__ == "__main__":
    unittest.main()
