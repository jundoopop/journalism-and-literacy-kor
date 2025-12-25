"""
API layer for HTTP request handling.

Provides:
- Standardized error responses
- Request/response middleware
- Admin authentication
"""

from .errors import (
    AppError,
    ValidationError,
    CrawlerError,
    LLMError,
    CacheError,
    DatabaseError,
    AuthenticationError,
    error_response
)

from .middleware import (
    correlation_id_middleware,
    admin_auth_middleware,
    metrics_middleware,
    error_handler_middleware
)

__all__ = [
    # Errors
    'AppError',
    'ValidationError',
    'CrawlerError',
    'LLMError',
    'CacheError',
    'DatabaseError',
    'AuthenticationError',
    'error_response',

    # Middleware
    'correlation_id_middleware',
    'admin_auth_middleware',
    'metrics_middleware',
    'error_handler_middleware',
]
