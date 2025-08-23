"""Ctags generation functionality.

This module provides functions to generate ctags for source code projects
with optimized parameters for analysis.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional, List


def run_ctags(
    source_dir: str,
    output_file: str = "tags.json",
    languages: str = "C++",
    additional_args: Optional[List[str]] = None,
) -> int:
    """Run ctags command with specified parameters.

    Args:
        source_dir: Directory to scan for source files
        output_file: Output file name (default: tags.json)
        languages: Programming languages to include (default: C++)
        additional_args: Additional ctags arguments

    Returns:
        Exit code from ctags command
    """
    # Verify source directory exists
    if not Path(source_dir).exists():
        print(f"Error: Source directory '{source_dir}' does not exist", file=sys.stderr)
        return 1

    # Build ctags command
    cmd = [
        "ctags",
        "-R",  # Recursive
        f"--languages={languages}",
        "--output-format=json",
        "--fields=+n+S+a+K+Z+t",  # Extended fields: line numbers, signatures, access, kind, scope, type
        "--extras=+q",  # Include qualified tags
        "--tag-relative=never",  # Use absolute paths
        "-o",
        output_file,
        source_dir,
    ]

    # Add any additional arguments
    if additional_args:
        cmd.extend(additional_args)

    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True)
        print(f"Successfully generated tags in '{output_file}'")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Error running ctags: {e}", file=sys.stderr)
        return e.returncode
    except FileNotFoundError:
        print("Error: ctags command not found. Please install ctags.", file=sys.stderr)
        print("On macOS: brew install ctags", file=sys.stderr)
        print("On Ubuntu/Debian: sudo apt install universal-ctags", file=sys.stderr)
        return 1


def main_generator() -> None:
    """Main entry point for ctags generation."""
    parser = argparse.ArgumentParser(
        description="Generate ctags for C++ projects with JSON output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s cpp/                    # Generate tags.json from cpp/ directory
  %(prog)s src/ -o symbols.json    # Custom output file
  %(prog)s . --languages=C++,Python  # Multiple languages
  %(prog)s code/ --extras=+f       # Additional ctags options
        """,
    )

    parser.add_argument("source_dir", help="Source directory to scan for code files")

    parser.add_argument(
        "-o",
        "--output",
        default="tags.json",
        help="Output file name (default: tags.json)",
    )

    parser.add_argument(
        "--languages",
        default="C++",
        help="Programming languages to include (default: C++)",
    )

    parser.add_argument(
        "--extras", help="Additional ctags --extras options (e.g., +f for file scope)"
    )

    parser.add_argument("--fields", help="Additional ctags --fields options")

    args = parser.parse_args()

    # Build additional arguments
    additional_args = []
    if args.extras:
        additional_args.extend(["--extras", args.extras])
    if args.fields:
        additional_args.extend(["--fields", args.fields])

    # Run ctags
    exit_code = run_ctags(
        source_dir=args.source_dir,
        output_file=args.output,
        languages=args.languages,
        additional_args=additional_args if additional_args else None,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main_generator()
