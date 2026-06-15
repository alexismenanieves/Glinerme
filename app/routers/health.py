"""Health check endpoints."""

from typing import cast

from fastapi import APIRouter, Request

from app.schemas.api import HealthResponse
from app.services.schema_registry import SchemaRegistry
from app.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Return service health and runtime configuration."""
    settings = get_settings()
    schema_registry = cast(SchemaRegistry, request.app.state.schema_registry)
    model_loaded = request.app.state.model is not None
    return HealthResponse(
        status="ok" if model_loaded else "degraded",
        model_name=settings.model_name,
        model_loaded=model_loaded,
        schema_count=schema_registry.count,
        max_workers=settings.max_workers,
        device=settings.device,
    )
