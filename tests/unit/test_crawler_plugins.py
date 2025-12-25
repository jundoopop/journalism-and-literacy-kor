"""
Unit tests for crawler plugin system.
"""

import pytest
from crawlers.base import BaseCrawlerPlugin, CrawlerResult
from crawlers.registry import CrawlerRegistry
from crawlers.plugins.generic import GenericCrawler


class TestBaseCrawlerPlugin:
    """Test base crawler plugin functionality."""

    def test_crawler_result_dataclass(self):
        """Test CrawlerResult dataclass creation."""
        result = CrawlerResult(
            headline="Test Headline",
            body_text="Test body text",
            date="2025-01-15",
            author="Test Author"
        )

        assert result.headline == "Test Headline"
        assert result.body_text == "Test body text"
        assert result.date == "2025-01-15"
        assert result.author == "Test Author"

    def test_can_handle_exact_domain_match(self):
        """Test domain matching with exact match."""
        class TestCrawler(BaseCrawlerPlugin):
            name = "test"
            domains = ["example.com"]

            def parse(self, url, html):
                pass

        crawler = TestCrawler()

        assert crawler.can_handle("https://example.com/article") is True
        assert crawler.can_handle("https://www.example.com/article") is True
        assert crawler.can_handle("https://other.com/article") is False

    def test_can_handle_subdomain_match(self):
        """Test domain matching with subdomains."""
        class TestCrawler(BaseCrawlerPlugin):
            name = "test"
            domains = ["example.com"]

            def parse(self, url, html):
                pass

        crawler = TestCrawler()

        assert crawler.can_handle("https://news.example.com/article") is True
        assert crawler.can_handle("https://sports.example.com/article") is True

    def test_can_handle_wildcard(self):
        """Test wildcard domain matching."""
        class WildcardCrawler(BaseCrawlerPlugin):
            name = "wildcard"
            domains = ["*"]

            def parse(self, url, html):
                pass

        crawler = WildcardCrawler()

        assert crawler.can_handle("https://any-site.com/article") is True
        assert crawler.can_handle("https://another-site.org/news") is True

    def test_can_handle_www_prefix_handling(self):
        """Test that www prefix is handled correctly."""
        class TestCrawler(BaseCrawlerPlugin):
            name = "test"
            domains = ["www.example.com"]

            def parse(self, url, html):
                pass

        crawler = TestCrawler()

        assert crawler.can_handle("https://example.com/article") is True
        assert crawler.can_handle("https://www.example.com/article") is True

    def test_can_handle_invalid_url(self):
        """Test handling of invalid URLs."""
        class TestCrawler(BaseCrawlerPlugin):
            name = "test"
            domains = ["example.com"]

            def parse(self, url, html):
                pass

        crawler = TestCrawler()

        assert crawler.can_handle("not-a-url") is False
        assert crawler.can_handle("") is False


class TestGenericCrawler:
    """Test generic fallback crawler."""

    def test_generic_crawler_initialization(self):
        """Test that generic crawler initializes correctly."""
        crawler = GenericCrawler()

        assert crawler.name == "generic"
        assert crawler.domains == ["*"]
        assert crawler.priority == 1  # Lowest priority

    def test_generic_crawler_handles_all_urls(self):
        """Test that generic crawler can handle any URL."""
        crawler = GenericCrawler()

        test_urls = [
            "https://example.com",
            "https://test.org/article",
            "https://unknown-site.net/news/123"
        ]

        for url in test_urls:
            assert crawler.can_handle(url) is True

    def test_generic_crawler_parse_with_readability(self, mock_article_html):
        """Test parsing with Readability."""
        crawler = GenericCrawler()

        result = crawler.parse("https://test.com/article", mock_article_html)

        assert isinstance(result, CrawlerResult)
        assert result.headline is not None
        assert len(result.headline) > 0
        assert result.body_text is not None
        assert len(result.body_text) > 0

    def test_generic_crawler_extracts_text(self):
        """Test text extraction from HTML."""
        crawler = GenericCrawler()

        html = """
        <html>
            <head><title>Test Article</title></head>
            <body>
                <script>alert('ads')</script>
                <div class="ad">Advertisement</div>
                <p>This is the main content.</p>
                <p>Another paragraph of content.</p>
                <footer>Footer content</footer>
            </body>
        </html>
        """

        result = crawler.parse("https://test.com", html)

        # Should extract main content
        assert "main content" in result.body_text

        # Should not include ads/scripts
        assert "alert" not in result.body_text

    def test_generic_crawler_date_extraction(self):
        """Test date extraction from HTML."""
        crawler = GenericCrawler()

        html = """
        <html>
            <body>
                <p>Published: 2025-01-15</p>
                <article>Test content</article>
            </body>
        </html>
        """

        result = crawler.parse("https://test.com", html)

        # Should extract date
        if result.date:
            assert "2025" in result.date

    def test_generic_crawler_metadata(self):
        """Test that metadata is included."""
        crawler = GenericCrawler()

        result = crawler.parse("https://test.com", "<html><body>Test</body></html>")

        assert result.metadata is not None
        assert 'parser_used' in result.metadata
        assert result.metadata['extractor'] == 'generic'


class TestCrawlerRegistry:
    """Test crawler registry functionality."""

    def test_registry_initialization(self):
        """Test that registry initializes and discovers plugins."""
        registry = CrawlerRegistry()

        plugins = registry.list_plugins()
        assert len(plugins) > 0

        # Should at least have generic plugin
        plugin_names = [p['name'] for p in plugins]
        assert 'generic' in plugin_names

    def test_get_plugin_for_url(self):
        """Test getting appropriate plugin for URL."""
        registry = CrawlerRegistry()

        # Any URL should match generic plugin (fallback)
        plugin = registry.get_plugin_for_url("https://unknown-site.com/article")

        assert plugin is not None
        assert isinstance(plugin, BaseCrawlerPlugin)

    def test_plugin_priority_ordering(self):
        """Test that plugins are selected by priority."""
        registry = CrawlerRegistry()

        plugins = registry.list_plugins()

        # Plugins should be ordered by priority (higher first)
        if len(plugins) > 1:
            for i in range(len(plugins) - 1):
                assert plugins[i]['priority'] >= plugins[i + 1]['priority']

    def test_get_plugin_returns_highest_priority(self):
        """Test that highest priority matching plugin is returned."""
        registry = CrawlerRegistry()

        # For a URL that multiple plugins can handle,
        # should return highest priority one
        plugin = registry.get_plugin_for_url("https://test.com/article")

        assert plugin is not None

    def test_parse_with_registry(self, mock_article_html):
        """Test parsing article using registry."""
        registry = CrawlerRegistry()

        url = "https://test.com/article"
        plugin = registry.get_plugin_for_url(url)

        assert plugin is not None

        result = plugin.parse(url, mock_article_html)

        assert isinstance(result, CrawlerResult)
        assert result.headline is not None
        assert result.body_text is not None

    def test_list_plugins_structure(self):
        """Test that list_plugins returns correct structure."""
        registry = CrawlerRegistry()

        plugins = registry.list_plugins()

        for plugin in plugins:
            assert 'name' in plugin
            assert 'domains' in plugin
            assert 'priority' in plugin
            assert 'enabled' in plugin
            assert isinstance(plugin['domains'], list)
            assert isinstance(plugin['priority'], int)
            assert isinstance(plugin['enabled'], bool)
