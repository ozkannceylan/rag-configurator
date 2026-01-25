"""FastAPI application for Ingestion Service."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router
from app.core.settings import settings
from app.db.mongodb import mongodb

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.service_name} in {settings.environment} mode")

    # Connect to MongoDB
    await mongodb.connect()
    logger.info("MongoDB connected")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.service_name}")

    # Disconnect from MongoDB
    await mongodb.disconnect()
    logger.info("MongoDB disconnected")


# Create FastAPI application
app = FastAPI(
    title="Ingestion Service",
    description="Async document ingestion and processing service for RAG pipelines",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "environment": settings.environment,
    }


@app.get("/health/detailed", tags=["health"])
async def health_detailed():
    """Detailed health check including dependencies."""
    health_status = {
        "status": "healthy",
        "service": settings.service_name,
        "environment": settings.environment,
        "dependencies": {},
    }

    # Check MongoDB
    try:
        await mongodb.get_database().command("ping")
        health_status["dependencies"]["mongodb"] = "healthy"
    except Exception as e:
        health_status["dependencies"]["mongodb"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check Redis/Celery broker (basic check)
    try:
        from app.core.celery_app import celery_app

        # Ping the broker
        celery_app.control.ping(timeout=1.0)
        health_status["dependencies"]["celery_broker"] = "healthy"
    except Exception as e:
        health_status["dependencies"]["celery_broker"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    return health_status


# Include API routers
app.include_router(api_v1_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.is_development,
    )
