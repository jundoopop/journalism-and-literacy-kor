"""
Configuration management for LLM providers

Provides default configurations for each provider and handles
environment variable overrides.
"""

import os
from typing import Optional
from .base import LLMProvider, LLMConfig


# Default model names for each provider (NEWEST 2025 LIGHTWEIGHT MODELS)
DEFAULT_MODELS = {
    LLMProvider.GEMINI: "gemini-2.5-flash-lite",
    LLMProvider.OPENAI: "gpt-5-nano",
    LLMProvider.CLAUDE: "claude-4.5-haiku",
    LLMProvider.LLAMA: "meta-llama/Llama-3.1-8B-Instruct",
    LLMProvider.MISTRAL: "mistral-small-2506"
}

# Default base URLs for providers that need them
DEFAULT_BASE_URLS = {
    LLMProvider.OPENAI: "https://api.openai.com/v1",
    LLMProvider.LLAMA: "https://api.together.xyz/v1",
}


def get_default_config(provider: LLMProvider, api_key: str = "") -> LLMConfig:
    """
    Get default configuration for a provider

    Args:
        provider: LLM provider enum
        api_key: API key (will be set by factory if empty)

    Returns:
        LLMConfig with default settings from environment or hardcoded defaults
    """
    # Get model name from environment or use default
    model_env_var = f"{provider.value.upper()}_MODEL"
    model_name = os.getenv(model_env_var, DEFAULT_MODELS[provider])

    # Get common LLM settings from environment
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    max_tokens_env = os.getenv("LLM_MAX_TOKENS")
    max_tokens = int(max_tokens_env) if max_tokens_env else None

    timeout = int(os.getenv("LLM_TIMEOUT", "40"))
    max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))

    # Get base URL if provider needs one
    base_url = None
    if provider in DEFAULT_BASE_URLS:
        base_url_env_var = f"{provider.value.upper()}_BASE_URL"
        base_url = os.getenv(base_url_env_var, DEFAULT_BASE_URLS[provider])

    return LLMConfig(
        provider=provider,
        api_key=api_key,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
        base_url=base_url
    )


def get_provider_from_env() -> str:
    """
    Get the default provider name from environment

    Returns:
        Provider name (default: "gemini")
    """
    return os.getenv("LLM_PROVIDER", "gemini")
