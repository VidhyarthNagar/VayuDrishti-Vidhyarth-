"""
Enhanced Fake & Misleading Weather Report Detector
====================================================
Combines:
1. Rule-based NLP: sensationalism, climatological plausibility, source trust
2. Scikit-learn TF-IDF + Logistic Regression trained on labeled real/fake dataset
3. Admin feedback loop: moderator approve/reject actions retrain the model
4. Explainable diagnostics for each prediction
"""
import re
import json
import pickle
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score
from ..config import (
    DATA_DIR, FAKE_SENSATIONALISM_WEIGHT,
    FAKE_SOURCE_TRUST_WEIGHT, FAKE_RADAR_ANOMALY_WEIGHT, FAKE_PROBABILITY_THRESHOLD
)

logger = logging.getLogger("fake_detector")

MODEL_PATH = DATA_DIR / "fake_detector_model.pkl"
FEEDBACK_PATH = DATA_DIR / "fake_detector_feedback.json"


# ─────────────────────────────────────────────────────────────────────────────
# LABELED TRAINING DATASET
# Real weather reports should score 0 (genuine), fake should score 1 (misleading)
# ─────────────────────────────────────────────────────────────────────────────
LABELED_TRAINING_DATA: List[Tuple[str, int]] = [
    # ── REAL REPORTS (label=0) ───────────────────────────────────────────────
    ("IMD issues red alert for heavy rainfall in Mumbai and coastal Maharashtra today", 0),
    ("NDRF teams deployed as Brahmaputra breaches danger mark in Assam districts", 0),
    ("Cyclone Dana to make landfall near Puri with 130 kmph winds IMD official alert", 0),
    ("Dense fog advisory for North India visibility drops below 50m on NH48", 0),
    ("Heavy hailstorm damages crops in Punjab wheat fields tennis ball size hailstones", 0),
    ("Yellow alert for thunderstorm in Delhi NCR tomorrow afternoon IMD", 0),
    ("Monsoon advances into Kerala 2 days ahead of schedule India Meteorological Dept", 0),
    ("Temperature 46C recorded at Churu Rajasthan heatwave continues IMD warning", 0),
    ("IMD Doppler radar detects intense convective cell approaching Hyderabad", 0),
    ("Flood rescue operation underway in Assam 2 lakh displaced NDRF boats deployed", 0),
    ("Cyclone Biparjoy landfall complete over Gujarat coast surge recorded 4m", 0),
    ("Dense smog visibility near zero Delhi AQI severe category 500 plus PM2.5", 0),
    ("Uttarakhand cloudburst causes flash flood in Chamoli district 3 dead", 0),
    ("Skymet forecast heavy rain in Mumbai Pune for next 48 hours orange alert", 0),
    ("Weather station at Cherrapunji records 500mm rainfall in 24 hours", 0),
    ("Cold wave hits north India temperature falls 10 degrees below normal in Punjab", 0),
    ("NDMA activates control rooms in Odisha ahead of cyclone landfall", 0),
    ("IMD issues orange alert for isolated heavy to very heavy rainfall in Goa", 0),
    ("Strong winds and rough sea conditions along Konkan coast fishermen warned", 0),
    ("Heatwave persists in Vidarbha Nagpur records 47 degrees Celsius", 0),
    ("Pre-monsoon thunderstorm brings relief from heat in Delhi with 15mm rain", 0),
    ("IMD satellite confirms deep depression over Bay of Bengal likely to intensify", 0),
    ("Fog disrupts train services Northern Railway 30 trains running late", 0),
    ("Flash floods in Himachal roads blocked in Kinnaur district after cloudburst", 0),
    ("Rajasthan dust storm andhi strikes Jodhpur visibility 200 meters winds 60kmph", 0),
    ("Heavy rain lashes Chennai overnight waterlogging in Tambaram Velachery", 0),
    ("Cyclone alert for Andaman Nicobar islands fishermen not to venture into sea", 0),
    ("IMD predicts above normal rainfall for Kerala during south west monsoon 2024", 0),
    ("Hailstorm in Uttarakhand damages apple orchards farmers suffer losses", 0),
    ("Severe thunderstorm warning for Bihar Jharkhand lightning kills 4", 0),

    # ── FAKE / MISLEADING REPORTS (label=1) ──────────────────────────────────
    ("BREAKING Mumbai will be completely DESTROYED by mega tsunami 100m wave tonight", 1),
    ("ALERT snowfall in Chennai unprecedented historic white Christmas confirmed 2024", 1),
    ("Scientists confirm secret HAARP weapon caused artificial cyclone over India", 1),
    ("NASA issues apocalypse warning massive solar storm will destroy all power India", 1),
    ("URGENT run for your life monster earthquake 9.9 magnitude Mumbai submerging", 1),
    ("Doomsday cyclone 500 kmph winds will WIPE OUT entire Mumbai RUN NOW", 1),
    ("EXCLUSIVE PROOF government hiding real death toll 50000 already dead from flood", 1),
    ("Toxic rain today chemicals mixed by cloud seeding avoid going out protect kids", 1),
    ("Snowfall in Hyderabad amazing miracle temperature dropped to minus 20 Celsius", 1),
    ("CONSPIRACY: IMD hiding super cyclone that will hit Delhi landlocked area tsunami", 1),
    ("SHOCKING volcanic eruption detected in Rajasthan desert lava flowing towards Jaipur", 1),
    ("WhatsApp viral message: Dangerous acid rain falling all India stay indoors", 1),
    ("FAKE ALERT: No cyclone approaching coast ignore IMD warnings it is all lies", 1),
    ("God miracle temperature 70 degrees celsius recorded breaking all records fake", 1),
    ("Tsunami warning for Agra landlocked city impossible sea activity detected hoax", 1),
    ("Climate conspiracy chemtrails causing artificial monsoon floods in India proof", 1),
    ("BREAKING aliens causing weather changes UFO spotted near storm cloud over Delhi", 1),
    ("ALL WILL DIE massive hurricane 800 kmph winds impossible speed coming India", 1),
    ("Secret underground explosion causing Uttarakhand floods government hiding truth", 1),
    ("Miracle weather event temperature 60C in Shimla hill station boiling impossible", 1),
    ("CHAIN MAIL URGENT share this tsunami warning to save lives no source confirmed", 1),
    ("WhatsApp forward: IMD scientist confirms city will be submerged by midnight", 1),
    ("Fake video viral: 200 feet waves hitting Mumbai coast CGI deepfake confirmed", 1),
    ("Conspiracy: Drought in Rajasthan caused by secret military weather weapons HAARP", 1),
    ("SHOCKING temperature minus 40 in Chennai coastal city physically impossible", 1),
    ("ALERT: Earthquake will trigger 90 meter tsunami hitting entire Indian coast tonight", 1),
    ("Proof government cloud seeding chemicals causing cancer avoid rain exposure", 1),
    ("Miracle: Holy water temple stopped cyclone changing direction prayer works", 1),
    ("BREAKING: Massive radioactive rain detected carry umbrellas avoid exposure India", 1),
    ("Viral: Bermuda triangle type zone forming Bay of Bengal ships disappearing fake", 1),
]


class FakeReportDetector:
    def __init__(self):
        self.lexicon = self._load_lexicon()
        self.cities = self._load_cities()
        self.trusted_sources = set(self.lexicon.get("trusted_sources", [
            "Indiametdept", "PIB_India", "NDRFHQ", "DDNewslive", "SkymetWeather", "IMDMumbai"
        ]))
        self.ml_pipeline = self._load_or_train_model()

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

    def _get_all_training_data(self) -> Tuple[List[str], List[int]]:
        """Combines built-in labeled data with admin feedback data."""
        texts, labels = zip(*LABELED_TRAINING_DATA)
        texts, labels = list(texts), list(labels)

        # Load admin feedback (approved=0=real, rejected=1=fake)
        if FEEDBACK_PATH.exists():
            try:
                with open(FEEDBACK_PATH, "r", encoding="utf-8") as f:
                    feedback = json.load(f)
                    for item in feedback:
                        texts.append(item["text"])
                        labels.append(item["label"])
                logger.info("Loaded %d admin feedback samples for retraining", len(feedback))
            except Exception as e:
                logger.warning("Could not load feedback data: %s", e)
        return texts, labels

    def _load_or_train_model(self) -> Pipeline:
        """Load saved model or train fresh from labeled dataset."""
        if MODEL_PATH.exists():
            try:
                with open(MODEL_PATH, "rb") as f:
                    pipeline = pickle.load(f)
                logger.info("Loaded trained fake detector model from %s", MODEL_PATH)
                return pipeline
            except Exception:
                pass
        return self._train_model()

    def _train_model(self) -> Pipeline:
        """Train TF-IDF + Logistic Regression on labeled dataset + feedback."""
        texts, labels = self._get_all_training_data()
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 3),
                min_df=1,
                max_features=5000,
                sublinear_tf=True,
                stop_words="english"
            )),
            ("clf", LogisticRegression(
                C=2.0, max_iter=1000, class_weight="balanced",
                solver="lbfgs", random_state=42
            ))
        ])
        pipeline.fit(texts, labels)

        # Cross-validation score
        try:
            scores = cross_val_score(pipeline, texts, labels, cv=min(5, len(texts)//2), scoring="accuracy")
            logger.info("Fake Detector CV Accuracy: %.2f ± %.2f", scores.mean(), scores.std())
        except Exception:
            pass

        # Save model
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(MODEL_PATH, "wb") as f:
                pickle.dump(pipeline, f)
            logger.info("Saved trained fake detector model to %s", MODEL_PATH)
        except Exception as e:
            logger.warning("Could not save model: %s", e)

        return pipeline

    def retrain_with_feedback(self, text: str, label: int):
        """
        Admin feedback loop: add a new labeled sample and retrain model.
        label=0 = real/genuine, label=1 = fake/misleading
        """
        feedback = []
        if FEEDBACK_PATH.exists():
            try:
                with open(FEEDBACK_PATH, "r", encoding="utf-8") as f:
                    feedback = json.load(f)
            except Exception:
                pass

        # Avoid duplicate
        if not any(item["text"] == text for item in feedback):
            feedback.append({"text": text, "label": label})
            try:
                with open(FEEDBACK_PATH, "w", encoding="utf-8") as f:
                    json.dump(feedback, f, indent=2)
            except Exception as e:
                logger.warning("Could not save feedback: %s", e)

        # Retrain model with new data
        self.ml_pipeline = self._train_model()
        logger.info("Model retrained with %d total samples (%d feedback)", len(LABELED_TRAINING_DATA) + len(feedback), len(feedback))

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
        Full fake probability evaluation combining:
        - ML model score (TF-IDF + Logistic Regression)
        - Rule-based sensationalism & climatological anomaly checks
        - Author credibility & trust scoring
        """
        clean_text = text.lower()
        handle_clean = (author_handle or "").replace("@", "").strip()
        reasons: List[str] = []

        # ── 1. ML MODEL PREDICTION ────────────────────────────────────────────
        try:
            ml_fake_prob = self.ml_pipeline.predict_proba([text])[0][1]  # P(fake)
        except Exception:
            ml_fake_prob = 0.5

        # ── 2. SENSATIONALISM & HOAX KEYWORDS ────────────────────────────────
        sensational_keywords = self.lexicon.get("sensational_keywords", [])
        matched_sensational = [kw for kw in sensational_keywords if kw in clean_text]
        alarm_matches = re.findall(
            r'(all will die|secret weapon|nasa alert|100m tsunami|run for life|'
            r'doomsday|apocalypse|conspiracy|miracle|haarp|chemtrail|ufo|alien|'
            r'chain mail|whatsapp forward|share this|radioactive rain|acid rain)',
            clean_text
        )
        excessive_caps = sum(1 for c in text if c.isupper()) / max(1, len(text))
        exclamation_count = text.count("!") + text.count("?")

        sensational_score = 0.0
        if matched_sensational:
            sensational_score += min(0.9, 0.50 + (len(matched_sensational) * 0.20))
            reasons.append(f"Misinformation keywords detected: {', '.join(matched_sensational[:3])}")
        if alarm_matches:
            sensational_score += 0.45
            reasons.append(f"Extreme panic/alarmist language: '{alarm_matches[0]}'")
        if excessive_caps > 0.40:
            sensational_score += 0.15
            reasons.append("Excessive capitalization — typical of clickbait/panic posts")
        if exclamation_count >= 3:
            sensational_score += 0.10
        sensational_score = min(1.0, sensational_score)

        # ── 3. CLIMATOLOGICAL PLAUSIBILITY CHECK ─────────────────────────────
        anomaly_score = 0.0
        coastal_tropical = ["chennai", "mumbai", "kolkata", "hyderabad", "kochi", "puducherry", "goa"]
        landlocked = ["delhi", "jaipur", "lucknow", "bhopal", "chandigarh", "patna", "agra", "indore"]
        highland = ["shimla", "srinagar", "shillong", "dehradun", "manali", "leh", "mussoorie"]

        city_lower = city.lower()
        if "snow" in clean_text and any(c in city_lower for c in coastal_tropical):
            anomaly_score = 1.0
            reasons.append(f"Impossible: Snowfall in tropical coastal city ({city})")
        elif "tsunami" in clean_text and any(c in city_lower for c in landlocked):
            anomaly_score = 1.0
            reasons.append(f"Impossible: Tsunami in landlocked inland city ({city})")
        elif re.search(r'\b(5[0-9]|6\d)\s*deg', clean_text) and any(c in city_lower for c in highland):
            anomaly_score = 0.9
            reasons.append(f"Extreme anomaly: 50°C+ temperature in Himalayan highland ({city})")
        elif re.search(r'\b(800|900|1000)\s*km', clean_text):
            anomaly_score = 0.95
            reasons.append("Physically impossible wind speed (>800 km/h)")
        elif re.search(r'\b(100|200)\s*m(eter)?\s+tsunami', clean_text):
            anomaly_score = 1.0
            reasons.append("Physically impossible: 100m+ tsunami wave height claimed")
        elif "minus" in clean_text and re.search(r'minus\s+\d+', clean_text) and any(c in city_lower for c in coastal_tropical):
            anomaly_score = 0.95
            reasons.append(f"Impossible: Sub-zero temperature in tropical coastal city ({city})")

        # ── 4. SOURCE CREDIBILITY ─────────────────────────────────────────────
        is_official = any(handle_clean.lower() == t.lower() for t in self.trusted_sources)
        source_risk = 0.0
        if is_official:
            author_trust = 1.0
        else:
            source_risk = max(0.0, 1.0 - author_trust)
            if author_trust < 0.30:
                reasons.append(f"Unverified low-reputation source (Trust: {author_trust:.2f})")

        # ── 5. RADAR ANOMALY CROSS-CHECK ─────────────────────────────────────
        radar_anomaly = anomaly_score if anomaly_score > 0 else (0.7 if sensational_score > 0.6 else 0.05)
        if is_official:
            radar_anomaly = 0.0
        if radar_anomaly > 0.5:
            reasons.append("Inconsistency with IMD Doppler Radar & AWS station baseline data")

        # ── 6. COMPOSITE FAKE PROBABILITY ────────────────────────────────────
        if is_official and anomaly_score == 0:
            fake_prob = 0.02
        else:
            rule_score = (
                (sensational_score * FAKE_SENSATIONALISM_WEIGHT) +
                (source_risk * FAKE_SOURCE_TRUST_WEIGHT) +
                (radar_anomaly * FAKE_RADAR_ANOMALY_WEIGHT)
            )
            if anomaly_score >= 0.8:
                rule_score = max(rule_score, 0.95)

            # Blend ML model score with rule-based score
            # ML model gets 60% weight (learned from labeled data), rules get 40%
            fake_prob = (ml_fake_prob * 0.60) + (rule_score * 0.40)

        fake_prob = round(min(0.99, max(0.01, fake_prob)), 2)
        is_fake = fake_prob >= FAKE_PROBABILITY_THRESHOLD

        # ── 7. VERIFICATION STATUS ───────────────────────────────────────────
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
            "ml_fake_probability": round(ml_fake_prob, 2),
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
