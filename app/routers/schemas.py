"""Schema listing and upload endpoints."""

from typing import Annotated, cast

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status

from app.schemas.api import SchemaListResponse, SchemaUploadResponse
from app.services.schema_registry import SchemaConflictError, SchemaRegistry
from app.services.schema_validation import SchemaValidationError

router = APIRouter(prefix="/v1", tags=["schemas"])

ALLOWED_EXTENSIONS = {".yaml", ".yml"}


@router.get("/schemas", response_model=SchemaListResponse)
async def list_schemas(request: Request) -> SchemaListResponse:
    """List available named extraction schemas."""
    schema_registry = cast(SchemaRegistry, request.app.state.schema_registry)
    return SchemaListResponse(schemas=schema_registry.list_summaries())


@router.post(
    "/schemas/upload",
    response_model=SchemaUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_schema(
    request: Request,
    file: Annotated[UploadFile, File()],
    overwrite: bool = Query(default=False),
) -> SchemaUploadResponse:
    """Upload a YAML schema file and register it for extraction requests."""
    filename = file.filename or ""
    if not any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a .yaml or .yml extension",
        )

    content_bytes = await file.read()
    if not content_bytes.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Schema file is empty",
        )

    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Schema file must be valid UTF-8 text",
        ) from exc

    schema_registry = cast(SchemaRegistry, request.app.state.schema_registry)
    try:
        summary, replaced = schema_registry.register_from_yaml(
            content,
            overwrite=overwrite,
        )
    except SchemaValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except SchemaConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return SchemaUploadResponse(
        message="Schema uploaded successfully",
        uploaded_schema=summary,
        overwritten=replaced,
    )
