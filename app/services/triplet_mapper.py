"""Convert GLiNER2 extraction output into API-friendly structures."""

from typing import Any

from app.schemas.api import Triplet


def _confidence_from_pair(head: Any, tail: Any) -> float | None:
    """Return the minimum head/tail confidence when either span provides one."""
    head_conf = head.get("confidence") if isinstance(head, dict) else None
    tail_conf = tail.get("confidence") if isinstance(tail, dict) else None
    if head_conf is None and tail_conf is None:
        return None
    if head_conf is None:
        assert tail_conf is not None
        return float(tail_conf)
    if tail_conf is None:
        return float(head_conf)
    return float(min(head_conf, tail_conf))


def _text_from_span(value: Any) -> str:
    """Extract display text from a GLiNER2 span or plain string value."""
    if isinstance(value, dict):
        text = value.get("text")
        if text is not None:
            return str(text)
    return str(value)


def map_relations_to_triplets(
    relation_extraction: dict[str, Any],
    *,
    page_id: str | None = None,
) -> list[Triplet]:
    """Map GLiNER2 relation output to flat subject-predicate-object triplets."""
    triplets: list[Triplet] = []
    for predicate, pairs in relation_extraction.items():
        if not isinstance(pairs, list):
            continue
        for pair in pairs:
            if isinstance(pair, tuple) and len(pair) == 2:
                subject, obj = pair
                triplets.append(
                    Triplet(
                        subject=str(subject),
                        predicate=str(predicate),
                        object=str(obj),
                        page_id=page_id,
                    )
                )
                continue
            if isinstance(pair, dict):
                head = pair.get("head")
                tail = pair.get("tail")
                if head is None or tail is None:
                    continue
                triplets.append(
                    Triplet(
                        subject=_text_from_span(head),
                        predicate=str(predicate),
                        object=_text_from_span(tail),
                        confidence=_confidence_from_pair(head, tail),
                        page_id=page_id,
                    )
                )
    return triplets


def normalize_entities(entities: dict[str, Any]) -> dict[str, list[str]]:
    """Flatten GLiNER2 entity spans into label -> text list mappings."""
    normalized: dict[str, list[str]] = {}
    for label, values in entities.items():
        if not isinstance(values, list):
            continue
        texts: list[str] = []
        for value in values:
            if isinstance(value, dict) and "text" in value:
                texts.append(str(value["text"]))
            else:
                texts.append(str(value))
        normalized[str(label)] = texts
    return normalized
