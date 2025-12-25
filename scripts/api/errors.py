"""
Standardized error handling for API responses.

Provides consistent error responses across all endpoints
with proper HTTP status codes and detailed error information.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from flask import jsonify

from observability import get_correlation_id


class AppError(Exception):
    """
    Base application error.

    All custom exceptions should inherit from this class.
    """

    code = "INTERNAL_ERROR"
    status_code = 500

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize application error.

        Args:
            message: Human-readable error message
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary for JSON response.

        Returns:
            Dictionary with error information
        """
        return {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "correlation_id": get_correlation_id() or "none",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }


class ValidationError(AppError):
    """Request validation error (400 Bad Request)."""
    code = "VALIDATION_ERROR"
    status_code = 400


class CrawlerError(AppError):
    """Article crawling/parsing error (400 Bad Request)."""
    code = "CRAWLER_FAILED"
    status_code = 400


class LLMError(AppError):
    """LLM provider error (500 Internal Server Error)."""
    code = "LLM_API_ERROR"
    status_code = 500

    def __init__(self, provider: str, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize LLM error.

        Args:
            provider: LLM provider name
            message: Error message
            details: Optional additional details
        """
        super().__init__(f"[{provider}] {message}", details or {})
        self.provider = provider
        self.details["provider"] = provider


class CacheError(AppError):
    """Cache operation error (non-critical, 500 if severe)."""
    code = "CACHE_ERROR"
    status_code = 500


class DatabaseError(AppError):
    """Database operation error (500 Internal Server Error)."""
    code = "DATABASE_ERROR"
    status_code = 500


class AuthenticationError(AppError):
    """Authentication error (401 Unauthorized)."""
    code = "AUTHENTICATION_ERROR"
    status_code = 401


class NotFoundError(AppError):
    """Resource not found (404 Not Found)."""
    code = "NOT_FOUND"
    status_code = 404


class RateLimitError(AppError):
    """Rate limit exceeded (429 Too Many Requests)."""
    code = "RATE_LIMIT_EXCEEDED"
    status_code = 429


def error_response(error: AppError):
    """
    Create a Flask JSON response from an AppError.

    Args:
        error: Application error instance

    Returns:
        Flask JSON response with appropriate status code

    Example:
        try:
            ...
        except ValidationError as e:
            return error_response(e)
    """
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def make_success_response(data: Dict[str, Any], status_code: int = 200):
    """
    Create a standardized success response.

    Args:
        data: Response data
        status_code: HTTP status code (default: 200)

    Returns:
        Flask JSON response

    Example:
        return make_success_response({
            'url': url,
            'headline': headline,
            'sentences': sentences
        })
    """
    response_data = {
        "success": True,
        "correlation_id": get_correlation_id() or "none",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **data
    }

    response = jsonify(response_data)
    response.status_code = status_code
    return response
