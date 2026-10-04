"""
Configuration module for centralized settings management.

Provides type-safe configuration using Pydantic with
environment variable support and validation.
"""

from pathlib import Path
from dotenv import load_dotenv

# Populate the environment before nested settings and legacy provider readers load.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

from .settings import (
    settings,
    Settings,
    ObservabilitySettings,
    DatabaseSettings,
    CacheSettings,
    LLMSettings
)

__all__ = [
    'settings',
    'Settings',
    'ObservabilitySettings',
    'DatabaseSettings',
    'CacheSettings',
    'LLMSettings'
]


def ensure_dir(path: str):
    """Create the parent directory of an output file."""
    from pathlib import Path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
