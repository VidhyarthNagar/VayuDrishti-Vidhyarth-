"""
Vercel Serverless Entrypoint for VayuDrishti Platform
======================================================
When RENDER_BACKEND_URL is set, this proxy:
  - Forwards all POST/PUT/DELETE writes (citizen reports, etc.) to Render (master DB)
  - Reads (GET) can be served locally from Vercel's ephemeral SQLite seed
  - This ensures citizen reports posted on Vercel appear on Render in real-time
"""
import os
import sys
import json
import requests as _requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

RENDER_BACKEND_URL = os.environ.get("RENDER_BACKEND_URL", "").rstrip("/")

# Ensure database is initialized in /tmp on Vercel
try:
    from backend.app.database import init_db, seed_database_if_empty
    init_db()
    seed_database_if_empty()
except Exception as e:
    print(f"Vercel DB Init Warning: {e}")

from backend.app.main import app as _fastapi_app
from fastapi import Request
from fastapi.responses import JSONResponse, Response
import httpx


# ── Proxy middleware: forward writes to Render ─────────────────────────────
PROXY_PATHS = [
    "/api/citizen",      # Citizen weather reports
    "/api/admin",        # Admin actions
    "/api/reports",      # Report mutations (POST)
]

WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


async def _proxy_to_render(request: Request):
    """Forward the request to the Render backend and return its response."""
    path = request.url.path
    query = str(request.url.query)
    target = f"{RENDER_BACKEND_URL}{path}"
    if query:
        target += f"?{query}"

    try:
        body = await request.body()
        headers = dict(request.headers)
        # Strip hop-by-hop headers
        for h in ["host", "content-length", "transfer-encoding"]:
            headers.pop(h, None)
        headers["X-Forwarded-From"] = "vercel-mirror"

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.request(
                method=request.method,
                url=target,
                content=body,
                headers=headers
            )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            media_type=resp.headers.get("content-type", "application/json")
        )
    except Exception as exc:
        return JSONResponse(
            {"error": f"Render proxy error: {str(exc)}", "target": target},
            status_code=502
        )


@_fastapi_app.middleware("http")
async def render_sync_middleware(request: Request, call_next):
    """If RENDER_BACKEND_URL is set and this is a write to a sync'd path, proxy to Render."""
    if (
        RENDER_BACKEND_URL
        and request.method in WRITE_METHODS
        and any(request.url.path.startswith(p) for p in PROXY_PATHS)
    ):
        return await _proxy_to_render(request)
    return await call_next(request)


# Export ASGI app for Vercel
app = _fastapi_app
