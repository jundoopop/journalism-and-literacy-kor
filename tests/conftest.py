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
def no_external_io(monkeypatch):
    """Tests must explicitly fake network and credential-store boundaries."""
    import socket
    import keyring

    def unexpected_network(*args, **kwargs):
        pytest.fail("Unexpected network access; supply an explicit fake in this test")

    monkeypatch.setattr(socket.socket, 'connect', unexpected_network)
    monkeypatch.setattr(socket, 'getaddrinfo', unexpected_network)
    monkeypatch.setattr(keyring, 'get_password', lambda *args, **kwargs: None)
    # Provider fallback must not load credentials from a developer's .env file.
    monkeypatch.setattr('dotenv.load_dotenv', lambda *args, **kwargs: False)


@pytest.fixture(autouse=True)
def reset_services(tmp_path, monkeypatch, no_external_io):
    """Each test gets its own database, configuration and metrics state."""
    import importlib
    from config import settings
    from observability import metrics, set_correlation_id
    db = importlib.import_module('database.init_db')
    if db._engine is not None:
        db._engine.dispose()
    db._engine = db._SessionFactory = None
    monkeypatch.setattr(settings.database, 'path', str(tmp_path / 'analytics.db'))
    monkeypatch.setattr(settings.cache, 'enabled', False)
    monkeypatch.setattr(settings.observability, 'log_dir', str(tmp_path / 'logs'))
    for provider in ('gemini', 'mistral', 'openai', 'claude', 'llama'):
        monkeypatch.setattr(settings.llm, provider + '_api_key', None)
        monkeypatch.delenv(provider.upper() + '_API_KEY', raising=False)
    metrics.reset()
    metrics.enable()
    set_correlation_id(None)
    server = sys.modules.get('server')
    if server is not None:
        server.health_service.clear_cache()
    yield
    if db._engine is not None:
        db._engine.dispose()
    db._engine = db._SessionFactory = None
    set_correlation_id(None)


@pytest.fixture
def mock_redis_client():
    """In-memory Redis operations; expiration is tested separately in the browser."""
    from unittest.mock import Mock
    from fnmatch import fnmatch

    redis_mock = Mock(spec=['ping', 'get', 'setex', 'delete', 'keys', 'flushdb', 'info'])
    redis_mock.ping.return_value = True
    stored = {}
    redis_mock.get.side_effect = stored.get

    def setex(key, ttl, value):
        stored[key] = value
        return True

    def delete(*keys):
        count = sum(key in stored for key in set(keys))
        for key in keys:
            stored.pop(key, None)
        return count

    redis_mock.setex.side_effect = setex
    redis_mock.delete.side_effect = delete
    redis_mock.keys.side_effect = lambda pattern: [key for key in stored if fnmatch(key, pattern)]
    redis_mock.flushdb.side_effect = stored.clear
    redis_mock.info.return_value = {'redis_version': 'fixture'}

    return redis_mock


@pytest.fixture
def measured_providers(monkeypatch):
    from threading import local
    from types import SimpleNamespace
    from llm.base import AnalysisResult
    import consensus_analyzer
    from llm.factory import LLMFactory

    clock = local()
    monkeypatch.setattr(
        consensus_analyzer, "perf_counter", lambda: getattr(clock, "now", 0)
    )

    def install(failures=()):
        calls = []

        def create(provider):
            def analyze(article, prompt):
                calls.append(provider)
                clock.now = getattr(clock, "now", 0) + {"gemini": 0.125, "mistral": 0.875}[provider]
                if provider in failures:
                    raise TimeoutError("fixture timeout")
                sentences = {"첫 문장.": "첫 이유"}
                if provider == "mistral":
                    sentences["둘째 문장."] = "둘째 이유"
                return AnalysisResult(sentences, provider, f"fixture-{provider}")

            return SimpleNamespace(analyze_article=analyze)

        monkeypatch.setattr(LLMFactory, "create", create)
        return calls

    return install
