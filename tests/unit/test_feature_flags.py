"""
Unit tests for feature flags service.
"""

import pytest
from datetime import datetime, timedelta
from services import FeatureFlagsService
from database import init_database


class TestFeatureFlagsService:
    """Test feature flags service functionality."""

    @pytest.fixture(autouse=True)
    def setup(self, temp_database, monkeypatch):
        """Setup test database before each test."""
        monkeypatch.setenv("DATABASE_PATH", temp_database)
        init_database()
        self.service = FeatureFlagsService(cache_duration=1)  # 1 second cache for testing

    def test_service_initialization(self):
        """Test that service initializes correctly."""
        assert self.service is not None
        assert self.service._cache == {}

    def test_create_default_flags(self):
        """Test creating default feature flags."""
        self.service.create_default_flags()

        all_flags = self.service.get_all_flags()
        assert len(all_flags) > 0

        # Check for expected default flags
        flag_names = [f['name'] for f in all_flags]
        assert 'cache_enabled' in flag_names
        assert 'strict_consensus' in flag_names

    def test_set_and_get_flag(self):
        """Test setting and retrieving a flag."""
        success = self.service.set_flag(
            'test_flag',
            enabled=True,
            config={'timeout': 30},
            description='Test flag'
        )

        assert success is True

        flag = self.service.get_flag('test_flag')
        assert flag is not None
        assert flag['name'] == 'test_flag'
        assert flag['enabled'] is True
        assert flag['config']['timeout'] == 30

    def test_is_enabled(self):
        """Test checking if a flag is enabled."""
        self.service.set_flag('enabled_flag', True)
        self.service.set_flag('disabled_flag', False)

        assert self.service.is_enabled('enabled_flag') is True
        assert self.service.is_enabled('disabled_flag') is False

    def test_is_enabled_default(self):
        """Test default value for non-existent flag."""
        assert self.service.is_enabled('nonexistent', default=True) is True
        assert self.service.is_enabled('nonexistent', default=False) is False

    def test_get_config(self):
        """Test retrieving flag configuration."""
        config = {'max_retries': 3, 'timeout': 60}
        self.service.set_flag('config_flag', True, config=config)

        retrieved_config = self.service.get_config('config_flag')
        assert retrieved_config == config

    def test_get_config_nonexistent(self):
        """Test retrieving config for non-existent flag."""
        config = self.service.get_config('nonexistent')
        assert config == {}

    def test_get_enabled_flags(self):
        """Test getting all enabled flags."""
        self.service.set_flag('flag1', True)
        self.service.set_flag('flag2', True)
        self.service.set_flag('flag3', False)

        enabled = self.service.get_enabled_flags()
        enabled_names = [f['name'] for f in enabled]

        assert 'flag1' in enabled_names
        assert 'flag2' in enabled_names
        assert 'flag3' not in enabled_names

    def test_update_flag(self):
        """Test updating an existing flag."""
        self.service.set_flag('update_test', True, config={'version': 1})

        # Update the flag
        self.service.set_flag('update_test', False, config={'version': 2})

        flag = self.service.get_flag('update_test')
        assert flag['enabled'] is False
        assert flag['config']['version'] == 2

    def test_cache_functionality(self):
        """Test that cache reduces database queries."""
        import time

        self.service.set_flag('cached_flag', True)

        # First call - loads from database
        result1 = self.service.is_enabled('cached_flag')

        # Second call - should use cache
        result2 = self.service.is_enabled('cached_flag')

        assert result1 == result2 == True

        # Wait for cache to expire
        time.sleep(1.1)

        # This should reload from database
        result3 = self.service.is_enabled('cached_flag')
        assert result3 is True

    def test_cache_invalidation_on_set(self):
        """Test that cache is invalidated when flag is updated."""
        self.service.set_flag('invalidate_test', True)

        # Load into cache
        assert self.service.is_enabled('invalidate_test') is True

        # Update flag - should invalidate cache
        self.service.set_flag('invalidate_test', False)

        # Should reflect new value immediately
        assert self.service.is_enabled('invalidate_test') is False

    def test_get_all_flags(self):
        """Test retrieving all flags."""
        self.service.set_flag('flag1', True)
        self.service.set_flag('flag2', False)

        all_flags = self.service.get_all_flags()

        assert len(all_flags) >= 2
        flag_names = [f['name'] for f in all_flags]
        assert 'flag1' in flag_names
        assert 'flag2' in flag_names

    def test_flag_with_complex_config(self):
        """Test flag with nested configuration."""
        complex_config = {
            'providers': ['gemini', 'mistral'],
            'thresholds': {
                'min_consensus': 0.7,
                'max_timeout': 30
            },
            'features': ['caching', 'retry']
        }

        self.service.set_flag('complex_flag', True, config=complex_config)

        retrieved = self.service.get_config('complex_flag')
        assert retrieved == complex_config
        assert retrieved['providers'] == ['gemini', 'mistral']
        assert retrieved['thresholds']['min_consensus'] == 0.7
