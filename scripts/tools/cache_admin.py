#!/usr/bin/env python3
"""
CLI tool for cache administration.

Usage:
    python scripts/tools/cache_admin.py stats              # View cache statistics
    python scripts/tools/cache_admin.py clear              # Clear all cache
    python scripts/tools/cache_admin.py invalidate <url>   # Invalidate specific URL
    python scripts/tools/cache_admin.py health             # Check cache health
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.services import CacheService
from scripts.config import settings


def print_section(title: str):
    """Print section header."""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def print_metric(name: str, value: any, unit: str = ""):
    """Print metric in formatted way."""
    print(f"  {name:<30} {value} {unit}")


def view_cache_stats():
    """View cache statistics."""
    cache = CacheService()

    if not cache.is_enabled():
        print("\nCache is disabled or not connected")
        return

    stats = cache.get_stats()

    print_section("Cache Statistics")

    print_metric("Total Requests:", stats.total_requests)
    print_metric("Cache Hits:", stats.hits)
    print_metric("Cache Misses:", stats.misses)
    print_metric("Hit Rate:", f"{stats.hit_rate * 100:.1f}%")
    print_metric("Redis Connected:", "Yes" if stats.redis_connected else "No")

    if stats.redis_info:
        print_section("Redis Information")
        print_metric("Version:", stats.redis_info.get('version', 'N/A'))
        print_metric("Memory Used:", stats.redis_info.get('used_memory_human', 'N/A'))
        print_metric("Connected Clients:", stats.redis_info.get('connected_clients', 'N/A'))
        print_metric("Total Commands:", stats.redis_info.get('total_commands_processed', 'N/A'))

        # Redis-level cache stats
        redis_hits = stats.redis_info.get('keyspace_hits', 0)
        redis_misses = stats.redis_info.get('keyspace_misses', 0)
        redis_total = redis_hits + redis_misses

        if redis_total > 0:
            redis_hit_rate = redis_hits / redis_total
            print_metric("Redis Hit Rate:", f"{redis_hit_rate * 100:.1f}%")

    print()


def check_cache_health():
    """Check cache health status."""
    cache = CacheService()

    health = cache.health_check()

    print_section("Cache Health Check")

    status = health.get('status', 'unknown')
    print_metric("Status:", status)

    if 'message' in health:
        print_metric("Message:", health['message'])

    if 'latency_ms' in health:
        print_metric("Latency:", f"{health['latency_ms']}ms")

    if 'host' in health:
        print_metric("Host:", health['host'])

    if 'port' in health:
        print_metric("Port:", health['port'])

    if 'error' in health:
        print(f"\n  Error: {health['error']}")

    print()


def clear_cache(confirm: bool = False):
    """Clear all cache (requires confirmation)."""
    cache = CacheService()

    if not cache.is_enabled():
        print("\nCache is disabled or not connected")
        return

    if not confirm:
        response = input("\nAre you sure you want to clear ALL cache? This cannot be undone. (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted")
            return

    print("\nClearing all cache...")

    success = cache.clear_all()

    if success:
        print("✓ Cache cleared successfully")
    else:
        print("✗ Failed to clear cache")

    print()


def invalidate_url(url: str, providers: Optional[str] = None):
    """Invalidate cache for a specific URL."""
    cache = CacheService()

    if not cache.is_enabled():
        print("\nCache is disabled or not connected")
        return

    provider_list = providers.split(',') if providers else None

    print(f"\nInvalidating cache for: {url}")
    if provider_list:
        print(f"Providers: {', '.join(provider_list)}")

    deleted = cache.invalidate(url, providers=provider_list)

    print(f"✓ Deleted {deleted} cache entries")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Cache administration tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  stats                   View cache statistics
  health                  Check cache health
  clear                   Clear all cache (requires confirmation)
  invalidate <url>        Invalidate cache for specific URL

Examples:
  python scripts/tools/cache_admin.py stats
  python scripts/tools/cache_admin.py health
  python scripts/tools/cache_admin.py clear --yes
  python scripts/tools/cache_admin.py invalidate "https://chosun.com/..."
  python scripts/tools/cache_admin.py invalidate "https://chosun.com/..." --providers gemini,mistral
        """
    )

    parser.add_argument(
        'command',
        choices=['stats', 'health', 'clear', 'invalidate'],
        help='Command to execute'
    )

    parser.add_argument(
        'url',
        nargs='?',
        help='URL to invalidate (required for invalidate command)'
    )

    parser.add_argument(
        '--providers',
        type=str,
        help='Comma-separated list of providers (for invalidate command)'
    )

    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt (for clear command)'
    )

    args = parser.parse_args()

    try:
        if args.command == 'stats':
            view_cache_stats()

        elif args.command == 'health':
            check_cache_health()

        elif args.command == 'clear':
            clear_cache(confirm=args.yes)

        elif args.command == 'invalidate':
            if not args.url:
                print("Error: URL is required for invalidate command", file=sys.stderr)
                parser.print_help()
                sys.exit(1)

            invalidate_url(args.url, providers=args.providers)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
