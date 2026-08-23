"""
Antigravity VayuDrishti - National Weather Big Data Analytics Platform
Configuration Settings
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

# Serverless environment detection (Vercel, AWS Lambda) where /var/task is read-only
IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
if IS_SERVERLESS:
    DB_PATH = Path("/tmp") / "weather_bigdata.db"
else:
    DB_PATH = BASE_DIR / "weather_bigdata.db"

# Spatiotemporal Clustering Settings for Deduplication
DEDUP_DISTANCE_KM_THRESHOLD = 8.0  # within 8 km radius
DEDUP_TIME_WINDOW_MINUTES = 45     # within 45 minutes
DEDUP_SEMANTIC_SIMILARITY_THRESHOLD = 0.62  # TF-IDF Cosine similarity

# Fake / Misleading Detection Settings
FAKE_SENSATIONALISM_WEIGHT = 0.40
FAKE_SOURCE_TRUST_WEIGHT = 0.30
FAKE_RADAR_ANOMALY_WEIGHT = 0.30
FAKE_PROBABILITY_THRESHOLD = 0.65  # Flag if >= 0.65

# Server Configuration
HOST = "0.0.0.0"
PORT = 8080

# Administrative Security & RBAC Configuration
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_DEFAULT_PASSWORD = os.environ.get("ADMIN_PASSWORD", "IMD@Admin2026")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "vdu-adm-imd-session-key-9982")
