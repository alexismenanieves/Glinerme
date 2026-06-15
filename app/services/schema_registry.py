"""Load and compile named YAML extraction schemas for GLiNER2."""

import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from gliner2 import GLiNER2

from app.schemas.api import SchemaSummary
from app.schemas.yaml_schema import ExtractionSchemaDefinition
from app.services.schema_validation import SchemaValidationError, parse_schema_yaml


class SchemaConflictError(ValueError):
    """Raised when registering a schema that already exists."""


@dataclass(frozen=True)
class CompiledSchema:
    """YAML schema definition paired with a GLiNER2 runtime schema."""

    definition: ExtractionSchemaDefinition
    gliner_schema: Any


class SchemaRegistry:
    """Registry of named extraction schemas loaded from YAML files."""

    def __init__(self, schemas_dir: Path, model: GLiNER2) -> None:
        """Load and compile all ``*.yaml`` schemas from ``schemas_dir``."""
        self._schemas_dir = schemas_dir
        self._model = model
        self._schemas: dict[str, CompiledSchema] = {}
        self._lock = threading.Lock()
        self._schemas_dir.mkdir(parents=True, exist_ok=True)
        self._load_all()

    def _load_all(self) -> None:
        """Scan the schemas directory and build compiled schema objects."""
        yaml_files = sorted(self._schemas_dir.glob("*.yaml"))
        yaml_files.extend(sorted(self._schemas_dir.glob("*.yml")))
        if not yaml_files:
            return

        for path in yaml_files:
            definition = self._load_definition(path)
            if definition.name in self._schemas:
                msg = f"Duplicate schema name '{definition.name}' in {path}"
                raise ValueError(msg)
            self._schemas[definition.name] = self._compile(definition)

    def _load_definition(self, path: Path) -> ExtractionSchemaDefinition:
        """Parse and validate one YAML schema file from disk."""
        content = path.read_text(encoding="utf-8")
        try:
            raw = parse_schema_yaml(content)
        except SchemaValidationError as exc:
            msg = f"{path}: {exc}"
            raise ValueError(msg) from exc
        return ExtractionSchemaDefinition.model_validate(raw)

    def _compile(self, definition: ExtractionSchemaDefinition) -> CompiledSchema:
        """Build a compiled schema object from a validated definition."""
        return CompiledSchema(
            definition=definition,
            gliner_schema=self._build_gliner_schema(definition),
        )

    def _build_gliner_schema(self, definition: ExtractionSchemaDefinition) -> Any:
        """Build a GLiNER2 schema from entity and relation label definitions."""
        builder = self._model.create_schema()
        if definition.entities:
            builder = builder.entities(definition.entities)
        if definition.relations:
            builder = builder.relations(definition.relations)
        return builder

    def _schema_path(self, name: str) -> Path:
        """Return the on-disk path for a schema name."""
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
        return self._schemas_dir / f"{safe_name}.yaml"

    def register_from_yaml(
        self,
        content: str,
        *,
        overwrite: bool = False,
    ) -> tuple[SchemaSummary, bool]:
        """Validate, persist, and register a schema from YAML text."""
        raw = parse_schema_yaml(content)
        definition = ExtractionSchemaDefinition.model_validate(raw)

        with self._lock:
            replaced = definition.name in self._schemas
            if replaced and not overwrite:
                msg = f"Schema '{definition.name}' already exists"
                raise SchemaConflictError(msg)

            path = self._schema_path(definition.name)
            path.write_text(
                yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            self._schemas[definition.name] = self._compile(definition)

        summary = SchemaSummary(
            name=definition.name,
            description=definition.description,
            entity_count=len(definition.entities),
            relation_count=len(definition.relations),
        )
        return summary, replaced

    def get(self, name: str) -> CompiledSchema:
        """Return a compiled schema by name."""
        if name not in self._schemas:
            available = ", ".join(sorted(self._schemas))
            msg = f"Unknown schema '{name}'. Available schemas: {available}"
            raise KeyError(msg)
        return self._schemas[name]

    def list_summaries(self) -> list[SchemaSummary]:
        """Return metadata for all registered schemas."""
        return [
            SchemaSummary(
                name=compiled.definition.name,
                description=compiled.definition.description,
                entity_count=len(compiled.definition.entities),
                relation_count=len(compiled.definition.relations),
            )
            for compiled in self._schemas.values()
        ]

    @property
    def count(self) -> int:
        """Return the number of loaded schemas."""
        return len(self._schemas)
