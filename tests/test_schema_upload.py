from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from app.routers import health, schemas
from app.services.schema_registry import SchemaRegistry
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

VALID_SCHEMA = {
    "name": "uploaded_schema",
    "description": "Uploaded schema",
    "entities": {"person": "A person"},
    "relations": {"works_for": "Employment relation"},
    "inference": {
        "threshold": 0.5,
        "include_confidence": True,
        "include_spans": False,
    },
}


def _yaml_file(content: str, filename: str = "custom.yaml") -> dict[str, tuple]:
    """Build a multipart file payload for schema upload tests."""
    return {
        "file": (filename, BytesIO(content.encode()), "application/x-yaml"),
    }


@pytest.fixture
def upload_app(tmp_path: Path) -> FastAPI:
    model = MagicMock()
    builder = MagicMock()
    model.create_schema.return_value = builder
    builder.entities.return_value = builder
    builder.relations.return_value = builder

    registry = SchemaRegistry(tmp_path / "schemas", model)
    app = FastAPI()
    app.include_router(health.router)
    app.include_router(schemas.router)
    app.state.schema_registry = registry
    return app


@pytest.fixture
async def upload_client(upload_app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=upload_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_upload_schema_success(upload_client: AsyncClient) -> None:
    content = yaml.dump(VALID_SCHEMA)
    response = await upload_client.post(
        "/v1/schemas/upload",
        files=_yaml_file(content),
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["uploaded_schema"]["name"] == "uploaded_schema"
    assert payload["overwritten"] is False


@pytest.mark.asyncio
async def test_upload_schema_conflict(upload_client: AsyncClient) -> None:
    content = yaml.dump(VALID_SCHEMA)
    first = await upload_client.post(
        "/v1/schemas/upload",
        files=_yaml_file(content),
    )
    assert first.status_code == 201

    second = await upload_client.post(
        "/v1/schemas/upload",
        files=_yaml_file(content),
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_upload_schema_overwrite(upload_client: AsyncClient) -> None:
    content = yaml.dump(VALID_SCHEMA)
    files = {"file": ("custom.yaml", BytesIO(content.encode()), "application/x-yaml")}
    await upload_client.post("/v1/schemas/upload", files=files)

    updated = VALID_SCHEMA.copy()
    updated["description"] = "Updated description"
    files = {
        "file": (
            "custom.yaml",
            BytesIO(yaml.dump(updated).encode()),
            "application/x-yaml",
        )
    }
    response = await upload_client.post(
        "/v1/schemas/upload?overwrite=true",
        files=files,
    )
    assert response.status_code == 201
    assert response.json()["overwritten"] is True


@pytest.mark.asyncio
async def test_upload_schema_rejects_empty_file(upload_client: AsyncClient) -> None:
    response = await upload_client.post(
        "/v1/schemas/upload",
        files={"file": ("empty.yaml", BytesIO(b""), "application/x-yaml")},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_schema_rejects_invalid_extension(
    upload_client: AsyncClient,
) -> None:
    response = await upload_client.post(
        "/v1/schemas/upload",
        files={"file": ("schema.txt", BytesIO(b"name: demo"), "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_schema_rejects_missing_sections(
    upload_client: AsyncClient,
) -> None:
    invalid = {"name": "bad", "entities": {"person": "x"}}
    response = await upload_client.post(
        "/v1/schemas/upload",
        files={
            "file": (
                "bad.yaml",
                BytesIO(yaml.dump(invalid).encode()),
                "application/x-yaml",
            )
        },
    )
    assert response.status_code == 422
    assert "relations" in response.json()["detail"]


@pytest.mark.asyncio
async def test_uploaded_schema_available_for_listing(
    upload_client: AsyncClient,
) -> None:
    content = yaml.dump(VALID_SCHEMA)
    await upload_client.post(
        "/v1/schemas/upload",
        files=_yaml_file(content),
    )

    list_response = await upload_client.get("/v1/schemas")
    assert list_response.status_code == 200
    names = [item["name"] for item in list_response.json()["schemas"]]
    assert "uploaded_schema" in names
