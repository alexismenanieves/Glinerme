from unittest.mock import AsyncMock, MagicMock

import pytest
from app.routers import extract, health, schemas
from app.schemas.api import ExtractResponse, SchemaSummary, Triplet
from app.services.schema_registry import CompiledSchema, SchemaRegistry
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app_with_mocks() -> tuple[FastAPI, MagicMock, MagicMock]:
    mock_model = MagicMock()
    mock_registry = MagicMock(spec=SchemaRegistry)
    mock_registry.count = 1
    mock_registry.list_summaries.return_value = [
        SchemaSummary(
            name="test_schema",
            description="Test",
            entity_count=1,
            relation_count=1,
        )
    ]

    compiled = CompiledSchema(
        definition=MagicMock(name="test_schema"),
        gliner_schema=MagicMock(),
    )
    mock_registry.get.return_value = compiled

    mock_extractor = MagicMock()
    mock_extractor.extract_page = AsyncMock(
        return_value=ExtractResponse(
            schema_name="test_schema",
            page_id="p1",
            triplets=[
                Triplet(
                    subject="John",
                    predicate="works_for",
                    object="Apple Inc.",
                    confidence=0.93,
                    page_id="p1",
                )
            ],
            entities={"person": ["John"], "organization": ["Apple Inc."]},
        )
    )

    app = FastAPI()
    app.include_router(health.router)
    app.include_router(schemas.router)
    app.include_router(extract.router)
    app.state.model = mock_model
    app.state.schema_registry = mock_registry
    app.state.executor = MagicMock()
    app.state.extractor = mock_extractor
    return app, mock_extractor, mock_registry


@pytest.fixture
async def client(app_with_mocks: tuple) -> AsyncClient:
    app, _, _ = app_with_mocks
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["schema_count"] == 1


@pytest.mark.asyncio
async def test_list_schemas(client: AsyncClient) -> None:
    response = await client.get("/v1/schemas")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["schemas"]) == 1
    assert payload["schemas"][0]["name"] == "test_schema"


@pytest.mark.asyncio
async def test_extract_single(
    client: AsyncClient,
    app_with_mocks: tuple,
) -> None:
    _, mock_extractor, mock_registry = app_with_mocks
    response = await client.post(
        "/v1/extract",
        json={
            "text": "John works for Apple Inc.",
            "schema_name": "test_schema",
            "page_id": "p1",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_name"] == "test_schema"
    assert payload["triplets"][0]["predicate"] == "works_for"
    mock_registry.get.assert_called_once_with("test_schema")
    mock_extractor.extract_page.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_unknown_schema(
    client: AsyncClient,
    app_with_mocks: tuple,
) -> None:
    _, _, mock_registry = app_with_mocks
    mock_registry.get.side_effect = KeyError("Unknown schema 'missing'")
    response = await client.post(
        "/v1/extract",
        json={"text": "hello", "schema_name": "missing"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_extract_batch(
    client: AsyncClient,
    app_with_mocks: tuple,
) -> None:
    _, mock_extractor, _ = app_with_mocks
    response = await client.post(
        "/v1/extract/batch",
        json={
            "schema_name": "test_schema",
            "pages": [
                {"page_id": "p1", "text": "John works for Apple Inc."},
                {"page_id": "p2", "text": "Sarah founded TechStartup."},
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_name"] == "test_schema"
    assert len(payload["results"]) == 2
    assert mock_extractor.extract_page.await_count == 2
