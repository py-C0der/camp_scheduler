"""
WebSocket and Server-Sent Events (SSE) Real-time Connection Manager.
"""

import asyncio
import json
from typing import Dict, List, Set, Any
from fastapi import WebSocket


class ConnectionManager:
    """
    Tracks active client WebSocket connections keyed by user_id.
    Supports instant push and broadcast.
    """

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)

    async def disconnect(self, user_id: str, websocket: WebSocket):
        async with self.lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

    async def send_personal_message(self, user_id: str, message: Dict[str, Any]):
        """Pushes real-time notification payload to user's open tabs."""
        sockets_to_remove = set()
        async with self.lock:
            sockets = list(self.active_connections.get(user_id, set()))

        payload = json.dumps(message)
        for ws in sockets:
            try:
                await ws.send_text(payload)
            except Exception:
                sockets_to_remove.add(ws)

        if sockets_to_remove:
            async with self.lock:
                if user_id in self.active_connections:
                    self.active_connections[user_id].difference_update(sockets_to_remove)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcasts real-time system message to all connected users."""
        payload = json.dumps(message)
        async with self.lock:
            all_sockets = [ws for s_set in self.active_connections.values() for ws in s_set]

        for ws in all_sockets:
            try:
                await ws.send_text(payload)
            except Exception:
                pass


ws_manager = ConnectionManager()
