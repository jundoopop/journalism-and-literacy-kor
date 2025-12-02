"""
Custom exceptions for LLM module

Provides a clear exception hierarchy for all LLM-related errors.
All exceptions inherit from LLMError for easy catch-all handling.
"""


class LLMError(Exception):
    """Base exception for all LLM-related errors"""
    pass


class LLMProviderError(LLMError):
    """Error from LLM provider API call"""
    pass


class JSONParseError(LLMError):
    """Error parsing JSON response from LLM"""
    pass


class ConfigurationError(LLMError):
    """Error in LLM configuration"""
    pass


class APIKeyError(ConfigurationError):
    """API key missing or invalid"""
    pass


class UnsupportedProviderError(LLMError):
    """Requested provider not supported or not implemented"""
    pass
