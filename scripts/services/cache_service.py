"""
Cache service for Redis-based caching.

Provides a clean interface for caching LLM analysis results
with automatic fallback if Redis is unavailable.
"""

import hashlib
import json
from typing import Optional, Any, Dict, List
from dataclasses import dataclass
import redis

from .base_service import BaseService, ServiceError
from config import settings


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int
    misses: int
    total_requests: int
    hit_rate: float
    redis_connected: bool
    redis_info: Optional[Dict[str, Any]] = None


class CacheError(ServiceError):
    """Exception raised when cache operations fail."""
    pass


class CacheService(BaseService):
    """
    Service for caching LLM analysis results.

    Uses Redis for distributed caching with automatic fallback
    to no-cache mode if Redis is unavailable.

    Cache Key Format:
        article:{url_hash}:providers:{sorted_providers}:v1

    Example:
        cache = CacheService()

        # Store analysis result
        cache.set_analysis_result(url, ['gemini'], analysis_data)

        # Retrieve cached result
        result = cache.get_analysis_result(url, ['gemini'])
    """

    def __init__(self):
        super().__init__("CacheService")
        self._redis_client: Optional[redis.Redis] = None
        self._enabled = settings.cache.enabled
        self._stats = {"hits": 0, "misses": 0}

        if self._enabled:
            self._connect_redis()

    def _connect_redis(self):
        """Connect to Redis with error handling."""
        try:
            self._redis_client = redis.Redis(
                host=settings.cache.redis_host,
                port=settings.cache.redis_port,
                db=settings.cache.redis_db,
                password=settings.cache.redis_password,
                decode_responses=True,  # Automatically decode bytes to strings
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )

            # Test connection
            self._redis_client.ping()

            self.log_info(
                "Redis connected successfully",
                host=settings.cache.redis_host,
                port=settings.cache.redis_port,
                db=settings.cache.redis_db
            )

        except Exception as e:
            self.log_warning(
                "Redis connection failed, caching disabled",
                error=str(e),
                host=settings.cache.redis_host
            )
            self._redis_client = None
            self._enabled = False

    def _generate_cache_key(self, url: str, providers: List[str]) -> str:
        """
        Generate a cache key for an article analysis.

        Args:
            url: Article URL
            providers: List of LLM provider names

        Returns:
            Cache key string

        Example:
            article:a3d8f9:providers:gemini,mistral:v1
        """
        # Hash the URL to keep key length manageable
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

        # Sort providers for consistent cache keys
        sorted_providers = ','.join(sorted(providers))

        return f"article:{url_hash}:providers:{sorted_providers}:v1"

    def get_analysis_result(self, url: str, providers: List[str]) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis result for an article.

        Args:
            url: Article URL
            providers: List of provider names used for analysis

        Returns:
            Cached analysis result or None if not found

        Example:
            result = cache.get_analysis_result(url, ['gemini', 'mistral'])
            if result:
                print("Cache hit!")
        """
        if not self._enabled or not self._redis_client:
            self._stats["misses"] += 1
            return None

        cache_key = self._generate_cache_key(url, providers)

        try:
            cached_data = self._redis_client.get(cache_key)

            if cached_data:
                self._stats["hits"] += 1
                self.increment_counter("cache_hits", tags={"providers": ','.join(sorted(providers))})

                self.log_debug(
                    "Cache hit",
                    cache_key=cache_key,
                    url=url[:50]
                )

                # Parse JSON and return
                return json.loads(cached_data)

            else:
                self._stats["misses"] += 1
                self.increment_counter("cache_misses", tags={"providers": ','.join(sorted(providers))})

                self.log_debug(
                    "Cache miss",
                    cache_key=cache_key,
                    url=url[:50]
                )

                return None

        except Exception as e:
            self.log_error(
                "Cache get failed",
                exc=e,
                cache_key=cache_key
            )
            self._stats["misses"] += 1
            return None

    def set_analysis_result(
        self,
        url: str,
        providers: List[str],
        analysis_result: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache an analysis result.

        Args:
            url: Article URL
            providers: List of provider names used
            analysis_result: Analysis result data to cache
            ttl: Time to live in seconds (default: from settings)

        Returns:
            True if cached successfully, False otherwise

        Example:
            success = cache.set_analysis_result(
                url=url,
                providers=['gemini'],
                analysis_result={'sentences': [...], 'headline': '...'}
            )
        """
        if not self._enabled or not self._redis_client:
            return False

        cache_key = self._generate_cache_key(url, providers)
        ttl = ttl or settings.cache.ttl

        try:
            # Serialize to JSON
            cached_data = json.dumps(analysis_result)

            # Store with TTL
            self._redis_client.setex(cache_key, ttl, cached_data)

            self.log_debug(
                "Cache set",
                cache_key=cache_key,
                ttl=ttl,
                url=url[:50]
            )

            self.increment_counter("cache_sets", tags={"providers": ','.join(sorted(providers))})

            return True

        except Exception as e:
            self.log_error(
                "Cache set failed",
                exc=e,
                cache_key=cache_key
            )
            return False

    def invalidate(self, url: str, providers: Optional[List[str]] = None) -> int:
        """
        Invalidate cached results for a URL.

        Args:
            url: Article URL to invalidate
            providers: Optional specific provider combination to invalidate
                      If None, invalidates all provider combinations for this URL

        Returns:
            Number of keys deleted

        Example:
            # Invalidate all cached results for a URL
            cache.invalidate(url)

            # Invalidate specific provider combination
            cache.invalidate(url, ['gemini', 'mistral'])
        """
        if not self._enabled or not self._redis_client:
            return 0

        try:
            if providers:
                # Invalidate specific cache key
                cache_key = self._generate_cache_key(url, providers)
                deleted = self._redis_client.delete(cache_key)

                self.log_info(
                    "Cache invalidated",
                    cache_key=cache_key,
                    deleted=deleted
                )

                return deleted

            else:
                # Invalidate all variations for this URL
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                pattern = f"article:{url_hash}:*"

                # Find all matching keys
                keys = self._redis_client.keys(pattern)

                if keys:
                    deleted = self._redis_client.delete(*keys)

                    self.log_info(
                        "Cache invalidated (all providers)",
                        pattern=pattern,
                        deleted=deleted
                    )

                    return deleted

                return 0

        except Exception as e:
            self.log_error(
                "Cache invalidation failed",
                exc=e,
                url=url
            )
            return 0

    def clear_all(self) -> bool:
        """
        Clear all cached data (WARNING: Deletes everything).

        Returns:
            True if successful, False otherwise

        Example:
            cache.clear_all()  # Use with caution!
        """
        if not self._enabled or not self._redis_client:
            return False

        try:
            self._redis_client.flushdb()

            self.log_warning("All cache cleared")

            return True

        except Exception as e:
            self.log_error("Cache clear failed", exc=e)
            return False

    def get_stats(self) -> CacheStats:
        """
        Get cache statistics.

        Returns:
            CacheStats with hit/miss rates and Redis info

        Example:
            stats = cache.get_stats()
            print(f"Hit rate: {stats.hit_rate:.2%}")
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0.0

        redis_info = None
        if self._enabled and self._redis_client:
            try:
                info = self._redis_client.info()
                redis_info = {
                    "version": info.get("redis_version"),
                    "used_memory_human": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "total_commands_processed": info.get("total_commands_processed"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                }
            except Exception as e:
                self.log_error("Failed to get Redis info", exc=e)

        return CacheStats(
            hits=self._stats["hits"],
            misses=self._stats["misses"],
            total_requests=total,
            hit_rate=hit_rate,
            redis_connected=self._redis_client is not None,
            redis_info=redis_info
        )

    def health_check(self) -> Dict[str, Any]:
        """
        Check cache health status.

        Returns:
            Dictionary with health information

        Example:
            health = cache.health_check()
            if health['status'] == 'healthy':
                print("Cache is working!")
        """
        if not self._enabled:
            return {
                "status": "disabled",
                "message": "Cache is disabled in settings"
            }

        if not self._redis_client:
            return {
                "status": "unhealthy",
                "message": "Redis connection failed"
            }

        try:
            # Test connection
            latency_start = __import__('time').time()
            self._redis_client.ping()
            latency_ms = int((__import__('time').time() - latency_start) * 1000)

            return {
                "status": "healthy",
                "latency_ms": latency_ms,
                "host": settings.cache.redis_host,
                "port": settings.cache.redis_port,
                "db": settings.cache.redis_db
            }

        except Exception as e:
            self.log_error("Cache health check failed", exc=e)

            return {
                "status": "unhealthy",
                "error": str(e)
            }

    def is_enabled(self) -> bool:
        """Check if cache is enabled and connected."""
        return self._enabled and self._redis_client is not None
