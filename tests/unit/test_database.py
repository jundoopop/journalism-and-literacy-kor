"""Database contracts: real SQLite sessions, models and repository operations."""
import json
from datetime import datetime
import pytest
from database import (RequestLog, AnalysisResult, ProviderMetric, FeatureFlag,
                      AnalyticsRepository, init_database, session_scope)


def request_record(correlation_id):
    return RequestLog(correlation_id=correlation_id, url='https://www.hani.co.kr/a',
                      mode='consensus', providers='["gemini"]', status='success', duration_ms=100)


@pytest.fixture(autouse=True)
def schema():
    init_database()


class TestDatabaseModels:
    def test_request_log_creation(self):
        with session_scope() as session:
            session.add(request_record('request'))
        with session_scope() as session:
            record = session.query(RequestLog).filter_by(correlation_id='request').one()
            assert record.mode == 'consensus'
            assert record.duration_ms == 100

    def test_analysis_result_creation(self):
        with session_scope() as session:
            session.add(request_record('analysis'))
            session.add(AnalysisResult(correlation_id='analysis', provider='gemini',
                                       sentence_count=3, latency_ms=2000, success=True))
        with session_scope() as session:
            result = session.query(AnalysisResult).filter_by(correlation_id='analysis').one()
            assert result.sentence_count == 3
            assert result.request.url == 'https://www.hani.co.kr/a'

    def test_provider_metric_creation(self):
        with session_scope() as session:
            session.add(ProviderMetric(provider='mistral', hour_bucket=datetime.utcnow(),
                                       total_requests=10, successful_requests=9, failed_requests=1,
                                       avg_latency_ms=1234.5, error_types='{"timeout": 1}'))
        with session_scope() as session:
            metric = session.query(ProviderMetric).filter_by(provider='mistral').one()
            assert metric.total_requests == 10
            assert metric.avg_latency_ms == 1234.5

    def test_feature_flag_creation(self):
        with session_scope() as session:
            session.add(FeatureFlag(flag_name='test_feature', enabled=True, config='{"timeout":30}'))
        with session_scope() as session:
            flag = session.query(FeatureFlag).filter_by(flag_name='test_feature').one()
            assert flag.enabled
            assert json.loads(flag.config)['timeout'] == 30

    def test_feature_flag_update(self):
        with session_scope() as session:
            repo = AnalyticsRepository(session)
            repo.set_feature_flag('update_test', True, config={'version': 1})
            old = repo.get_feature_flag('update_test').updated_at
            repo.set_feature_flag('update_test', False, config={'version': 2})
            flag = repo.get_feature_flag('update_test')
            assert not flag.enabled
            assert json.loads(flag.config)['version'] == 2
            assert flag.updated_at >= old


class TestAnalyticsRepository:
    @pytest.fixture(autouse=True)
    def setup(self):
        with session_scope() as session:
            self.repo = AnalyticsRepository(session)
            yield

    def log_request(self, key):
        return self.repo.log_request(key, 'https://www.hani.co.kr/a', 'consensus', ['gemini'], 'success', 100)

    def test_repository_initialization(self):
        assert self.repo.session is not None

    def test_log_request(self):
        self.log_request('req')
        assert self.repo.get_request_by_correlation_id('req').url == 'https://www.hani.co.kr/a'

    def test_log_analysis_result(self):
        self.log_request('analysis')
        self.repo.log_analysis_result('analysis', 'gemini', 3, latency_ms=1500)
        result = self.repo.get_analyses_by_correlation_id('analysis')[0]
        assert result.success and result.sentence_count == 3

    def test_log_provider_metric(self):
        hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        self.repo.update_provider_metrics('mistral', hour, 10, 9, 1, 100, {'timeout': 1})
        self.repo.update_provider_metrics('mistral', hour, 20, 18, 2, 110, {'timeout': 2})
        rows = self.repo.session.query(ProviderMetric).filter_by(provider='mistral').all()
        assert len(rows) == 1
        assert rows[0].total_requests == 20

    def test_get_recent_requests(self):
        for i in range(5):
            self.log_request(f'req-{i}')
        assert len(self.repo.get_request_history(limit=3)) == 3

    def test_get_provider_metrics(self):
        for i in range(3):
            self.log_request(f'metric-{i}')
            self.repo.log_analysis_result(f'metric-{i}', 'gemini', 2, latency_ms=100 + i * 100)
        stats = self.repo.get_provider_stats(provider='gemini')
        assert len(stats) == 1
        assert stats[0]['total_analyses'] == 3
        assert stats[0]['avg_latency_ms'] == 200

    def test_get_analysis_results_by_url(self):
        self.log_request('url-analysis')
        for name in ('gemini', 'mistral'):
            self.repo.log_analysis_result('url-analysis', name, 2)
        request = self.repo.session.query(RequestLog).filter_by(url='https://www.hani.co.kr/a').one()
        assert {r.provider for r in request.analysis_results} == {'gemini', 'mistral'}

    def test_get_failed_analyses(self):
        self.log_request('mixed')
        self.repo.log_analysis_result('mixed', 'gemini', 2)
        self.repo.log_analysis_result('mixed', 'mistral', 0, success=False, error_type='timeout')
        failed = self.repo.session.query(AnalysisResult).filter_by(success=False).all()
        assert len(failed) == 1 and failed[0].provider == 'mistral'

    def test_session_scope_commit(self):
        with session_scope() as session:
            session.add(request_record('commit'))
        assert self.repo.get_request_by_correlation_id('commit') is not None

    def test_session_scope_rollback_on_error(self):
        with pytest.raises(ValueError):
            with session_scope() as session:
                session.add(request_record('rollback'))
                session.flush()
                raise ValueError('rollback')
        assert self.repo.get_request_by_correlation_id('rollback') is None
