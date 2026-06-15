"""Entity and relation extraction endpoints."""

import asyncio
from typing import cast

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.api import (
    BatchExtractRequest,
    BatchExtractResponse,
    ExtractRequest,
    ExtractResponse,
)
from app.services.extractor import ExtractorService
from app.services.schema_registry import SchemaRegistry
from app.settings import get_settings

router = APIRouter(prefix="/v1", tags=["extract"])


def _validate_text_length(text: str) -> None:
    """Reject input that exceeds the configured maximum text length."""
    settings = get_settings()
    if len(text) > settings.max_text_length:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Text exceeds maximum length of {settings.max_text_length} characters"
            ),
        )


@router.post("/extract", response_model=ExtractResponse)
async def extract_single(request: Request, body: ExtractRequest) -> ExtractResponse:
    """Extract entities and relations from a single markdown page."""
    _validate_text_length(body.text)
    schema_registry = cast(SchemaRegistry, request.app.state.schema_registry)
    extractor = cast(ExtractorService, request.app.state.extractor)

    try:
        compiled = schema_registry.get(body.schema_name)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return await extractor.extract_page(
        body.text,
        compiled,
        page_id=body.page_id,
    )


@router.post("/extract/batch", response_model=BatchExtractResponse)
async def extract_batch(
    request: Request,
    body: BatchExtractRequest,
) -> BatchExtractResponse:
    """Extract entities and relations from multiple pages in parallel."""
    schema_registry = cast(SchemaRegistry, request.app.state.schema_registry)
    extractor = cast(ExtractorService, request.app.state.extractor)

    for page in body.pages:
        _validate_text_length(page.text)

    try:
        compiled = schema_registry.get(body.schema_name)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    tasks = [
        extractor.extract_page(page.text, compiled, page_id=page.page_id)
        for page in body.pages
    ]
    results = await asyncio.gather(*tasks)

    return BatchExtractResponse(schema_name=body.schema_name, results=list(results))
