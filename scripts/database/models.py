"""
SQLAlchemy models for analytics database.

Defines tables for:
- Request logging and audit trail
- Analysis results and metrics
- Provider performance tracking
- Feature flags configuration
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class RequestLog(Base):
    """
    Log of all API requests for debugging and analytics.

    Tracks each request with correlation ID for end-to-end tracing.
    """
    __tablename__ = 'request_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    correlation_id = Column(String(50), unique=True, nullable=False, index=True)
    url = Column(Text, nullable=False)
    mode = Column(String(20), nullable=False)  # 'single' or 'consensus'
    providers = Column(Text)  # JSON array of provider names
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    status = Column(String(20), nullable=False)  # 'success', 'error', 'partial'
    duration_ms = Column(Integer)
    error_message = Column(Text)
    error_type = Column(String(100))

    # Relationship to analysis results
    analysis_results = relationship("AnalysisResult", back_populates="request", cascade="all, delete-orphan")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_request_timestamp', 'timestamp'),
        Index('idx_request_status', 'status'),
        Index('idx_request_mode', 'mode'),
    )

    def __repr__(self):
        return f"<RequestLog(id={self.id}, correlation_id='{self.correlation_id}', status='{self.status}')>"


class AnalysisResult(Base):
    """
    Individual LLM analysis results for each request.

    Tracks per-provider analysis outcomes for detailed metrics.
    """
    __tablename__ = 'analysis_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    correlation_id = Column(String(50), ForeignKey('request_log.correlation_id'), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    sentence_count = Column(Integer)
    model_name = Column(String(100))
    success = Column(Boolean, default=True, nullable=False)
    error_type = Column(String(100))
    error_message = Column(Text)
    latency_ms = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to request log
    request = relationship("RequestLog", back_populates="analysis_results")

    # Indexes
    __table_args__ = (
        Index('idx_analysis_provider', 'provider'),
        Index('idx_analysis_timestamp', 'timestamp'),
        Index('idx_analysis_success', 'success'),
    )

    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, provider='{self.provider}', success={self.success})>"


class ProviderMetric(Base):
    """
    Aggregated metrics for LLM providers.

    Stores hourly aggregated performance metrics for trend analysis.
    """
    __tablename__ = 'provider_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False, index=True)
    hour_bucket = Column(DateTime, nullable=False, index=True)  # Hourly aggregation
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    avg_latency_ms = Column(Float)
    error_types = Column(Text)  # JSON object of error type counts
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Unique constraint on provider + hour_bucket
    __table_args__ = (
        Index('idx_provider_metrics_unique', 'provider', 'hour_bucket', unique=True),
        Index('idx_provider_metrics_provider', 'provider'),
        Index('idx_provider_metrics_hour', 'hour_bucket'),
    )

    def __repr__(self):
        return f"<ProviderMetric(provider='{self.provider}', hour_bucket='{self.hour_bucket}', total={self.total_requests})>"


class FeatureFlag(Base):
    """
    Feature flag configuration.

    Allows enabling/disabling features without code changes.
    """
    __tablename__ = 'feature_flags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    flag_name = Column(String(100), unique=True, nullable=False, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    config = Column(Text)  # JSON configuration
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<FeatureFlag(flag_name='{self.flag_name}', enabled={self.enabled})>"
