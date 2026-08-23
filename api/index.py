"""
Vercel Serverless Entrypoint for VayuDrishti Platform
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Ensure database is initialized in /tmp on Vercel
try:
    from backend.app.database import init_db, seed_database_if_empty
    init_db()
    seed_database_if_empty()
except Exception as e:
    print(f"Vercel DB Init Warning: {e}")

from backend.app.main import app

# Export ASGI app for Vercel
app = app
