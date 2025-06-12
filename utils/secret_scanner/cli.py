#!/usr/bin/env python3
"""
Command-line interface for the custom secret scanner.
This module provides a CLI wrapper around the secret scanner functionality
for use with pre-commit hooks and standalone execution.
"""

import sys
import argparse
from pathlib import Path
from typing import List

from .scanner import check_secrets


def scan_file(file_path: str) -> List[dict]:
    """
    Scan a single file for secrets.

    Args:
        file_path: Path to the file to scan

    Returns:
        List of findings from the secret scanner
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return check_secrets(content)
    except Exception as e:
        print(f"Error scanning {file_path}: {e}", file=sys.stderr)
        return []


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Custom secret scanner for detecting hardcoded secrets in files"
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='Files to scan for secrets'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    if not args.files:
        print("No files provided to scan", file=sys.stderr)
        return 0

    total_findings = 0

    for file_path in args.files:
        if not Path(file_path).exists():
            if args.verbose:
                print(f"Skipping non-existent file: {file_path}", file=sys.stderr)
            continue

        findings = scan_file(file_path)

        if findings:
            total_findings += len(findings)
            print(f"\n🚨 Secrets detected in {file_path}:")
            for finding in findings:
                print(f"  Line {finding['LineNumber']}: {finding['SecretType']} - {finding['SecretValue'][:20]}...")
        elif args.verbose:
            print(f"✅ No secrets found in {file_path}")

    if total_findings > 0:
        print(f"\n❌ Total secrets found: {total_findings}")
        return 1
    else:
        if args.verbose:
            print(f"\n✅ No secrets detected in {len(args.files)} files")
        return 0


if __name__ == '__main__':
    sys.exit(main())