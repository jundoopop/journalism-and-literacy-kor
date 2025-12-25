#!/usr/bin/env python3
"""
Comprehensive test script for all implemented phases.

Tests each phase's components to ensure everything works correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'scripts'))

import os
os.chdir(project_root / 'scripts')

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f" {title}")
    print('='*70)


def print_test(name, passed, details=""):
    """Print test result."""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"  {status}: {name}")
    if details:
        print(f"    {details}")


def test_phase1_observability():
    """Test Phase 1: Observability & Configuration."""
    print_section("PHASE 1: Observability & Configuration")

    # Test 1: Import observability modules
    try:
        from observability import setup_logging, get_logger, get_correlation_id, metrics
        print_test("Import observability modules", True)
    except Exception as e:
        print_test("Import observability modules", False, str(e))
        return

    # Test 2: Setup logging
    try:
        from config import settings
        setup_logging(
            log_level=settings.observability.log_level,
            log_format=settings.observability.log_format,
            log_dir=settings.observability.log_dir
        )
        logger = get_logger("test")
        logger.info("Test log message")
        print_test("Setup logging", True)
    except Exception as e:
        print_test("Setup logging", False, str(e))

    # Test 3: Configuration loading
    try:
        from config import settings
        assert settings.flask_port > 0
        assert settings.database.path is not None
        print_test("Configuration loading", True, f"Port: {settings.flask_port}, DB: {settings.database.path}")
    except Exception as e:
        print_test("Configuration loading", False, str(e))

    # Test 4: Metrics collection
    try:
        from observability import metrics
        metrics.increment("test_counter")
        metrics.gauge("test_gauge", 42.0)
        summary = metrics.get_summary()
        assert "test_counter" in summary
        print_test("Metrics collection", True, f"{len(summary)} metrics tracked")
    except Exception as e:
        print_test("Metrics collection", False, str(e))

    # Test 5: Database initialization
    try:
        from database import init_database, check_database_health
        init_database()
        health = check_database_health()
        print_test("Database initialization", health['status'] == 'healthy',
                  f"Status: {health['status']}")
    except Exception as e:
        print_test("Database initialization", False, str(e))


def test_phase1_services():
    """Test Phase 1: Service Layer."""
    print_section("PHASE 1: Service Layer")

    # Test 1: Import services
    try:
        from services import (
            BaseService, CrawlerService, AnalysisService,
            CacheService, HealthService, FeatureFlagsService
        )
        print_test("Import all services", True)
    except Exception as e:
        print_test("Import all services", False, str(e))
        return

    # Test 2: CrawlerService
    try:
        from services import CrawlerService
        crawler = CrawlerService()
        supported = crawler.get_supported_domains()
        print_test("CrawlerService initialization", True,
                  f"{len(supported)} supported domains")
    except Exception as e:
        print_test("CrawlerService initialization", False, str(e))

    # Test 3: AnalysisService
    try:
        from services import AnalysisService, CacheService
        cache = CacheService()
        analysis = AnalysisService(cache_service=cache)
        providers = analysis.get_available_providers()
        print_test("AnalysisService initialization", True,
                  f"{len(providers)} LLM providers available")
    except Exception as e:
        print_test("AnalysisService initialization", False, str(e))


def test_phase2_caching():
    """Test Phase 2: Redis Caching."""
    print_section("PHASE 2: Redis Caching")

    # Test 1: CacheService initialization
    try:
        from services import CacheService
        cache = CacheService()
        print_test("CacheService initialization", True)
    except Exception as e:
        print_test("CacheService initialization", False, str(e))
        return

    # Test 2: Cache health check
    try:
        health = cache.health_check()
        is_healthy = health['status'] in ['healthy', 'disabled']
        print_test("Cache health check", is_healthy,
                  f"Status: {health['status']}")
    except Exception as e:
        print_test("Cache health check", False, str(e))

    # Test 3: Cache operations (if Redis is available)
    try:
        if cache.is_enabled():
            # Test set/get
            test_key = "test_article_url"
            test_data = {"sentences": {"test": "reason"}, "headline": "Test"}

            cache.set_analysis_result(test_key, ["gemini"], test_data)
            retrieved = cache.get_analysis_result(test_key, ["gemini"])

            success = retrieved is not None and retrieved.get('headline') == 'Test'
            print_test("Cache set/get operations", success)

            # Cleanup
            cache.invalidate(test_key, ["gemini"])
        else:
            print_test("Cache operations", True, "Redis not available (expected)")
    except Exception as e:
        print_test("Cache operations", False, str(e))

    # Test 4: Cache statistics
    try:
        stats = cache.get_stats()
        print_test("Cache statistics", True,
                  f"Hits: {stats.hits}, Misses: {stats.misses}, Hit rate: {stats.hit_rate:.1%}")
    except Exception as e:
        print_test("Cache statistics", False, str(e))


def test_phase3_health_checks():
    """Test Phase 3: Enhanced Health Checks."""
    print_section("PHASE 3: Enhanced Health Checks")

    # Test 1: HealthService initialization
    try:
        from services import HealthService, CacheService
        cache = CacheService()
        health_service = HealthService(cache_service=cache)
        print_test("HealthService initialization", True)
    except Exception as e:
        print_test("HealthService initialization", False, str(e))
        return

    # Test 2: Check all providers
    try:
        all_providers = health_service.check_all_providers()
        print_test("Check all LLM providers", True,
                  f"{len(all_providers)} providers checked")

        for provider, status in all_providers.items():
            print(f"    - {provider}: {status['status']}")
    except Exception as e:
        print_test("Check all LLM providers", False, str(e))

    # Test 3: System health
    try:
        system_health = health_service.get_system_health()
        print_test("Get system health", True,
                  f"Overall status: {system_health['overall_status']}")
    except Exception as e:
        print_test("Get system health", False, str(e))


def test_phase3_cli_tools():
    """Test Phase 3: CLI Admin Tools."""
    print_section("PHASE 3: CLI Admin Tools")

    # Test 1: Import CLI tools modules
    try:
        import importlib.util

        tools = [
            'view_metrics',
            'view_logs',
            'cache_admin',
            'feature_flags'
        ]

        for tool in tools:
            tool_path = project_root / 'scripts' / 'tools' / f'{tool}.py'
            spec = importlib.util.spec_from_file_location(tool, tool_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                # Don't execute, just check if loadable
                print_test(f"CLI tool: {tool}.py", True, "Loadable")
            else:
                print_test(f"CLI tool: {tool}.py", False, "Not found")

    except Exception as e:
        print_test("CLI tools import", False, str(e))


def test_phase4_feature_flags():
    """Test Phase 4: Feature Flags Service."""
    print_section("PHASE 4: Feature Flags Service")

    # Test 1: FeatureFlagsService initialization
    try:
        from services import FeatureFlagsService
        flags = FeatureFlagsService()
        print_test("FeatureFlagsService initialization", True)
    except Exception as e:
        print_test("FeatureFlagsService initialization", False, str(e))
        return

    # Test 2: Create default flags
    try:
        flags.create_default_flags()
        all_flags = flags.get_all_flags()
        print_test("Create default flags", len(all_flags) > 0,
                  f"{len(all_flags)} flags created")
    except Exception as e:
        print_test("Create default flags", False, str(e))

    # Test 3: Flag operations
    try:
        # Check enabled
        cache_enabled = flags.is_enabled('cache_enabled')

        # Get config
        strict_config = flags.get_config('strict_consensus')

        # Get enabled flags
        enabled = flags.get_enabled_flags()

        print_test("Flag operations", True,
                  f"{len(enabled)} flags enabled")
    except Exception as e:
        print_test("Flag operations", False, str(e))

    # Test 4: Set custom flag
    try:
        success = flags.set_flag(
            'test_flag',
            True,
            config={'timeout': 30},
            description='Test flag'
        )

        test_flag = flags.get_flag('test_flag')
        print_test("Set custom flag", success and test_flag is not None)
    except Exception as e:
        print_test("Set custom flag", False, str(e))


def test_phase4_prompt_manager():
    """Test Phase 4: Prompt Experimentation."""
    print_section("PHASE 4: Prompt Experimentation")

    # Test 1: PromptManager initialization
    try:
        from llm.prompts.prompt_manager import PromptManager
        manager = PromptManager()
        print_test("PromptManager initialization", True)
    except Exception as e:
        print_test("PromptManager initialization", False, str(e))
        return

    # Test 2: List templates
    try:
        templates = manager.list_templates()
        print_test("List prompt templates", len(templates) > 0,
                  f"{len(templates)} templates found")

        for template in templates:
            print(f"    - {template['name']} ({template['version']})")
    except Exception as e:
        print_test("List prompt templates", False, str(e))

    # Test 3: Get prompt
    try:
        prompt = manager.get_prompt(
            'article_analysis',
            article_text="테스트 기사 내용입니다."
        )
        print_test("Get prompt", len(prompt) > 0,
                  f"{len(prompt)} characters")
    except Exception as e:
        print_test("Get prompt", False, str(e))

    # Test 4: List experiments
    try:
        experiments = manager.list_experiments()
        print_test("List experiments", True,
                  f"{len(experiments)} experiments configured")
    except Exception as e:
        print_test("List experiments", False, str(e))


def test_phase4_crawler_plugins():
    """Test Phase 4: Crawler Plugin System."""
    print_section("PHASE 4: Crawler Plugin System")

    # Test 1: CrawlerRegistry initialization
    try:
        from crawlers.registry import CrawlerRegistry
        registry = CrawlerRegistry()
        print_test("CrawlerRegistry initialization", True)
    except Exception as e:
        print_test("CrawlerRegistry initialization", False, str(e))
        return

    # Test 2: List plugins
    try:
        plugins = registry.list_plugins()
        print_test("List crawler plugins", len(plugins) > 0,
                  f"{len(plugins)} plugins registered")

        for plugin in plugins:
            print(f"    - {plugin['name']}: {plugin['domains']} (priority={plugin['priority']})")
    except Exception as e:
        print_test("List crawler plugins", False, str(e))

    # Test 3: Plugin selection
    try:
        # Test with known domain
        test_urls = [
            'https://chosun.com/test',
            'https://joongang.co.kr/test',
            'https://unknown-site.com/test'
        ]

        for url in test_urls:
            plugin = registry.get_plugin_for_url(url)
            status = plugin is not None
            plugin_name = plugin.name if plugin else 'None'
            print_test(f"Plugin for {url}", status, f"Selected: {plugin_name}")

    except Exception as e:
        print_test("Plugin selection", False, str(e))


def test_integration():
    """Test integration between components."""
    print_section("INTEGRATION TESTS")

    # Test 1: Feature flags + Analysis service
    try:
        from services import FeatureFlagsService, AnalysisService, CacheService

        flags = FeatureFlagsService()
        cache = CacheService()
        analysis = AnalysisService(cache_service=cache)

        # Check if cache is enabled via feature flag
        cache_enabled = flags.is_enabled('cache_enabled')

        print_test("Feature flags + Analysis integration", True,
                  f"Cache enabled: {cache_enabled}")
    except Exception as e:
        print_test("Feature flags + Analysis integration", False, str(e))

    # Test 2: Prompt manager + Feature flags
    try:
        from llm.prompts.prompt_manager import PromptManager
        from services import FeatureFlagsService

        manager = PromptManager()
        flags = FeatureFlagsService()

        # Simulate choosing prompt based on feature flag
        use_enhanced = flags.is_enabled('use_enhanced_prompt')
        version = 'v2' if use_enhanced else 'v1'

        prompt = manager.get_prompt('article_analysis', version=version, article_text="테스트")

        print_test("Prompt manager + Feature flags", True,
                  f"Using version: {version}")
    except Exception as e:
        print_test("Prompt manager + Feature flags", False, str(e))

    # Test 3: Health service + Cache + Database
    try:
        from services import HealthService, CacheService

        cache = CacheService()
        health = HealthService(cache_service=cache)

        system_health = health.get_system_health()

        components_count = len(system_health.get('components', {}))

        print_test("Health + Cache + Database integration", True,
                  f"{components_count} components monitored")
    except Exception as e:
        print_test("Health + Cache + Database integration", False, str(e))


def main():
    """Run all tests."""
    print(f"\n{'='*70}")
    print(" COMPREHENSIVE PHASE TESTING")
    print(" Testing all implemented phases (1-4)")
    print('='*70)

    try:
        # Phase 1 tests
        test_phase1_observability()
        test_phase1_services()

        # Phase 2 tests
        test_phase2_caching()

        # Phase 3 tests
        test_phase3_health_checks()
        test_phase3_cli_tools()

        # Phase 4 tests
        test_phase4_feature_flags()
        test_phase4_prompt_manager()
        test_phase4_crawler_plugins()

        # Integration tests
        test_integration()

        print_section("TEST SUMMARY")
        print("  All phase tests completed!")
        print("  Review results above for any failures.")
        print()

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
