"""
Base service class with common functionality.

Provides:
- Logging with correlation ID tracking
- Error handling utilities
- Retry logic with exponential backoff
"""

import logging
from typing import Optional, Any, Callable
import functools
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from observability import get_logger, get_correlation_id, metrics


class ServiceError(Exception):
    """Base exception for service layer errors."""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class BaseService:
    """
    Base class for all services.

    Provides common functionality like logging, error handling,
    and metrics collection.
    """

    def __init__(self, service_name: Optional[str] = None):
        """
        Initialize the base service.

        Args:
            service_name: Name of the service (used for logging)
        """
        self.service_name = service_name or self.__class__.__name__
        self.logger = get_logger(f"services.{self.service_name.lower()}")

    def log_info(self, message: str, **kwargs):
        """
        Log an info message with correlation ID.

        Args:
            message: Log message
            **kwargs: Additional context for logging
        """
        extra = {'correlation_id': get_correlation_id(), **kwargs}
        self.logger.info(message, extra=extra)

    def log_error(self, message: str, exc: Optional[Exception] = None, **kwargs):
        """
        Log an error message with correlation ID.

        Args:
            message: Log message
            exc: Optional exception to log
            **kwargs: Additional context for logging
        """
        extra = {'correlation_id': get_correlation_id(), **kwargs}
        if exc:
            self.logger.error(f"{message}: {str(exc)}", exc_info=exc, extra=extra)
        else:
            self.logger.error(message, extra=extra)

    def log_warning(self, message: str, **kwargs):
        """
        Log a warning message with correlation ID.

        Args:
            message: Log message
            **kwargs: Additional context for logging
        """
        extra = {'correlation_id': get_correlation_id(), **kwargs}
        self.logger.warning(message, extra=extra)

    def log_debug(self, message: str, **kwargs):
        """
        Log a debug message with correlation ID.

        Args:
            message: Log message
            **kwargs: Additional context for logging
        """
        extra = {'correlation_id': get_correlation_id(), **kwargs}
        self.logger.debug(message, extra=extra)

    def with_retry(
        self,
        max_attempts: int = 3,
        exceptions: tuple = (Exception,),
        wait_min: int = 1,
        wait_max: int = 10
    ):
        """
        Decorator for retrying operations with exponential backoff.

        Args:
            max_attempts: Maximum number of retry attempts
            exceptions: Tuple of exceptions to retry on
            wait_min: Minimum wait time in seconds
            wait_max: Maximum wait time in seconds

        Returns:
            Decorator function

        Example:
            @self.with_retry(max_attempts=3, exceptions=(APIError,))
            def call_api():
                ...
        """
        def decorator(func: Callable) -> Callable:
            @retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
                retry=retry_if_exception_type(exceptions),
                reraise=True
            )
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def track_metric(self, metric_name: str, value: Any, tags: Optional[dict] = None):
        """
        Track a metric.

        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags for the metric
        """
        if tags is None:
            tags = {}

        # Add service name to tags
        tags['service'] = self.service_name.lower()

        # Track based on value type
        if isinstance(value, (int, float)):
            metrics.gauge(metric_name, value, tags=tags)
        else:
            self.log_warning(f"Unknown metric type for {metric_name}: {type(value)}")

    def increment_counter(self, counter_name: str, value: int = 1, tags: Optional[dict] = None):
        """
        Increment a counter metric.

        Args:
            counter_name: Name of the counter
            value: Amount to increment (default: 1)
            tags: Optional tags for the metric
        """
        if tags is None:
            tags = {}

        tags['service'] = self.service_name.lower()
        metrics.increment(counter_name, value, tags=tags)

    def record_timing(self, operation_name: str, duration_ms: float, tags: Optional[dict] = None):
        """
        Record a timing metric.

        Args:
            operation_name: Name of the operation
            duration_ms: Duration in milliseconds
            tags: Optional tags for the metric
        """
        if tags is None:
            tags = {}

        tags['service'] = self.service_name.lower()
        metrics.timing(operation_name, duration_ms, tags=tags)
