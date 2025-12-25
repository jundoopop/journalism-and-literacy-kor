#!/usr/bin/env python3
"""
CLI tool for viewing system metrics.

Usage:
    python scripts/tools/view_metrics.py                    # View all metrics
    python scripts/tools/view_metrics.py --last 24h         # Metrics from last 24 hours
    python scripts/tools/view_metrics.py --provider gemini  # Filter by provider
    python scripts/tools/view_metrics.py --mode consensus   # Filter by mode
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.database import session_scope, AnalyticsRepository
from scripts.config import settings


def parse_time_range(time_str: str) -> datetime:
    """
    Parse time range string like '24h', '7d', '30m'.

    Args:
        time_str: Time range string

    Returns:
        datetime object for the start of the range
    """
    now = datetime.utcnow()

    if time_str.endswith('h'):
        hours = int(time_str[:-1])
        return now - timedelta(hours=hours)
    elif time_str.endswith('d'):
        days = int(time_str[:-1])
        return now - timedelta(days=days)
    elif time_str.endswith('m'):
        minutes = int(time_str[:-1])
        return now - timedelta(minutes=minutes)
    else:
        raise ValueError(f"Invalid time range format: {time_str}. Use format like '24h', '7d', '30m'")


def format_percentage(value: float) -> str:
    """Format decimal as percentage."""
    return f"{value * 100:.1f}%"


def format_duration(ms: float) -> str:
    """Format milliseconds in human-readable format."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    else:
        return f"{ms / 1000:.2f}s"


def print_section(title: str):
    """Print section header."""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def print_metric(name: str, value: Any, unit: str = ""):
    """Print metric in formatted way."""
    print(f"  {name:<30} {value} {unit}")


def view_request_metrics(repo: AnalyticsRepository, since: Optional[datetime] = None, mode: Optional[str] = None):
    """View request-level metrics."""
    print_section("Request Metrics")

    # Get request statistics
    stats = repo.get_request_stats(since=since, mode=mode)

    if not stats:
        print("  No data available")
        return

    print_metric("Total Requests:", stats.get('total_requests', 0))
    print_metric("Successful:", stats.get('successful_requests', 0))
    print_metric("Failed:", stats.get('failed_requests', 0))
    print_metric("Partial:", stats.get('partial_requests', 0))

    if stats.get('total_requests', 0) > 0:
        success_rate = stats.get('successful_requests', 0) / stats['total_requests']
        print_metric("Success Rate:", format_percentage(success_rate))

    if 'avg_duration_ms' in stats:
        print_metric("Avg Duration:", format_duration(stats['avg_duration_ms']))

    if 'p50_duration_ms' in stats:
        print_metric("p50 Duration:", format_duration(stats['p50_duration_ms']))

    if 'p95_duration_ms' in stats:
        print_metric("p95 Duration:", format_duration(stats['p95_duration_ms']))

    if 'p99_duration_ms' in stats:
        print_metric("p99 Duration:", format_duration(stats['p99_duration_ms']))


def view_provider_metrics(repo: AnalyticsRepository, provider: Optional[str] = None, since: Optional[datetime] = None):
    """View LLM provider metrics."""
    print_section("LLM Provider Metrics")

    stats = repo.get_provider_stats(provider=provider, since=since)

    if not stats:
        print("  No data available")
        return

    # Group by provider
    provider_data: Dict[str, Dict[str, Any]] = {}

    for stat in stats:
        prov = stat.get('provider', 'unknown')
        if prov not in provider_data:
            provider_data[prov] = {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'total_latency': 0,
                'total_sentences': 0
            }

        provider_data[prov]['total'] += stat.get('total_analyses', 0)
        provider_data[prov]['successful'] += stat.get('successful_analyses', 0)
        provider_data[prov]['failed'] += stat.get('failed_analyses', 0)
        provider_data[prov]['total_latency'] += stat.get('avg_latency_ms', 0) * stat.get('total_analyses', 0)
        provider_data[prov]['total_sentences'] += stat.get('avg_sentences', 0) * stat.get('total_analyses', 0)

    # Print stats for each provider
    for prov, data in sorted(provider_data.items()):
        print(f"\n  {prov.upper()}:")
        print_metric("    Total Analyses:", data['total'])
        print_metric("    Successful:", data['successful'])
        print_metric("    Failed:", data['failed'])

        if data['total'] > 0:
            success_rate = data['successful'] / data['total']
            print_metric("    Success Rate:", format_percentage(success_rate))

            avg_latency = data['total_latency'] / data['total']
            print_metric("    Avg Latency:", format_duration(avg_latency))

            avg_sentences = data['total_sentences'] / data['total']
            print_metric("    Avg Sentences:", f"{avg_sentences:.1f}")


def view_error_breakdown(repo: AnalyticsRepository, since: Optional[datetime] = None):
    """View error breakdown."""
    print_section("Error Breakdown")

    errors = repo.get_error_breakdown(since=since)

    if not errors:
        print("  No errors found")
        return

    total_errors = sum(e.get('count', 0) for e in errors)

    for error in errors:
        error_type = error.get('error_type', 'Unknown')
        count = error.get('count', 0)
        percentage = (count / total_errors * 100) if total_errors > 0 else 0

        print(f"  {error_type:<30} {count:>5} ({percentage:>5.1f}%)")

        # Show sample error message
        if 'sample_message' in error:
            sample = error['sample_message'][:60]
            print(f"    Sample: {sample}...")


def view_cache_metrics(repo: AnalyticsRepository):
    """View cache metrics from database."""
    print_section("Cache Performance")

    # This would come from cache_service in real-time
    # For now, show placeholder
    print("  Use 'cache_admin.py stats' for real-time cache statistics")


def main():
    parser = argparse.ArgumentParser(
        description="View system metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/tools/view_metrics.py
  python scripts/tools/view_metrics.py --last 24h
  python scripts/tools/view_metrics.py --provider gemini
  python scripts/tools/view_metrics.py --mode consensus --last 7d
        """
    )

    parser.add_argument(
        '--last',
        type=str,
        help='Time range (e.g., 24h, 7d, 30m)'
    )

    parser.add_argument(
        '--provider',
        type=str,
        choices=['gemini', 'mistral', 'openai', 'claude', 'llama'],
        help='Filter by LLM provider'
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['single', 'consensus'],
        help='Filter by analysis mode'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    args = parser.parse_args()

    # Parse time range
    since = None
    if args.last:
        try:
            since = parse_time_range(args.last)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Connect to database
    try:
        with session_scope() as session:
            repo = AnalyticsRepository(session)

            # Print header
            time_range_str = f"Last {args.last}" if args.last else "All Time"
            print(f"\nSystem Metrics - {time_range_str}")
            print(f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

            # View different metrics
            view_request_metrics(repo, since=since, mode=args.mode)
            view_provider_metrics(repo, provider=args.provider, since=since)
            view_error_breakdown(repo, since=since)
            view_cache_metrics(repo)

            print("\n")

    except Exception as e:
        print(f"Error accessing database: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
