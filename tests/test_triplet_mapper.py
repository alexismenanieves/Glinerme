from typing import Any

import pytest
from app.services.triplet_mapper import (
    map_relations_to_triplets,
    normalize_entities,
)


def test_map_relations_from_tuples() -> None:
    relation_extraction = {
        "works_for": [("John", "Apple Inc.")],
        "located_in": [("Apple Inc.", "Cupertino")],
    }
    triplets = map_relations_to_triplets(relation_extraction, page_id="p1")
    assert len(triplets) == 2
    assert triplets[0].subject == "John"
    assert triplets[0].predicate == "works_for"
    assert triplets[0].object == "Apple Inc."
    assert triplets[0].page_id == "p1"
    assert triplets[0].confidence is None


def test_map_relations_from_confidence_dicts() -> None:
    relation_extraction = {
        "works_for": [
            {
                "head": {"text": "John", "confidence": 0.95},
                "tail": {"text": "Apple Inc.", "confidence": 0.92},
            }
        ]
    }
    triplets = map_relations_to_triplets(relation_extraction)
    assert len(triplets) == 1
    assert triplets[0].confidence == pytest.approx(0.92)


def test_normalize_entities_with_confidence() -> None:
    entities = {
        "person": [{"text": "John", "confidence": 0.99}],
        "company": ["Apple Inc."],
    }
    normalized = normalize_entities(entities)
    assert normalized == {"person": ["John"], "company": ["Apple Inc."]}


def test_map_relations_skips_invalid_pairs() -> None:
    relation_extraction: dict[str, Any] = {
        "works_for": [{"head": {"text": "John"}}],
        "invalid": "not-a-list",
    }
    triplets = map_relations_to_triplets(relation_extraction)
    assert triplets == []
