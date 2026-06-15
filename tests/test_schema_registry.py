from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from app.schemas.yaml_schema import ExtractionSchemaDefinition
from app.services.schema_registry import SchemaRegistry


@pytest.fixture
def schemas_dir(tmp_path: Path) -> Path:
    schema_path = tmp_path / "test_schema.yaml"
    schema_path.write_text(
        yaml.dump(
            {
                "name": "test_schema",
                "description": "Test schema",
                "entities": {"person": "A person"},
                "relations": {"works_for": "Employment relation"},
                "inference": {
                    "threshold": 0.5,
                    "include_confidence": True,
                    "include_spans": False,
                },
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_schema_definition_validation() -> None:
    definition = ExtractionSchemaDefinition.model_validate(
        {
            "name": "demo",
            "entities": {"person": "desc"},
            "relations": {"works_for": "desc"},
        }
    )
    assert definition.name == "demo"
    assert definition.inference.threshold == 0.5


def test_schema_registry_loads_named_schemas(schemas_dir: Path) -> None:
    model = MagicMock()
    builder = MagicMock()
    model.create_schema.return_value = builder
    builder.entities.return_value = builder
    builder.relations.return_value = builder

    registry = SchemaRegistry(schemas_dir, model)
    summaries = registry.list_summaries()

    assert registry.count == 1
    assert summaries[0].name == "test_schema"
    assert summaries[0].entity_count == 1
    assert summaries[0].relation_count == 1

    compiled = registry.get("test_schema")
    assert compiled.definition.name == "test_schema"
    model.create_schema.assert_called_once()
    builder.entities.assert_called_once()
    builder.relations.assert_called_once()


def test_schema_registry_unknown_schema(schemas_dir: Path) -> None:
    model = MagicMock()
    builder = MagicMock()
    model.create_schema.return_value = builder
    builder.entities.return_value = builder
    builder.relations.return_value = builder

    registry = SchemaRegistry(schemas_dir, model)
    with pytest.raises(KeyError, match="Unknown schema"):
        registry.get("missing")


def test_schema_registry_allows_empty_directory(tmp_path: Path) -> None:
    model = MagicMock()
    registry = SchemaRegistry(tmp_path / "schemas", model)
    assert registry.count == 0


def test_schema_registry_register_from_yaml(schemas_dir: Path) -> None:
    model = MagicMock()
    builder = MagicMock()
    model.create_schema.return_value = builder
    builder.entities.return_value = builder
    builder.relations.return_value = builder

    registry = SchemaRegistry(schemas_dir, model)
    content = yaml.dump(
        {
            "name": "dynamic_schema",
            "description": "Dynamic",
            "entities": {"company": "A company"},
            "relations": {"acquired": "Acquisition"},
            "inference": {
                "threshold": 0.6,
                "include_confidence": True,
                "include_spans": False,
            },
        }
    )
    summary, replaced = registry.register_from_yaml(content)
    assert summary.name == "dynamic_schema"
    assert replaced is False
    assert registry.count == 2
    assert (schemas_dir / "dynamic_schema.yaml").is_file()
