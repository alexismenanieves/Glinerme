"""GLiNER2 model loading helpers."""

from gliner2 import GLiNER2

from app.settings import Settings


def load_model(settings: Settings) -> GLiNER2:
    """Load the configured GLiNER2 model from Hugging Face or local cache."""
    return GLiNER2.from_pretrained(settings.model_name, map_location=settings.device)
