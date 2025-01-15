from fastapi import WebSocket

from typing import List
import asyncio
from fastapi.websockets import WebSocketState
from collections import deque

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.frame_buffers = {}
        self._connection_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        try:
            await websocket.accept()
            async with self._connection_lock:
                self.active_connections.append(websocket)
                self.frame_buffers[websocket] = deque(maxlen=2)
            print(f"Client connected. Total connections: {len(self.active_connections)}")
            return True
        except Exception as e:
            print(f"Error during connection: {e}")
            return False

    async def disconnect(self, websocket: WebSocket):
        async with self._connection_lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            if websocket in self.frame_buffers:
                del self.frame_buffers[websocket]
        try:
            await websocket.close()
        except Exception as e:
            print(f"Error during disconnect: {e}")
        print(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def is_connected(self, websocket: WebSocket) -> bool:
        try:
            return (
                websocket in self.active_connections and 
                websocket.client_state != WebSocketState.DISCONNECTED and
                websocket.application_state != WebSocketState.DISCONNECTED
            )
        except Exception:
            return False

    async def add_frame(self, websocket: WebSocket, frame):
        if await self.is_connected(websocket):
            async with self._connection_lock:
                self.frame_buffers[websocket].append(frame)

    async def get_latest_frame(self, websocket: WebSocket):
        if websocket in self.frame_buffers and self.frame_buffers[websocket]:
            return self.frame_buffers[websocket][-1]
        return None

    async def send_json(self, websocket: WebSocket, data: dict):
        if await self.is_connected(websocket):
            try:
                await websocket.send_json(data)
                return True
            except Exception as e:
                print(f"Error sending JSON: {e}")
                await self.disconnect(websocket)
                return False
        return False