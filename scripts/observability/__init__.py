"""
Observability module for monitoring, logging, and metrics collection.

This module provides:
- Structured logging with correlation IDs
- Request context management
- Metrics collection and aggregation
"""

from .logging_config import setup_logging, get_logger
from .context import request_context, get_correlation_id, set_correlation_id
from .metrics import metrics

__all__ = [
    'setup_logging',
    'get_logger',
    'request_context',
    'get_correlation_id',
    'set_correlation_id',
    'metrics',
]
