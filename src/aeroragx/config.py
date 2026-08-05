"""Configuration loading and validation."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class NTRSConfig(BaseModel):
    """NASA Technical Reports Server connection settings."""

    base_url: str = "https://ntrs.nasa.gov/api"
    timeout_seconds: float = Field(default=30.0, gt=0)


class AppConfig(BaseModel):
    """Top-level application configuration."""

    project_name: str = "AeroRAG-X"
    data_dir: Path = Path("data")
    ntrs: NTRSConfig = NTRSConfig()


def load_config(path: Path) -> AppConfig:
    """Load and validate a YAML configuration file."""
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("Configuration root must be a YAML mapping.")

    return AppConfig.model_validate(raw)
