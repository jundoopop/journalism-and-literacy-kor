"""
Crawler plugins for news site specific parsing.

Provides extensible plugin system for adding support for new news sites.
"""

from .base import BaseCrawlerPlugin
from .registry import CrawlerRegistry

__all__ = ['BaseCrawlerPlugin', 'CrawlerRegistry']
