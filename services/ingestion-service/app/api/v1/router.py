"""API v1 router aggregating all endpoints."""

from fastapi import APIRouter

from app.api.v1 import ingest

router = APIRouter()

# Include sub-routers
router.include_router(ingest.router, prefix="/ingest", tags=["ingestion"])


@router.get("/", tags=["root"])
async def root():
    """API v1 root endpoint."""
    return {
        "message": "Ingestion Service API v1",
        "version": "1.0.0",
        "endpoints": {
            "ingestion": "/api/v1/ingest",
        },
    }
