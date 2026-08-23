"""
Database Engine & Repository for National Weather Big Data Analytics Platform
Uses SQLite with WAL mode, indexing, and JSON fields for fast querying.
"""
import sqlite3
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from .config import DB_PATH, DATA_DIR

logger = logging.getLogger("weather_db")

def get_db_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Weather Reports Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weather_reports (
        id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        author_handle TEXT,
        author_name TEXT,
        author_trust_score REAL DEFAULT 0.8,
        text TEXT NOT NULL,
        hashtags TEXT, -- JSON array
        timestamp TEXT NOT NULL,
        city TEXT NOT NULL,
        district TEXT,
        state TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        event_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        media_type TEXT DEFAULT 'none',
        media_url TEXT,
        verification_status TEXT NOT NULL, -- 'verified_imd', 'verified_ai', 'under_review', 'fake_misleading', 'citizen_corroborated'
        ai_confidence REAL DEFAULT 0.85,
        fake_probability REAL DEFAULT 0.05,
        duplicate_cluster_id TEXT,
        is_cluster_primary INTEGER DEFAULT 1,
        cluster_size INTEGER DEFAULT 1,
        radar_cross_verified INTEGER DEFAULT 1,
        admin_notes TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # Indexes for lightning fast multi-dimensional analytics & filters
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_time ON weather_reports(timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_event ON weather_reports(event_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_state ON weather_reports(state);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_city ON weather_reports(city);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_status ON weather_reports(verification_status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_cluster ON weather_reports(duplicate_cluster_id);")

    # 2. Emergency Alerts & CAP Broadcasts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emergency_alerts (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        event_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        state TEXT NOT NULL,
        districts TEXT NOT NULL, -- JSON array
        instructions TEXT NOT NULL,
        issued_by TEXT NOT NULL,
        issued_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        status TEXT DEFAULT 'active'
    );
    """)

    # 3. Moderation Audit Trail Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS moderation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id TEXT NOT NULL,
        action TEXT NOT NULL, -- 'approve', 'mark_fake', 'merge_duplicate', 'escalate_alert'
        admin_user TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        reason TEXT,
        previous_status TEXT,
        new_status TEXT
    );
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully at %s", DB_PATH)

def seed_database_if_empty():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM weather_reports;")
    row = cursor.fetchone()
    count = row["count"] if row else 0

    if count == 0:
        seed_file = DATA_DIR / "seed_data.json"
        if seed_file.exists():
            with open(seed_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                reports = data.get("reports", [])
                now_str = datetime.now(timezone.utc).isoformat()

                for r in reports:
                    cursor.execute("""
                    INSERT OR REPLACE INTO weather_reports (
                        id, source, author_handle, author_name, author_trust_score,
                        text, hashtags, timestamp, city, district, state,
                        lat, lon, event_type, severity, media_type, media_url,
                        verification_status, ai_confidence, fake_probability,
                        duplicate_cluster_id, is_cluster_primary, cluster_size,
                        radar_cross_verified, admin_notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        r.get("id"),
                        r.get("source", "Twitter/X"),
                        r.get("author_handle", "@WeatherWatcher"),
                        r.get("author_name", "Anonymous"),
                        r.get("author_trust_score", 0.8),
                        r.get("text", ""),
                        json.dumps(r.get("hashtags", ["#IMD"])),
                        r.get("timestamp", now_str),
                        r.get("city", "Mumbai"),
                        r.get("district", r.get("city", "Mumbai")),
                        r.get("state", "Maharashtra"),
                        r.get("lat", 19.0760),
                        r.get("lon", 72.8777),
                        r.get("event_type", "rainfall"),
                        r.get("severity", "Moderate"),
                        r.get("media_type", "image"),
                        r.get("media_url", ""),
                        r.get("verification_status", "verified_ai"),
                        r.get("ai_confidence", 0.9),
                        r.get("fake_probability", 0.05),
                        r.get("duplicate_cluster_id"),
                        1 if r.get("is_cluster_primary", True) else 0,
                        r.get("cluster_size", 1),
                        1 if r.get("radar_cross_verified", True) else 0,
                        r.get("admin_notes", ""),
                        now_str
                    ))
                conn.commit()
                logger.info("Seeded %d reports into database.", len(reports))

    conn.close()

def save_report(report_dict: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    if not report_dict.get("created_at"):
        report_dict["created_at"] = now_str

    hashtags_val = report_dict.get("hashtags", [])
    if isinstance(hashtags_val, list):
        hashtags_json = json.dumps(hashtags_val)
    else:
        hashtags_json = str(hashtags_val)

    cursor.execute("""
    INSERT OR REPLACE INTO weather_reports (
        id, source, author_handle, author_name, author_trust_score,
        text, hashtags, timestamp, city, district, state,
        lat, lon, event_type, severity, media_type, media_url,
        verification_status, ai_confidence, fake_probability,
        duplicate_cluster_id, is_cluster_primary, cluster_size,
        radar_cross_verified, admin_notes, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        report_dict["id"],
        report_dict.get("source", "Citizen Report"),
        report_dict.get("author_handle", "@Citizen"),
        report_dict.get("author_name", "Citizen"),
        report_dict.get("author_trust_score", 0.8),
        report_dict["text"],
        hashtags_json,
        report_dict.get("timestamp", now_str),
        report_dict["city"],
        report_dict.get("district", report_dict["city"]),
        report_dict["state"],
        float(report_dict["lat"]),
        float(report_dict["lon"]),
        report_dict["event_type"],
        report_dict.get("severity", "Moderate"),
        report_dict.get("media_type", "none"),
        report_dict.get("media_url", ""),
        report_dict.get("verification_status", "verified_ai"),
        float(report_dict.get("ai_confidence", 0.85)),
        float(report_dict.get("fake_probability", 0.05)),
        report_dict.get("duplicate_cluster_id"),
        1 if report_dict.get("is_cluster_primary", True) else 0,
        int(report_dict.get("cluster_size", 1)),
        1 if report_dict.get("radar_cross_verified", True) else 0,
        report_dict.get("admin_notes", ""),
        report_dict["created_at"]
    ))
    conn.commit()
    conn.close()
    return report_dict
