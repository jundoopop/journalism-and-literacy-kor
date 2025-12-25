"""
Unit tests for database models and repository.
"""

import pytest
from datetime import datetime, timedelta
from database import (
    RequestLog, AnalysisResult, ProviderMetric, FeatureFlag,
    AnalyticsRepository, init_database, session_scope
)


class TestDatabaseModels:
    """Test database model creation and operations."""

    @pytest.fixture(autouse=True)
    def setup(self, temp_database, monkeypatch):
        """Setup test database before each test."""
        monkeypatch.setenv("DATABASE_PATH", temp_database)
        init_database()

    def test_request_log_creation(self):
        """Test creating a request log entry."""
        with session_scope() as session:
            log = RequestLog(
                correlation_id="test_123",
                url="https://test.com/article",
                mode="consensus",
                providers='["gemini", "mistral"]',
                status="success",
                duration_ms=1500
            )

            session.add(log)
            session.commit()

            # Retrieve and verify
            retrieved = session.query(RequestLog).filter_by(
                correlation_id="test_123"
            ).first()

            assert retrieved is not None
            assert retrieved.url == "https://test.com/article"
            assert retrieved.mode == "consensus"
            assert retrieved.status == "success"
            assert retrieved.duration_ms == 1500

    def test_analysis_result_creation(self):
        """Test creating an analysis result entry."""
        with session_scope() as session:
            result = AnalysisResult(
                correlation_id="test_456",
                url="https://example.com/article",
                provider="gemini",
                success=True,
                response_data={"sentences": {"test": "reason"}},
                duration_ms=2000.0,
                model_name="gemini-2.5-flash-lite"
            )

            session.add(result)
            session.commit()

            # Retrieve and verify
            retrieved = session.query(AnalysisResult).filter_by(
                correlation_id="test_456"
            ).first()

            assert retrieved is not None
            assert retrieved.provider == "gemini"
            assert retrieved.success is True
            assert retrieved.response_data["sentences"] == {"test": "reason"}

    def test_provider_metric_creation(self):
        """Test creating provider metrics."""
        with session_scope() as session:
            metric = ProviderMetric(
                provider="mistral",
                metric_type="latency",
                value=1234.5,
                timestamp=datetime.utcnow(),
                metadata={"model": "mistral-large"}
            )

            session.add(metric)
            session.commit()

            # Retrieve and verify
            retrieved = session.query(ProviderMetric).filter_by(
                provider="mistral"
            ).first()

            assert retrieved is not None
            assert retrieved.metric_type == "latency"
            assert retrieved.value == 1234.5

    def test_feature_flag_creation(self):
        """Test creating feature flags."""
        with session_scope() as session:
            flag = FeatureFlag(
                name="test_feature",
                enabled=True,
                config={"timeout": 30},
                description="Test feature flag"
            )

            session.add(flag)
            session.commit()

            # Retrieve and verify
            retrieved = session.query(FeatureFlag).filter_by(
                name="test_feature"
            ).first()

            assert retrieved is not None
            assert retrieved.enabled is True
            assert retrieved.config["timeout"] == 30

    def test_feature_flag_update(self):
        """Test updating feature flag."""
        with session_scope() as session:
            flag = FeatureFlag(
                name="update_test",
                enabled=True,
                config={"version": 1}
            )
            session.add(flag)
            session.commit()

        # Update the flag
        with session_scope() as session:
            flag = session.query(FeatureFlag).filter_by(
                name="update_test"
            ).first()

            flag.enabled = False
            flag.config = {"version": 2}
            session.commit()

        # Verify update
        with session_scope() as session:
            flag = session.query(FeatureFlag).filter_by(
                name="update_test"
            ).first()

            assert flag.enabled is False
            assert flag.config["version"] == 2
            assert flag.updated_at > flag.created_at


class TestAnalyticsRepository:
    """Test analytics repository operations."""

    @pytest.fixture(autouse=True)
    def setup(self, temp_database, monkeypatch):
        """Setup test database and repository."""
        monkeypatch.setenv("DATABASE_PATH", temp_database)
        init_database()
        self.repo = AnalyticsRepository()

    def test_repository_initialization(self):
        """Test that repository initializes correctly."""
        assert self.repo is not None

    def test_log_request(self):
        """Test logging a request."""
        self.repo.log_request(
            correlation_id="req_123",
            method="GET",
            endpoint="/health",
            status_code=200,
            duration_ms=50.0,
            client_ip="127.0.0.1"
        )

        # Verify logged
        with session_scope() as session:
            log = session.query(RequestLog).filter_by(
                correlation_id="req_123"
            ).first()

            assert log is not None
            assert log.endpoint == "/health"

    def test_log_analysis_result(self):
        """Test logging an analysis result."""
        self.repo.log_analysis_result(
            correlation_id="req_456",
            url="https://test.com",
            provider="gemini",
            success=True,
            response_data={"test": "data"},
            duration_ms=1500.0,
            model_name="gemini-flash",
            error_message=None
        )

        # Verify logged
        with session_scope() as session:
            result = session.query(AnalysisResult).filter_by(
                correlation_id="req_456"
            ).first()

            assert result is not None
            assert result.provider == "gemini"
            assert result.success is True

    def test_log_provider_metric(self):
        """Test logging provider metrics."""
        self.repo.log_provider_metric(
            provider="mistral",
            metric_type="success_rate",
            value=0.95,
            metadata={"period": "1h"}
        )

        # Verify logged
        with session_scope() as session:
            metric = session.query(ProviderMetric).filter_by(
                provider="mistral",
                metric_type="success_rate"
            ).first()

            assert metric is not None
            assert metric.value == 0.95

    def test_get_recent_requests(self):
        """Test retrieving recent requests."""
        # Log multiple requests
        for i in range(5):
            self.repo.log_request(
                correlation_id=f"req_{i}",
                method="POST",
                endpoint="/analyze",
                status_code=200,
                duration_ms=1000.0
            )

        # Get recent requests
        recent = self.repo.get_recent_requests(limit=3)

        assert len(recent) == 3

    def test_get_provider_metrics(self):
        """Test retrieving provider metrics."""
        # Log metrics
        now = datetime.utcnow()

        for i in range(3):
            self.repo.log_provider_metric(
                provider="gemini",
                metric_type="latency",
                value=1000.0 + i * 100
            )

        # Get metrics
        metrics = self.repo.get_provider_metrics(
            provider="gemini",
            metric_type="latency",
            since=now - timedelta(minutes=5)
        )

        assert len(metrics) == 3

    def test_get_analysis_results_by_url(self):
        """Test retrieving analysis results for a specific URL."""
        url = "https://test.com/article"

        # Log multiple results for same URL
        for provider in ["gemini", "mistral"]:
            self.repo.log_analysis_result(
                correlation_id=f"req_{provider}",
                url=url,
                provider=provider,
                success=True,
                response_data={},
                duration_ms=1000.0
            )

        # Get results
        results = self.repo.get_analysis_results_by_url(url)

        assert len(results) >= 2
        providers = [r.provider for r in results]
        assert "gemini" in providers
        assert "mistral" in providers

    def test_get_failed_analyses(self):
        """Test retrieving failed analyses."""
        # Log successful and failed results
        self.repo.log_analysis_result(
            correlation_id="success",
            url="https://test.com",
            provider="gemini",
            success=True,
            response_data={},
            duration_ms=1000.0
        )

        self.repo.log_analysis_result(
            correlation_id="failure",
            url="https://test.com",
            provider="mistral",
            success=False,
            response_data={},
            duration_ms=1000.0,
            error_message="API error"
        )

        # Get failed analyses
        failed = self.repo.get_failed_analyses(limit=10)

        assert len(failed) >= 1
        assert all(not r.success for r in failed)

    def test_session_scope_commit(self):
        """Test that session_scope commits on success."""
        with session_scope() as session:
            log = RequestLog(
                correlation_id="commit_test",
                method="GET",
                endpoint="/test",
                status_code=200,
                duration_ms=100.0
            )
            session.add(log)

        # Should be committed
        with session_scope() as session:
            retrieved = session.query(RequestLog).filter_by(
                correlation_id="commit_test"
            ).first()

            assert retrieved is not None

    def test_session_scope_rollback_on_error(self):
        """Test that session_scope rolls back on error."""
        try:
            with session_scope() as session:
                log = RequestLog(
                    correlation_id="rollback_test",
                    method="GET",
                    endpoint="/test",
                    status_code=200,
                    duration_ms=100.0
                )
                session.add(log)

                # Raise error before commit
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should be rolled back
        with session_scope() as session:
            retrieved = session.query(RequestLog).filter_by(
                correlation_id="rollback_test"
            ).first()

            assert retrieved is None
