"""WebSocket Event Broker and Topic Connection Manager."""
import json
from typing import Any, Dict, List
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        # Maps topic (e.g. "assessment:UUID", "esp32:UUID") to list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, topic: str):
        await websocket.accept()
        if topic not in self.active_connections:
            self.active_connections[topic] = []
        self.active_connections[topic].append(websocket)

    def disconnect(self, websocket: WebSocket, topic: str):
        if topic in self.active_connections and websocket in self.active_connections[topic]:
            self.active_connections[topic].remove(websocket)
            if not self.active_connections[topic]:
                del self.active_connections[topic]

    async def broadcast(self, topic: str, event_type: str, data: Dict[str, Any]):
        if topic in self.active_connections:
            message = json.dumps({"event": event_type, "data": data})
            dead_connections = []
            for connection in self.active_connections[topic]:
                try:
                    await connection.send_text(message)
                except Exception:
                    dead_connections.append(connection)

            for dead in dead_connections:
                self.disconnect(dead, topic)


ws_manager = WebSocketManager()
