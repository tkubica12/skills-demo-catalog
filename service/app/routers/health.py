"""Health check router."""

from __future__ import annotations

from fastapi import APIRouter

from app.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["ops"])
def health() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(status="ok")
