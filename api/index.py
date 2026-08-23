"""
Vercel Serverless Entrypoint for VayuDrishti
=============================================
Since Render is the master backend with persistent data, ALL requests
(reads and writes) are proxied to Render. Vercel becomes a pure mirror.

This means:
- Both Vercel and Render show IDENTICAL data
- Password changes on either = changes on Render (single source of truth)
- Citizen reports on Vercel appear instantly on Render and vice versa
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

RENDER_BACKEND_URL = os.environ.get("RENDER_BACKEND_URL", "").rstrip("/")

# If RENDER_BACKEND_URL is set, create a pure proxy app that forwards EVERYTHING to Render
if RENDER_BACKEND_URL:
    from fastapi import FastAPI, Request
    from fastapi.responses import Response, StreamingResponse
    import httpx

    app = FastAPI(title="VayuDrishti Vercel Mirror")

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
    async def full_proxy(request: Request, path: str):
        """Forward every single request to the Render backend."""
        target_url = f"{RENDER_BACKEND_URL}/{path}"
        query = str(request.url.query)
        if query:
            target_url += f"?{query}"

        try:
            body = await request.body()
            headers = {
                k: v for k, v in request.headers.items()
                if k.lower() not in ("host", "content-length", "transfer-encoding", "connection")
            }
            headers["X-Forwarded-From"] = "vercel-mirror"
            headers["X-Forwarded-Host"] = request.headers.get("host", "")

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.request(
                    method=request.method,
                    url=target_url,
                    content=body,
                    headers=headers
                )

            # Stream the response back
            response_headers = {
                k: v for k, v in resp.headers.items()
                if k.lower() not in ("transfer-encoding", "connection", "content-encoding")
            }
            # Allow cross-origin requests
            response_headers["Access-Control-Allow-Origin"] = "*"

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=response_headers,
                media_type=resp.headers.get("content-type", "application/json")
            )

        except httpx.TimeoutException:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "Render backend timeout. Please try again."}, status_code=504)
        except Exception as exc:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": f"Proxy error: {str(exc)}"}, status_code=502)

else:
    # Fallback: run standalone if no Render URL configured
    try:
        from backend.app.database import init_db, seed_database_if_empty
        init_db()
        seed_database_if_empty()
    except Exception as e:
        print(f"DB init warning: {e}")
    from backend.app.main import app
