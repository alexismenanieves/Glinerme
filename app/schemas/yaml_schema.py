"""Pydantic models for YAML extraction schema definitions."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class InferenceConfig(BaseModel):
    """Inference options applied when running GLiNER2 extraction."""

    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    include_confidence: bool = True
    include_spans: bool = False


class ExtractionSchemaDefinition(BaseModel):
    """Validated extraction schema loaded from a YAML file."""

    name: str
    description: str = ""
    entities: dict[str, str] = Field(default_factory=dict)
    relations: dict[str, str] = Field(default_factory=dict)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)

    @field_validator("entities", "relations", mode="before")
    @classmethod
    def normalize_label_maps(cls, value: Any) -> dict[str, str]:
        """Coerce entity and relation label maps to ``str -> str``."""
        if value is None:
            return {}
        if not isinstance(value, dict):
            msg = "Expected a mapping of label names to descriptions"
            raise TypeError(msg)
        return {str(key): str(desc) for key, desc in value.items()}

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Ensure schema names are non-empty after trimming."""
        normalized = value.strip()
        if not normalized:
            msg = "Schema name must not be empty"
            raise ValueError(msg)
        return normalized
