"""
Unit tests for observability module (logging, metrics, context).
"""

import pytest
import json
import tempfile
from pathlib import Path
from observability import (
    setup_logging, get_logger, get_correlation_id,
    set_correlation_id, request_context, metrics
)


class TestLogging:
    """Test structured logging functionality."""

    def test_setup_logging_creates_log_directory(self, tmp_path):
        """Test that setup_logging creates log directory if it doesn't exist."""
        log_dir = tmp_path / "test_logs"
        assert not log_dir.exists()

        setup_logging(log_level="INFO", log_format="json", log_dir=str(log_dir))

        assert log_dir.exists()

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a valid logger instance."""
        logger = get_logger("test_component")

        assert logger is not None
        assert logger.name == "test_component"

    def test_logger_includes_component_name(self, tmp_path, caplog):
        """Test that log messages include component name."""
        log_dir = tmp_path / "logs"
        setup_logging(log_level="INFO", log_format="text", log_dir=str(log_dir))

        logger = get_logger("test_module")
        logger.info("Test message")

        assert "test_module" in caplog.text

    def test_json_log_format(self, tmp_path):
        """Test that JSON log format produces valid JSON."""
        log_dir = tmp_path / "logs"
        setup_logging(log_level="INFO", log_format="json", log_dir=str(log_dir))

        logger = get_logger("test")
        logger.info("Test JSON logging", extra={"custom_field": "value"})

        # Check that log file contains valid JSON
        log_file = list(log_dir.glob("*.log"))[0]
        with open(log_file) as f:
            line = f.readline()
            log_entry = json.loads(line)

            assert "message" in log_entry
            assert "timestamp" in log_entry
            assert log_entry["message"] == "Test JSON logging"


class TestCorrelationID:
    """Test correlation ID context management."""

    def test_set_and_get_correlation_id(self):
        """Test setting and retrieving correlation ID."""
        test_id = "test_correlation_123"
        set_correlation_id(test_id)

        retrieved_id = get_correlation_id()
        assert retrieved_id == test_id

    def test_correlation_id_with_context_manager(self):
        """Test correlation ID with context manager."""
        # Set an ID outside context
        set_correlation_id("outside_id")
        assert get_correlation_id() == "outside_id"

        # Inside context, should have new ID
        with request_context("inside_id") as ctx:
            assert get_correlation_id() == "inside_id"
            assert ctx.correlation_id == "inside_id"

        # After context exits, should restore previous ID
        assert get_correlation_id() == "outside_id"

    def test_correlation_id_is_thread_local(self):
        """Test that correlation IDs are isolated per thread."""
        import threading

        ids = {}

        def set_and_get(thread_id):
            correlation_id = f"thread_{thread_id}"
            set_correlation_id(correlation_id)
            ids[thread_id] = get_correlation_id()

        threads = [
            threading.Thread(target=set_and_get, args=(i,))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should have its own correlation ID
        assert len(ids) == 5
        for i in range(5):
            assert ids[i] == f"thread_{i}"


class TestMetrics:
    """Test metrics collection."""

    def setup_method(self):
        """Reset metrics before each test."""
        metrics._metrics.clear()

    def test_increment_counter(self):
        """Test incrementing a counter metric."""
        metrics.increment("test_counter")
        metrics.increment("test_counter")
        metrics.increment("test_counter", value=3)

        summary = metrics.get_summary()
        assert "test_counter" in summary
        assert summary["test_counter"]["value"] == 5

    def test_gauge_metric(self):
        """Test setting a gauge metric."""
        metrics.gauge("test_gauge", 42.5)
        metrics.gauge("test_gauge", 100.0)

        summary = metrics.get_summary()
        assert "test_gauge" in summary
        assert summary["test_gauge"]["value"] == 100.0

    def test_timing_metric(self):
        """Test recording timing metrics."""
        metrics.timing("test_latency", 123.45)
        metrics.timing("test_latency", 200.0)
        metrics.timing("test_latency", 50.0)

        summary = metrics.get_summary()
        assert "test_latency" in summary

        timing_data = summary["test_latency"]
        assert timing_data["count"] == 3
        assert timing_data["avg"] == (123.45 + 200.0 + 50.0) / 3

    def test_get_metric(self):
        """Test retrieving a specific metric."""
        metrics.increment("specific_metric", value=10)

        metric = metrics.get_metric("specific_metric")
        assert metric is not None
        assert metric["value"] == 10

    def test_get_nonexistent_metric(self):
        """Test retrieving a metric that doesn't exist."""
        metric = metrics.get_metric("nonexistent")
        assert metric is None

    def test_metrics_with_labels(self):
        """Test metrics with labels."""
        metrics.increment("requests", labels={"endpoint": "/analyze", "status": "200"})
        metrics.increment("requests", labels={"endpoint": "/analyze", "status": "500"})
        metrics.increment("requests", labels={"endpoint": "/health", "status": "200"})

        summary = metrics.get_summary()

        # Should have separate metrics for different label combinations
        assert "requests:endpoint=/analyze,status=200" in summary or \
               any("requests" in key and "analyze" in key for key in summary.keys())
