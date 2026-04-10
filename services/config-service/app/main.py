"""Config Service - Main FastAPI Application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rag_config_common.auth.middleware import ServiceAuthMiddleware
from rag_config_common.observability import setup_tracing

from app.api.v1.router import api_router
from app.core.settings import settings
from app.core.token_blacklist import token_blacklist
from app.db.mongodb import mongodb


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await mongodb.connect()
    await token_blacklist.connect()
    yield
    # Shutdown
    await token_blacklist.disconnect()
    await mongodb.disconnect()


app = FastAPI(
    title="RAG Configurator - Config Service",
    description="Configuration management service for RAG pipelines",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

setup_tracing(
    app,
    service_name=settings.OTEL_SERVICE_NAME,
    environment=settings.ENVIRONMENT,
    endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
)

app.add_middleware(
    ServiceAuthMiddleware,
    secret=settings.INTER_SERVICE_SECRET,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "config-service"}
