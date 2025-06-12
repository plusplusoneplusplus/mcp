#!/usr/bin/env python3
"""
CLI tool for Azure DevOps identity resolution.

This tool provides command-line access to Azure DevOps identity resolution functionality,
allowing users to resolve identities (usernames, emails, display names) to their full
Azure DevOps identity information.
"""

import asyncio
import argparse
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to sys.path to allow importing from plugins
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from plugins.azrepo.azure_rest_utils import (
    resolve_identity,
    get_auth_headers,
    IdentityInfo,
    execute_bearer_token_command,
)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Azure DevOps Identity Resolution CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Resolve a single identity
  python azure_identity_cli.py resolve --organization myorg --identity "john.doe@company.com"

  # Resolve multiple identities
  python azure_identity_cli.py resolve --organization myorg --identity "john.doe@company.com" "jane.smith"

  # Resolve identities from a file
  python azure_identity_cli.py resolve --organization myorg --from-file identities.txt

  # Resolve with project context
  python azure_identity_cli.py resolve --organization myorg --project myproject --identity "john.doe"

  # Test authentication
  python azure_identity_cli.py test-auth --organization myorg

  # Output as JSON
  python azure_identity_cli.py resolve --organization myorg --identity "john.doe" --format json

Environment Variables:
  AZREPO_BEARER_TOKEN        - Static bearer token for authentication
  AZREPO_BEARER_TOKEN_COMMAND - Command to execute to get bearer token
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Resolve command
    resolve_parser = subparsers.add_parser(
        'resolve',
        help='Resolve Azure DevOps identities'
    )
    resolve_parser.add_argument(
        '--organization', '-o',
        required=True,
        help='Azure DevOps organization name or URL'
    )
    resolve_parser.add_argument(
        '--project', '-p',
        help='Azure DevOps project name (optional)'
    )

    # Identity input options (mutually exclusive)
    identity_group = resolve_parser.add_mutually_exclusive_group(required=True)
    identity_group.add_argument(
        '--identity', '-i',
        nargs='+',
        help='Identity to resolve (username, email, or display name). Can specify multiple.'
    )
    identity_group.add_argument(
        '--from-file', '-f',
        type=Path,
        help='File containing identities to resolve (one per line)'
    )

    resolve_parser.add_argument(
        '--format',
        choices=['human', 'json'],
        default='human',
        help='Output format (default: human)'
    )
    resolve_parser.add_argument(
        '--include-invalid',
        action='store_true',
        help='Include invalid/unresolved identities in output'
    )

    # Test auth command
    test_parser = subparsers.add_parser(
        'test-auth',
        help='Test Azure DevOps authentication'
    )
    test_parser.add_argument(
        '--organization', '-o',
        required=True,
        help='Azure DevOps organization name or URL'
    )

    return parser


def load_identities_from_file(file_path: Path) -> List[str]:
    """Load identities from a text file (one per line)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            identities = []
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):  # Skip empty lines and comments
                    identities.append(line)
            return identities
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)


def format_identity_human(identity_info: IdentityInfo, include_invalid: bool = False) -> str:
    """Format identity information for human-readable output."""
    if not identity_info.is_valid and not include_invalid:
        return ""

    lines = []
    if identity_info.is_valid:
        lines.append(f"✓ {identity_info.display_name}")
        lines.append(f"  Email: {identity_info.unique_name}")
        lines.append(f"  ID: {identity_info.id}")
        lines.append(f"  Descriptor: {identity_info.descriptor}")
    else:
        lines.append(f"✗ Failed to resolve identity")
        lines.append(f"  Error: {identity_info.error_message}")

    return "\n".join(lines)


def format_identity_json(identity_info: IdentityInfo) -> Dict[str, Any]:
    """Format identity information for JSON output."""
    return {
        "display_name": identity_info.display_name,
        "unique_name": identity_info.unique_name,
        "id": identity_info.id,
        "descriptor": identity_info.descriptor,
        "is_valid": identity_info.is_valid,
        "error_message": identity_info.error_message if identity_info.error_message else None
    }


async def resolve_identities_command(args) -> int:
    """Handle the resolve identities command."""
    # Get list of identities to resolve
    if args.identity:
        identities = args.identity
    else:
        identities = load_identities_from_file(args.from_file)

    if not identities:
        print("No identities to resolve.", file=sys.stderr)
        return 1

    print(f"Resolving {len(identities)} identit{'y' if len(identities) == 1 else 'ies'}...")

    results = []
    failed_count = 0

    for identity in identities:
        try:
            identity_info = await resolve_identity(
                identity=identity.strip(),
                organization=args.organization,
                project=args.project
            )
            results.append((identity, identity_info))

            if not identity_info.is_valid:
                failed_count += 1

        except Exception as e:
            # Create a failed IdentityInfo for consistency
            failed_info = IdentityInfo(
                display_name="",
                unique_name="",
                id="",
                descriptor="",
                is_valid=False,
                error_message=str(e)
            )
            results.append((identity, failed_info))
            failed_count += 1

    # Output results
    if args.format == 'json':
        output = {
            "organization": args.organization,
            "project": args.project,
            "total_count": len(identities),
            "resolved_count": len(identities) - failed_count,
            "failed_count": failed_count,
            "results": []
        }

        for original_identity, identity_info in results:
            if identity_info.is_valid or args.include_invalid:
                result_item = {
                    "input": original_identity,
                    **format_identity_json(identity_info)
                }
                output["results"].append(result_item)

        print(json.dumps(output, indent=2))
    else:
        # Human-readable format
        print(f"\nResults for organization: {args.organization}")
        if args.project:
            print(f"Project: {args.project}")
        print("-" * 50)

        for original_identity, identity_info in results:
            formatted = format_identity_human(identity_info, args.include_invalid)
            if formatted:
                print(f"\nInput: {original_identity}")
                print(formatted)

        print(f"\nSummary: {len(identities) - failed_count}/{len(identities)} resolved successfully")
        if failed_count > 0 and not args.include_invalid:
            print(f"Use --include-invalid to see failed resolutions")

    return 0 if failed_count == 0 else 1


async def test_auth_command(args) -> int:
    """Handle the test authentication command."""
    print(f"Testing authentication for organization: {args.organization}")

    try:
        # Test if we can get auth headers
        headers = get_auth_headers()

        if 'Authorization' not in headers:
            print("✗ No authorization header found")
            print("Please set AZREPO_BEARER_TOKEN or AZREPO_BEARER_TOKEN_COMMAND environment variable")
            return 1

        # Check if using token command
        token_command = os.getenv('AZREPO_BEARER_TOKEN_COMMAND')
        if token_command:
            print(f"✓ Using bearer token command: {token_command}")

            # Test executing the command
            token = execute_bearer_token_command(token_command)
            if token:
                print("✓ Bearer token command executed successfully")
                print(f"  Token length: {len(token)} characters")
                print(f"  Token preview: {token[:10]}...")
            else:
                print("✗ Bearer token command failed to return a token")
                return 1
        else:
            static_token = os.getenv('AZREPO_BEARER_TOKEN')
            if static_token:
                print("✓ Using static bearer token")
                print(f"  Token length: {len(static_token)} characters")
                print(f"  Token preview: {static_token[:10]}...")
            else:
                print("✗ No bearer token found")
                return 1

        # Test with a simple identity resolution
        print("\nTesting identity resolution with current user...")
        try:
            # Try to resolve a simple identity (this will test the full auth flow)
            test_identity = os.getenv('USER', 'testuser')
            identity_info = await resolve_identity(
                identity=test_identity,
                organization=args.organization
            )

            if identity_info.is_valid:
                print(f"✓ Successfully resolved test identity: {identity_info.display_name}")
            else:
                print(f"⚠ Test identity resolution failed (this may be normal): {identity_info.error_message}")

        except Exception as e:
            print(f"⚠ Test identity resolution failed: {e}")
            print("This may indicate authentication issues or network problems")

        print("\n✓ Authentication test completed")
        return 0

    except Exception as e:
        print(f"✗ Authentication test failed: {e}")
        return 1


async def main() -> int:
    """Main CLI function."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == 'resolve':
            return await resolve_identities_command(args)
        elif args.command == 'test-auth':
            return await test_auth_command(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
