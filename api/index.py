"""
VayuDrishti — Vercel Mirror Entry Point
========================================
This is a PURE HTTP PROXY to the Render backend.
It does NOT import any backend code, ML models, or database.
It only needs: fastapi + httpx (both tiny packages).

All requests (reads and writes) are forwarded to Render,
making both Vercel and Render show IDENTICAL data.
"""
import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response

RENDER_URL = os.environ.get("RENDER_BACKEND_URL", "https://vayudrishti-vidhyarth.onrender.com").rstrip("/")

app = FastAPI(title="VayuDrishti Vercel Mirror")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy(request: Request, path: str):
    """Forward every request to the Render master backend."""
    url = f"{RENDER_URL}/{path}"
    qs = str(request.url.query)
    if qs:
        url += f"?{qs}"

    body = await request.body()
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding", "connection")
    }
    headers["X-Forwarded-From"] = "vercel"

    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            r = await client.request(
                method=request.method,
                url=url,
                content=body,
                headers=headers
            )
        resp_headers = {
            k: v for k, v in r.headers.items()
            if k.lower() not in ("transfer-encoding", "connection", "content-encoding")
        }
        resp_headers["Access-Control-Allow-Origin"] = "*"
        return Response(
            content=r.content,
            status_code=r.status_code,
            headers=resp_headers,
            media_type=r.headers.get("content-type", "application/json")
        )
    except httpx.TimeoutException:
        return Response(
            content=b'{"error":"Render backend timeout - try again in a moment."}',
            status_code=504,
            media_type="application/json"
        )
    except Exception as e:
        return Response(
            content=f'{{"error":"Proxy error: {str(e)}"}}'.encode(),
            status_code=502,
            media_type="application/json"
        )
