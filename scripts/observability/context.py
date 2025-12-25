"""
Request context management with correlation ID tracking.

Provides a context manager for tracking requests across components
with unique correlation IDs for distributed tracing.
"""

import uuid
from contextvars import ContextVar
from typing import Optional, Dict, Any
from datetime import datetime

# Context variable for storing correlation ID (thread-safe)
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
_request_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar('request_context', default=None)


def generate_correlation_id() -> str:
    """Generate a unique correlation ID."""
    return f"req_{uuid.uuid4().hex[:12]}"


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID in context."""
    _correlation_id.set(correlation_id)


class RequestContext:
    """
    Context manager for request tracking.

    Automatically generates and tracks correlation IDs and additional
    request metadata throughout the request lifecycle.

    Usage:
        with request_context() as ctx:
            ctx.set('url', 'https://example.com')
            correlation_id = ctx.correlation_id
            logger.info("Processing request", extra=ctx.to_dict())
    """

    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or generate_correlation_id()
        self.start_time = datetime.utcnow()
        self._data: Dict[str, Any] = {}
        self._previous_correlation_id: Optional[str] = None
        self._previous_context: Optional[Dict[str, Any]] = None

    def __enter__(self) -> 'RequestContext':
        """Enter the context and set correlation ID."""
        self._previous_correlation_id = _correlation_id.get()
        self._previous_context = _request_context.get()

        _correlation_id.set(self.correlation_id)
        _request_context.set(self._data)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and restore previous correlation ID."""
        _correlation_id.set(self._previous_correlation_id)
        _request_context.set(self._previous_context)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the request context."""
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the request context."""
        return self._data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary for logging.

        Returns:
            Dict with correlation_id and all custom data
        """
        return {
            'correlation_id': self.correlation_id,
            **self._data
        }

    @property
    def elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds since context creation."""
        delta = datetime.utcnow() - self.start_time
        return int(delta.total_seconds() * 1000)


def request_context(correlation_id: Optional[str] = None) -> RequestContext:
    """
    Create a new request context.

    Args:
        correlation_id: Optional correlation ID. If not provided, generates a new one.

    Returns:
        RequestContext instance

    Example:
        with request_context() as ctx:
            ctx.set('url', article_url)
            logger.info("Starting analysis", extra=ctx.to_dict())
    """
    return RequestContext(correlation_id)


def get_current_context() -> Optional[Dict[str, Any]]:
    """Get the current request context data."""
    return _request_context.get()
