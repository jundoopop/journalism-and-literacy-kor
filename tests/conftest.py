"""
Pytest configuration and shared fixtures.
"""

import pytest
import sys
import tempfile
from pathlib import Path

# Add scripts to path BEFORE any other imports
project_root = Path(__file__).parent.parent
scripts_path = str(project_root / 'scripts')

# Remove any existing paths that might conflict
sys.path = [p for p in sys.path if not p.endswith('lab')]

# Insert scripts path at the very beginning
sys.path.insert(0, scripts_path)

import os
os.chdir(scripts_path)


@pytest.fixture
def temp_database():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_article_html():
    """Sample article HTML for testing crawlers."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Article - News Site</title>
        <meta name="author" content="Test Author">
        <meta property="article:published_time" content="2025-01-15T10:00:00Z">
    </head>
    <body>
        <article>
            <h1 class="article-title">테스트 기사 제목</h1>
            <div class="article-meta">
                <span class="author">홍길동 기자</span>
                <time datetime="2025-01-15">2025년 1월 15일</time>
            </div>
            <div class="article-body">
                <p>이것은 테스트 기사의 본문입니다.</p>
                <p>여러 문단으로 구성되어 있습니다.</p>
                <p>각 문단은 의미 있는 내용을 담고 있습니다.</p>
            </div>
        </article>
    </body>
    </html>
    """


@pytest.fixture
def mock_llm_response():
    """Sample LLM response for testing analysis."""
    return {
        "sentences": {
            "이것은 테스트 기사의 본문입니다.": "논리적 구조를 명확히 보여주는 문장",
            "여러 문단으로 구성되어 있습니다.": "글의 전개 방식을 설명하는 문장"
        },
        "headline": "테스트 기사 제목"
    }


@pytest.fixture
def mock_crawler_result():
    """Sample crawler result for testing."""
    from crawlers.base import CrawlerResult

    return CrawlerResult(
        headline="테스트 기사 제목",
        body_text="이것은 테스트 기사의 본문입니다.\n여러 문단으로 구성되어 있습니다.",
        date="2025-01-15",
        author="홍길동 기자",
        section="정치",
        tags=["테스트", "샘플"],
        metadata={"source": "test"}
    )


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "flask_port": 5001,
        "cache_enabled": True,
        "redis_host": "localhost",
        "redis_port": 6379,
        "database_path": ":memory:",
        "llm_timeout": 30,
        "llm_max_retries": 2,
        "observability": {
            "log_level": "INFO",
            "log_format": "json",
            "log_dir": "data/logs"
        }
    }


@pytest.fixture(autouse=True)
def reset_services():
    """Reset service instances between tests."""
    yield
    # Any cleanup needed between tests


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing without Redis server."""
    from unittest.mock import Mock

    redis_mock = Mock()
    redis_mock.ping.return_value = True
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = True
    redis_mock.delete.return_value = 1

    return redis_mock
