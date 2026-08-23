"""
Citizen Weather Watcher Portal API Router
Supports crowdsourced weather reporting with GPS geolocation, photo/media attachments,
and instant real-time AI validation feedback.
"""
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from ..ml_pipeline.pipeline import ingestion_pipeline
from ..ml_pipeline.classifier import weather_classifier
from ..ml_pipeline.fake_detector import fake_detector

router = APIRouter(prefix="/api/citizen", tags=["Citizen"])

class CitizenReportSubmission(BaseModel):
    author_name: str
    author_phone_or_email: Optional[str] = "Anonymous"
    text: str
    city: str
    state: str
    district: Optional[str] = None
    lat: float
    lon: float
    event_type: Optional[str] = None
    severity: Optional[str] = None
    media_url: Optional[str] = None
    hashtags: Optional[List[str]] = ["#CitizenReport", "#IMD"]

class PreviewValidationRequest(BaseModel):
    text: str
    city: str
    state: str

@router.post("/preview")
def preview_ai_validation(req: PreviewValidationRequest):
    """
    Provides real-time feedback to citizen reporters before final submission,
    displaying estimated event category, trust confidence, and anomaly check.
    """
    predicted_event, confidence, severity = weather_classifier.classify(req.text)
    fake_eval = fake_detector.evaluate(
        text=req.text,
        author_handle="@CitizenUser",
        author_trust=0.85,
        city=req.city,
        state=req.state,
        event_type=predicted_event
    )

    return {
        "predicted_event_type": predicted_event,
        "estimated_severity": severity,
        "ai_confidence_pct": round(confidence * 100, 1),
        "fake_risk_level": "High Risk (Misinformation Flagged)" if fake_eval["is_fake_flagged"] else (
            "Medium (Pending Review)" if fake_eval["fake_probability"] > 0.4 else "Low Risk (High Trust)"
        ),
        "fake_probability_pct": round(fake_eval["fake_probability"] * 100, 1),
        "radar_consistency": fake_eval["radar_cross_verified"],
        "diagnostic_notes": fake_eval["explanation_reasons"]
    }

@router.post("/submit")
def submit_citizen_report(req: CitizenReportSubmission):
    if len(req.text.strip()) < 5:
        raise HTTPException(status_code=400, detail="Report description is too short")

    # Anonymous citizen reporters get a lower starting trust score so the ML
    # fake detector is appropriately skeptical. Verified media orgs get higher trust.
    is_anonymous = req.author_name.strip().lower() in ("anonymous", "anon", "", "citizen")
    trust_score = 0.55 if is_anonymous else 0.72

    raw_payload = {
        "source": "Citizen Report",
        "author_handle": f"@Citizen_{abs(hash(req.author_name)) % 9000 + 1000}",
        "author_name": req.author_name if not is_anonymous else "Anonymous Citizen",
        "author_trust_score": trust_score,
        "text": req.text,
        "hashtags": req.hashtags or ["#CitizenReport", "#IMD"],
        "city": req.city,
        "district": req.district or req.city,
        "state": req.state,
        "lat": req.lat,
        "lon": req.lon,
        "event_type": req.event_type,
        "severity": req.severity,
        "media_type": "image" if req.media_url else "none",
        "media_url": req.media_url or ""
    }

    processed = ingestion_pipeline.process_raw_report(raw_payload)
    return {
        "success": True,
        "message": "Citizen weather report successfully submitted and processed by AI verification pipeline.",
        "report": processed
    }
