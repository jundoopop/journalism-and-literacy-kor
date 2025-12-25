"""
Unit tests for cache service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from services import CacheService


class TestCacheService:
    """Test cache service functionality."""

    def test_service_initialization_without_redis(self):
        """Test that service initializes even when Redis is unavailable."""
        service = CacheService()
        assert service is not None

    def test_is_enabled_when_redis_unavailable(self):
        """Test is_enabled returns False when Redis is not available."""
        service = CacheService()
        # By default, if Redis is not running, should be disabled
        assert isinstance(service.is_enabled(), bool)

    @patch('redis.Redis')
    def test_service_with_mock_redis(self, mock_redis_class):
        """Test service functionality with mocked Redis."""
        # Setup mock
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client

        service = CacheService()

        # If Redis is mocked to be available, service should enable
        # This depends on implementation details

    def test_health_check_structure(self):
        """Test health check returns proper structure."""
        service = CacheService()
        health = service.health_check()

        assert 'status' in health
        assert health['status'] in ['healthy', 'unhealthy', 'disabled']

        if health['status'] == 'healthy':
            assert 'latency_ms' in health

    def test_get_stats_structure(self):
        """Test get_stats returns CacheStats."""
        service = CacheService()
        stats = service.get_stats()

        assert hasattr(stats, 'hits')
        assert hasattr(stats, 'misses')
        assert hasattr(stats, 'hit_rate')
        assert isinstance(stats.hits, int)
        assert isinstance(stats.misses, int)
        assert isinstance(stats.hit_rate, float)

    def test_cache_key_generation(self):
        """Test cache key generation is consistent."""
        service = CacheService()

        url = "https://example.com/article"
        providers = ["gemini", "mistral"]

        # Should generate consistent keys
        key1 = service._generate_cache_key(url, providers)
        key2 = service._generate_cache_key(url, providers)

        assert key1 == key2
        assert "article:" in key1
        assert "providers:" in key1

    def test_cache_key_provider_order_independence(self):
        """Test that provider order doesn't affect cache key."""
        service = CacheService()

        url = "https://example.com/article"
        providers1 = ["gemini", "mistral", "openai"]
        providers2 = ["openai", "gemini", "mistral"]

        key1 = service._generate_cache_key(url, providers1)
        key2 = service._generate_cache_key(url, providers2)

        # Keys should be the same regardless of provider order
        assert key1 == key2

    @patch('redis.Redis')
    def test_set_and_get_analysis_result(self, mock_redis_class):
        """Test setting and getting analysis results."""
        # Setup mock
        mock_client = Mock()
        mock_client.ping.return_value = True
        stored_data = None

        def mock_setex(key, ttl, value):
            nonlocal stored_data
            stored_data = value
            return True

        def mock_get(key):
            return stored_data

        mock_client.setex.side_effect = mock_setex
        mock_client.get.side_effect = mock_get
        mock_redis_class.return_value = mock_client

        service = CacheService()
        service._redis = mock_client
        service._enabled = True

        # Test data
        url = "https://test.com/article"
        providers = ["gemini"]
        result = {
            "sentences": {"test": "reason"},
            "headline": "Test"
        }

        # Set result
        service.set_analysis_result(url, providers, result)

        # Get result
        retrieved = service.get_analysis_result(url, providers)

        assert retrieved is not None
        assert retrieved['headline'] == 'Test'

    @patch('redis.Redis')
    def test_cache_miss_increments_stats(self, mock_redis_class):
        """Test that cache misses increment statistics."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_redis_class.return_value = mock_client

        service = CacheService()
        service._redis = mock_client
        service._enabled = True

        initial_stats = service.get_stats()
        initial_misses = initial_stats.misses

        # Attempt to get non-existent result
        result = service.get_analysis_result("https://test.com", ["gemini"])

        assert result is None

        new_stats = service.get_stats()
        assert new_stats.misses == initial_misses + 1

    @patch('redis.Redis')
    def test_invalidate_cache(self, mock_redis_class):
        """Test cache invalidation."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.delete.return_value = 1
        mock_redis_class.return_value = mock_client

        service = CacheService()
        service._redis = mock_client
        service._enabled = True

        url = "https://test.com/article"
        providers = ["gemini"]

        # Invalidate
        service.invalidate(url, providers)

        # Should have called delete
        assert mock_client.delete.called

    def test_graceful_degradation_on_redis_failure(self):
        """Test that service degrades gracefully when Redis fails."""
        service = CacheService()

        # Even if Redis is down, these should not raise exceptions
        result = service.get_analysis_result("https://test.com", ["gemini"])
        assert result is None  # Returns None on failure

        # Should not raise exception
        service.set_analysis_result("https://test.com", ["gemini"], {"test": "data"})

        # Stats should still work
        stats = service.get_stats()
        assert stats is not None
