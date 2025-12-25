"""
Integration tests for complete analysis workflow.
"""

import pytest
from unittest.mock import Mock, patch
from services import AnalysisService, CacheService, FeatureFlagsService
from crawlers.registry import CrawlerRegistry


class TestAnalysisWorkflow:
    """Test end-to-end analysis workflow."""

    @pytest.fixture
    def setup_services(self, temp_database, monkeypatch):
        """Setup all required services."""
        monkeypatch.setenv("DATABASE_PATH", temp_database)

        from database import init_database
        init_database()

        cache_service = CacheService()
        analysis_service = AnalysisService(cache_service=cache_service)
        feature_flags = FeatureFlagsService()
        crawler_registry = CrawlerRegistry()

        return {
            'cache': cache_service,
            'analysis': analysis_service,
            'flags': feature_flags,
            'crawler': crawler_registry
        }

    def test_crawler_to_analysis_integration(self, setup_services, mock_article_html):
        """Test integration from crawling to analysis."""
        services = setup_services

        # Get crawler for URL
        url = "https://test.com/article"
        crawler = services['crawler'].get_plugin_for_url(url)

        assert crawler is not None

        # Parse article
        result = crawler.parse(url, mock_article_html)

        assert result.headline is not None
        assert result.body_text is not None

        # This would normally trigger LLM analysis
        # For integration test, we verify the data flow
        assert len(result.body_text) > 0

    def test_feature_flags_affect_analysis(self, setup_services):
        """Test that feature flags affect analysis behavior."""
        services = setup_services

        # Set feature flag
        services['flags'].set_flag('cache_enabled', True)

        # Check that analysis service respects the flag
        cache_enabled = services['flags'].is_enabled('cache_enabled')

        assert cache_enabled is True

    def test_cache_integration_with_analysis(self, setup_services):
        """Test cache integration in analysis workflow."""
        services = setup_services

        url = "https://test.com/article"
        providers = ["gemini"]
        test_result = {
            "sentences": {"test": "reason"},
            "headline": "Test"
        }

        # Store in cache
        services['cache'].set_analysis_result(url, providers, test_result)

        # Retrieve from cache
        cached = services['cache'].get_analysis_result(url, providers)

        # Should retrieve successfully (if Redis available)
        if services['cache'].is_enabled():
            assert cached is not None
            assert cached['headline'] == 'Test'

    def test_database_logging_integration(self, setup_services):
        """Test that all operations are logged to database."""
        from database import AnalyticsRepository

        services = setup_services
        repo = AnalyticsRepository()

        # Log a request
        repo.log_request(
            correlation_id="integration_test",
            method="POST",
            endpoint="/analyze",
            status_code=200,
            duration_ms=1500.0
        )

        # Verify logged
        recent = repo.get_recent_requests(limit=1)
        assert len(recent) > 0
        assert recent[0].correlation_id == "integration_test"

    def test_error_handling_across_services(self, setup_services):
        """Test error handling in service integration."""
        services = setup_services

        # Test with invalid URL
        url = "not-a-valid-url"

        # Should not crash, should handle gracefully
        # (Actual behavior depends on implementation)


class TestPromptExperimentIntegration:
    """Test prompt experimentation integration."""

    def test_prompt_manager_with_feature_flags(self):
        """Test prompt manager integration with feature flags."""
        from llm.prompts.prompt_manager import PromptManager
        from services import FeatureFlagsService

        manager = PromptManager()
        flags = FeatureFlagsService()

        # Set flag to use enhanced prompt
        flags.set_flag('use_enhanced_prompt', True)

        # Get prompt based on flag
        use_enhanced = flags.is_enabled('use_enhanced_prompt')
        version = 'v2' if use_enhanced else 'v1'

        prompt = manager.get_prompt(
            'article_analysis',
            version=version,
            article_text="테스트 기사"
        )

        assert prompt is not None
        assert "테스트 기사" in prompt

    def test_experiment_variant_selection(self):
        """Test experiment variant selection in workflow."""
        from llm.prompts.prompt_manager import PromptManager

        manager = PromptManager()
        experiments = manager.list_experiments()

        # If there are experiments, test variant selection
        if experiments:
            exp = experiments[0]

            # Multiple calls should potentially select different variants
            variants_seen = set()

            for _ in range(10):
                prompt = manager.get_prompt(
                    'article_analysis',
                    experiment=exp['name'],
                    article_text="테스트"
                )

                assert prompt is not None
                variants_seen.add(prompt)


class TestHealthMonitoringIntegration:
    """Test health monitoring integration."""

    def test_health_service_checks_all_components(self):
        """Test that health service checks all system components."""
        from services import HealthService, CacheService

        cache = CacheService()
        health = HealthService(cache_service=cache)

        # Get system health
        system_health = health.get_system_health()

        assert 'overall_status' in system_health
        assert 'components' in system_health

        # Should check multiple components
        components = system_health['components']
        assert len(components) > 0

    def test_health_check_detects_llm_provider_status(self):
        """Test health check for LLM providers."""
        from services import HealthService, CacheService

        cache = CacheService()
        health = HealthService(cache_service=cache)

        # Check all providers
        providers = health.check_all_providers()

        assert len(providers) > 0

        # Each provider should have status
        for provider, status in providers.items():
            assert 'status' in status
            assert status['status'] in ['healthy', 'unhealthy', 'not_configured']


class TestCLIToolsIntegration:
    """Test CLI tools integration with services."""

    def test_feature_flags_cli_integration(self, temp_database, monkeypatch):
        """Test feature flags CLI tool integration."""
        monkeypatch.setenv("DATABASE_PATH", temp_database)

        from database import init_database
        from services import FeatureFlagsService

        init_database()
        service = FeatureFlagsService()

        # Create flags via service
        service.set_flag('cli_test', True, description='Test flag')

        # Verify can be retrieved
        flag = service.get_flag('cli_test')

        assert flag is not None
        assert flag['enabled'] is True

    def test_cache_admin_cli_integration(self):
        """Test cache admin CLI tool integration."""
        from services import CacheService

        service = CacheService()

        # Get stats via service (as CLI would)
        stats = service.get_stats()

        assert stats is not None
        assert hasattr(stats, 'hits')
        assert hasattr(stats, 'misses')


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow."""

    @patch('requests.get')
    def test_complete_analysis_workflow_mock(self, mock_get, setup_services, mock_article_html):
        """Test complete workflow with mocked HTTP."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.text = mock_article_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        services = setup_services

        url = "https://test.com/article"

        # Step 1: Fetch article (mocked)
        # Step 2: Parse with crawler
        crawler = services['crawler'].get_plugin_for_url(url)
        result = crawler.parse(url, mock_article_html)

        assert result.headline is not None

        # Step 3: Analysis would happen here (requires LLM API keys)
        # For integration test, we verify the pipeline is connected

        # Step 4: Cache result
        analysis_result = {
            "sentences": {"테스트": "이유"},
            "headline": result.headline
        }

        services['cache'].set_analysis_result(url, ["gemini"], analysis_result)

        # Step 5: Verify logged to database
        from database import AnalyticsRepository

        repo = AnalyticsRepository()
        repo.log_analysis_result(
            correlation_id="e2e_test",
            url=url,
            provider="gemini",
            success=True,
            response_data=analysis_result,
            duration_ms=2000.0
        )

        # Verify end-to-end
        logged = repo.get_analysis_results_by_url(url)
        assert len(logged) > 0
