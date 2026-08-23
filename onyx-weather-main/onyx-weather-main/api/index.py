"""
Vercel Serverless Entrypoint for VayuDrishti Platform
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.main import app

app = app
