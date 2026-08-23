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

from .config import BASE_DIR, IS_SERVERLESS
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
    # Startup: Initialize Database, Seed default dataset
    try:
        init_db()
        seed_database_if_empty()
    except Exception as e:
        print(f"Warning: Database initialization error: {e}")

    if not IS_SERVERLESS:
        bg_task = asyncio.create_task(background_stream_worker())
        yield
        bg_task.cancel()
    else:
        yield

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

from fastapi.responses import Response, HTMLResponse
from fastapi import HTTPException

# Explicit Static File Server (works seamlessly across Vercel, Docker, Local)
@app.get("/static/{file_path:path}")
async def serve_static_file(file_path: str):
    candidates = [
        FRONTEND_DIR / file_path,
        BASE_DIR / "frontend" / file_path,
        Path(__file__).resolve().parent.parent.parent / "frontend" / file_path,
        Path("frontend") / file_path
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            mime_type = "text/plain"
            if file_path.endswith(".css"): mime_type = "text/css"
            elif file_path.endswith(".js"): mime_type = "application/javascript"
            elif file_path.endswith(".json"): mime_type = "application/json"
            elif file_path.endswith(".png"): mime_type = "image/png"
            elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"): mime_type = "image/jpeg"
            elif file_path.endswith(".svg"): mime_type = "image/svg+xml"
            return Response(
                content=c.read_bytes(),
                media_type=mime_type,
                headers={"Cache-Control": "public, max-age=3600"}
            )
    raise HTTPException(status_code=404, detail=f"Static file '{file_path}' not found")

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

from fastapi.responses import HTMLResponse

def get_html_content(filename: str) -> str:
    candidates = [
        FRONTEND_DIR / filename,
        BASE_DIR / "frontend" / filename,
        Path(__file__).resolve().parent.parent.parent / "frontend" / filename,
        Path("frontend") / filename
    ]
    for c in candidates:
        if c.exists():
            try:
                return c.read_text(encoding="utf-8")
            except Exception:
                pass
    return f"<html><body><h1>VayuDrishti Platform</h1><p>Loading {filename}...</p></body></html>"

@app.get("/", response_class=HTMLResponse)
async def root_index():
    return HTMLResponse(content=get_html_content("index.html"))

@app.get("/admin", response_class=HTMLResponse)
async def admin_portal():
    return HTMLResponse(content=get_html_content("admin.html"))

@app.get("/citizen", response_class=HTMLResponse)
async def citizen_portal():
    return HTMLResponse(content=get_html_content("citizen.html"))
