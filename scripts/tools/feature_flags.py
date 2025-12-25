#!/usr/bin/env python3
"""
CLI tool for managing feature flags.

Usage:
    python scripts/tools/feature_flags.py list                      # List all flags
    python scripts/tools/feature_flags.py get <flag_name>           # Get flag value
    python scripts/tools/feature_flags.py set <flag_name> <value>   # Set flag value
    python scripts/tools/feature_flags.py create <flag_name> <value> --description "..." # Create new flag
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.database import session_scope, AnalyticsRepository
from scripts.config import settings


def print_section(title: str):
    """Print section header."""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def list_flags():
    """List all feature flags."""
    with session_scope() as session:
        repo = AnalyticsRepository(session)
        flags = repo.get_all_feature_flags()

        if not flags:
            print("\nNo feature flags found")
            print("Use 'create' command to add new flags")
            return

        print_section("Feature Flags")

        for flag in flags:
            enabled_str = "✓ ENABLED" if flag.enabled else "✗ DISABLED"
            print(f"\n  {flag.flag_name}")
            print(f"    Status: {enabled_str}")

            if flag.config:
                print(f"    Config: {flag.config}")

            if flag.description:
                print(f"    Description: {flag.description}")

            print(f"    Updated: {flag.updated_at}")

        print()


def get_flag(flag_name: str):
    """Get a specific feature flag value."""
    with session_scope() as session:
        repo = AnalyticsRepository(session)
        flag = repo.get_feature_flag(flag_name)

        if not flag:
            print(f"\nFeature flag '{flag_name}' not found")
            print("Use 'list' to see all available flags")
            return

        print_section(f"Feature Flag: {flag_name}")

        enabled_str = "✓ ENABLED" if flag.enabled else "✗ DISABLED"
        print(f"  Status: {enabled_str}")

        if flag.config:
            print(f"  Config: {flag.config}")

        if flag.description:
            print(f"  Description: {flag.description}")

        print(f"  Created: {flag.created_at}")
        print(f"  Updated: {flag.updated_at}")

        print()


def set_flag(flag_name: str, value: str):
    """Set a feature flag value."""
    # Parse boolean values
    if value.lower() in ['true', 'false']:
        enabled = value.lower() == 'true'
        config = None
    else:
        # For non-boolean values, store in config and enable
        enabled = True
        try:
            # Try to parse as JSON
            import json
            config = json.loads(value)
        except:
            # Store as simple string value
            config = {"value": value}

    with session_scope() as session:
        repo = AnalyticsRepository(session)

        # Check if flag exists
        existing_flag = repo.get_feature_flag(flag_name)

        if not existing_flag:
            print(f"\nFeature flag '{flag_name}' not found")
            print("Use 'create' command to create new flags")
            return

        # Update flag
        flag = repo.set_feature_flag(flag_name, enabled, config)

        if flag:
            print(f"\n✓ Updated feature flag '{flag_name}'")
            print(f"  Status: {'ENABLED' if enabled else 'DISABLED'}")
            if config:
                print(f"  Config: {config}")
        else:
            print(f"\n✗ Failed to update feature flag '{flag_name}'")

        print()


def create_flag(flag_name: str, value: str, description: Optional[str] = None):
    """Create a new feature flag."""
    # Parse boolean values
    if value.lower() in ['true', 'false']:
        enabled = value.lower() == 'true'
        config = None
    else:
        # For non-boolean values, store in config and enable
        enabled = True
        try:
            # Try to parse as JSON
            import json
            config = json.loads(value)
        except:
            # Store as simple string value
            config = {"value": value}

    with session_scope() as session:
        repo = AnalyticsRepository(session)

        # Check if flag already exists
        existing_flag = repo.get_feature_flag(flag_name)

        if existing_flag:
            print(f"\nFeature flag '{flag_name}' already exists")
            print("Use 'set' command to update it")
            return

        # Create flag
        flag = repo.set_feature_flag(
            flag_name=flag_name,
            enabled=enabled,
            config=config,
            description=description
        )

        if flag:
            print(f"\n✓ Created feature flag '{flag_name}'")
            print(f"  Status: {'ENABLED' if enabled else 'DISABLED'}")
            if config:
                print(f"  Config: {config}")

            if description:
                print(f"  Description: {description}")
        else:
            print(f"\n✗ Failed to create feature flag '{flag_name}'")

        print()


def delete_flag(flag_name: str, confirm: bool = False):
    """Delete a feature flag."""
    if not confirm:
        response = input(f"\nAre you sure you want to delete flag '{flag_name}'? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted")
            return

    with session_scope() as session:
        repo = AnalyticsRepository(session)

        # For now, we'll disable the flag instead of deleting
        # (safer approach - can always re-enable)
        flag = repo.set_feature_flag(flag_name, enabled=False, config={"deleted": True})

        if flag:
            print(f"\n✓ Disabled feature flag '{flag_name}'")
            print("  (Flag is disabled but not deleted from database)")
        else:
            print(f"\n✗ Failed to disable feature flag '{flag_name}'")

        print()


def main():
    parser = argparse.ArgumentParser(
        description="Feature flags management tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  list                                List all feature flags
  get <flag_name>                     Get specific flag value
  set <flag_name> <value>             Set flag value
  create <flag_name> <value>          Create new flag
  delete <flag_name>                  Delete flag (requires confirmation)

Examples:
  python scripts/tools/feature_flags.py list
  python scripts/tools/feature_flags.py get cache_enabled
  python scripts/tools/feature_flags.py set cache_enabled true
  python scripts/tools/feature_flags.py create new_feature true --description "Enable new feature"
  python scripts/tools/feature_flags.py delete old_feature --yes
        """
    )

    parser.add_argument(
        'command',
        choices=['list', 'get', 'set', 'create', 'delete'],
        help='Command to execute'
    )

    parser.add_argument(
        'flag_name',
        nargs='?',
        help='Feature flag name'
    )

    parser.add_argument(
        'value',
        nargs='?',
        help='Feature flag value (for set/create commands)'
    )

    parser.add_argument(
        '--description',
        type=str,
        help='Flag description (for create command)'
    )

    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt (for delete command)'
    )

    args = parser.parse_args()

    try:
        if args.command == 'list':
            list_flags()

        elif args.command == 'get':
            if not args.flag_name:
                print("Error: flag_name is required for 'get' command", file=sys.stderr)
                parser.print_help()
                sys.exit(1)

            get_flag(args.flag_name)

        elif args.command == 'set':
            if not args.flag_name or not args.value:
                print("Error: flag_name and value are required for 'set' command", file=sys.stderr)
                parser.print_help()
                sys.exit(1)

            set_flag(args.flag_name, args.value)

        elif args.command == 'create':
            if not args.flag_name or not args.value:
                print("Error: flag_name and value are required for 'create' command", file=sys.stderr)
                parser.print_help()
                sys.exit(1)

            create_flag(args.flag_name, args.value, description=args.description)

        elif args.command == 'delete':
            if not args.flag_name:
                print("Error: flag_name is required for 'delete' command", file=sys.stderr)
                parser.print_help()
                sys.exit(1)

            delete_flag(args.flag_name, confirm=args.yes)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
