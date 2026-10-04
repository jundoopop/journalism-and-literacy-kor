"""
Configuration management for LLM providers

Provides default configurations for each provider and handles
environment variable overrides.
"""

import os
from typing import Optional
from .base import LLMProvider, LLMConfig


# Lightweight defaults reviewed against official catalogs on 2026-10-04.
# API availability and Korean extraction quality still require live evaluation.
DEFAULT_MODELS = {
    LLMProvider.GEMINI: "gemini-3.5-flash-lite",
    LLMProvider.OPENAI: "gpt-6-luna",
    LLMProvider.CLAUDE: "claude-haiku-4-5-20251001",
    LLMProvider.LLAMA: "meta-llama/Llama-3.1-8B-Instruct",
    LLMProvider.MISTRAL: "ministral-8b-2512"
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
    max_tokens = int(max_tokens_env) if max_tokens_env else 2048

    if max_tokens <= 0:
        raise ValueError("LLM_MAX_TOKENS must be positive")

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


# Alternatives use the same adapter; select via PROVIDER_MODEL in .env.
MODEL_OPTIONS = {
    "gemini": ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"],
    "openai": ["gpt-6-luna"],
    "claude": ["claude-haiku-4-5-20251001"],
    "mistral": ["ministral-3b-2512", "ministral-8b-2512"],
    # Legacy compatibility only; hosted availability not verified.
    "llama": ["meta-llama/Llama-3.1-8B-Instruct"],
}

def configuration_fingerprint(providers):
    """Cache identity without API keys, including prompt and generation settings."""
    import hashlib
    import json
    from .prompts.article_analysis import ARTICLE_ANALYSIS_PROMPT
    configs = []
    for name in sorted(providers):
        config = get_default_config(LLMProvider(name))
        configs.append((name, config.model_name, config.temperature, config.max_tokens, config.base_url))
    value = json.dumps([configs, ARTICLE_ANALYSIS_PROMPT], ensure_ascii=False)
    return hashlib.sha256(value.encode()).hexdigest()[:16]
