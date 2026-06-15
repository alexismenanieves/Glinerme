"""FastAPI application entrypoint and lifecycle management."""

import asyncio
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import extract, health, schemas
from app.services.extractor import ExtractorService
from app.services.model import load_model
from app.services.schema_registry import SchemaRegistry
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load the model and shared services once at startup."""
    settings = get_settings()
    model = load_model(settings)
    schema_registry = SchemaRegistry(settings.schemas_dir, model)
    executor = ThreadPoolExecutor(max_workers=settings.max_workers)
    semaphore = asyncio.Semaphore(settings.max_workers)
    extractor = ExtractorService(model, executor, semaphore)

    app.state.model = model
    app.state.schema_registry = schema_registry
    app.state.executor = executor
    app.state.extractor = extractor

    yield

    executor.shutdown(wait=True)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Glinerme",
        description="GLiNER2 entity-relationship extraction service",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(schemas.router)
    app.include_router(extract.router)
    return app


app = create_app()


def run() -> None:
    """Start the service with uvicorn using configured host and port."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
