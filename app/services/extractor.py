"""Run GLiNER2 extraction in a background thread pool."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

from gliner2 import GLiNER2

from app.schemas.api import ExtractResponse, Triplet
from app.services.schema_registry import CompiledSchema
from app.services.triplet_mapper import (
    map_relations_to_triplets,
    normalize_entities,
)


class ExtractorService:
    """Execute CPU-bound GLiNER2 inference without blocking the event loop."""

    def __init__(
        self,
        model: GLiNER2,
        executor: ThreadPoolExecutor,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Initialize the extractor with model and concurrency controls."""
        self._model = model
        self._executor = executor
        self._semaphore = semaphore

    def _extract_sync(
        self,
        text: str,
        compiled: CompiledSchema,
    ) -> dict[str, Any]:
        """Run synchronous GLiNER2 extraction for one page of text."""
        inference = compiled.definition.inference
        return cast(
            dict[str, Any],
            self._model.extract(
                text,
                compiled.gliner_schema,
                threshold=inference.threshold,
                include_confidence=inference.include_confidence,
                include_spans=inference.include_spans,
            ),
        )

    async def extract_page(
        self,
        text: str,
        compiled: CompiledSchema,
        *,
        page_id: str | None = None,
    ) -> ExtractResponse:
        """Extract entities and relations from one page asynchronously."""
        async with self._semaphore:
            loop = asyncio.get_running_loop()
            raw = await loop.run_in_executor(
                self._executor,
                self._extract_sync,
                text,
                compiled,
            )

        relation_extraction = raw.get("relation_extraction", {})
        entities = normalize_entities(raw.get("entities", {}))
        triplets: list[Triplet] = map_relations_to_triplets(
            relation_extraction,
            page_id=page_id,
        )

        return ExtractResponse(
            schema_name=compiled.definition.name,
            page_id=page_id,
            triplets=triplets,
            entities=entities,
        )
