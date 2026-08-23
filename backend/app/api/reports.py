"""
Reports API Router
Provides high-performance multi-dimensional querying and filtering:
- Date-wise (Start/End dates, Presets: today, 24h, 7d, 30d)
- Event-wise (Rainfall, Flooding, Thunderstorm, Heatwave, Fog, Dust Storm, Cyclone, Hailstorm)
- Location-wise (State, District, City, Bounding Box)
- Verification Status (verified_imd, verified_ai, under_review, fake_misleading, citizen_corroborated)
- Source filter (Twitter/X, Citizen Report, IMD Radar, Public API, RSS Feed)
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from ..database import get_db_connection

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.get("")
def get_reports(
    start_date: Optional[str] = Query(None, description="ISO Start date e.g. 2024-01-01"),
    end_date: Optional[str] = Query(None, description="ISO End date e.g. 2024-12-31"),
    preset_range: Optional[str] = Query(None, description="'today', '24h', '7d', '30d', 'all'"),
    event_type: Optional[str] = Query(None, description="Comma-separated event types e.g. 'rainfall,flooding'"),
    state: Optional[str] = Query(None, description="Indian State e.g. 'Maharashtra'"),
    city: Optional[str] = Query(None, description="City name e.g. 'Mumbai'"),
    status: Optional[str] = Query(None, description="Verification status e.g. 'verified_imd,verified_ai'"),
    source: Optional[str] = Query(None, description="Source filter e.g. 'Twitter/X'"),
    search: Optional[str] = Query(None, description="Text search in report text or hashtags"),
    only_primaries: bool = Query(False, description="If true, only return primary cluster reports"),
    min_lat: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    min_lon: Optional[float] = Query(None),
    max_lon: Optional[float] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    conditions = []
    params = []

    # 1. Preset or custom Date-wise filtering
    now = datetime.now(timezone.utc)
    if preset_range == "24h" or preset_range == "today":
        since_time = (now - timedelta(hours=24)).isoformat()
        conditions.append("timestamp >= ?")
        params.append(since_time)
    elif preset_range == "7d":
        since_time = (now - timedelta(days=7)).isoformat()
        conditions.append("timestamp >= ?")
        params.append(since_time)
    elif preset_range == "30d":
        since_time = (now - timedelta(days=30)).isoformat()
        conditions.append("timestamp >= ?")
        params.append(since_time)
    else:
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date)

    # 2. Event-wise filtering
    if event_type and event_type != "all":
        types = [t.strip().lower() for t in event_type.split(",") if t.strip()]
        if types:
            placeholders = ",".join(["?"] * len(types))
            conditions.append(f"event_type IN ({placeholders})")
            params.extend(types)

    # 3. Location-wise filtering
    if state and state != "all":
        conditions.append("LOWER(state) = LOWER(?)")
        params.append(state.strip())

    if city and city != "all":
        conditions.append("LOWER(city) = LOWER(?)")
        params.append(city.strip())

    # Bounding box
    if min_lat is not None and max_lat is not None and min_lon is not None and max_lon is not None:
        conditions.append("lat >= ? AND lat <= ? AND lon >= ? AND lon <= ?")
        params.extend([min_lat, max_lat, min_lon, max_lon])

    # 4. Verification Status filtering
    if status and status != "all":
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        if statuses:
            placeholders = ",".join(["?"] * len(statuses))
            conditions.append(f"verification_status IN ({placeholders})")
            params.extend(statuses)

    # 5. Source filtering
    if source and source != "all":
        conditions.append("LOWER(source) = LOWER(?)")
        params.append(source.strip())

    # 6. Text Search query
    if search:
        conditions.append("(text LIKE ? OR hashtags LIKE ? OR city LIKE ?)")
        search_pattern = f"%{search.strip()}%"
        params.extend([search_pattern, search_pattern, search_pattern])

    # 7. Deduplication primary filter
    if only_primaries:
        conditions.append("is_cluster_primary = 1")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Total Count query
    count_query = f"SELECT COUNT(*) as total FROM weather_reports {where_clause};"
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()["total"]

    # Data query
    data_query = f"""
        SELECT * FROM weather_reports
        {where_clause}
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?;
    """
    params.extend([limit, offset])
    cursor.execute(data_query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    # Format JSON fields
    for r in rows:
        try:
            r["hashtags"] = json.loads(r["hashtags"]) if r.get("hashtags") else []
        except Exception:
            r["hashtags"] = [r["hashtags"]] if r.get("hashtags") else []
        r["is_cluster_primary"] = bool(r.get("is_cluster_primary", 1))
        r["radar_cross_verified"] = bool(r.get("radar_cross_verified", 1))

    conn.close()

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "reports": rows
    }

@router.get("/{report_id}")
def get_report_by_id(report_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM weather_reports WHERE id = ?;", (report_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Weather report not found")

    report = dict(row)
    try:
        report["hashtags"] = json.loads(report["hashtags"]) if report.get("hashtags") else []
    except Exception:
        report["hashtags"] = []
    report["is_cluster_primary"] = bool(report.get("is_cluster_primary", 1))
    report["radar_cross_verified"] = bool(report.get("radar_cross_verified", 1))

    return report
