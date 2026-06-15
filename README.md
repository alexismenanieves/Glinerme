# GLiNER2 Entity-Relationship Extraction Service

Containerized FastAPI service that runs [GLiNER2](https://github.com/fastino-ai/GLiNER2) locally to extract entities and relationships from markdown page text, returning standardized triplets.

## Features

- Local GLiNER2 inference (no external API required)
- Named YAML extraction schemas in `config/schemas/`
- Single-page and batch extraction endpoints
- CPU-bound inference offloaded to a thread pool with concurrency limits
- Docker support with model pre-download at build time

## Quick Start

### Local development

```bash
uv sync --group dev
cp .env.example .env
uvicorn app.main:app --reload
```

Or:

```bash
uv run glinerme
```

### Docker

Build and run a single container:

```bash
docker build -t glinerme .
docker run --rm -p 3131:3131 glinerme
```

To use custom schemas without rebuilding, mount your schema directory:

```bash
docker run --rm -p 3131:3131 \
  -v "$(pwd)/config/schemas:/app/config/schemas:ro" \
  glinerme
```

The service listens on `http://localhost:3131`.

## Configuration

Environment variables (see [`.env.example`](.env.example)):

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `fastino/gliner2-base-v1` | Hugging Face model ID |
| `DEVICE` | `cpu` | Inference device (`cpu` or `cuda`) |
| `SCHEMAS_DIR` | `./config/schemas` | Directory of named YAML schemas |
| `MAX_WORKERS` | `2` | Max concurrent inference jobs |
| `MAX_TEXT_LENGTH` | `100000` | Max characters per page |
| `HF_HOME` | `/app/.cache/huggingface` | Model cache directory |

## YAML Schemas

Each file in `config/schemas/` defines one named profile:

```yaml
name: knowledge_graph
description: General-purpose extraction for markdown documents

entities:
  person: "Names of people"
  organization: "Companies or institutions"

relations:
  works_for: "Employment relationship"
  located_in: "Geographic relationship"

inference:
  threshold: 0.5
  include_confidence: true
  include_spans: false
```

Clients select a schema by `schema_name` in API requests. Schemas can also be uploaded at runtime via the API.

## API

### `GET /health`

Service health and configuration summary.

### `GET /v1/schemas`

List available schema names and metadata.

### `POST /v1/schemas/upload`

Upload a YAML schema file to register it dynamically. The schema becomes available immediately for extraction requests using its `name` field.

Required YAML sections: `entities`, `relations`, and `inference` (each must be present; `entities` and `relations` must be non-empty mappings).

```bash
curl -X POST http://localhost:3131/v1/schemas/upload \
  -F "file=@config/schemas/knowledge_graph.yaml"
```

To replace an existing schema:

```bash
curl -X POST "http://localhost:3131/v1/schemas/upload?overwrite=true" \
  -F "file=@config/schemas/knowledge_graph.yaml"
```

Validation failures return `422`; duplicate names return `409` unless `overwrite=true`.

### `POST /v1/extract`

Extract triplets from a single markdown page.

```bash
curl -X POST http://localhost:3131/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "John works for Apple Inc. in Cupertino.",
    "schema_name": "knowledge_graph",
    "page_id": "page-1"
  }'
```

Response:

```json
{
  "schema_name": "knowledge_graph",
  "page_id": "page-1",
  "triplets": [
    {
      "subject": "John",
      "predicate": "works_for",
      "object": "Apple Inc.",
      "confidence": 0.93,
      "page_id": "page-1"
    }
  ],
  "entities": {
    "person": ["John"],
    "organization": ["Apple Inc."],
    "location": ["Cupertino"]
  }
}
```

### `POST /v1/extract/batch`

Process multiple pages in parallel (up to `MAX_WORKERS`):

```bash
curl -X POST http://localhost:3131/v1/extract/batch \
  -H "Content-Type: application/json" \
  -d '{
    "schema_name": "knowledge_graph",
    "pages": [
      {"page_id": "p1", "text": "John works for Apple Inc."},
      {"page_id": "p2", "text": "Sarah founded TechStartup in 2020."}
    ]
  }'
```

Triplet confidence is the minimum of head and tail span confidences when available.

## CI/CD

On every push to `main`, GitHub Actions runs:

1. **Quality** — `ruff check`, `ruff format --check`, `mypy`, and `pytest`
2. **Publish** — builds the Docker image and pushes it to GHCR as `ghcr.io/<owner>/<repo>:latest` and `ghcr.io/<owner>/<repo>:<sha>`

Pull the published image:

```bash
docker pull ghcr.io/<owner>/<repo>:latest
docker run --rm -p 3131:3131 ghcr.io/<owner>/<repo>:latest
```

## Development

```bash
# Lint and format
uv run ruff check app tests
uv run ruff format app tests

# Type check
uv run mypy app

# Tests
uv run pytest
```

## Project Layout

```
config/schemas/     Named YAML extraction schemas
app/                FastAPI application
tests/              Unit and integration tests
Dockerfile          Container image with pre-downloaded model
```

## License

See [LICENSE](LICENSE).
