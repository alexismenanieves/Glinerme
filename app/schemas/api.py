"""Pydantic models for HTTP request and response payloads."""

from typing import Any

from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    """Request body for single-page extraction."""

    text: str = Field(..., min_length=1)
    schema_name: str = Field(..., min_length=1)
    page_id: str | None = None


class PageInput(BaseModel):
    """One markdown page within a batch extraction request."""

    page_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)


class BatchExtractRequest(BaseModel):
    """Request body for multi-page batch extraction."""

    schema_name: str = Field(..., min_length=1)
    pages: list[PageInput] = Field(..., min_length=1)


class Triplet(BaseModel):
    """Subject-predicate-object relation extracted from text."""

    subject: str
    predicate: str
    object: str
    confidence: float | None = None
    page_id: str | None = None


class ExtractResponse(BaseModel):
    """Extraction result for a single page."""

    schema_name: str
    page_id: str | None = None
    triplets: list[Triplet]
    entities: dict[str, list[str]]


class BatchExtractResponse(BaseModel):
    """Extraction results for a batch of pages."""

    schema_name: str
    results: list[ExtractResponse]


class SchemaSummary(BaseModel):
    """Metadata for one named YAML extraction schema."""

    name: str
    description: str
    entity_count: int
    relation_count: int


class SchemaListResponse(BaseModel):
    """List of available extraction schemas."""

    schemas: list[SchemaSummary]


class SchemaUploadResponse(BaseModel):
    """Response returned after uploading a schema YAML file."""

    message: str
    uploaded_schema: SchemaSummary
    overwritten: bool = False


class HealthResponse(BaseModel):
    """Service health and runtime configuration."""

    status: str
    model_name: str
    model_loaded: bool
    schema_count: int
    max_workers: int
    device: str


class ErrorResponse(BaseModel):
    """Structured API error payload."""

    detail: str
    extra: dict[str, Any] | None = None
