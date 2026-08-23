"""
National Weather Big Data Analytics Platform - Main Application Entrypoint
Mounts REST APIs, Static Assets, WebSocket Hub, and Background Workers.
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import BASE_DIR
from .database import init_db, seed_database_if_empty
from .api.reports import router as reports_router
from .api.analytics import router as analytics_router
from .api.admin import router as admin_router
from .api.citizen import router as citizen_router
from .api.stream import router as stream_router, background_stream_worker
from .api.export import router as export_router

FRONTEND_DIR = BASE_DIR / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database, Seed default dataset, launch background worker
    init_db()
    seed_database_if_empty()
    bg_task = asyncio.create_task(background_stream_worker())
    yield
    # Shutdown: Cancel background worker
    bg_task.cancel()

app = FastAPI(
    title="VayuDrishti - National Weather Big Data Analytics Platform",
    description="Scalable Indian meteorological big data ingestion, NLP classification, misinformation filtering, and geospatial visualization suite.",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for open integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(reports_router)
app.include_router(analytics_router)
app.include_router(admin_router)
app.include_router(citizen_router)
app.include_router(stream_router)
app.include_router(export_router)

# Direct WebSocket endpoint on App
from .api.stream import manager
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/api/stream/ws")
@app.websocket("/ws")
async def app_websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# Mount Frontend Static Directory
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
async def root_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "VayuDrishti National Weather Big Data Analytics Platform API Operational"}

@app.get("/admin")
async def admin_portal():
    admin_file = FRONTEND_DIR / "admin.html"
    if admin_file.exists():
        return FileResponse(str(admin_file))
    return {"message": "Admin portal"}

@app.get("/citizen")
async def citizen_portal():
    citizen_file = FRONTEND_DIR / "citizen.html"
    if citizen_file.exists():
        return FileResponse(str(citizen_file))
    return {"message": "Citizen portal"}
