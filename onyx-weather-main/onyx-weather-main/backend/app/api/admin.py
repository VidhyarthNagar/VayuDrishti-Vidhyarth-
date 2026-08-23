"""
Admin Command Center & Moderation API Router
Handles role-based security authentication, manual moderation, CAP emergency broadcasts, simulation triggers, and audit logs.
"""
import os
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Header, Depends, status
from ..config import DATA_DIR, ADMIN_USERNAME, ADMIN_DEFAULT_PASSWORD, ADMIN_TOKEN
from ..database import get_db_connection
from ..ingestion.generator import scenario_generator
from ..ingestion.live_fetcher import live_fetcher, get_api_keys, save_api_keys

router = APIRouter(prefix="/api/admin", tags=["Admin"])

AUTH_FILE = DATA_DIR / "admin_auth.json"

def get_current_admin_credentials() -> Dict[str, str]:
    creds = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_DEFAULT_PASSWORD,
        "token": ADMIN_TOKEN
    }
    if AUTH_FILE.exists():
        try:
            with open(AUTH_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if saved.get("password"): creds["password"] = saved["password"]
                if saved.get("username"): creds["username"] = saved["username"]
                if saved.get("token"): creds["token"] = saved["token"]
        except Exception:
            pass
    return creds

def save_admin_credentials(username: str, password: str):
    creds = get_current_admin_credentials()
    creds["username"] = username
    creds["password"] = password
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(AUTH_FILE, "w", encoding="utf-8") as f:
            json.dump(creds, f, indent=2)
    except Exception:
        pass

def verify_admin(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """FastAPI Dependency: verifies administrative session token."""
    creds = get_current_admin_credentials()
    valid_token = creds["token"]

    token_candidate = None
    if x_admin_token:
        token_candidate = x_admin_token.strip()
    elif authorization and authorization.startswith("Bearer "):
        token_candidate = authorization.split("Bearer ", 1)[1].strip()

    if not token_candidate or token_candidate != valid_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access Denied: Administrative authentication token required.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return True

# --- Authentication Endpoints ---

class AdminLoginRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    passcode: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/login")
def admin_login(req: AdminLoginRequest):
    creds = get_current_admin_credentials()
    input_pass = req.password or req.passcode or ""
    input_user = req.username or "admin"

    if input_pass == creds["password"] and (input_user == creds["username"] or not req.username):
        return {
            "success": True,
            "token": creds["token"],
            "admin_user": "IMD_Operations_HQ",
            "message": "Administrative authentication successful."
        }
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid administrative username or security passcode."
    )

@router.get("/verify-session")
def verify_session(auth: bool = Depends(verify_admin)):
    return {"valid": True, "user": "IMD_Operations_HQ"}

@router.post("/change-password")
def change_password(req: ChangePasswordRequest, auth: bool = Depends(verify_admin)):
    creds = get_current_admin_credentials()
    if req.old_password != creds["password"]:
        raise HTTPException(status_code=400, detail="Current password incorrect.")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters.")
    
    save_admin_credentials(creds["username"], req.new_password)
    return {"success": True, "message": "Admin password updated successfully."}

# --- Protected Admin Operations ---

class ApiKeysUpdateRequest(BaseModel):
    OPENWEATHER_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None
    WEATHERAPI_KEY: Optional[str] = None
    GNEWS_API_KEY: Optional[str] = None

@router.get("/api-keys")
def get_configured_api_keys(auth: bool = Depends(verify_admin)):
    keys = get_api_keys()
    masked = {}
    for k, v in keys.items():
        masked[k] = (v[:4] + "..." + v[-4:]) if len(v) > 8 else ("Configured" if v else "Not Set")
    return {"keys": masked, "raw_status": {k: bool(v) for k, v in keys.items()}}

@router.post("/api-keys")
def update_api_keys(req: ApiKeysUpdateRequest, auth: bool = Depends(verify_admin)):
    updates = {}
    if req.OPENWEATHER_API_KEY is not None: updates["OPENWEATHER_API_KEY"] = req.OPENWEATHER_API_KEY.strip()
    if req.NEWS_API_KEY is not None: updates["NEWS_API_KEY"] = req.NEWS_API_KEY.strip()
    if req.WEATHERAPI_KEY is not None: updates["WEATHERAPI_KEY"] = req.WEATHERAPI_KEY.strip()
    if req.GNEWS_API_KEY is not None: updates["GNEWS_API_KEY"] = req.GNEWS_API_KEY.strip()
    save_api_keys(updates)
    return {"success": True, "message": "API keys successfully updated and saved."}

@router.post("/sync-live-apis")
def sync_live_apis_endpoint(auth: bool = Depends(verify_admin)):
    result = live_fetcher.sync_all_live_sources()
    return result

class ModerationActionRequest(BaseModel):
    report_id: str
    action: str # 'approve', 'mark_fake', 'merge_cluster', 'delete'
    admin_user: str = "Admin_IMD_HQ"
    reason: Optional[str] = "Manual administrative review"
    target_cluster_id: Optional[str] = None

class EmergencyAlertRequest(BaseModel):
    title: str
    event_type: str
    severity: str
    state: str
    districts: List[str]
    instructions: str
    issued_by: str = "IMD National Disaster Command"
    valid_hours: int = 24

class TriggerScenarioRequest(BaseModel):
    scenario: str

@router.post("/moderate")
def moderate_report(req: ModerationActionRequest, auth: bool = Depends(verify_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM weather_reports WHERE id = ?;", (req.report_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Report not found")

    prev_status = row["verification_status"]
    now_str = datetime.now(timezone.utc).isoformat()

    if req.action == "approve":
        new_status = "verified_imd"
        cursor.execute("""
            UPDATE weather_reports
            SET verification_status = ?, fake_probability = 0.02, admin_notes = ?
            WHERE id = ?;
        """, (new_status, f"Manually verified by {req.admin_user}: {req.reason}", req.report_id))

    elif req.action == "mark_fake":
        new_status = "fake_misleading"
        cursor.execute("""
            UPDATE weather_reports
            SET verification_status = ?, fake_probability = 0.99, admin_notes = ?
            WHERE id = ?;
        """, (new_status, f"Manually flagged FAKE by {req.admin_user}: {req.reason}", req.report_id))

    elif req.action == "merge_cluster":
        new_status = prev_status
        target_cluster = req.target_cluster_id or f"CLUS-MERGED-{uuid.uuid4().hex[:6]}"
        cursor.execute("""
            UPDATE weather_reports
            SET duplicate_cluster_id = ?, is_cluster_primary = 0, admin_notes = ?
            WHERE id = ?;
        """, (target_cluster, f"Merged into cluster {target_cluster} by {req.admin_user}", req.report_id))

    elif req.action == "delete":
        cursor.execute("DELETE FROM weather_reports WHERE id = ?;", (req.report_id,))
        new_status = "deleted"
    else:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid action")

    # Record Audit Trail
    cursor.execute("""
        INSERT INTO moderation_logs (report_id, action, admin_user, timestamp, reason, previous_status, new_status)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (req.report_id, req.action, req.admin_user, now_str, req.reason, prev_status, new_status))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "report_id": req.report_id,
        "action": req.action,
        "new_status": new_status,
        "timestamp": now_str
    }

@router.post("/broadcast-alert")
def broadcast_emergency_alert(req: EmergencyAlertRequest, auth: bool = Depends(verify_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    alert_id = f"CAP-ALERT-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()
    expires_str = (now + timedelta(hours=req.valid_hours)).isoformat()

    cursor.execute("""
        INSERT INTO emergency_alerts (
            id, title, event_type, severity, state, districts, instructions, issued_by, issued_at, expires_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active');
    """, (
        alert_id,
        req.title,
        req.event_type,
        req.severity,
        req.state,
        json.dumps(req.districts),
        req.instructions,
        req.issued_by,
        now_str,
        expires_str
    ))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "alert_id": alert_id,
        "title": req.title,
        "issued_at": now_str,
        "expires_at": expires_str
    }

@router.get("/alerts")
def get_active_alerts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM emergency_alerts ORDER BY issued_at DESC LIMIT 50;")
    rows = [dict(r) for r in cursor.fetchall()]
    for r in rows:
        try:
            r["districts"] = json.loads(r["districts"])
        except Exception:
            r["districts"] = [r["districts"]]
    conn.close()
    return {"alerts": rows}

@router.post("/trigger-scenario")
def trigger_scenario(req: TriggerScenarioRequest, auth: bool = Depends(verify_admin)):
    generated = scenario_generator.trigger_scenario(req.scenario)
    return {
        "success": True,
        "scenario": req.scenario,
        "generated_reports_count": len(generated),
        "reports": generated
    }

@router.get("/moderation-logs")
def get_moderation_logs(limit: int = 50, auth: bool = Depends(verify_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM moderation_logs ORDER BY timestamp DESC LIMIT ?;", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"logs": rows}
