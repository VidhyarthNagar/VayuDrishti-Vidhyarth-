"""
Export API Router
Enables downloading filtered datasets and intelligence summaries in CSV, JSON, and formatted text/report formats.
"""
import io
import csv
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Query, Response
from ..database import get_db_connection

router = APIRouter(prefix="/api/export", tags=["Export"])

@router.get("/csv")
def export_csv(
    event_type: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    conditions = []
    params = []
    if event_type and event_type != "all":
        conditions.append("event_type = ?")
        params.append(event_type.lower())
    if state and state != "all":
        conditions.append("LOWER(state) = LOWER(?)")
        params.append(state)
    if status and status != "all":
        conditions.append("verification_status = ?")
        params.append(status)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    cursor.execute(f"SELECT * FROM weather_reports {where_clause} ORDER BY timestamp DESC LIMIT 2000;", params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    output = io.StringIO()
    if rows:
        headers = list(rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    else:
        output.write("No matching weather reports found.")

    csv_data = output.getvalue()
    filename = f"imd_weather_bigdata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/json")
def export_json(
    event_type: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    conditions = []
    params = []
    if event_type and event_type != "all":
        conditions.append("event_type = ?")
        params.append(event_type.lower())
    if state and state != "all":
        conditions.append("LOWER(state) = LOWER(?)")
        params.append(state)
    if status and status != "all":
        conditions.append("verification_status = ?")
        params.append(status)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    cursor.execute(f"SELECT * FROM weather_reports {where_clause} ORDER BY timestamp DESC LIMIT 2000;", params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    for r in rows:
        try:
            r["hashtags"] = json.loads(r["hashtags"]) if r.get("hashtags") else []
        except Exception:
            r["hashtags"] = []

    json_str = json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "count": len(rows), "data": rows}, indent=2)
    filename = f"imd_weather_intelligence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
