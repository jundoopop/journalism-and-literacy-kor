"""Real Flask routing/middleware with fake outbound dependencies."""
from unittest.mock import Mock
import pytest


@pytest.fixture
def api(monkeypatch, tmp_path):
    from config import settings
    monkeypatch.setattr(settings.cache, "enabled", False)
    monkeypatch.setattr(settings.database, "path", str(tmp_path / "analytics.db"))
    monkeypatch.setattr(settings.observability, "log_dir", str(tmp_path / "logs"))
    monkeypatch.setattr(settings, "admin_token", "test-token")
    monkeypatch.setattr(settings, "enable_admin_api", True)
    import server
    from database import init_database
    init_database()
    crawler = Mock(side_effect=AssertionError("outbound work must not occur"))
    monkeypatch.setattr(server.crawler_service, "crawl_article", crawler)
    return server, server.app.test_client(), crawler


@pytest.mark.parametrize("payload", [[], "url", None, {}, {"url": 42}, {"url": "https://localhost/a"}])
def test_bad_payload_is_400_without_outbound_work(api, payload):
    server, client, crawler = api
    import json
    response = client.post("/analyze", data=json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    crawler.assert_not_called()


@pytest.mark.parametrize("providers", [None, [], "gemini", ["unknown"], ["gemini", "gemini"], [{}]])
def test_invalid_provider_list_is_400(api, providers):
    _, client, crawler = api
    response = client.post("/analyze_consensus", json={"url": "https://www.hani.co.kr/a", "providers": providers})
    assert response.status_code == 400
    crawler.assert_not_called()


def test_http_errors_keep_status_and_json(api):
    _, client, crawler = api
    assert client.post("/analyze", data="{", content_type="application/json").status_code == 400
    assert client.post("/analyze", data="{}").status_code == 415
    assert client.get("/analyze").status_code == 405
    assert client.post("/analyze", data="a" * 17000, content_type="application/json").status_code == 413
    crawler.assert_not_called()


def test_untrusted_browser_origin_cannot_trigger_analysis(api):
    _, client, crawler = api
    response = client.post("/analyze", json={"url": "https://www.hani.co.kr/a"},
                           headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    assert "Access-Control-Allow-Origin" not in response.headers
    crawler.assert_not_called()


def test_extension_preflight_allowed(api):
    _, client, _ = api
    origin = "chrome-extension://" + "a" * 32
    response = client.options("/analyze", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
    assert response.headers["Access-Control-Allow-Origin"] == origin


def test_liveness_survives_dependency_outage_and_readiness_fails(api, monkeypatch):
    server, client, _ = api
    monkeypatch.setattr(server.health_service, "get_system_health", lambda: {"overall_status": "unhealthy"})
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 503


def test_metrics_require_auth_and_have_bounded_route_labels(api):
    _, client, _ = api
    client.get("/unmatched-one")
    client.get("/unmatched-two")
    assert client.get("/metrics").status_code == 401
    response = client.get("/metrics", headers={"X-Admin-Token": "test-token"})
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'route="unmatched"' in text
    assert "unmatched-one" not in text
    assert "news_http_request_duration_seconds_bucket" in text


def test_actual_consensus_route_handles_one_failed_model(api, monkeypatch):
    server, client, _ = api
    from llm.base import AnalysisResult
    from llm.factory import LLMFactory
    from services.crawler_service import ArticleData
    monkeypatch.setattr(server.crawler_service, "crawl_article", lambda url: ArticleData(url, "News", "문장", {}))
    def provider(name=None, **kwargs):
        name = kwargs.get("provider", name)
        fake = Mock()
        if name == "mistral":
            fake.analyze_article.side_effect = TimeoutError("upstream timed out")
        else:
            fake.analyze_article.return_value = AnalysisResult({"문장": "이유"}, name, "fake")
        return fake
    monkeypatch.setattr(LLMFactory, "create", provider)
    response = client.post("/analyze_consensus", json={"url": "https://www.hani.co.kr/a", "providers": ["gemini", "mistral"]})
    assert response.status_code == 200
    body = response.get_json()
    assert body["total_providers"] == 2
    assert body["failed_providers"] == ["mistral"]
    assert body["sentences"][0]["consensus_level"] == "insufficient"
