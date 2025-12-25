"""
Base crawler plugin class.

Defines the interface that all crawler plugins must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class CrawlerResult:
    """
    Standardized crawler result.

    Attributes:
        headline: Article headline/title
        body_text: Main article body text
        date: Publication date (ISO format)
        author: Author name(s)
        section: Section/category
        tags: Article tags/keywords
        metadata: Additional metadata
    """
    headline: str
    body_text: str
    date: Optional[str] = None
    author: Optional[str] = None
    section: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseCrawlerPlugin(ABC):
    """
    Base class for news site crawler plugins.

    Subclasses should override parse() method to implement
    site-specific parsing logic.

    Example:
        class ChosunCrawler(BaseCrawlerPlugin):
            name = "chosun"
            domains = ["chosun.com", "www.chosun.com"]

            def parse(self, url, html):
                soup = BeautifulSoup(html, 'lxml')
                headline = soup.select_one('.article-title').text
                body = soup.select_one('.article-body').text
                return CrawlerResult(
                    headline=headline,
                    body_text=body
                )
    """

    # Plugin metadata (override in subclasses)
    name: str = "base"
    domains: List[str] = []
    priority: int = 10  # Higher priority = tried first (0-100)
    enabled: bool = True

    @abstractmethod
    def parse(self, url: str, html: str) -> CrawlerResult:
        """
        Parse HTML content into structured article data.

        Args:
            url: Article URL
            html: HTML content

        Returns:
            CrawlerResult with parsed article data

        Raises:
            Exception: If parsing fails
        """
        pass

    def can_handle(self, url: str) -> bool:
        """
        Check if this plugin can handle the given URL.

        Args:
            url: Article URL

        Returns:
            True if plugin can handle this URL
        """
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            domain = parsed.netloc

            # Remove www. prefix for comparison
            if domain.startswith('www.'):
                domain = domain[4:]

            # Check if domain matches any of this plugin's domains
            for plugin_domain in self.domains:
                # Wildcard support
                if plugin_domain == '*':
                    return True

                if plugin_domain.startswith('www.'):
                    plugin_domain = plugin_domain[4:]

                if domain.endswith(plugin_domain):
                    return True

            return False

        except Exception:
            return False

    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.name}', domains={self.domains})>"
