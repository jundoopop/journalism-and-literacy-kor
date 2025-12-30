"""
Benchmark Data Loader

Loads the Korean news benchmark dataset from Excel, fetches article text from URLs,
and prepares data for evaluation.
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict
import pandas as pd
from tqdm import tqdm

# Import existing crawler infrastructure
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.crawlers.factory import CrawlerFactory
from scripts.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkArticle:
    """Represents a single article in the benchmark dataset"""
    article_id: str
    issue: str  # 이슈
    newspaper: str  # 신문사
    title: str  # 기사제목
    url: str
    body_text: str  # Fetched from URL
    gold_sentences: List[str]  # From 핵심1-4 columns

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'BenchmarkArticle':
        """Create from dictionary"""
        return cls(**data)


class BenchmarkDataLoader:
    """Loads and prepares benchmark dataset"""

    def __init__(
        self,
        excel_path: str = "data/benchset/korean_news_benchmark_issue_based_50.xlsx",
        cache_path: str = "data/benchset/preprocessed_articles.json"
    ):
        self.excel_path = Path(excel_path)
        self.cache_path = Path(cache_path)
        self.crawler_factory = CrawlerFactory()

    def load_excel(self) -> pd.DataFrame:
        """Load the Excel benchmark dataset"""
        logger.info(f"Loading Excel dataset from {self.excel_path}")
        df = pd.read_excel(self.excel_path)
        logger.info(f"Loaded {len(df)} articles")
        return df

    def parse_gold_sentences(self, row: pd.Series) -> List[str]:
        """Extract gold standard sentences from 핵심1-4 columns"""
        gold_sentences = []
        for col in ['핵심1', '핵심2', '핵심3', '핵심4']:
            if col in row and pd.notna(row[col]):
                sentence = str(row[col]).strip()
                if sentence:
                    gold_sentences.append(sentence)
        return gold_sentences

    def fetch_article_text(self, url: str) -> Optional[str]:
        """
        Fetch article body text from URL using existing crawler infrastructure

        Args:
            url: Article URL

        Returns:
            Article body text or None if fetch failed
        """
        try:
            # Extract domain from URL
            from urllib.parse import urlparse
            domain = urlparse(url).netloc

            # Get appropriate crawler
            crawler = self.crawler_factory.get_crawler(domain)
            if not crawler:
                logger.warning(f"No crawler available for domain: {domain}")
                return None

            # Fetch article
            article = crawler.crawl(url)
            if article and article.body_text:
                logger.debug(f"Successfully fetched article from {url}")
                return article.body_text
            else:
                logger.warning(f"Failed to fetch article body from {url}")
                return None

        except Exception as e:
            logger.error(f"Error fetching article from {url}: {e}")
            return None

    def process_dataset(self, use_cache: bool = True) -> List[BenchmarkArticle]:
        """
        Process the entire dataset: load Excel, fetch articles, create BenchmarkArticle objects

        Args:
            use_cache: If True, load from cache if available

        Returns:
            List of BenchmarkArticle objects
        """
        # Check cache first
        if use_cache and self.cache_path.exists():
            logger.info(f"Loading from cache: {self.cache_path}")
            return self.load_from_cache()

        # Load Excel
        df = self.load_excel()

        articles = []
        failed_urls = []

        # Process each row
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing articles"):
            try:
                # Extract metadata
                article_id = str(row['article_id'])
                issue = str(row['이슈'])
                newspaper = str(row['신문사'])
                title = str(row['기사제목'])
                url = str(row['URL'])

                # Parse gold standard sentences
                gold_sentences = self.parse_gold_sentences(row)

                if not gold_sentences:
                    logger.warning(f"No gold sentences found for {article_id}")

                # Fetch article text
                body_text = self.fetch_article_text(url)

                if body_text is None:
                    logger.warning(f"Failed to fetch article {article_id} from {url}")
                    failed_urls.append((article_id, url))
                    body_text = ""  # Use empty string as placeholder

                # Create BenchmarkArticle
                article = BenchmarkArticle(
                    article_id=article_id,
                    issue=issue,
                    newspaper=newspaper,
                    title=title,
                    url=url,
                    body_text=body_text,
                    gold_sentences=gold_sentences
                )

                articles.append(article)

            except Exception as e:
                logger.error(f"Error processing row {idx}: {e}")
                continue

        # Report statistics
        success_count = sum(1 for a in articles if a.body_text)
        logger.info(f"Successfully fetched {success_count}/{len(articles)} articles ({success_count/len(articles)*100:.1f}%)")

        if failed_urls:
            logger.warning(f"Failed to fetch {len(failed_urls)} articles:")
            for art_id, url in failed_urls[:5]:  # Show first 5
                logger.warning(f"  - {art_id}: {url}")

        # Save to cache
        self.save_to_cache(articles)

        return articles

    def save_to_cache(self, articles: List[BenchmarkArticle]):
        """Save processed articles to cache file"""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        cache_data = {
            'version': '1.0',
            'article_count': len(articles),
            'articles': [article.to_dict() for article in articles]
        }

        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(articles)} articles to cache: {self.cache_path}")

    def load_from_cache(self) -> List[BenchmarkArticle]:
        """Load processed articles from cache file"""
        with open(self.cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        articles = [BenchmarkArticle.from_dict(data) for data in cache_data['articles']]
        logger.info(f"Loaded {len(articles)} articles from cache")

        return articles


def main():
    """Test data loader"""
    logging.basicConfig(level=logging.INFO)

    loader = BenchmarkDataLoader()
    articles = loader.process_dataset(use_cache=False)

    print(f"\nLoaded {len(articles)} articles")
    print(f"\nSample article:")
    if articles:
        sample = articles[0]
        print(f"ID: {sample.article_id}")
        print(f"Issue: {sample.issue}")
        print(f"Newspaper: {sample.newspaper}")
        print(f"Title: {sample.title}")
        print(f"URL: {sample.url}")
        print(f"Gold sentences: {len(sample.gold_sentences)}")
        for i, sent in enumerate(sample.gold_sentences, 1):
            print(f"  {i}. {sent[:100]}...")
        print(f"Body length: {len(sample.body_text)} chars")
        print(f"Body preview: {sample.body_text[:200]}...")


if __name__ == '__main__':
    main()
