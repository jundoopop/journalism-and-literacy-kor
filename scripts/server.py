"""
Flask API Server for News Literacy Highlighter
Refactored to use service layer, observability, and structured architecture

Receives article URLs → Crawls content → Analyzes with LLM(s) → Returns highlight sentences
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import time

# New architecture imports
from config import settings
from observability import setup_logging, get_logger, request_context, get_correlation_id, metrics
from services import CrawlerService, AnalysisService, CacheService, HealthService, FeatureFlagsService
from api.middleware import setup_middleware, admin_auth_middleware
from api.errors import (
    ValidationError,
    CrawlerError as APICrawlerError,
    LLMError as APILLMError,
    error_response,
    make_success_response
)
from database import init_database, get_session, session_scope, AnalyticsRepository, check_database_health

# Setup logging first
setup_logging(
    log_level=settings.observability.log_level,
    log_format=settings.observability.log_format,
    log_dir=settings.observability.log_dir
)

logger = get_logger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Setup all middleware (correlation ID, metrics, error handling)
setup_middleware(app)

# Initialize services
cache_service = CacheService()
crawler_service = CrawlerService()
analysis_service = AnalysisService(cache_service=cache_service)
health_service = HealthService(cache_service=cache_service)
feature_flags_service = FeatureFlagsService()

# Initialize database
try:
    init_database()
    logger.info("Database initialized successfully")

    # Create default feature flags
    feature_flags_service.create_default_flags()
    logger.info("Feature flags initialized")
except Exception as e:
    logger.error(f"Database initialization failed: {e}")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def log_request_to_database(
    url: str,
    mode: str,
    providers: list,
    status: str,
    duration_ms: int,
    error_message: str = None
):
    """Log request to analytics database."""
    try:
        with session_scope() as session:
            repo = AnalyticsRepository(session)
            repo.log_request(
                correlation_id=get_correlation_id() or "unknown",
                url=url,
                mode=mode,
                providers=providers,
                status=status,
                duration_ms=duration_ms,
                error_message=error_message,
                error_type=type(error_message).__name__ if error_message else None
            )
    except Exception as e:
        logger.error(f"Failed to log request to database: {e}")


def log_analysis_to_database(provider: str, sentence_count: int, latency_ms: int, success: bool = True):
    """Log analysis result to database."""
    try:
        with session_scope() as session:
            repo = AnalyticsRepository(session)
            repo.log_analysis_result(
                correlation_id=get_correlation_id() or "unknown",
                provider=provider,
                sentence_count=sentence_count,
                latency_ms=latency_ms,
                success=success
            )
    except Exception as e:
        logger.error(f"Failed to log analysis to database: {e}")


# ============================================================================
# HEALTH & TEST ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """
    Enhanced health check endpoint with component status.

    Returns:
        JSON response with detailed system health
    """
    system_health = health_service.get_system_health()
    return jsonify(system_health)


@app.route('/test', methods=['GET'])
def test():
    """Simple test endpoint."""
    return jsonify({
        "message": "Flask server is running with new architecture!",
        "version": "2.0.0",
        "correlation_id": get_correlation_id()
    })


# ============================================================================
# ANALYSIS ENDPOINTS
# ============================================================================

@app.route('/analyze', methods=['POST'])
def analyze_article_endpoint():
    """
    Analyze article with single LLM (Gemini by default).

    Request Body:
        {
            "url": "https://www.chosun.com/..."
        }

    Response (Success):
        {
            "success": true,
            "correlation_id": "req_abc123",
            "url": "...",
            "headline": "...",
            "sentences": [
                {
                    "text": "Sentence text",
                    "reason": "Reason for selection",
                    "consensus_level": "medium"
                }
            ],
            "count": 5
        }
    """
    start_time = time.time()
    data = request.get_json()

    # Validate request
    if not data or 'url' not in data:
        error = ValidationError("URL field is required in request body")
        return error_response(error)

    url = data.get('url')
    if not isinstance(url, str) or not url.strip():
        error = ValidationError("URL must be a non-empty string")
        return error_response(error)

    logger.info("Single LLM analysis request received", url=url)

    try:
        # Step 1: Crawl article
        logger.info("[1/3] Crawling article")
        article_data = crawler_service.crawl_article(url)

        # Step 2: Analyze with single LLM (with caching)
        logger.info("[2/3] Analyzing with Gemini")
        analysis_result = analysis_service.analyze_single(
            article_text=article_data.body_text,
            provider='gemini',
            url=url,
            use_cache=settings.enable_cache
        )

        # Log to database
        log_analysis_to_database(
            provider='gemini',
            sentence_count=len(analysis_result.sentences),
            latency_ms=analysis_result.duration_ms,
            success=True
        )

        # Step 3: Format response
        logger.info("[3/3] Formatting response")
        sentences_with_metadata = [
            {
                "text": sentence,
                "reason": reason,
                "consensus_level": "medium"  # Single mode uses medium by default
            }
            for sentence, reason in analysis_result.sentences.items()
        ]

        duration_ms = int((time.time() - start_time) * 1000)

        # Log request success
        log_request_to_database(
            url=url,
            mode='single',
            providers=['gemini'],
            status='success',
            duration_ms=duration_ms
        )

        return make_success_response({
            "url": url,
            "headline": article_data.headline,
            "sentences": sentences_with_metadata,
            "count": len(sentences_with_metadata)
        })

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)

        # Log request failure
        log_request_to_database(
            url=url,
            mode='single',
            providers=['gemini'],
            status='error',
            duration_ms=duration_ms,
            error_message=str(e)
        )

        # Convert to appropriate error type
        if 'crawler' in str(e).lower() or 'crawl' in str(e).lower():
            error = APICrawlerError(str(e), details={'url': url})
        else:
            error = APILLMError('gemini', str(e))

        return error_response(error)


@app.route('/analyze_consensus', methods=['POST'])
def analyze_consensus_endpoint():
    """
    Analyze article with multiple LLM providers for consensus.

    Request Body:
        {
            "url": "https://www.chosun.com/...",
            "providers": ["gemini", "mistral"]  # optional
        }

    Response (Success):
        {
            "success": true,
            "correlation_id": "req_abc123",
            "url": "...",
            "headline": "...",
            "total_providers": 2,
            "successful_providers": ["gemini", "mistral"],
            "sentences": [
                {
                    "text": "sentence text",
                    "consensus_score": 2,
                    "consensus_level": "high",
                    "selected_by": ["gemini", "mistral"],
                    "reasons": {
                        "gemini": "reason...",
                        "mistral": "reason..."
                    }
                }
            ],
            "count": 5
        }
    """
    start_time = time.time()
    data = request.get_json()

    # Validate request
    if not data or 'url' not in data:
        error = ValidationError("URL field is required in request body")
        return error_response(error)

    url = data.get('url')
    providers = data.get('providers', settings.consensus_providers)

    logger.info("Consensus analysis request received", url=url, providers=providers)

    try:
        # Step 1: Crawl article
        logger.info("[1/3] Crawling article")
        article_data = crawler_service.crawl_article(url)

        # Step 2: Analyze with consensus (with caching)
        logger.info(f"[2/3] Analyzing with {len(providers)} providers")
        consensus_result = analysis_service.analyze_consensus(
            article_text=article_data.body_text,
            providers=providers,
            url=url,
            use_cache=settings.enable_cache
        )

        # Log each provider's result
        for provider in consensus_result.successful_providers:
            log_analysis_to_database(
                provider=provider,
                sentence_count=len(consensus_result.sentences),
                latency_ms=consensus_result.total_duration_ms // len(consensus_result.successful_providers),
                success=True
            )

        # Step 3: Format response
        logger.info("[3/3] Formatting response")
        duration_ms = int((time.time() - start_time) * 1000)

        # Determine status
        status = 'success' if len(consensus_result.failed_providers) == 0 else 'partial'

        # Log request
        log_request_to_database(
            url=url,
            mode='consensus',
            providers=providers,
            status=status,
            duration_ms=duration_ms
        )

        return make_success_response({
            "url": url,
            "headline": article_data.headline,
            "total_providers": consensus_result.total_providers,
            "successful_providers": consensus_result.successful_providers,
            "failed_providers": consensus_result.failed_providers,
            "sentences": consensus_result.sentences,
            "count": len(consensus_result.sentences)
        })

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)

        # Log request failure
        log_request_to_database(
            url=url,
            mode='consensus',
            providers=providers,
            status='error',
            duration_ms=duration_ms,
            error_message=str(e)
        )

        # Convert to appropriate error type
        if 'crawler' in str(e).lower() or 'crawl' in str(e).lower():
            error = APICrawlerError(str(e), details={'url': url})
        else:
            error = APILLMError('consensus', str(e))

        return error_response(error)


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.route('/admin/metrics', methods=['GET'])
@admin_auth_middleware()
def get_metrics():
    """
    Get system metrics (admin only).

    Requires X-Admin-Token header.
    """
    metrics_summary = metrics.get_summary()

    return make_success_response({
        "metrics": metrics_summary
    })


@app.route('/admin/health/detailed', methods=['GET'])
@admin_auth_middleware()
def get_detailed_health():
    """
    Get detailed health check (admin only).

    Requires X-Admin-Token header.
    """
    # Get comprehensive system health (includes LLM providers)
    system_health = health_service.get_system_health()
    cache_stats = cache_service.get_stats()

    # Add cache stats and metrics to the response
    system_health['cache_stats'] = {
        "hits": cache_stats.hits,
        "misses": cache_stats.misses,
        "hit_rate": cache_stats.hit_rate,
        "total_requests": cache_stats.total_requests,
        "redis_connected": cache_stats.redis_connected
    }
    system_health['metrics'] = metrics.get_summary()

    return make_success_response(system_health)


@app.route('/admin/cache/stats', methods=['GET'])
@admin_auth_middleware()
def get_cache_stats():
    """
    Get cache statistics (admin only).

    Requires X-Admin-Token header.
    """
    stats = cache_service.get_stats()

    return make_success_response({
        "hits": stats.hits,
        "misses": stats.misses,
        "total_requests": stats.total_requests,
        "hit_rate": stats.hit_rate,
        "redis_connected": stats.redis_connected,
        "redis_info": stats.redis_info
    })


@app.route('/admin/cache/clear', methods=['POST'])
@admin_auth_middleware()
def clear_cache():
    """
    Clear cache (admin only).

    Query Parameters:
        pattern: Optional pattern to match (e.g., "article:*")

    Requires X-Admin-Token header.
    """
    pattern = request.args.get('pattern')

    if pattern == '*' or not pattern:
        # Clear all
        success = cache_service.clear_all()
        message = "All cache cleared" if success else "Cache clear failed"
    else:
        # Pattern-based clearing not implemented yet
        return make_success_response({
            "message": "Pattern-based clearing not yet implemented",
            "use_pattern": "*"
        })

    return make_success_response({
        "message": message,
        "success": success
    })


@app.route('/admin/feature_flags', methods=['GET'])
@admin_auth_middleware()
def get_feature_flags():
    """
    Get all feature flags (admin only).

    Requires X-Admin-Token header.
    """
    all_flags = feature_flags_service.get_all_flags()

    return make_success_response({
        "flags": all_flags,
        "total": len(all_flags),
        "enabled": len(feature_flags_service.get_enabled_flags())
    })


@app.route('/admin/feature_flags/<flag_name>', methods=['GET'])
@admin_auth_middleware()
def get_feature_flag(flag_name: str):
    """
    Get specific feature flag (admin only).

    Requires X-Admin-Token header.
    """
    flag = feature_flags_service.get_flag(flag_name)

    if not flag:
        error = ValidationError(f"Feature flag '{flag_name}' not found")
        return error_response(error)

    return make_success_response({
        "flag_name": flag_name,
        **flag
    })


@app.route('/admin/feature_flags', methods=['POST'])
@admin_auth_middleware()
def set_feature_flag():
    """
    Set feature flag value (admin only).

    Request Body:
        {
            "flag_name": "cache_enabled",
            "enabled": true,
            "config": {"key": "value"},  // optional
            "description": "..."         // optional
        }

    Requires X-Admin-Token header.
    """
    data = request.get_json()

    if not data or 'flag_name' not in data or 'enabled' not in data:
        error = ValidationError("flag_name and enabled fields are required")
        return error_response(error)

    flag_name = data.get('flag_name')
    enabled = data.get('enabled')
    config = data.get('config')
    description = data.get('description')

    success = feature_flags_service.set_flag(
        flag_name=flag_name,
        enabled=enabled,
        config=config,
        description=description
    )

    if success:
        return make_success_response({
            "message": f"Feature flag '{flag_name}' updated",
            "flag_name": flag_name,
            "enabled": enabled
        })
    else:
        error = APILLMError('system', f"Failed to update feature flag '{flag_name}'")
        return error_response(error)


@app.route('/admin/feature_flags/<flag_name>', methods=['DELETE'])
@admin_auth_middleware()
def disable_feature_flag(flag_name: str):
    """
    Disable feature flag (admin only).

    Requires X-Admin-Token header.
    """
    # Check if flag exists
    flag = feature_flags_service.get_flag(flag_name)

    if not flag:
        error = ValidationError(f"Feature flag '{flag_name}' not found")
        return error_response(error)

    # Disable the flag
    success = feature_flags_service.set_flag(flag_name, enabled=False)

    if success:
        return make_success_response({
            "message": f"Feature flag '{flag_name}' disabled",
            "flag_name": flag_name
        })
    else:
        error = APILLMError('system', f"Failed to disable feature flag '{flag_name}'")
        return error_response(error)


@app.route('/admin/feature_flags/reload', methods=['POST'])
@admin_auth_middleware()
def reload_feature_flags():
    """
    Force reload feature flags from database (admin only).

    Requires X-Admin-Token header.
    """
    feature_flags_service.reload()

    return make_success_response({
        "message": "Feature flags reloaded",
        "total": len(feature_flags_service.get_all_flags())
    })


# ============================================================================
# STARTUP
# ============================================================================

def print_startup_banner():
    """Print server startup information."""
    banner = f"""
{'='*70}
News Literacy Highlighter - API Server v2.0
{'='*70}
✓ Server: http://{settings.flask_host}:{settings.flask_port}
✓ Health: http://localhost:{settings.flask_port}/health
✓ Test: http://localhost:{settings.flask_port}/test

Endpoints:
  POST /analyze                - Single LLM analysis
  POST /analyze_consensus      - Multi-LLM consensus analysis

Admin Endpoints (requires X-Admin-Token):
  GET  /admin/metrics          - System metrics
  GET  /admin/health/detailed  - Detailed health check

Configuration:
  Environment: {'Development' if settings.flask_debug else 'Production'}
  Log Level: {settings.observability.log_level}
  Log Format: {settings.observability.log_format}
  Database: {settings.database.path}
  Cache Enabled: {settings.enable_cache}
  Metrics Enabled: {settings.enable_metrics}
  Consensus Providers: {', '.join(settings.consensus_providers)}

{'='*70}
"""
    print(banner)


if __name__ == '__main__':
    print_startup_banner()

    # Run Flask server
    app.run(
        host=settings.flask_host,
        port=settings.flask_port,
        debug=settings.flask_debug
    )
