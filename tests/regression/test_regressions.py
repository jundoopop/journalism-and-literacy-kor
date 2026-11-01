"""Regression cases for failures found during the reliability review.

No live news sites or paid model calls are used.
"""
import logging
from unittest.mock import Mock

import pytest
from flask import Flask


def test_crawler_import_and_parse_without_second_download(monkeypatch):
    import crawler_unified
    html = "<html><title>News</title><body><article><p>" + "기사 본문입니다. " * 100 + "</p></article></body></html>"
    fetch = Mock(side_effect=AssertionError("parsing must not download"))
    monkeypatch.setattr("requests.get", fetch)
    result = crawler_unified.parse_article("https://www.hani.co.kr/article", html)
    assert "기사 본문" in result["body_text"]
    fetch.assert_not_called()


def test_consensus_calls_provider_contract():
    from consensus_analyzer import ConsensusAnalyzer
    from llm.base import AnalysisResult, BaseLLMProvider
    analyzer = ConsensusAnalyzer.__new__(ConsensusAnalyzer)
    provider = Mock(spec=BaseLLMProvider)
    provider.analyze_article.return_value = AnalysisResult(
        sentences={"문장": "이유"}, provider="gemini", model="fake"
    )
    analyzer.llm_instances = {"gemini": provider}
    result = analyzer._analyze_with_provider("gemini", "문장")
    assert result["success"]
    assert result["sentences"] == {"문장": "이유"}


def test_one_surviving_provider_is_not_high_consensus():
    from consensus_analyzer import ConsensusAnalyzer
    analyzer = ConsensusAnalyzer.__new__(ConsensusAnalyzer)
    analyzer.providers = ["gemini", "mistral"]
    analyzer.llm_instances = {"gemini": object()}
    results = [
        {"provider": "gemini", "success": True, "sentences": {"문장": "이유"}},
        {"provider": "mistral", "success": False, "sentences": {}},
    ]
    result = analyzer._calculate_consensus(results)
    assert result["total_providers"] == 2
    assert result["sentences"][0]["consensus_level"] == "insufficient"
    assert result["failed_providers"] == ["mistral"]


def test_disabled_admin_api_is_not_an_authentication_bypass(monkeypatch):
    from api.middleware import admin_auth_middleware
    from config import settings
    monkeypatch.setattr(settings, "enable_admin_api", False)
    app = Flask(__name__)
    called = Mock(return_value={"secret": True})
    app.add_url_rule("/admin/test", view_func=admin_auth_middleware()(called))
    assert app.test_client().get("/admin/test").status_code == 404
    called.assert_not_called()


def test_default_server_is_local_and_non_debug():
    from config import Settings
    settings = Settings(_env_file=None)
    assert settings.flask_host == "127.0.0.1"
    assert settings.flask_debug is False


def test_cache_modes_do_not_share_incompatible_payloads():
    from services import CacheService
    cache = CacheService()
    url = "https://www.hani.co.kr/a"
    assert cache._generate_cache_key(url, ["gemini"], "single") != cache._generate_cache_key(url, ["gemini"], "consensus")


def test_timing_samples_are_bounded():
    from observability.metrics import MetricsCollector
    collector = MetricsCollector()
    for value in range(3000):
        collector.timing("latency", value)
    assert collector.get_summary()["timings"]["latency"]["default"]["count"] == 1024


def test_structured_logging_preserves_fields(caplog):
    from observability import get_logger
    with caplog.at_level(logging.INFO):
        get_logger("regression").info("request", method="POST", path="/analyze")
    record = next(r for r in caplog.records if r.name == "regression")
    assert record.method == "POST" and record.path == "/analyze"


def test_initialization_failure_is_reported(monkeypatch):
    from consensus_analyzer import ConsensusAnalyzer
    from llm.factory import LLMFactory
    from llm.base import AnalysisResult
    from llm.exceptions import APIKeyError
    fake = Mock()
    fake.analyze_article.return_value = AnalysisResult({"문장": "이유"}, "gemini", "fake")
    def create(provider):
        if provider == "mistral":
            raise APIKeyError("missing key")
        return fake
    monkeypatch.setattr(LLMFactory, "create", create)
    result = ConsensusAnalyzer(["gemini", "mistral"]).analyze_article("문장")
    assert result["failed_providers"] == ["mistral"]
    assert result["total_providers"] == 2


def test_partial_consensus_is_not_cached(monkeypatch):
    from services import AnalysisService
    cache = Mock()
    cache.is_enabled.return_value = True
    cache.get_analysis_result.return_value = None
    analyzer = Mock()
    analyzer.analyze_article.return_value = {
        "sentences": [], "total_providers": 2,
        "successful_providers": ["gemini"], "failed_providers": ["mistral"],
    }
    service = AnalysisService(cache)
    monkeypatch.setattr(service, "_get_consensus_analyzer", lambda providers: analyzer)
    service.analyze_consensus("article", ["gemini", "mistral"], url="https://www.hani.co.kr/a")
    cache.set_analysis_result.assert_not_called()
