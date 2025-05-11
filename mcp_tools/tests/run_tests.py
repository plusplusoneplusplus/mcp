#!/usr/bin/env python3
# Script to run all mcp_tools tests

import os
import sys
import subprocess
from pathlib import Path


def main():
    # Get the directory of this script
    script_dir = Path(__file__).resolve().parent

    print(f"\n=== Running MCP Tools Tests ===\n")

    # Run pytest on the tests directory
    cmd = [sys.executable, "-m", "pytest", str(script_dir), "-v"]

    try:
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print(f"\nTests FAILED with exit code {result.returncode}")
        else:
            print(f"\nAll tests PASSED")
    except Exception as e:
        print(f"Error running tests: {e}")

    print("\n=== Tests completed ===\n")


if __name__ == "__main__":
    main()
