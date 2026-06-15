"""Tests for YAML schema validation helpers."""

import pytest
from app.services.schema_validation import SchemaValidationError, parse_schema_yaml

VALID_SCHEMA = """
name: demo
description: Demo schema
entities:
  person: A person
relations:
  works_for: Employment relation
inference:
  threshold: 0.5
  include_confidence: true
  include_spans: false
"""


def test_parse_schema_yaml_accepts_valid_schema() -> None:
    raw = parse_schema_yaml(VALID_SCHEMA)
    assert raw["name"] == "demo"
    assert "person" in raw["entities"]


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("", "Schema file is empty"),
        ("   \n  ", "Schema file is empty"),
        ("---\n", "Schema file is empty"),
        ("[]", "Schema file must contain a YAML mapping"),
        (
            "name: demo\nentities:\n  person: x\nrelations:\n  works_for: x",
            "Missing required 'inference' section",
        ),
        (
            "name: demo\nrelations:\n  works_for: x\ninference:\n  threshold: 0.5",
            "Missing required 'entities' section",
        ),
        (
            "name: demo\nentities:\n  person: x\ninference:\n  threshold: 0.5",
            "Missing required 'relations' section",
        ),
        (
            (
                "name: demo\nentities: {}\nrelations:\n  works_for: x\n"
                "inference:\n  threshold: 0.5"
            ),
            "'entities' section must be a non-empty mapping",
        ),
        (
            (
                "name: demo\nentities:\n  person: x\nrelations: []\n"
                "inference:\n  threshold: 0.5"
            ),
            "'relations' section must be a non-empty mapping",
        ),
        (
            (
                "name: demo\nentities:\n  person: x\nrelations:\n"
                "  works_for: x\ninference: 0.5"
            ),
            "'inference' section must be a mapping",
        ),
    ],
)
def test_parse_schema_yaml_rejects_invalid_schema(content: str, expected: str) -> None:
    with pytest.raises(SchemaValidationError, match=expected):
        parse_schema_yaml(content)
