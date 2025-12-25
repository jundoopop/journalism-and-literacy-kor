"""
Flask middleware for request processing.

Provides:
- Correlation ID injection
- Admin authentication
- Metrics collection
- Error handling
"""

import time
import secrets
from functools import wraps
from typing import Callable
from flask import request, g, jsonify

from observability import request_context, get_logger, metrics
from config import settings
from .errors import AuthenticationError, error_response

logger = get_logger(__name__)


def correlation_id_middleware(app):
    """
    Middleware to inject correlation ID into all requests.

    Creates a unique correlation ID for each request and stores
    it in the request context for logging and tracing.

    Args:
        app: Flask application instance

    Usage:
        correlation_id_middleware(app)
    """

    @app.before_request
    def before_request():
        """Set up request context with correlation ID."""
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get('X-Correlation-ID')

        # Create request context
        ctx = request_context(correlation_id)
        ctx.__enter__()

        # Store context in Flask's g object for cleanup
        g.request_context = ctx
        g.request_start_time = time.time()

        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=request.path,
            remote_addr=request.remote_addr,
            correlation_id=ctx.correlation_id
        )

    @app.after_request
    def after_request(response):
        """Clean up request context and add correlation ID to response."""
        # Add correlation ID to response headers
        if hasattr(g, 'request_context'):
            response.headers['X-Correlation-ID'] = g.request_context.correlation_id

            # Calculate request duration
            if hasattr(g, 'request_start_time'):
                duration_ms = int((time.time() - g.request_start_time) * 1000)

                # Log response
                logger.info(
                    "Request completed",
                    method=request.method,
                    path=request.path,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    correlation_id=g.request_context.correlation_id
                )

        return response

    @app.teardown_request
    def teardown_request(exc=None):
        """Clean up request context."""
        if hasattr(g, 'request_context'):
            g.request_context.__exit__(None, None, None)


def admin_auth_middleware(require_auth: bool = True):
    """
    Decorator for admin endpoints requiring authentication.

    Validates admin token from X-Admin-Token header.

    Args:
        require_auth: Whether to require authentication (default: True)

    Returns:
        Decorator function

    Usage:
        @app.route('/admin/metrics')
        @admin_auth_middleware()
        def get_metrics():
            ...
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip auth if disabled in settings
            if not settings.enable_admin_api or not require_auth:
                return f(*args, **kwargs)

            # Get token from header
            provided_token = request.headers.get('X-Admin-Token')

            if not provided_token:
                logger.warning(
                    "Admin authentication failed: No token provided",
                    path=request.path,
                    remote_addr=request.remote_addr
                )

                error = AuthenticationError(
                    "Admin token required. Provide X-Admin-Token header.",
                    details={"header": "X-Admin-Token"}
                )
                return error_response(error)

            # Validate token (constant-time comparison)
            expected_token = settings.admin_token

            if not expected_token:
                logger.error(
                    "Admin token not configured in settings",
                    path=request.path
                )

                error = AuthenticationError(
                    "Admin authentication not configured",
                    details={"reason": "ADMIN_TOKEN not set in environment"}
                )
                return error_response(error)

            # Use constant-time comparison to prevent timing attacks
            if not secrets.compare_digest(provided_token, expected_token):
                logger.warning(
                    "Admin authentication failed: Invalid token",
                    path=request.path,
                    remote_addr=request.remote_addr
                )

                # Track failed auth attempts
                metrics.increment("admin_auth_failures", tags={
                    "path": request.path,
                    "remote_addr": request.remote_addr
                })

                error = AuthenticationError(
                    "Invalid admin token",
                    details={"header": "X-Admin-Token"}
                )
                return error_response(error)

            # Authentication successful
            logger.debug(
                "Admin authentication successful",
                path=request.path
            )

            metrics.increment("admin_auth_success", tags={"path": request.path})

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def metrics_middleware(app):
    """
    Middleware to collect request metrics.

    Tracks request counts, latencies, and status codes.

    Args:
        app: Flask application instance
    """

    @app.before_request
    def before_request_metrics():
        """Record request start time."""
        g.metrics_start_time = time.time()

    @app.after_request
    def after_request_metrics(response):
        """Record request metrics."""
        if not settings.enable_metrics:
            return response

        if hasattr(g, 'metrics_start_time'):
            duration_ms = (time.time() - g.metrics_start_time) * 1000

            # Track request count
            metrics.increment("http_requests_total", tags={
                "method": request.method,
                "path": request.path,
                "status": str(response.status_code)
            })

            # Track request latency
            metrics.timing("http_request_duration_ms", duration_ms, tags={
                "method": request.method,
                "path": request.path,
                "status": str(response.status_code)
            })

            # Track status codes
            status_class = f"{response.status_code // 100}xx"
            metrics.increment("http_responses_total", tags={
                "status_class": status_class,
                "path": request.path
            })

        return response


def error_handler_middleware(app):
    """
    Middleware to handle uncaught exceptions.

    Converts all exceptions to standardized error responses.

    Args:
        app: Flask application instance
    """

    from .errors import AppError

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        """Handle AppError exceptions."""
        logger.error(
            f"Application error: {error.message}",
            error_code=error.code,
            error_details=error.details,
            status_code=error.status_code
        )

        # Track error metrics
        metrics.increment("app_errors_total", tags={
            "error_code": error.code,
            "status_code": str(error.status_code)
        })

        return error_response(error)

    @app.errorhandler(404)
    def handle_404(error):
        """Handle 404 Not Found."""
        from .errors import NotFoundError

        error = NotFoundError(
            f"Endpoint not found: {request.path}",
            details={"path": request.path, "method": request.method}
        )

        return error_response(error)

    @app.errorhandler(500)
    def handle_500(error):
        """Handle 500 Internal Server Error."""
        logger.error(
            "Unhandled exception",
            exc_info=error,
            path=request.path
        )

        from .errors import AppError

        error = AppError(
            "An unexpected error occurred",
            details={"path": request.path}
        )

        metrics.increment("unhandled_exceptions_total", tags={
            "path": request.path
        })

        return error_response(error)

    @app.errorhandler(Exception)
    def handle_exception(error: Exception):
        """Handle all uncaught exceptions."""
        logger.exception(
            "Unhandled exception",
            exc_info=error,
            path=request.path,
            error_type=type(error).__name__
        )

        from .errors import AppError

        app_error = AppError(
            "An unexpected error occurred",
            details={
                "path": request.path,
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        )

        metrics.increment("unhandled_exceptions_total", tags={
            "path": request.path,
            "error_type": type(error).__name__
        })

        return error_response(app_error)


def setup_middleware(app):
    """
    Setup all middleware for the Flask application.

    Args:
        app: Flask application instance

    Usage:
        from api.middleware import setup_middleware

        app = Flask(__name__)
        setup_middleware(app)
    """
    # Order matters! Applied in reverse order (last registered = first executed)

    # 1. Error handling (outermost)
    error_handler_middleware(app)

    # 2. Metrics collection
    if settings.enable_metrics:
        metrics_middleware(app)

    # 3. Correlation ID (innermost, for all requests)
    correlation_id_middleware(app)

    logger.info("All middleware configured successfully")
