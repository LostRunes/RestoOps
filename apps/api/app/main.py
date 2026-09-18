from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.logging import setup_logging, logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting up RestoOps API service", environment=settings.ENVIRONMENT)
    # Register event-driven notification handlers
    from app.services.notification_handlers import register_notification_handlers
    register_notification_handlers()
    yield
    logger.info("Shutting down RestoOps API service")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Routers
from app.api.v1.router import api_router
from app.api.websockets.webrtc_ws import router as webrtc_ws_router
from app.api.websockets.notification_ws import router as notification_ws_router

app.include_router(api_router, prefix=settings.API_V1_STR)
# WebRTC WebSocket signaling — registered directly (not under /api/v1)
app.include_router(webrtc_ws_router)
# Real-time notification WebSocket
app.include_router(notification_ws_router)

# Prometheus Metrics
Instrumentator().instrument(app).expose(app)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to RestoOps API",
        "docs": "/docs",
        "health": "/health",
    }
