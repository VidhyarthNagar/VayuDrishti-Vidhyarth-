"""
Real-time WebSocket & Streaming Hub
Broadcasts live incoming weather reports and active alerts to connected browser dashboards.
"""
import asyncio
import json
import logging
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..ingestion.generator import scenario_generator

logger = logging.getLogger("stream_hub")
router = APIRouter(prefix="/api/stream", tags=["Streaming"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("New WebSocket client connected. Total clients: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected. Remaining: %d", len(self.active_connections))

    async def broadcast_json(self, data: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive client ping or filter commands
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning("WebSocket error: %s", str(e))
        manager.disconnect(websocket)

async def background_stream_worker():
    """Background task generating a simulated real-time report every 10 seconds and broadcasting to all connected clients."""
    while True:
        try:
            await asyncio.sleep(10.0)
            if manager.active_connections:
                new_report = scenario_generator.generate_single_live_stream_report()
                payload = {
                    "type": "NEW_REPORT",
                    "report": new_report
                }
                await manager.broadcast_json(payload)
        except Exception as e:
            logger.error("Background stream worker exception: %s", str(e))
            await asyncio.sleep(5.0)
