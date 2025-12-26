"""
Centralized logging configuration with structured JSON logging.

Provides consistent logging across all components with:
- JSON structured output
- Correlation ID tracking
- Component-based loggers
- Configurable log levels
- Log rotation
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional
from pythonjsonlogger import jsonlogger

from .context import get_correlation_id


class CorrelationIdFilter(logging.Filter):
    """
    Logging filter that adds correlation ID to log records.

    Automatically injects the current correlation ID from context
    into all log records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation_id to the log record."""
        correlation_id = get_correlation_id()
        record.correlation_id = correlation_id if correlation_id else 'none'
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for structured logging.

    Formats log records as JSON with consistent field names and
    additional metadata.
    """

    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to JSON log output."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        if not log_record.get('timestamp'):
            log_record['timestamp'] = self.formatTime(record, self.datefmt)

        # Add level name
        log_record['level'] = record.levelname

        # Add logger name as component
        log_record['component'] = record.name

        # Ensure correlation_id is present
        if not log_record.get('correlation_id'):
            log_record['correlation_id'] = getattr(record, 'correlation_id', 'none')

        # Include token/cost fields if present on the record
        for field_name in (
            'prompt_tokens',
            'completion_tokens',
            'total_tokens',
            'cost_usd',
            'token_estimated'
        ):
            if field_name not in log_record and hasattr(record, field_name):
                log_record[field_name] = getattr(record, field_name)


def setup_logging(
    log_level: str = 'INFO',
    log_format: str = 'json',
    log_dir: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = True
) -> None:
    """
    Setup centralized logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ('json' or 'text')
        log_dir: Directory for log files (default: data/logs)
        enable_console: Whether to log to console
        enable_file: Whether to log to files

    Example:
        setup_logging(log_level='DEBUG', log_format='json')
    """
    # Get log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create log directory
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'data', 'logs')
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add correlation ID filter
    correlation_filter = CorrelationIdFilter()

    # Setup formatters
    if log_format == 'json':
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(component)s %(correlation_id)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S.%fZ'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s [%(correlation_id)s] %(levelname)-8s [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(correlation_filter)
        root_logger.addHandler(console_handler)

    # File handlers (separate files for different components)
    if enable_file:
        # Main application log (all messages)
        main_file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, 'app.log'),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=7  # Keep 7 days of logs
        )
        main_file_handler.setLevel(numeric_level)
        main_file_handler.setFormatter(formatter)
        main_file_handler.addFilter(correlation_filter)
        root_logger.addHandler(main_file_handler)

        # Error log (errors only)
        error_file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, 'error.log'),
            maxBytes=10 * 1024 * 1024,
            backupCount=7
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(formatter)
        error_file_handler.addFilter(correlation_filter)
        root_logger.addHandler(error_file_handler)

    # Set logging levels for noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging initialized",
        extra={
            'log_level': log_level,
            'log_format': log_format,
            'log_dir': log_dir,
            'console_enabled': enable_console,
            'file_enabled': enable_file
        }
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a component.

    Args:
        name: Logger name (typically __name__ or component name)

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Processing started", extra={'url': article_url})
    """
    return logging.getLogger(name)
