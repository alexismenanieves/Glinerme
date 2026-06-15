"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Runtime configuration for the extraction service."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    model_name: str = Field(default="fastino/gliner2-base-v1", alias="MODEL_NAME")
    device: str = Field(default="cpu", alias="DEVICE")
    schemas_dir: Path = Field(default=Path("./config/schemas"), alias="SCHEMAS_DIR")
    max_workers: int = Field(default=2, alias="MAX_WORKERS")
    max_text_length: int = Field(default=100_000, alias="MAX_TEXT_LENGTH")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=3131, alias="PORT")
    hf_home: Path = Field(default=Path("/app/.cache/huggingface"), alias="HF_HOME")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
