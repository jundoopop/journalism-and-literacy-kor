"""
Crawler plugin registry for auto-discovery and selection.

Manages available crawler plugins and selects the best plugin
for a given URL.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Type
import importlib.util

from observability import get_logger
from .base import BaseCrawlerPlugin, CrawlerResult

logger = get_logger(__name__)


class CrawlerRegistry:
    """
    Registry for managing crawler plugins.

    Auto-discovers plugins from the plugins directory and provides
    methods for selecting the best plugin for a URL.

    Example:
        registry = CrawlerRegistry()

        # Find plugin for URL
        plugin = registry.get_plugin_for_url('https://chosun.com/...')

        # Parse article
        result = plugin.parse(url, html)
    """

    def __init__(self, plugins_dir: Optional[Path] = None, config_file: Optional[Path] = None):
        """
        Initialize crawler registry.

        Args:
            plugins_dir: Directory containing plugin files
            config_file: YAML configuration file
        """
        self.logger = get_logger(__name__)

        # Default paths
        if plugins_dir is None:
            plugins_dir = Path(__file__).parent / 'plugins'

        if config_file is None:
            config_file = Path(__file__).parent / 'plugin_config.yaml'

        self.plugins_dir = plugins_dir
        self.config_file = config_file

        # Storage
        self._plugins: Dict[str, BaseCrawlerPlugin] = {}
        self._config: Dict[str, any] = {}

        # Load plugins and config
        self._load_config()
        self._discover_plugins()

    def _load_config(self):
        """Load plugin configuration from YAML."""
        if not self.config_file.exists():
            self.logger.info(f"Config file not found: {self.config_file}")
            self._create_default_config()
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}

            self.logger.info(f"Loaded config with {len(self._config.get('plugins', []))} plugin configs")

        except Exception as e:
            self.logger.error("Failed to load plugin config", exc=e)

    def _create_default_config(self):
        """Create default plugin configuration."""
        default_config = {
            'plugins': [
                {
                    'name': 'chosun',
                    'enabled': True,
                    'priority': 10,
                    'domains': ['chosun.com']
                },
                {
                    'name': 'joongang',
                    'enabled': True,
                    'priority': 10,
                    'domains': ['joongang.co.kr']
                },
                {
                    'name': 'hani',
                    'enabled': True,
                    'priority': 10,
                    'domains': ['hani.co.kr']
                },
                {
                    'name': 'hankook',
                    'enabled': True,
                    'priority': 10,
                    'domains': ['hankookilbo.com']
                },
                {
                    'name': 'khan',
                    'enabled': True,
                    'priority': 10,
                    'domains': ['khan.co.kr']
                },
                {
                    'name': 'generic',
                    'enabled': True,
                    'priority': 1,  # Fallback, lowest priority
                    'domains': ['*']
                }
            ]
        }

        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)

            self.logger.info(f"Created default config file: {self.config_file}")
            self._config = default_config

        except Exception as e:
            self.logger.error("Failed to create default config", exc=e)

    def _discover_plugins(self):
        """Discover and load all plugins from plugins directory."""
        if not self.plugins_dir.exists():
            self.logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            return

        # Find all .py files in plugins directory
        for plugin_file in self.plugins_dir.glob('*.py'):
            if plugin_file.name.startswith('_'):
                continue

            try:
                # Load module dynamically
                module_name = plugin_file.stem
                spec = importlib.util.spec_from_file_location(module_name, plugin_file)

                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Find plugin classes
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)

                        # Check if it's a plugin class (subclass of BaseCrawlerPlugin)
                        if (isinstance(attr, type) and
                            issubclass(attr, BaseCrawlerPlugin) and
                            attr is not BaseCrawlerPlugin):

                            # Instantiate plugin
                            plugin = attr()

                            # Apply config overrides
                            plugin_config = self._get_plugin_config(plugin.name)

                            if plugin_config:
                                plugin.enabled = plugin_config.get('enabled', plugin.enabled)
                                plugin.priority = plugin_config.get('priority', plugin.priority)
                                plugin.domains = plugin_config.get('domains', plugin.domains)

                            # Register plugin if enabled
                            if plugin.enabled:
                                self._plugins[plugin.name] = plugin
                                self.logger.info(f"Loaded plugin: {plugin.name} (priority={plugin.priority})")

            except Exception as e:
                self.logger.error(f"Failed to load plugin from {plugin_file}", exc=e)

        self.logger.info(f"Discovered {len(self._plugins)} plugins")

    def _get_plugin_config(self, plugin_name: str) -> Optional[Dict]:
        """Get configuration for a specific plugin."""
        plugins_config = self._config.get('plugins', [])

        for plugin_config in plugins_config:
            if plugin_config.get('name') == plugin_name:
                return plugin_config

        return None

    def get_plugin_for_url(self, url: str) -> Optional[BaseCrawlerPlugin]:
        """
        Get the best plugin for a URL.

        Args:
            url: Article URL

        Returns:
            Plugin instance or None

        Example:
            plugin = registry.get_plugin_for_url('https://chosun.com/...')
            if plugin:
                result = plugin.parse(url, html)
        """
        # Find all plugins that can handle this URL
        matching_plugins = [
            plugin for plugin in self._plugins.values()
            if plugin.can_handle(url)
        ]

        if not matching_plugins:
            self.logger.warning(f"No plugin found for URL: {url}")
            return None

        # Sort by priority (highest first)
        matching_plugins.sort(key=lambda p: p.priority, reverse=True)

        selected = matching_plugins[0]

        self.logger.info(f"Selected plugin '{selected.name}' for URL: {url[:50]}...")

        return selected

    def get_plugin(self, name: str) -> Optional[BaseCrawlerPlugin]:
        """
        Get plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None
        """
        return self._plugins.get(name)

    def list_plugins(self) -> List[Dict[str, any]]:
        """
        List all registered plugins.

        Returns:
            List of plugin info dictionaries
        """
        plugins = []

        for plugin in self._plugins.values():
            plugins.append({
                'name': plugin.name,
                'domains': plugin.domains,
                'priority': plugin.priority,
                'enabled': plugin.enabled
            })

        # Sort by priority
        plugins.sort(key=lambda p: p['priority'], reverse=True)

        return plugins

    def reload(self):
        """Reload plugins from disk."""
        self.logger.info("Reloading plugins")
        self._plugins.clear()
        self._load_config()
        self._discover_plugins()
