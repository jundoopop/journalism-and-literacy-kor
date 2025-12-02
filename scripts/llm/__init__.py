"""
Unified LLM Module

Provides a clean, maintainable abstraction layer for multiple LLM providers.
Supports: Gemini, OpenAI, Claude, Llama, Mistral.

Usage:
    from llm import LLMFactory

    # Auto-detect provider from environment
    analyzer = LLMFactory.create()

    # Explicit provider
    analyzer = LLMFactory.create(provider='gemini')

    # Extract sentences from article
    sentences = analyzer.get_highlight_sentences(article_text)
"""

from .factory import LLMFactory
from .base import AnalysisResult, LLMProvider, LLMConfig
from .exceptions import (
    LLMError,
    LLMProviderError,
    JSONParseError,
    ConfigurationError,
    APIKeyError,
    UnsupportedProviderError
)

__version__ = "1.0.0"

__all__ = [
    # Factory
    "LLMFactory",
    # Data classes
    "AnalysisResult",
    "LLMProvider",
    "LLMConfig",
    # Exceptions
    "LLMError",
    "LLMProviderError",
    "JSONParseError",
    "ConfigurationError",
    "APIKeyError",
    "UnsupportedProviderError",
]
