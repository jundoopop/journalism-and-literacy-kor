"""
Health check service for monitoring system components.

Provides comprehensive health checks for:
- LLM providers
- Database
- Cache (Redis)
- Services
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from .base_service import BaseService
from config import settings


class HealthService(BaseService):
    """
    Service for health checking all system components.

    Performs health checks on LLM providers, database, cache,
    and other services.
    """

    def __init__(self, cache_service=None):
        super().__init__("HealthService")
        self._cache_service = cache_service
        self._provider_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_duration = 60  # Cache health checks for 60 seconds

    def check_llm_provider(self, provider: str) -> Dict[str, Any]:
        """
        Check health of a specific LLM provider.

        Args:
            provider: Provider name (gemini, mistral, openai, etc.)

        Returns:
            Dictionary with health status

        Example:
            health = health_service.check_llm_provider('gemini')
            if health['status'] == 'up':
                print("Gemini is healthy!")
        """
        # Check cache first
        now = time.time()
        if provider in self._provider_cache:
            cached = self._provider_cache[provider]
            if now - cached['timestamp'] < self._cache_duration:
                self.log_debug(f"Using cached health for {provider}")
                return cached['health']

        self.log_info(f"Checking health for provider: {provider}")

        try:
            start_time = time.time()

            # Try to import and initialize the provider
            if provider == 'gemini':
                health = self._check_gemini_health()
            elif provider == 'mistral':
                health = self._check_mistral_health()
            elif provider == 'openai':
                health = self._check_openai_health()
            elif provider == 'claude':
                health = self._check_claude_health()
            elif provider == 'llama':
                health = self._check_llama_health()
            else:
                health = {
                    'status': 'unknown',
                    'message': f'Unknown provider: {provider}'
                }

            # Add check duration
            health['check_duration_ms'] = int((time.time() - start_time) * 1000)
            health['last_check'] = datetime.utcnow().isoformat() + 'Z'

            # Cache the result
            self._provider_cache[provider] = {
                'health': health,
                'timestamp': now
            }

            return health

        except Exception as e:
            self.log_error(f"Health check failed for {provider}", exc=e)

            health = {
                'status': 'error',
                'message': f'Health check failed: {str(e)}',
                'last_check': datetime.utcnow().isoformat() + 'Z'
            }

            return health

    def _check_gemini_health(self) -> Dict[str, Any]:
        """Check Gemini API health."""
        if not settings.llm.gemini_api_key:
            return {
                'status': 'not_configured',
                'message': 'GEMINI_API_KEY not set'
            }

        try:
            from gemini_handler import GeminiAnalyzer
            analyzer = GeminiAnalyzer()

            return {
                'status': 'up',
                'model': 'gemini-2.5-flash-lite',
                'api_key_configured': True
            }

        except ValueError as e:
            if 'API key' in str(e):
                return {
                    'status': 'not_configured',
                    'message': 'Invalid API key'
                }
            raise

        except Exception as e:
            return {
                'status': 'down',
                'message': str(e)
            }

    def _check_mistral_health(self) -> Dict[str, Any]:
        """Check Mistral API health."""
        if not settings.llm.mistral_api_key:
            return {
                'status': 'not_configured',
                'message': 'MISTRAL_API_KEY not set'
            }

        try:
            from llm.factory import LLMFactory
            provider = LLMFactory.create('mistral')

            return {
                'status': 'up',
                'model': 'mistral-small-2506',
                'api_key_configured': True
            }

        except Exception as e:
            if 'API key' in str(e).lower():
                return {
                    'status': 'not_configured',
                    'message': 'Invalid API key'
                }

            return {
                'status': 'down',
                'message': str(e)
            }

    def _check_openai_health(self) -> Dict[str, Any]:
        """Check OpenAI API health."""
        if not settings.llm.openai_api_key:
            return {
                'status': 'not_configured',
                'message': 'OPENAI_API_KEY not set'
            }

        try:
            from llm.factory import LLMFactory
            provider = LLMFactory.create('openai')

            return {
                'status': 'up',
                'model': 'gpt-5-nano',
                'api_key_configured': True
            }

        except Exception as e:
            if 'API key' in str(e).lower() or 'auth' in str(e).lower():
                return {
                    'status': 'not_configured',
                    'message': 'Invalid API key'
                }

            return {
                'status': 'down',
                'message': str(e)
            }

    def _check_claude_health(self) -> Dict[str, Any]:
        """Check Claude API health."""
        if not settings.llm.claude_api_key:
            return {
                'status': 'not_configured',
                'message': 'CLAUDE_API_KEY not set'
            }

        try:
            from llm.factory import LLMFactory
            provider = LLMFactory.create('claude')

            return {
                'status': 'up',
                'model': 'claude-4.5-haiku',
                'api_key_configured': True
            }

        except Exception as e:
            if 'API key' in str(e).lower() or 'auth' in str(e).lower():
                return {
                    'status': 'not_configured',
                    'message': 'Invalid API key'
                }

            return {
                'status': 'down',
                'message': str(e)
            }

    def _check_llama_health(self) -> Dict[str, Any]:
        """Check Llama API health."""
        if not settings.llm.llama_api_key:
            return {
                'status': 'not_configured',
                'message': 'LLAMA_API_KEY not set'
            }

        try:
            from llm.factory import LLMFactory
            provider = LLMFactory.create('llama')

            return {
                'status': 'up',
                'model': 'meta-llama/Llama-3.1-8B-Instruct',
                'api_key_configured': True
            }

        except Exception as e:
            if 'API key' in str(e).lower() or 'auth' in str(e).lower():
                return {
                    'status': 'not_configured',
                    'message': 'Invalid API key'
                }

            return {
                'status': 'down',
                'message': str(e)
            }

    def check_all_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        Check health of all LLM providers.

        Returns:
            Dictionary mapping provider names to health status

        Example:
            all_health = health_service.check_all_providers()
            for provider, health in all_health.items():
                print(f"{provider}: {health['status']}")
        """
        providers = ['gemini', 'mistral', 'openai', 'claude', 'llama']
        results = {}

        for provider in providers:
            results[provider] = self.check_llm_provider(provider)

        return results

    def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status.

        Returns:
            Dictionary with all component health information

        Example:
            health = health_service.get_system_health()
            if health['overall_status'] == 'healthy':
                print("System is healthy!")
        """
        self.log_info("Performing comprehensive system health check")

        # Check all components
        database_health = self._check_database_health()
        cache_health = self._check_cache_health()
        llm_providers = self.check_all_providers()

        # Determine overall status
        overall_status = self._determine_overall_status(
            database_health,
            cache_health,
            llm_providers
        )

        return {
            'overall_status': overall_status,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'components': {
                'database': database_health,
                'cache': cache_health,
                'llm_providers': llm_providers
            }
        }

    def _check_database_health(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            from database import check_database_health
            return check_database_health()

        except Exception as e:
            self.log_error("Database health check failed", exc=e)
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    def _check_cache_health(self) -> Dict[str, Any]:
        """Check cache health."""
        if self._cache_service:
            return self._cache_service.health_check()
        else:
            return {
                'status': 'not_initialized',
                'message': 'Cache service not available'
            }

    def _determine_overall_status(
        self,
        database_health: Dict[str, Any],
        cache_health: Dict[str, Any],
        llm_providers: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Determine overall system health status.

        Args:
            database_health: Database health info
            cache_health: Cache health info
            llm_providers: LLM provider health info

        Returns:
            'healthy', 'degraded', or 'unhealthy'
        """
        # Critical: Database must be healthy
        if database_health.get('status') != 'healthy':
            return 'unhealthy'

        # At least one LLM provider must be up
        providers_up = sum(
            1 for p in llm_providers.values()
            if p.get('status') == 'up'
        )

        if providers_up == 0:
            return 'unhealthy'

        # Cache is nice to have but not critical
        if cache_health.get('status') not in ['healthy', 'disabled']:
            return 'degraded'

        # If some providers are down but at least one is up
        if providers_up < len(llm_providers):
            return 'degraded'

        return 'healthy'

    def clear_cache(self):
        """Clear the health check cache."""
        self._provider_cache.clear()
        self.log_info("Health check cache cleared")
