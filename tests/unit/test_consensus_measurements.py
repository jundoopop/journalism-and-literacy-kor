"""Provider observations use a deterministic clock, never wall-clock sleeps."""
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize("failures", [(), ("mistral",), ("gemini", "mistral")])
def test_each_provider_keeps_its_own_duration_count_and_outcome(measured_providers, failures):
    from consensus_analyzer import ConsensusAnalyzer

    measured_providers(failures)
    result = ConsensusAnalyzer(["gemini", "mistral"]).analyze_article("첫 문장. 둘째 문장.")
    observations = result["provider_metrics"]
    for provider, duration, count in [("gemini", 125, 1), ("mistral", 875, 2)]:
        assert observations[provider]["duration_ms"] == duration
        assert observations[provider]["success"] == (provider not in failures)
        assert observations[provider]["sentence_count"] == (0 if provider in failures else count)


def test_cache_hit_does_not_reuse_historical_provider_observations(monkeypatch):
    from services import AnalysisService

    cache = Mock()
    cache.is_enabled.return_value = True
    cache.get_analysis_result.return_value = {
        "sentences": [], "total_providers": 2,
        "successful_providers": ["gemini", "mistral"], "failed_providers": [],
        "total_duration_ms": 1000,
        "provider_metrics": {"gemini": {"duration_ms": 125}},
    }
    service = AnalysisService(cache)
    outbound = Mock(side_effect=AssertionError("Cache hits must not call providers"))
    monkeypatch.setattr(service, "_get_consensus_analyzer", outbound)
    result = service.analyze_consensus("첫 문장.", ["gemini", "mistral"], url="https://www.hani.co.kr/a")
    assert result.provider_metrics == {}
    outbound.assert_not_called()


def test_initialization_failure_has_no_fabricated_call_duration(monkeypatch):
    from consensus_analyzer import ConsensusAnalyzer
    from llm.base import AnalysisResult
    from llm.exceptions import APIKeyError
    from llm.factory import LLMFactory

    llm = Mock()
    llm.analyze_article.return_value = AnalysisResult({'문장.': '이유'}, 'gemini', 'fixture')

    def create(provider):
        if provider == 'mistral':
            raise APIKeyError('fixture missing key')
        return llm

    monkeypatch.setattr(LLMFactory, 'create', create)
    result = ConsensusAnalyzer(['gemini', 'mistral']).analyze_article('문장.')
    assert result['provider_metrics']['mistral']['duration_ms'] is None
    assert result['provider_metrics']['mistral']['success'] is False
