"""
Repository pattern for database access.

Provides a clean interface for querying and persisting analytics data.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import json

from .models import RequestLog, AnalysisResult, ProviderMetric, FeatureFlag
from observability import get_logger

logger = get_logger(__name__)


class AnalyticsRepository:
    """
    Repository for analytics database operations.

    Provides methods for logging requests, storing results,
    and querying metrics.
    """

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def log_request(
        self,
        correlation_id: str,
        url: str,
        mode: str,
        providers: List[str],
        status: str,
        duration_ms: int,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None
    ) -> RequestLog:
        """
        Log an API request.

        Args:
            correlation_id: Unique request ID
            url: Article URL
            mode: Analysis mode ('single' or 'consensus')
            providers: List of provider names
            status: Request status ('success', 'error', 'partial')
            duration_ms: Request duration in milliseconds
            error_message: Optional error message
            error_type: Optional error type

        Returns:
            Created RequestLog instance
        """
        request_log = RequestLog(
            correlation_id=correlation_id,
            url=url,
            mode=mode,
            providers=json.dumps(providers),
            status=status,
            duration_ms=duration_ms,
            error_message=error_message,
            error_type=error_type
        )

        self.session.add(request_log)
        self.session.commit()

        logger.debug(f"Logged request: {correlation_id} ({status})")

        return request_log

    def log_analysis_result(
        self,
        correlation_id: str,
        provider: str,
        sentence_count: int,
        model_name: Optional[str] = None,
        success: bool = True,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> AnalysisResult:
        """
        Log an LLM analysis result.

        Args:
            correlation_id: Request correlation ID
            provider: LLM provider name
            sentence_count: Number of sentences selected
            model_name: Model name used
            success: Whether analysis succeeded
            error_type: Optional error type
            error_message: Optional error message
            latency_ms: Provider latency in milliseconds

        Returns:
            Created AnalysisResult instance
        """
        analysis_result = AnalysisResult(
            correlation_id=correlation_id,
            provider=provider,
            sentence_count=sentence_count,
            model_name=model_name,
            success=success,
            error_type=error_type,
            error_message=error_message,
            latency_ms=latency_ms
        )

        self.session.add(analysis_result)
        self.session.commit()

        logger.debug(f"Logged analysis result: {provider} ({success})")

        return analysis_result

    def get_request_history(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        mode: Optional[str] = None
    ) -> List[RequestLog]:
        """
        Get recent request history.

        Args:
            limit: Maximum number of results
            offset: Pagination offset
            status: Optional filter by status
            mode: Optional filter by mode

        Returns:
            List of RequestLog instances
        """
        query = self.session.query(RequestLog).order_by(desc(RequestLog.timestamp))

        if status:
            query = query.filter(RequestLog.status == status)
        if mode:
            query = query.filter(RequestLog.mode == mode)

        return query.limit(limit).offset(offset).all()

    def get_request_by_correlation_id(self, correlation_id: str) -> Optional[RequestLog]:
        """
        Get request by correlation ID.

        Args:
            correlation_id: Request correlation ID

        Returns:
            RequestLog instance or None
        """
        return self.session.query(RequestLog).filter(
            RequestLog.correlation_id == correlation_id
        ).first()

    def get_request_stats(
        self,
        since: Optional[datetime] = None,
        mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get request statistics.

        Args:
            since: Optional datetime to filter from
            mode: Optional mode filter ('single' or 'consensus')

        Returns:
            Dictionary with request statistics
        """
        query = self.session.query(RequestLog)

        if since:
            query = query.filter(RequestLog.timestamp >= since)
        if mode:
            query = query.filter(RequestLog.mode == mode)

        requests = query.all()

        if not requests:
            return {}

        total = len(requests)
        successful = sum(1 for r in requests if r.status == 'success')
        failed = sum(1 for r in requests if r.status == 'error')
        partial = sum(1 for r in requests if r.status == 'partial')

        durations = [r.duration_ms for r in requests if r.duration_ms is not None]

        if durations:
            durations_sorted = sorted(durations)
            avg_duration = sum(durations) / len(durations)
            p50_idx = int(len(durations_sorted) * 0.5)
            p95_idx = int(len(durations_sorted) * 0.95)
            p99_idx = int(len(durations_sorted) * 0.99)

            return {
                'total_requests': total,
                'successful_requests': successful,
                'failed_requests': failed,
                'partial_requests': partial,
                'avg_duration_ms': avg_duration,
                'p50_duration_ms': durations_sorted[p50_idx],
                'p95_duration_ms': durations_sorted[p95_idx],
                'p99_duration_ms': durations_sorted[p99_idx]
            }
        else:
            return {
                'total_requests': total,
                'successful_requests': successful,
                'failed_requests': failed,
                'partial_requests': partial
            }

    def get_analyses_by_correlation_id(self, correlation_id: str) -> List[AnalysisResult]:
        """
        Get all analysis results for a correlation ID.

        Args:
            correlation_id: Request correlation ID

        Returns:
            List of AnalysisResult instances
        """
        return self.session.query(AnalysisResult).filter(
            AnalysisResult.correlation_id == correlation_id
        ).all()

    def get_error_breakdown(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get error breakdown by type.

        Args:
            since: Optional datetime to filter from

        Returns:
            List of dictionaries with error statistics
        """
        query = self.session.query(RequestLog).filter(
            RequestLog.status == 'error'
        )

        if since:
            query = query.filter(RequestLog.timestamp >= since)

        error_requests = query.all()

        # Group by error type
        error_types: Dict[str, Dict[str, Any]] = {}

        for req in error_requests:
            error_type = req.error_type or 'Unknown'

            if error_type not in error_types:
                error_types[error_type] = {
                    'error_type': error_type,
                    'count': 0,
                    'sample_message': req.error_message
                }

            error_types[error_type]['count'] += 1

        return list(error_types.values())

    def get_provider_stats(
        self,
        provider: Optional[str] = None,
        since: Optional[datetime] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get provider statistics.

        Args:
            provider: Optional provider name filter
            since: Optional datetime to filter from
            hours: Number of hours to look back if since not specified

        Returns:
            List of dictionaries with provider statistics
        """
        if not since:
            since = datetime.utcnow() - timedelta(hours=hours)

        query = self.session.query(AnalysisResult).filter(
            AnalysisResult.timestamp >= since
        )

        if provider:
            query = query.filter(AnalysisResult.provider == provider)

        results = query.all()

        if not results:
            return []

        # Group by provider
        provider_stats: Dict[str, Dict[str, Any]] = {}

        for result in results:
            prov = result.provider

            if prov not in provider_stats:
                provider_stats[prov] = {
                    'provider': prov,
                    'total_analyses': 0,
                    'successful_analyses': 0,
                    'failed_analyses': 0,
                    'total_latency': 0,
                    'total_sentences': 0,
                    'latency_count': 0
                }

            stats = provider_stats[prov]
            stats['total_analyses'] += 1

            if result.success:
                stats['successful_analyses'] += 1
            else:
                stats['failed_analyses'] += 1

            if result.latency_ms is not None:
                stats['total_latency'] += result.latency_ms
                stats['latency_count'] += 1

            if result.sentence_count is not None:
                stats['total_sentences'] += result.sentence_count

        # Calculate averages
        for prov, stats in provider_stats.items():
            if stats['latency_count'] > 0:
                stats['avg_latency_ms'] = stats['total_latency'] / stats['latency_count']
            else:
                stats['avg_latency_ms'] = 0

            if stats['total_analyses'] > 0:
                stats['avg_sentences'] = stats['total_sentences'] / stats['total_analyses']
            else:
                stats['avg_sentences'] = 0

            # Remove intermediate fields
            del stats['total_latency']
            del stats['total_sentences']
            del stats['latency_count']

        return list(provider_stats.values())

    def update_provider_metrics(
        self,
        provider: str,
        hour_bucket: datetime,
        total_requests: int,
        successful_requests: int,
        failed_requests: int,
        avg_latency_ms: float,
        error_types: Dict[str, int]
    ) -> ProviderMetric:
        """
        Update or create provider metrics for an hour bucket.

        Args:
            provider: Provider name
            hour_bucket: Hour bucket (minute/second should be 0)
            total_requests: Total requests in this hour
            successful_requests: Successful requests
            failed_requests: Failed requests
            avg_latency_ms: Average latency
            error_types: Dictionary of error types and counts

        Returns:
            ProviderMetric instance
        """
        # Try to find existing metric
        metric = self.session.query(ProviderMetric).filter(
            ProviderMetric.provider == provider,
            ProviderMetric.hour_bucket == hour_bucket
        ).first()

        if metric:
            # Update existing
            metric.total_requests = total_requests
            metric.successful_requests = successful_requests
            metric.failed_requests = failed_requests
            metric.avg_latency_ms = avg_latency_ms
            metric.error_types = json.dumps(error_types)
            metric.updated_at = datetime.utcnow()
        else:
            # Create new
            metric = ProviderMetric(
                provider=provider,
                hour_bucket=hour_bucket,
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                avg_latency_ms=avg_latency_ms,
                error_types=json.dumps(error_types)
            )
            self.session.add(metric)

        self.session.commit()

        return metric

    def get_feature_flag(self, flag_name: str) -> Optional[FeatureFlag]:
        """
        Get a feature flag by name.

        Args:
            flag_name: Feature flag name

        Returns:
            FeatureFlag instance or None
        """
        return self.session.query(FeatureFlag).filter(
            FeatureFlag.flag_name == flag_name
        ).first()

    def get_all_feature_flags(self) -> List[FeatureFlag]:
        """
        Get all feature flags.

        Returns:
            List of FeatureFlag instances
        """
        return self.session.query(FeatureFlag).all()

    def set_feature_flag(
        self,
        flag_name: str,
        enabled: bool,
        config: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ) -> FeatureFlag:
        """
        Set a feature flag value.

        Args:
            flag_name: Feature flag name
            enabled: Whether flag is enabled
            config: Optional JSON configuration
            description: Optional description

        Returns:
            FeatureFlag instance
        """
        flag = self.get_feature_flag(flag_name)

        if flag:
            flag.enabled = enabled
            if config is not None:
                flag.config = json.dumps(config)
            if description is not None:
                flag.description = description
            flag.updated_at = datetime.utcnow()
        else:
            flag = FeatureFlag(
                flag_name=flag_name,
                enabled=enabled,
                config=json.dumps(config) if config else None,
                description=description
            )
            self.session.add(flag)

        self.session.commit()

        logger.info(f"Feature flag '{flag_name}' set to {enabled}")

        return flag

    def cleanup_old_records(self, days: int = 30):
        """
        Clean up old records to prevent database growth.

        Args:
            days: Keep records from last N days
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Delete old request logs (cascade will delete analysis results)
        deleted_requests = self.session.query(RequestLog).filter(
            RequestLog.timestamp < cutoff
        ).delete()

        # Delete old provider metrics
        deleted_metrics = self.session.query(ProviderMetric).filter(
            ProviderMetric.hour_bucket < cutoff
        ).delete()

        self.session.commit()

        logger.info(f"Cleaned up {deleted_requests} old requests and {deleted_metrics} old metrics")

        return {
            'deleted_requests': deleted_requests,
            'deleted_metrics': deleted_metrics
        }
