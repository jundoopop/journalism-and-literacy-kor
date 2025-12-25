"""
Database module for analytics and persistence.

Provides:
- SQLAlchemy models for request logs, metrics, and configuration
- Repository pattern for data access
- Database initialization and migration support
"""

from .models import RequestLog, AnalysisResult, ProviderMetric, FeatureFlag, Base
from .repository import AnalyticsRepository
from .init_db import init_database, get_session, get_engine, session_scope, check_database_health

__all__ = [
    'RequestLog',
    'AnalysisResult',
    'ProviderMetric',
    'FeatureFlag',
    'Base',
    'AnalyticsRepository',
    'init_database',
    'get_session',
    'get_engine',
    'session_scope',
    'check_database_health',
]
