"""
Crawler service for fetching and parsing articles.

Encapsulates the crawler logic, providing a clean interface
for article fetching with logging and error handling.
"""

import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .base_service import BaseService, ServiceError
from observability import metrics


@dataclass
class ArticleData:
    """Structured article data."""
    url: str
    headline: str
    body_text: str
    metadata: Dict[str, Any]
    fetch_duration_ms: Optional[int] = None


class CrawlerError(ServiceError):
    """Exception raised when crawler fails."""
    pass


class CrawlerService(BaseService):
    """
    Service for crawling and parsing news articles.

    Wraps the existing crawler functionality with:
    - Structured logging
    - Error handling
    - Metrics collection
    """

    def __init__(self):
        super().__init__("CrawlerService")
        self._crawler = None

    def _get_crawler(self):
        """Lazy load the crawler to avoid circular imports."""
        if self._crawler is None:
            # Import here to avoid circular dependency
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from crawler_unified import fetch, parse_article
            self._crawler = {'fetch': fetch, 'parse': parse_article}
        return self._crawler

    def crawl_article(self, url: str) -> ArticleData:
        """
        Fetch and parse an article from a URL.

        Args:
            url: Article URL to crawl

        Returns:
            ArticleData with parsed content

        Raises:
            CrawlerError: If crawling or parsing fails

        Example:
            article = crawler_service.crawl_article('https://chosun.com/...')
            print(article.headline, article.body_text)
        """
        start_time = time.time()

        self.log_info("Starting article crawl", url=url)
        self.increment_counter("crawler_requests", tags={"url_domain": self._extract_domain(url)})

        try:
            with metrics.timer("crawler_fetch_duration", tags={"url_domain": self._extract_domain(url)}):
                # Use existing crawler
                crawler = self._get_crawler()
                html = crawler['fetch'](url)

                if not html:
                    raise CrawlerError(f"Failed to fetch HTML from {url}")

                # Parse the article
                parsed = crawler['parse'](url, html)

                if not parsed or 'body_text' not in parsed:
                    raise CrawlerError(f"Failed to parse article from {url}")

            duration_ms = int((time.time() - start_time) * 1000)

            article_data = ArticleData(
                url=url,
                headline=parsed.get('headline', ''),
                body_text=parsed.get('body_text', ''),
                metadata={
                    'date': parsed.get('date'),
                    'author': parsed.get('author'),
                    'section': parsed.get('section'),
                    'parser_used': parsed.get('parser_used', 'unknown')
                },
                fetch_duration_ms=duration_ms
            )

            self.log_info(
                "Article crawled successfully",
                url=url,
                headline=article_data.headline[:100],
                body_length=len(article_data.body_text),
                duration_ms=duration_ms,
                parser_used=article_data.metadata.get('parser_used')
            )

            self.increment_counter("crawler_success", tags={
                "url_domain": self._extract_domain(url),
                "parser": article_data.metadata.get('parser_used', 'unknown')
            })

            return article_data

        except CrawlerError:
            raise

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            self.log_error(
                "Crawler failed",
                exc=e,
                url=url,
                duration_ms=duration_ms
            )

            self.increment_counter("crawler_failures", tags={
                "url_domain": self._extract_domain(url),
                "error_type": type(e).__name__
            })

            raise CrawlerError(
                f"Failed to crawl article from {url}",
                details={'url': url, 'error': str(e), 'error_type': type(e).__name__}
            ) from e

    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL for metrics tagging.

        Args:
            url: Full URL

        Returns:
            Domain name (e.g., 'chosun.com')
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return 'unknown'

    def get_supported_domains(self) -> list:
        """
        Get list of supported news domains.

        Returns:
            List of domain names
        """
        return [
            'chosun.com',
            'joongang.co.kr',
            'hani.co.kr',
            'hankookilbo.com',
            'khan.co.kr'
        ]

    def is_url_supported(self, url: str) -> bool:
        """
        Check if URL is from a supported news domain.

        Args:
            url: URL to check

        Returns:
            True if domain is supported
        """
        domain = self._extract_domain(url)
        supported_domains = self.get_supported_domains()

        for supported in supported_domains:
            if domain.endswith(supported):
                return True

        return False
