"""
Generic fallback crawler plugin using Readability.

Used when no site-specific plugin matches the URL.
"""

import re
from bs4 import BeautifulSoup
from readability import Document
from dateutil import parser as dateparser

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from crawlers.base import BaseCrawlerPlugin, CrawlerResult


class GenericCrawler(BaseCrawlerPlugin):
    """
    Generic crawler using Readability for content extraction.

    Falls back to this when no site-specific crawler is available.
    """

    name = "generic"
    domains = ["*"]  # Matches all domains
    priority = 1  # Lowest priority - used as fallback
    enabled = True

    def parse(self, url: str, html: str) -> CrawlerResult:
        """
        Parse article using Readability.

        Args:
            url: Article URL
            html: HTML content

        Returns:
            CrawlerResult with extracted content
        """
        # Try Readability first
        try:
            doc = Document(html)
            content_html = doc.summary(html_partial=True)
            headline = doc.short_title()

            # Extract text from HTML
            body_text = self._html_to_text(content_html)

            # Try to extract date
            date = self._extract_date(html)

            return CrawlerResult(
                headline=headline,
                body_text=body_text,
                date=date,
                metadata={
                    'parser_used': 'readability',
                    'extractor': 'generic'
                }
            )

        except Exception as e:
            # Fallback to basic BeautifulSoup parsing
            soup = BeautifulSoup(html, "lxml")

            headline = ""
            if soup.title:
                headline = soup.title.string.strip()

            # Try common article body selectors
            body_node = None
            for selector in [
                ('div', 'article-body'),
                ('article', 'article'),
                ('div', 'content'),
                ('main', 'main')
            ]:
                tag, class_pattern = selector
                body_node = soup.find(tag, class_=re.compile(class_pattern, re.I))
                if body_node:
                    break

            # Fallback to body tag
            if not body_node:
                body_node = soup.body or soup

            body_text = self._html_to_text(str(body_node))
            date = self._extract_date(html)

            return CrawlerResult(
                headline=headline,
                body_text=body_text,
                date=date,
                metadata={
                    'parser_used': 'beautifulsoup',
                    'extractor': 'generic',
                    'fallback': True
                }
            )

    def _html_to_text(self, html_content: str) -> str:
        """
        Extract clean text from HTML.

        Args:
            html_content: HTML string

        Returns:
            Clean text content
        """
        soup = BeautifulSoup(html_content, "lxml")

        # Remove unwanted elements
        for element in soup(["script", "style", "noscript", "iframe", "header", "footer", "aside", "nav"]):
            element.decompose()

        # Remove common ad/recommendation boxes
        for class_pattern in ["ad", "banner", "recommend", "related", "widget", "sidebar"]:
            for element in soup.find_all(class_=re.compile(class_pattern, re.I)):
                element.decompose()

        # Extract text
        text_lines = []
        for line in soup.get_text("\n").splitlines():
            line = line.strip()
            if line and len(line) > 10:  # Filter out very short lines
                text_lines.append(line)

        return "\n".join(text_lines)

    def _extract_date(self, html: str) -> str:
        """
        Try to extract publication date from HTML.

        Args:
            html: HTML content

        Returns:
            ISO format date string or None
        """
        # Try to find date patterns
        patterns = [
            r'(20\d{2}[./-]\d{1,2}[./-]\d{1,2})',  # 2024-01-15 or 2024.01.15
            r'(20\d{2}년\s*\d{1,2}월\s*\d{1,2}일)',  # 2024년 1월 15일
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    date_str = match.group(1)
                    parsed_date = dateparser.parse(date_str)
                    if parsed_date:
                        return parsed_date.date().isoformat()
                except Exception:
                    continue

        return None
