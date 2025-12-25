#!/usr/bin/env python3
"""
CLI tool for viewing structured logs.

Usage:
    python scripts/tools/view_logs.py --correlation-id req_abc123
    python scripts/tools/view_logs.py --last 1h --level ERROR
    python scripts/tools/view_logs.py --component llm.gemini
    python scripts/tools/view_logs.py --url "https://chosun.com/..."
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.config import settings
from scripts.database import session_scope, AnalyticsRepository


def parse_time_range(time_str: str) -> datetime:
    """Parse time range string like '24h', '7d', '30m'."""
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
        raise ValueError(f"Invalid time range: {time_str}")


def read_log_files(log_dir: Path, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Read and parse JSON log files.

    Args:
        log_dir: Directory containing log files
        since: Optional datetime to filter logs after

    Returns:
        List of log entries
    """
    log_entries = []

    if not log_dir.exists():
        return log_entries

    # Find all .log files
    log_files = sorted(log_dir.glob('*.log'))

    for log_file in log_files:
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)

                        # Filter by time if specified
                        if since:
                            timestamp_str = entry.get('timestamp', '')
                            if timestamp_str:
                                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                if timestamp < since:
                                    continue

                        log_entries.append(entry)

                    except json.JSONDecodeError:
                        # Skip malformed lines
                        continue

        except Exception as e:
            print(f"Warning: Failed to read {log_file}: {e}", file=sys.stderr)

    return log_entries


def filter_logs(
    logs: List[Dict[str, Any]],
    correlation_id: Optional[str] = None,
    level: Optional[str] = None,
    component: Optional[str] = None,
    url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Filter logs by criteria."""
    filtered = logs

    if correlation_id:
        filtered = [log for log in filtered if log.get('correlation_id') == correlation_id]

    if level:
        filtered = [log for log in filtered if log.get('level') == level.upper()]

    if component:
        filtered = [log for log in filtered if component in log.get('component', '')]

    if url:
        filtered = [log for log in filtered if url in str(log.get('url', ''))]

    return filtered


def format_log_entry(entry: Dict[str, Any], verbose: bool = False) -> str:
    """Format a log entry for display."""
    timestamp = entry.get('timestamp', 'N/A')
    level = entry.get('level', 'INFO')
    component = entry.get('component', 'unknown')
    correlation_id = entry.get('correlation_id', 'none')
    message = entry.get('message', '')

    # Color codes for levels
    colors = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m'  # Magenta
    }
    reset = '\033[0m'

    color = colors.get(level, '')

    # Basic format
    output = f"{color}[{timestamp}] {level:<8}{reset} [{correlation_id}] {component}: {message}"

    # Add extra fields in verbose mode
    if verbose:
        extra_fields = {k: v for k, v in entry.items()
                       if k not in ['timestamp', 'level', 'component', 'correlation_id', 'message']}

        if extra_fields:
            output += f"\n  Extra: {json.dumps(extra_fields, indent=2)}"

    return output


def print_timeline(logs: List[Dict[str, Any]]):
    """Print logs as a timeline for a correlation ID."""
    if not logs:
        print("No logs found")
        return

    # Sort by timestamp
    sorted_logs = sorted(logs, key=lambda x: x.get('timestamp', ''))

    # Get correlation ID from first log
    correlation_id = sorted_logs[0].get('correlation_id', 'unknown')

    print(f"\n{'=' * 70}")
    print(f" Timeline for {correlation_id}")
    print('=' * 70)

    # Print each log with time offset from first
    first_timestamp = None

    for log in sorted_logs:
        timestamp_str = log.get('timestamp', '')

        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

            if first_timestamp is None:
                first_timestamp = timestamp
                offset_str = "+0ms"
            else:
                offset_ms = int((timestamp - first_timestamp).total_seconds() * 1000)
                offset_str = f"+{offset_ms}ms"

            print(f"  {offset_str:>8} {format_log_entry(log)}")
        else:
            print(f"  {' ' * 8} {format_log_entry(log)}")

    print()


def view_logs_by_correlation_id(correlation_id: str):
    """View all logs for a specific correlation ID from database."""
    print(f"\nQuerying database for correlation_id: {correlation_id}")

    try:
        with session_scope() as session:
            repo = AnalyticsRepository(session)

            # Get request log
            request = repo.get_request_by_correlation_id(correlation_id)

            if request:
                print(f"\n{'=' * 70}")
                print(" Request Details")
                print('=' * 70)
                print(f"  URL: {request.url}")
                print(f"  Mode: {request.mode}")
                print(f"  Providers: {request.providers}")
                print(f"  Status: {request.status}")
                print(f"  Duration: {request.duration_ms}ms")
                print(f"  Created: {request.created_at}")

                if request.error_message:
                    print(f"  Error: {request.error_message}")

            # Get analysis results
            analyses = repo.get_analyses_by_correlation_id(correlation_id)

            if analyses:
                print(f"\n{'=' * 70}")
                print(" Analysis Results")
                print('=' * 70)

                for analysis in analyses:
                    print(f"\n  Provider: {analysis.provider}")
                    print(f"  Success: {analysis.success}")
                    print(f"  Sentences: {analysis.sentence_count}")
                    print(f"  Latency: {analysis.latency_ms}ms")
                    print(f"  Created: {analysis.created_at}")

            if not request and not analyses:
                print(f"No database records found for {correlation_id}")

    except Exception as e:
        print(f"Error querying database: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="View structured logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/tools/view_logs.py --correlation-id req_abc123
  python scripts/tools/view_logs.py --last 1h --level ERROR
  python scripts/tools/view_logs.py --component llm.gemini --last 24h
        """
    )

    parser.add_argument(
        '--correlation-id',
        type=str,
        help='Filter by correlation ID'
    )

    parser.add_argument(
        '--last',
        type=str,
        help='Time range (e.g., 24h, 7d, 30m)'
    )

    parser.add_argument(
        '--level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Filter by log level'
    )

    parser.add_argument(
        '--component',
        type=str,
        help='Filter by component name'
    )

    parser.add_argument(
        '--url',
        type=str,
        help='Filter by article URL (partial match)'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show extra fields in logs'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Limit number of results (default: 100)'
    )

    args = parser.parse_args()

    # If correlation ID specified, use database query
    if args.correlation_id:
        view_logs_by_correlation_id(args.correlation_id)
        return

    # Otherwise, read from log files
    since = None
    if args.last:
        try:
            since = parse_time_range(args.last)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Read logs
    log_dir = Path(settings.observability.log_dir)
    logs = read_log_files(log_dir, since=since)

    # Filter logs
    filtered_logs = filter_logs(
        logs,
        level=args.level,
        component=args.component,
        url=args.url
    )

    # Limit results
    if len(filtered_logs) > args.limit:
        print(f"Showing first {args.limit} of {len(filtered_logs)} logs")
        filtered_logs = filtered_logs[:args.limit]

    # Display logs
    print(f"\nFound {len(filtered_logs)} log entries")

    for log in filtered_logs:
        print(format_log_entry(log, verbose=args.verbose))

    print()


if __name__ == '__main__':
    main()
