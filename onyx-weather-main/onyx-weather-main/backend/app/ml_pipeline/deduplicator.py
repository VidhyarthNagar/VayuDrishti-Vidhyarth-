import math
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from ..config import (
    DEDUP_DISTANCE_KM_THRESHOLD,
    DEDUP_TIME_WINDOW_MINUTES,
    DEDUP_SEMANTIC_SIMILARITY_THRESHOLD
)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in kilometers."""
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def parse_iso_time(time_str: str) -> datetime:
    try:
        clean_time = time_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_time)
    except Exception:
        return datetime.now(timezone.utc)

class DeduplicationEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words="english")

    def process_new_report(
        self,
        new_report: Dict[str, Any],
        recent_reports: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Checks if new_report is a duplicate of any recent report in the same spatial-temporal bucket.
        Returns updated report dictionary with:
          - duplicate_cluster_id
          - is_cluster_primary (bool)
          - cluster_size (int)
          - deduplication_match_id (optional matching report id)
        """
        if not recent_reports:
            cluster_id = f"CLUS-{new_report.get('city', 'IND')[:3].upper()}-{uuid.uuid4().hex[:6]}"
            new_report["duplicate_cluster_id"] = cluster_id
            new_report["is_cluster_primary"] = True
            new_report["cluster_size"] = 1
            return new_report

        new_lat = float(new_report.get("lat", 0.0))
        new_lon = float(new_report.get("lon", 0.0))
        new_time = parse_iso_time(new_report.get("timestamp", datetime.utcnow().isoformat()))
        new_text = new_report.get("text", "")

        # 1. Filter candidates by Spatiotemporal proximity
        spatial_candidates = []
        for rep in recent_reports:
            rep_lat = float(rep.get("lat", 0.0))
            rep_lon = float(rep.get("lon", 0.0))
            rep_time = parse_iso_time(rep.get("timestamp", datetime.utcnow().isoformat()))

            dist_km = haversine_distance(new_lat, new_lon, rep_lat, rep_lon)
            time_diff_mins = abs((new_time - rep_time).total_seconds()) / 60.0

            if dist_km <= DEDUP_DISTANCE_KM_THRESHOLD and time_diff_mins <= DEDUP_TIME_WINDOW_MINUTES:
                spatial_candidates.append((rep, dist_km, time_diff_mins))

        if not spatial_candidates:
            cluster_id = f"CLUS-{new_report.get('city', 'IND')[:3].upper()}-{uuid.uuid4().hex[:6]}"
            new_report["duplicate_cluster_id"] = cluster_id
            new_report["is_cluster_primary"] = True
            new_report["cluster_size"] = 1
            return new_report

        # 2. Semantic text similarity check on spatial candidates
        candidate_texts = [c[0].get("text", "") for c in spatial_candidates]
        all_texts = [new_text] + candidate_texts

        try:
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            sim_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
        except Exception:
            sim_scores = [0.0] * len(candidate_texts)

        # Check best match
        best_match_idx = -1
        best_sim = 0.0
        for i, sim in enumerate(sim_scores):
            if sim > best_sim:
                best_sim = sim
                best_match_idx = i

        # If similarity exceeds threshold or same event and very close proximity (< 1km)
        matched = False
        if best_match_idx >= 0:
            matched_rep, dist_km, time_diff = spatial_candidates[best_match_idx]
            is_same_event = new_report.get("event_type") == matched_rep.get("event_type")

            if best_sim >= DEDUP_SEMANTIC_SIMILARITY_THRESHOLD or (is_same_event and dist_km <= 1.5 and time_diff <= 20.0):
                matched = True
                cluster_id = matched_rep.get("duplicate_cluster_id") or f"CLUS-{new_report.get('city', 'IND')[:3].upper()}-{uuid.uuid4().hex[:6]}"
                new_report["duplicate_cluster_id"] = cluster_id
                new_report["is_cluster_primary"] = False
                new_report["cluster_size"] = int(matched_rep.get("cluster_size", 1)) + 1
                new_report["admin_notes"] = f"Deduplicated: Corroborates cluster {cluster_id} (Distance {dist_km:.2f}km, Text Sim: {best_sim:.2f})."
                return new_report

        # No duplicate matched -> Establish as new cluster primary
        cluster_id = f"CLUS-{new_report.get('city', 'IND')[:3].upper()}-{uuid.uuid4().hex[:6]}"
        new_report["duplicate_cluster_id"] = cluster_id
        new_report["is_cluster_primary"] = True
        new_report["cluster_size"] = 1
        return new_report

# Global singleton deduplicator
deduplication_engine = DeduplicationEngine()
