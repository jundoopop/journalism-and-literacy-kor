"""
Factory pattern for creating LLM provider instances

Handles provider registration, instantiation, and configuration.
Supports fallback chains for reliability.
"""

from typing import Optional, List
from .base import BaseLLMProvider, LLMProvider
from .exceptions import UnsupportedProviderError, APIKeyError
from .config import get_default_config, get_provider_from_env
from .utils.security import get_api_key
import logging

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating LLM provider instances"""

    _provider_registry = {}

    @classmethod
    def register_provider(cls, provider: LLMProvider, provider_class):
        """
        Register a provider implementation

        Args:
            provider: LLMProvider enum value
            provider_class: Provider class (subclass of BaseLLMProvider)
        """
        cls._provider_registry[provider] = provider_class
        logger.debug(f"Registered provider: {provider.value}")

    @classmethod
    def create(
        cls,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs
    ) -> BaseLLMProvider:
        """
        Create LLM provider instance

        Args:
            provider: Provider name (gemini/openai/claude/llama/mistral)
                     Falls back to LLM_PROVIDER env variable or "gemini"
            api_key: API key (optional, will auto-detect from secure sources)
            model_name: Model name (optional, uses provider default)
            **kwargs: Additional configuration parameters (temperature, max_tokens, etc.)

        Returns:
            Configured LLM provider instance

        Raises:
            UnsupportedProviderError: If provider not supported
            APIKeyError: If API key not found
        """
        # Determine provider
        if provider is None:
            provider = get_provider_from_env()

        try:
            provider_enum = LLMProvider(provider.lower())
        except ValueError:
            raise UnsupportedProviderError(
                f"Provider '{provider}' not supported. "
                f"Supported: {[p.value for p in LLMProvider]}"
            )

        # Get API key if not provided
        if api_key is None:
            api_key = get_api_key(provider_enum)
            if not api_key:
                raise APIKeyError(
                    f"API key for {provider} not found. "
                    f"Set {provider.upper()}_API_KEY environment variable, "
                    f"store in system keyring, or provide via api_key parameter."
                )

        # Get default configuration
        config = get_default_config(provider_enum, api_key)

        # Override with provided values
        if model_name:
            config.model_name = model_name

        # Apply additional kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # Get provider class
        provider_class = cls._provider_registry.get(provider_enum)
        if not provider_class:
            raise UnsupportedProviderError(
                f"Provider {provider} registered but implementation not found. "
                f"This is likely a bug."
            )

        # Create and return instance
        logger.info(f"Creating {provider} provider with model {config.model_name}")
        return provider_class(config)

    @classmethod
    def create_with_fallback(
        cls,
        primary_provider: str,
        fallback_providers: List[str],
        **kwargs
    ) -> BaseLLMProvider:
        """
        Create provider with fallback chain

        Tries providers in order until one succeeds.

        Args:
            primary_provider: Primary provider to try first
            fallback_providers: List of fallback providers in order
            **kwargs: Configuration parameters

        Returns:
            First successfully initialized provider

        Raises:
            APIKeyError: If all providers fail to initialize
        """
        providers_to_try = [primary_provider] + fallback_providers

        last_error = None
        for provider in providers_to_try:
            try:
                return cls.create(provider=provider, **kwargs)
            except (APIKeyError, UnsupportedProviderError) as e:
                logger.warning(f"Failed to initialize {provider}: {e}")
                last_error = e
                continue

        raise APIKeyError(
            f"Failed to initialize any provider from: {providers_to_try}. "
            f"Last error: {last_error}"
        )


# Auto-register all available providers
def _register_providers():
    """Register all available providers"""
    logger.debug("Registering LLM providers...")

    try:
        from .providers.gemini import GeminiProvider
        LLMFactory.register_provider(LLMProvider.GEMINI, GeminiProvider)
    except ImportError as e:
        logger.warning(f"Gemini provider not available: {e}")

    try:
        from .providers.openai_provider import OpenAIProvider
        LLMFactory.register_provider(LLMProvider.OPENAI, OpenAIProvider)
    except ImportError as e:
        logger.warning(f"OpenAI provider not available: {e}")

    try:
        from .providers.claude import ClaudeProvider
        LLMFactory.register_provider(LLMProvider.CLAUDE, ClaudeProvider)
    except ImportError as e:
        logger.warning(f"Claude provider not available: {e}")

    try:
        from .providers.llama import LlamaProvider
        LLMFactory.register_provider(LLMProvider.LLAMA, LlamaProvider)
    except ImportError as e:
        logger.warning(f"Llama provider not available: {e}")

    try:
        from .providers.mistral import MistralProvider
        LLMFactory.register_provider(LLMProvider.MISTRAL, MistralProvider)
    except ImportError as e:
        logger.warning(f"Mistral provider not available: {e}")

    logger.info(f"Registered {len(LLMFactory._provider_registry)} providers")


# Auto-register on import
_register_providers()
