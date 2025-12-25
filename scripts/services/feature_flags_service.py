"""
Feature flags service for runtime feature control.

Provides programmatic access to feature flags with in-memory caching
for performance. Enables/disables features without code changes.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .base_service import BaseService
from database import session_scope, AnalyticsRepository


class FeatureFlagsService(BaseService):
    """
    Service for managing and checking feature flags.

    Provides fast, cached access to feature flags with automatic
    refresh to keep flags up-to-date.

    Example:
        flags = FeatureFlagsService()

        # Check if feature is enabled
        if flags.is_enabled('use_new_prompt'):
            # Use new prompt
            pass

        # Get flag config
        config = flags.get_config('llm_params')
        temperature = config.get('temperature', 0.2)
    """

    def __init__(self, cache_duration: int = 60):
        """
        Initialize feature flags service.

        Args:
            cache_duration: Cache duration in seconds (default: 60)
        """
        super().__init__("FeatureFlagsService")
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration = cache_duration

    def _load_flags_from_db(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all feature flags from database.

        Returns:
            Dictionary mapping flag names to flag data
        """
        flags = {}

        try:
            with session_scope() as session:
                repo = AnalyticsRepository(session)
                all_flags = repo.get_all_feature_flags()

                for flag in all_flags:
                    flags[flag.flag_name] = {
                        'enabled': flag.enabled,
                        'config': self._parse_config(flag.config),
                        'description': flag.description,
                        'updated_at': flag.updated_at
                    }

                self.log_info(f"Loaded {len(flags)} feature flags from database")

        except Exception as e:
            self.log_error("Failed to load feature flags from database", exc=e)
            # Return empty dict on error - flags will default to disabled

        return flags

    def _parse_config(self, config_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Parse JSON config string.

        Args:
            config_str: JSON config string

        Returns:
            Parsed config dict or None
        """
        if not config_str:
            return None

        try:
            return json.loads(config_str)
        except json.JSONDecodeError as e:
            self.log_warning(f"Failed to parse feature flag config: {config_str}", exc=e)
            return None

    def _refresh_cache_if_needed(self):
        """Refresh cache if it's expired."""
        now = datetime.utcnow()

        # Refresh if cache is empty or expired
        if (not self._cache_timestamp or
            (now - self._cache_timestamp).total_seconds() > self._cache_duration):

            self.log_debug("Refreshing feature flags cache")
            self._cache = self._load_flags_from_db()
            self._cache_timestamp = now

    def is_enabled(self, flag_name: str, default: bool = False) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag_name: Feature flag name
            default: Default value if flag not found (default: False)

        Returns:
            True if enabled, False otherwise

        Example:
            if flags.is_enabled('use_enhanced_prompt'):
                prompt = get_enhanced_prompt()
            else:
                prompt = get_standard_prompt()
        """
        self._refresh_cache_if_needed()

        flag_data = self._cache.get(flag_name)

        if flag_data is None:
            self.log_debug(f"Feature flag '{flag_name}' not found, using default: {default}")
            return default

        enabled = flag_data.get('enabled', default)

        self.log_debug(f"Feature flag '{flag_name}' is {'enabled' if enabled else 'disabled'}")

        return enabled

    def get_config(self, flag_name: str, default: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Get feature flag configuration.

        Args:
            flag_name: Feature flag name
            default: Default config if flag not found

        Returns:
            Configuration dictionary or default

        Example:
            config = flags.get_config('llm_params', {'temperature': 0.2})
            temperature = config.get('temperature')
            max_tokens = config.get('max_tokens', 1000)
        """
        self._refresh_cache_if_needed()

        flag_data = self._cache.get(flag_name)

        if flag_data is None:
            self.log_debug(f"Feature flag '{flag_name}' not found, using default config")
            return default

        config = flag_data.get('config', default)

        self.log_debug(f"Got config for feature flag '{flag_name}'")

        return config

    def get_flag(self, flag_name: str) -> Optional[Dict[str, Any]]:
        """
        Get complete feature flag data.

        Args:
            flag_name: Feature flag name

        Returns:
            Dictionary with enabled, config, description, updated_at

        Example:
            flag = flags.get_flag('new_feature')
            if flag and flag['enabled']:
                config = flag['config']
                description = flag['description']
        """
        self._refresh_cache_if_needed()
        return self._cache.get(flag_name)

    def get_all_flags(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all feature flags.

        Returns:
            Dictionary of all flags

        Example:
            all_flags = flags.get_all_flags()
            for name, data in all_flags.items():
                print(f"{name}: {data['enabled']}")
        """
        self._refresh_cache_if_needed()
        return self._cache.copy()

    def get_enabled_flags(self) -> List[str]:
        """
        Get list of all enabled flag names.

        Returns:
            List of enabled flag names

        Example:
            enabled = flags.get_enabled_flags()
            print(f"Enabled features: {', '.join(enabled)}")
        """
        self._refresh_cache_if_needed()

        enabled_flags = [
            name for name, data in self._cache.items()
            if data.get('enabled', False)
        ]

        return enabled_flags

    def set_flag(
        self,
        flag_name: str,
        enabled: bool,
        config: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ) -> bool:
        """
        Set a feature flag value.

        Args:
            flag_name: Feature flag name
            enabled: Whether flag is enabled
            config: Optional configuration dictionary
            description: Optional description

        Returns:
            True if successful, False otherwise

        Example:
            # Enable a flag
            flags.set_flag('new_feature', True, description="New feature rollout")

            # Enable with config
            flags.set_flag('llm_params', True, config={'temperature': 0.3})

            # Disable a flag
            flags.set_flag('old_feature', False)
        """
        try:
            with session_scope() as session:
                repo = AnalyticsRepository(session)

                flag = repo.set_feature_flag(
                    flag_name=flag_name,
                    enabled=enabled,
                    config=config,
                    description=description
                )

                if flag:
                    # Invalidate cache to force reload
                    self._cache_timestamp = None

                    self.log_info(
                        f"Feature flag '{flag_name}' set to {enabled}",
                        flag_name=flag_name,
                        enabled=enabled
                    )

                    self.increment_counter("feature_flags_updated", tags={"flag": flag_name})

                    return True
                else:
                    self.log_error(f"Failed to set feature flag '{flag_name}'")
                    return False

        except Exception as e:
            self.log_error(f"Error setting feature flag '{flag_name}'", exc=e)
            return False

    def reload(self):
        """
        Force reload of feature flags from database.

        Example:
            # After updating flags via admin panel
            flags.reload()
        """
        self.log_info("Force reloading feature flags")
        self._cache_timestamp = None
        self._refresh_cache_if_needed()

    def clear_cache(self):
        """
        Clear the feature flags cache.

        Example:
            flags.clear_cache()
        """
        self.log_info("Clearing feature flags cache")
        self._cache = {}
        self._cache_timestamp = None

    def create_default_flags(self):
        """
        Create default feature flags if they don't exist.

        This is useful for initial setup or ensuring certain flags exist.

        Example:
            flags.create_default_flags()
        """
        default_flags = [
            {
                'name': 'cache_enabled',
                'enabled': True,
                'config': None,
                'description': 'Enable Redis caching for LLM analysis results'
            },
            {
                'name': 'metrics_enabled',
                'enabled': True,
                'config': None,
                'description': 'Enable metrics collection'
            },
            {
                'name': 'use_enhanced_prompt',
                'enabled': False,
                'config': None,
                'description': 'Use enhanced article analysis prompt (experimental)'
            },
            {
                'name': 'strict_consensus',
                'enabled': False,
                'config': {'min_providers': 3},
                'description': 'Require at least 3 providers for consensus'
            }
        ]

        try:
            with session_scope() as session:
                repo = AnalyticsRepository(session)

                for flag_data in default_flags:
                    # Check if flag already exists
                    existing = repo.get_feature_flag(flag_data['name'])

                    if not existing:
                        repo.set_feature_flag(
                            flag_name=flag_data['name'],
                            enabled=flag_data['enabled'],
                            config=flag_data['config'],
                            description=flag_data['description']
                        )

                        self.log_info(f"Created default feature flag: {flag_data['name']}")

                # Reload cache after creating defaults
                self.reload()

        except Exception as e:
            self.log_error("Failed to create default feature flags", exc=e)
