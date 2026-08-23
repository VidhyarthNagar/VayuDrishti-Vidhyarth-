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

from ..ingestion.live_fetcher import live_fetcher

async def background_stream_worker():
    """
    Continuous Real-Time Big Data Ingestion Worker:
    1. Periodically syncs live internet streams (Google News IMD RSS, Open-Meteo AWS stations, Custom APIs).
    2. Broadcasts newly ingested and AI-verified intelligence reports live to all connected browser dashboards via WebSockets.
    """
    cycle_counter = 0
    while True:
        try:
            await asyncio.sleep(15.0)
            cycle_counter += 1

            # Every 45 seconds (every 3 cycles), sync real live Internet sources
            if cycle_counter % 3 == 0:
                try:
                    sync_res = live_fetcher.sync_all_live_sources()
                    new_reports = sync_res.get("reports", [])
                    for r in new_reports[:3]:
                        if manager.active_connections:
                            await manager.broadcast_json({
                                "type": "NEW_REPORT",
                                "report": r
                            })
                            await asyncio.sleep(1.0)
                except Exception as sync_err:
                    logger.warning("Periodic live Internet sync error: %s", str(sync_err))

            # In-between cycles: Stream live telemetry or radar pulse
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
