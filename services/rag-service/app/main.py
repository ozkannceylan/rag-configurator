"""RAG Service - FastAPI application for query processing."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from rag_config_common.auth.middleware import ServiceAuthMiddleware
from rag_config_common.observability import setup_tracing

from app.api.v1.router import router as api_v1_router
from app.core.query_cache import query_cache
from app.core.settings import settings
from app.db.mongodb import mongodb

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.service_name}...")
    logger.info(f"Environment: {settings.environment}")

    # Connect to MongoDB
    await mongodb.connect()

    # Connect query cache
    await query_cache.connect()

    # Initialize MLflow if configured
    if settings.mlflow_enabled:
        try:
            import mlflow

            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            mlflow.set_experiment(settings.mlflow_experiment_name)
            logger.info(f"MLflow tracking enabled: {settings.mlflow_tracking_uri}")
        except Exception as e:
            logger.warning(f"Failed to initialize MLflow: {e}")

    logger.info(f"{settings.service_name} started successfully")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.service_name}...")
    await query_cache.disconnect()
    await mongodb.disconnect()
    logger.info(f"{settings.service_name} stopped")


# Create FastAPI application
app = FastAPI(
    title="RAG Service",
    description="Query processing and response generation for RAG pipelines",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

setup_tracing(
    app,
    service_name=settings.otel_service_name,
    environment=settings.environment,
    endpoint=settings.otel_exporter_otlp_endpoint,
)

app.add_middleware(
    ServiceAuthMiddleware,
    secret=settings.inter_service_secret,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.is_development else "An error occurred",
        },
    )


# Health endpoints
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health/ready", tags=["health"])
async def readiness_check():
    """Readiness check endpoint."""
    checks = {
        "mongodb": False,
    }

    # Check MongoDB
    try:
        db = mongodb.get_database()
        await db.command("ping")
        checks["mongodb"] = True
    except Exception as e:
        logger.error(f"MongoDB health check failed: {e}")

    # Check LLM provider availability
    llm_available = False
    if settings.default_llm_provider == "openai" and settings.openai_api_key:
        llm_available = True
    elif settings.default_llm_provider == "anthropic" and settings.anthropic_api_key:
        llm_available = True
    elif settings.default_llm_provider == "ollama":
        llm_available = True  # Assume Ollama is available if configured
    elif settings.default_llm_provider == "vllm" and settings.vllm_base_url:
        llm_available = True

    checks["llm_provider"] = llm_available

    all_healthy = all(checks.values())

    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health/live", tags=["health"])
async def liveness_check():
    """Liveness check endpoint."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }


# Include API routers
app.include_router(api_v1_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "docs": "/docs" if settings.is_development else None,
        "health": "/health",
        "api": "/api/v1",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.is_development,
    )
