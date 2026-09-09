"""
Application entry point.

Startup / Shutdown (lifespan):
  - Initializes Redis Connection Pool
  - Disposes DB engine and PubSub tasks on graceful shutdown

Registers:
  - Global exception handlers (domain → HTTP)
  - CORS middleware
  - All presentation routers
  - Health check endpoint
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionFactory, engine
from app.core.exceptions import register_exception_handlers
from app.core.redis import redis_client
from app.presentation.routers.auth import router as auth_router
from app.presentation.routers.chat import router as chat_router
from app.presentation.routers.rooms import router as rooms_router
from app.presentation.websocket.pubsub_manager import pubsub_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    await redis_client.init_pool()
    yield
    await pubsub_manager.shutdown()
    await redis_client.close_pool()
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Enterprise real-time chat built with Clean Architecture — "
        "FastAPI · Async PostgreSQL · Redis Pub/Sub · WebSockets"
    ),
    lifespan=lifespan,
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(rooms_router)
app.include_router(chat_router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Deep readiness probe — verifies PostgreSQL and Redis connectivity."""
    db_ok = False
    redis_ok = False

    try:
        async with AsyncSessionFactory() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    try:
        redis_ok = await redis_client.ping()
    except Exception:
        pass

    code = status.HTTP_200_OK if (db_ok and redis_ok) else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=code,
        content={
            "status": "healthy" if (db_ok and redis_ok) else "degraded",
            "components": {
                "database": "reachable" if db_ok else "unreachable",
                "redis": "reachable" if redis_ok else "unreachable",
            },
        },
    )