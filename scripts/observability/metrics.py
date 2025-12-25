"""
Metrics collection and aggregation system.

Provides a lightweight metrics collection system that stores
metrics in memory and can periodically flush to database.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    In-memory metrics collector with aggregation.

    Collects counters, timings, and gauges. Metrics are aggregated
    in memory and can be flushed to database periodically.

    Thread-safe for concurrent metric collection.
    """

    def __init__(self):
        self._counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._timings: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._gauges: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._lock = Lock()
        self._enabled = True

    def enable(self):
        """Enable metrics collection."""
        self._enabled = True
        logger.info("Metrics collection enabled")

    def disable(self):
        """Disable metrics collection."""
        self._enabled = False
        logger.info("Metrics collection disabled")

    def increment(self, metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """
        Increment a counter metric.

        Args:
            metric_name: Name of the metric (e.g., 'llm_requests')
            value: Amount to increment by (default: 1)
            tags: Optional tags for metric dimensions (e.g., {'provider': 'gemini'})

        Example:
            metrics.increment('llm_requests', tags={'provider': 'gemini', 'status': 'success'})
        """
        if not self._enabled:
            return

        tag_key = self._make_tag_key(tags)
        with self._lock:
            self._counters[metric_name][tag_key] += value

    def timing(self, metric_name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None):
        """
        Record a timing metric in milliseconds.

        Args:
            metric_name: Name of the metric (e.g., 'llm_latency')
            duration_ms: Duration in milliseconds
            tags: Optional tags for metric dimensions

        Example:
            start = time.time()
            # ... do work ...
            metrics.timing('llm_latency', (time.time() - start) * 1000, tags={'provider': 'gemini'})
        """
        if not self._enabled:
            return

        tag_key = self._make_tag_key(tags)
        with self._lock:
            self._timings[metric_name][tag_key].append(duration_ms)

    def gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        Set a gauge metric (snapshot value).

        Args:
            metric_name: Name of the metric (e.g., 'cache_hit_rate')
            value: Current value
            tags: Optional tags for metric dimensions

        Example:
            metrics.gauge('cache_hit_rate', 0.45)
            metrics.gauge('active_connections', 10)
        """
        if not self._enabled:
            return

        tag_key = self._make_tag_key(tags)
        with self._lock:
            self._gauges[metric_name][tag_key] = value

    def timer(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        """
        Context manager for timing operations.

        Args:
            metric_name: Name of the metric
            tags: Optional tags for metric dimensions

        Returns:
            Timer context manager

        Example:
            with metrics.timer('llm_analysis', tags={'provider': 'gemini'}):
                result = analyze_article(text)
        """
        return Timer(self, metric_name, tags)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all collected metrics.

        Returns:
            Dictionary with counters, timings (with percentiles), and gauges
        """
        with self._lock:
            summary = {
                'counters': {},
                'timings': {},
                'gauges': {}
            }

            # Counters
            for metric_name, tag_values in self._counters.items():
                summary['counters'][metric_name] = dict(tag_values)

            # Timings with percentiles
            for metric_name, tag_values in self._timings.items():
                summary['timings'][metric_name] = {}
                for tag_key, values in tag_values.items():
                    if values:
                        sorted_values = sorted(values)
                        n = len(sorted_values)
                        summary['timings'][metric_name][tag_key] = {
                            'count': n,
                            'min': min(values),
                            'max': max(values),
                            'avg': sum(values) / n,
                            'p50': sorted_values[int(n * 0.5)],
                            'p95': sorted_values[int(n * 0.95)],
                            'p99': sorted_values[int(n * 0.99)] if n > 100 else sorted_values[-1]
                        }

            # Gauges
            for metric_name, tag_values in self._gauges.items():
                summary['gauges'][metric_name] = dict(tag_values)

            return summary

    def reset(self):
        """Reset all metrics (useful after flushing to database)."""
        with self._lock:
            self._counters.clear()
            self._timings.clear()
            self._gauges.clear()
            logger.debug("Metrics reset")

    def _make_tag_key(self, tags: Optional[Dict[str, str]]) -> str:
        """Convert tags dictionary to a string key."""
        if not tags:
            return 'default'
        return ','.join(f"{k}={v}" for k, v in sorted(tags.items()))

    def _parse_tag_key(self, tag_key: str) -> Dict[str, str]:
        """Parse tag key back to dictionary."""
        if tag_key == 'default':
            return {}
        return dict(item.split('=') for item in tag_key.split(','))


class Timer:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, metric_name: str, tags: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.metric_name = metric_name
        self.tags = tags
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration_ms = (time.time() - self.start_time) * 1000
            self.collector.timing(self.metric_name, duration_ms, self.tags)


# Global metrics instance
metrics = MetricsCollector()
