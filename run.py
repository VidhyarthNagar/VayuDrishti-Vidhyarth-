"""
VayuDrishti - National Weather Big Data Analytics Platform (Root Launcher)
"""
import os
import sys
from pathlib import Path

# Force UTF-8 standard output encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ROOT_DIR / "onyx-weather-main" / "onyx-weather-main"

if PROJECT_DIR.exists():
    sys.path.insert(0, str(PROJECT_DIR))
    os.chdir(PROJECT_DIR)
    import uvicorn
    if __name__ == "__main__":
        print("=" * 70)
        print("[VayuDrishti] National Weather Big Data Analytics Platform")
        print("[IMD Hub] India Meteorological Intelligence, NLP Fake Detection & GIS Map")
        print("=" * 70)
        print("Dashboard URL: http://127.0.0.1:8080")
        print("Admin Command: http://127.0.0.1:8080/admin")
        print("Citizen Portal: http://127.0.0.1:8080/citizen")
        print("=" * 70)
        uvicorn.run(
            "backend.app.main:app",
            host="0.0.0.0",
            port=8080,
            reload=False,
            log_level="info"
        )
