"""Shared request validation before any outbound or paid work."""
from flask import request
from config import settings
from url_safety import UnsafeURL, validate_news_url
from .errors import ValidationError

PROVIDERS = {"gemini", "mistral", "openai", "claude", "llama"}


def analysis_request(consensus=False):
    data = request.get_json()
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")
    try:
        url = validate_news_url(data.get("url"))
    except UnsafeURL as exc:
        raise ValidationError(str(exc)) from exc
    if not consensus:
        provider = data.get("provider", "gemini")
        if not isinstance(provider, str) or provider not in PROVIDERS:
            raise ValidationError("provider must be a supported provider name")
        return url
    providers = data.get("providers", settings.consensus_providers)
    if (not isinstance(providers, list) or not 1 <= len(providers) <= len(PROVIDERS)
            or any(not isinstance(p, str) or p not in PROVIDERS for p in providers)
            or len(set(providers)) != len(providers)):
        raise ValidationError("providers must contain 1–5 unique supported provider names")
    return url, providers
