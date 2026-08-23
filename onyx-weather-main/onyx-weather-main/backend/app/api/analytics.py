"""
Big Data Analytics API Router
Provides aggregated metrics, time-series distributions, state vulnerability indexes,
and AI verification insights.
"""
from fastapi import APIRouter
from ..database import get_db_connection
from ..ingestion.imd_api_client import get_all_radar_stations

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/summary")
def get_analytics_summary():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. High Level Ingestion Counters
    cursor.execute("SELECT COUNT(*) as total FROM weather_reports;")
    total_reports = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as verified FROM weather_reports WHERE verification_status IN ('verified_imd', 'verified_ai', 'citizen_corroborated');")
    total_verified = cursor.fetchone()["verified"]

    cursor.execute("SELECT COUNT(*) as fake FROM weather_reports WHERE verification_status = 'fake_misleading';")
    total_fake = cursor.fetchone()["fake"]

    cursor.execute("SELECT COUNT(*) as pending FROM weather_reports WHERE verification_status = 'under_review';")
    total_pending = cursor.fetchone()["pending"]

    cursor.execute("SELECT COUNT(DISTINCT duplicate_cluster_id) as unique_clusters FROM weather_reports WHERE duplicate_cluster_id IS NOT NULL;")
    unique_clusters = cursor.fetchone()["unique_clusters"]

    # 2. Event Type Distribution
    cursor.execute("""
        SELECT event_type, COUNT(*) as count
        FROM weather_reports
        GROUP BY event_type
        ORDER BY count DESC;
    """)
    event_distribution = {r["event_type"]: r["count"] for r in cursor.fetchall()}

    # 3. Verification Status Distribution
    cursor.execute("""
        SELECT verification_status, COUNT(*) as count
        FROM weather_reports
        GROUP BY verification_status;
    """)
    status_distribution = {r["verification_status"]: r["count"] for r in cursor.fetchall()}

    # 4. Source Distribution
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM weather_reports
        GROUP BY source
        ORDER BY count DESC;
    """)
    source_distribution = {r["source"]: r["count"] for r in cursor.fetchall()}

    # 5. State-wise Breakdown (Top Vulnerability Zones)
    cursor.execute("""
        SELECT state, COUNT(*) as count,
               SUM(CASE WHEN event_type IN ('flooding', 'cyclone', 'hailstorm') THEN 1 ELSE 0 END) as severe_count
        FROM weather_reports
        GROUP BY state
        ORDER BY count DESC
        LIMIT 15;
    """)
    state_breakdown = [dict(r) for r in cursor.fetchall()]

    # 6. Active Emergency Alerts
    cursor.execute("SELECT COUNT(*) as active_alerts FROM emergency_alerts WHERE status = 'active';")
    active_alerts = cursor.fetchone()["active_alerts"]

    # Calculations
    dedup_saved = max(0, total_reports - unique_clusters) if total_reports and unique_clusters else 0
    dedup_rate_pct = round((dedup_saved / max(1, total_reports)) * 100, 1)
    fake_interception_rate_pct = round((total_fake / max(1, total_reports)) * 100, 1)

    conn.close()

    return {
        "total_reports": total_reports,
        "total_verified": total_verified,
        "total_fake_intercepted": total_fake,
        "total_under_review": total_pending,
        "active_emergency_alerts": active_alerts,
        "deduplication_reduction_pct": dedup_rate_pct,
        "fake_interception_rate_pct": fake_interception_rate_pct,
        "event_distribution": event_distribution,
        "status_distribution": status_distribution,
        "source_distribution": source_distribution,
        "state_breakdown": state_breakdown,
        "radar_stations": get_all_radar_stations()
    }

@router.get("/timeline")
def get_timeline_stats():
    """Generates hourly or daily volume time-series for Chart.js rendering."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT strftime('%Y-%m-%dT%H:00:00', timestamp) as hour_bucket,
               COUNT(*) as count,
               SUM(CASE WHEN verification_status = 'fake_misleading' THEN 1 ELSE 0 END) as fake_count,
               SUM(CASE WHEN verification_status IN ('verified_imd', 'verified_ai') THEN 1 ELSE 0 END) as verified_count
        FROM weather_reports
        GROUP BY hour_bucket
        ORDER BY hour_bucket DESC
        LIMIT 24;
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    rows.reverse()
    conn.close()

    return {
        "timeline": rows
    }
