"""Security Audit Tests: WebSocket Security & Topic Isolation (Section 20)."""
import pytest
from starlette.websockets import WebSocketDisconnect
from app.core.security import create_access_token
from app.core.websocket import ws_manager


def test_unauthenticated_websocket_connection_rejected(client):
    """Verify that websocket connection without a valid JWT token is closed with code 1008."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/esp32/test-device-uuid") as websocket:
            websocket.receive_text()
    assert exc_info.value.code == 1008


def test_invalid_token_websocket_connection_rejected(client):
    """Verify that websocket connection with forged/invalid token is closed."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/esp32/test-device-uuid?token=invalid.jwt.token") as websocket:
            websocket.receive_text()
    assert exc_info.value.code == 1008


def test_authenticated_websocket_connects_and_communicates(client, seeded_users):
    """Verify that a valid token allows connection and echo/ack."""
    admin = seeded_users["admin"]
    token = create_access_token({"sub": admin.id, "role": "ADMIN"})

    with client.websocket_connect(f"/ws/esp32/test-dev-uuid?token={token}") as ws:
        ws.send_text("PING")
        ack = ws.receive_text()
        assert "ACK" in ack


def test_topic_isolation_in_websocket_manager():
    """Verify that messages broadcast to topic A are NOT sent to topic B."""
    class MockWebSocket:
        def __init__(self):
            self.received = []

        async def accept(self):
            pass

        async def send_text(self, data: str):
            self.received.append(data)

    import asyncio

    ws_case_a = MockWebSocket()
    ws_case_b = MockWebSocket()

    async def run_isolation_check():
        await ws_manager.connect(ws_case_a, "case:CASE-A")
        await ws_manager.connect(ws_case_b, "case:CASE-B")

        # Broadcast to CASE-A only
        await ws_manager.broadcast("case:CASE-A", "NEW_FINDING", {"case": "CASE-A"})

        # Verify CASE-A got it, but CASE-B did NOT
        assert len(ws_case_a.received) == 1
        assert len(ws_case_b.received) == 0

        ws_manager.disconnect(ws_case_a, "case:CASE-A")
        ws_manager.disconnect(ws_case_b, "case:CASE-B")

    asyncio.run(run_isolation_check())
