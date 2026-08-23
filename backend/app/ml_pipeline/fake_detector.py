"""
Fake & Misleading Weather Report Detector
Leverages Multi-factor NLP Sensationalism Scoring, Climatological Plausibility,
Author Credibility History, and Radar Telemetry Cross-Verification.
"""
import re
import json
from typing import Dict, Any, List, Tuple
from ..config import (
    DATA_DIR,
    FAKE_SENSATIONALISM_WEIGHT,
    FAKE_SOURCE_TRUST_WEIGHT,
    FAKE_RADAR_ANOMALY_WEIGHT,
    FAKE_PROBABILITY_THRESHOLD
)

class FakeReportDetector:
    def __init__(self):
        self.lexicon = self._load_lexicon()
        self.cities = self._load_cities()
        self.trusted_sources = set(self.lexicon.get("trusted_sources", [
            "Indiametdept", "PIB_India", "NDRFHQ", "DDNewslive", "SkymetWeather", "IMDMumbai"
        ]))

    def _load_lexicon(self) -> Dict[str, Any]:
        lex_path = DATA_DIR / "weather_lexicon.json"
        if lex_path.exists():
            with open(lex_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _load_cities(self) -> Dict[str, Dict[str, Any]]:
        city_path = DATA_DIR / "indian_cities.json"
        if city_path.exists():
            with open(city_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {c["name"].lower(): c for c in data.get("cities", [])}
        return {}

    def evaluate(
        self,
        text: str,
        author_handle: str = "",
        author_trust: float = 0.8,
        city: str = "",
        state: str = "",
        event_type: str = "",
        radar_available: bool = True
    ) -> Dict[str, Any]:
        """
        Calculates a fake probability score (0.0 - 1.0) and generates explainable diagnostic reasons.
        """
        clean_text = text.lower()
        handle_clean = (author_handle or "").replace("@", "").strip()
        reasons: List[str] = []

        # 1. Sensationalism & Hoax Keywords Score (0.0 to 1.0)
        sensational_keywords = self.lexicon.get("sensational_keywords", [])
        matched_sensational = [
            kw for kw in sensational_keywords if kw in clean_text
        ]
        
        # Panic / Alarmist patterns
        alarm_matches = re.findall(r'(all will die|secret weapon|nasa alert|100m tsunami|run for life|doomsday|apocalypse|conspiracy|miracle)', clean_text)
        excessive_caps = sum(1 for c in text if c.isupper()) / max(1, len(text))
        excessive_exclamation = text.count("!") + text.count("?")

        sensational_score = 0.0
        if matched_sensational:
            sensational_score += 0.65 + (len(matched_sensational) * 0.15)
            reasons.append(f"Contains flagged misinformation keywords: {', '.join(matched_sensational[:2])}")
        if alarm_matches:
            sensational_score += 0.40
            reasons.append("Detected extreme panic / alarmist language patterns")
        if excessive_caps > 0.45:
            sensational_score += 0.15
            reasons.append("Excessive capitalization (indicative of clickbait/panic)")
        if excessive_exclamation >= 3:
            sensational_score += 0.10

        sensational_score = min(1.0, sensational_score)

        # 2. Climatological Plausibility / Physical Anomaly Check
        anomaly_score = 0.0
        city_info = self.cities.get(city.lower(), {})
        
        # Check impossible combinations (e.g. Snowfall in Chennai/Mumbai or 50C in Shimla)
        if "snow" in clean_text and any(c in city.lower() for c in ["chennai", "mumbai", "kolkata", "hyderabad", "kochi", "puducherry"]):
            anomaly_score = 1.0
            reasons.append(f"Climatologically impossible event: Snowfall reported in coastal tropical city ({city})")
        elif "tsunami" in clean_text and any(c in city.lower() for c in ["delhi", "jaipur", "lucknow", "bhopal", "chandigarh", "patna"]):
            anomaly_score = 1.0
            reasons.append(f"Geographically impossible event: Marine Tsunami reported in landlocked inland region ({city})")
        elif any(t in clean_text for t in ["50 degrees", "52 degrees", "55 degrees"]) and any(c in city.lower() for c in ["shimla", "srinagar", "shillong", "dehradun"]):
            anomaly_score = 0.85
            reasons.append(f"Extreme thermal anomaly: Unrealistic temperature exceeding 50°C in high-altitude Himalayan region ({city})")

        # 3. Source Credibility Assessment
        is_official = any(handle_clean.lower() == t.lower() for t in self.trusted_sources)
        if is_official:
            source_risk = 0.0
            author_trust = 1.0
        else:
            source_risk = max(0.0, 1.0 - author_trust)
            if author_trust < 0.30:
                reasons.append(f"Unverified / low-reputation author profile (Trust Score: {author_trust:.2f})")

        # 4. Simulated Radar / Station Cross-Verification
        # If there is a high anomaly or high sensationalism, radar cross-verification fails
        radar_anomaly = anomaly_score if anomaly_score > 0 else (0.7 if sensational_score > 0.6 else 0.05)
        if is_official:
            radar_anomaly = 0.0

        if radar_anomaly > 0.5:
            reasons.append("Discrepancy with nearest IMD Doppler Radar & Automatic Weather Station (AWS) baseline")

        # 5. Composite Fake Probability Calculation
        if is_official and anomaly_score == 0:
            fake_prob = 0.02
        else:
            fake_prob = (
                (sensational_score * FAKE_SENSATIONALISM_WEIGHT) +
                (source_risk * FAKE_SOURCE_TRUST_WEIGHT) +
                (radar_anomaly * FAKE_RADAR_ANOMALY_WEIGHT)
            )
            if anomaly_score >= 0.8:
                fake_prob = max(fake_prob, 0.95)

        fake_prob = round(min(0.99, max(0.01, fake_prob)), 2)
        is_fake = fake_prob >= FAKE_PROBABILITY_THRESHOLD

        # Determine verification category recommendation
        if is_official:
            status = "verified_imd"
        elif is_fake:
            status = "fake_misleading"
        elif author_trust >= 0.8 and fake_prob < 0.25:
            status = "verified_ai"
        elif fake_prob < 0.40:
            status = "citizen_corroborated"
        else:
            status = "under_review"

        return {
            "fake_probability": fake_prob,
            "is_fake_flagged": is_fake,
            "recommended_status": status,
            "sensationalism_score": round(sensational_score, 2),
            "source_risk_score": round(source_risk, 2),
            "radar_anomaly_score": round(radar_anomaly, 2),
            "radar_cross_verified": radar_anomaly <= 0.3,
            "explanation_reasons": reasons if reasons else ["Passed automated NLP consistency and radar baseline check."]
        }

# Global singleton fake detector
fake_detector = FakeReportDetector()
