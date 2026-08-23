"""
Unified AI/ML Ingestion & Intelligence Pipeline
Chains classification, spatiotemporal deduplication, fake detection, and persistence.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from .classifier import weather_classifier
from .fake_detector import fake_detector
from .deduplicator import deduplication_engine
from ..database import get_db_connection, save_report

logger = logging.getLogger("ml_pipeline")

class IngestionPipeline:
    def __init__(self):
        self.classifier = weather_classifier
        self.fake_detector = fake_detector
        self.deduplicator = deduplication_engine

    def _get_recent_reports(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, city, state, lat, lon, event_type, text, duplicate_cluster_id, cluster_size
            FROM weather_reports
            ORDER BY timestamp DESC
            LIMIT ?;
        """, (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def process_raw_report(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes raw incoming unstructured report data and runs it through the full AI/ML pipeline.
        """
        report_id = raw.get("id") or f"RPT-IN-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
        text = raw.get("text", "").strip()
        author_handle = raw.get("author_handle", "@Citizen")
        author_trust = float(raw.get("author_trust_score", 0.8))
        city = raw.get("city", "Mumbai")
        state = raw.get("state", "Maharashtra")
        lat = float(raw.get("lat", 19.0760))
        lon = float(raw.get("lon", 72.8777))
        source = raw.get("source", "Citizen Report")
        timestamp = raw.get("timestamp") or datetime.now(timezone.utc).isoformat()
        hashtags = raw.get("hashtags", ["#IMD"])

        # 1. Weather Event Classification & Severity Estimation
        if not raw.get("event_type"):
            event_type, ai_conf, severity = self.classifier.classify(text)
        else:
            event_type = raw.get("event_type")
            _, ai_conf, auto_sev = self.classifier.classify(text)
            severity = raw.get("severity") or auto_sev

        # 2. Fake & Misleading Detection
        fake_result = self.fake_detector.evaluate(
            text=text,
            author_handle=author_handle,
            author_trust=author_trust,
            city=city,
            state=state,
            event_type=event_type
        )
        fake_probability = fake_result["fake_probability"]
        is_fake = fake_result["is_fake_flagged"]
        recommended_status = fake_result["recommended_status"]
        radar_cross_verified = 1 if fake_result["radar_cross_verified"] else 0

        # 3. Deduplication against recent spatial-temporal window
        recent = self._get_recent_reports(limit=40)
        temp_report = {
            "id": report_id,
            "text": text,
            "city": city,
            "state": state,
            "lat": lat,
            "lon": lon,
            "timestamp": timestamp,
            "event_type": event_type
        }
        dedup_result = self.deduplicator.process_new_report(temp_report, recent)

        # 4. Assemble Final Enriched Model
        notes = []
        if is_fake:
            notes.append(f"AI FLAGGED: {', '.join(fake_result['explanation_reasons'])}")
        elif dedup_result.get("admin_notes"):
            notes.append(dedup_result["admin_notes"])
        elif raw.get("admin_notes"):
            notes.append(raw["admin_notes"])

        final_report = {
            "id": report_id,
            "source": source,
            "author_handle": author_handle,
            "author_name": raw.get("author_name", author_handle.replace("@", "")),
            "author_trust_score": author_trust,
            "text": text,
            "hashtags": hashtags if isinstance(hashtags, list) else [hashtags],
            "timestamp": timestamp,
            "city": city,
            "district": raw.get("district", city),
            "state": state,
            "lat": lat,
            "lon": lon,
            "event_type": event_type,
            "severity": severity,
            "media_type": raw.get("media_type", "image" if raw.get("media_url") else "none"),
            "media_url": raw.get("media_url", ""),
            "verification_status": raw.get("verification_status") or recommended_status,
            "ai_confidence": round(ai_conf, 2),
            "fake_probability": fake_probability,
            "duplicate_cluster_id": dedup_result.get("duplicate_cluster_id"),
            "is_cluster_primary": dedup_result.get("is_cluster_primary", True),
            "cluster_size": dedup_result.get("cluster_size", 1),
            "radar_cross_verified": radar_cross_verified,
            "admin_notes": " | ".join(notes),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # 5. Persist to Big Data Central Database
        save_report(final_report)
        logger.info("Processed & Saved Report %s [%s - %s] Status: %s", report_id, city, event_type, final_report["verification_status"])

        return final_report

# Global singleton pipeline instance
ingestion_pipeline = IngestionPipeline()
