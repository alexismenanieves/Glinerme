"""Validation helpers for YAML extraction schema files."""

from typing import Any

import yaml


class SchemaValidationError(ValueError):
    """Raised when uploaded or loaded schema YAML fails validation."""


def parse_schema_yaml(content: str) -> dict[str, Any]:
    """Parse schema YAML text and validate required sections."""
    if not content.strip():
        msg = "Schema file is empty"
        raise SchemaValidationError(msg)

    raw = yaml.safe_load(content)
    if raw is None:
        msg = "Schema file is empty"
        raise SchemaValidationError(msg)
    if not isinstance(raw, dict):
        msg = "Schema file must contain a YAML mapping at the top level"
        raise SchemaValidationError(msg)

    validate_raw_schema(raw)
    return raw


def validate_raw_schema(raw: dict[str, Any]) -> None:
    """Ensure a schema mapping includes required non-empty sections."""
    if "entities" not in raw:
        msg = "Missing required 'entities' section"
        raise SchemaValidationError(msg)
    entities = raw["entities"]
    if not isinstance(entities, dict) or not entities:
        msg = "'entities' section must be a non-empty mapping"
        raise SchemaValidationError(msg)

    if "relations" not in raw:
        msg = "Missing required 'relations' section"
        raise SchemaValidationError(msg)
    relations = raw["relations"]
    if not isinstance(relations, dict) or not relations:
        msg = "'relations' section must be a non-empty mapping"
        raise SchemaValidationError(msg)

    if "inference" not in raw:
        msg = "Missing required 'inference' section"
        raise SchemaValidationError(msg)
    inference = raw["inference"]
    if not isinstance(inference, dict):
        msg = "'inference' section must be a mapping"
        raise SchemaValidationError(msg)
