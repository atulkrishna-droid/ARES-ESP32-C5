"""ARES Platform FastAPI Application Entrypoint."""
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api_router import api_v1_router
from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import AresException
from app.core.logging import logger
from app.websocket.manager import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database tables are created
    logger.info("Initializing ARES Platform backend and database schema...")
    init_db()
    logger.info("ARES Platform database initialization complete.")
    yield
    # Shutdown
    logger.info("ARES Platform shutting down.")


app = FastAPI(
    title="ARES Cybersecurity Assessment Platform",
    description="Authorized Reconnaissance, Evidence & Security Assessment Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID and Access Log Middleware
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


# Global Exception Handler for Domain Exceptions
@app.exception_handler(AresException)
async def ares_exception_handler(request: Request, exc: AresException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


# Mount API Router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


from typing import Optional
from app.core.security import decode_token


# WebSocket Endpoints with Token Authentication & Topic Isolation
@app.websocket("/ws/esp32/{device_id}")
async def ws_esp32_endpoint(websocket: WebSocket, device_id: str, token: Optional[str] = None):
    effective_token = token or websocket.query_params.get("token")
    if not effective_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        decode_token(effective_token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    topic = f"esp32:{device_id}"
    await ws_manager.connect(websocket, topic)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f'{{"status":"ACK","received":"{data}"}}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, topic)


@app.websocket("/ws/assessments/{assessment_id}")
async def ws_assessment_endpoint(websocket: WebSocket, assessment_id: str, token: Optional[str] = None):
    effective_token = token or websocket.query_params.get("token")
    if not effective_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        decode_token(effective_token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    topic = f"assessment:{assessment_id}"
    await ws_manager.connect(websocket, topic)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, topic)
