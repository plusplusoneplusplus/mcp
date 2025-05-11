#!/usr/bin/env python3
# Script to run all mcp_core tests

import os
import sys
import subprocess
from pathlib import Path


def main():
    # Get the directory of this script
    script_dir = Path(__file__).resolve().parent

    # Find all test_*.py files
    test_files = list(script_dir.glob("test_*.py"))
    test_files.sort()

    if not test_files:
        print("No test files found!")
        return

    print(f"\n=== Running {len(test_files)} MCP Core Tests ===\n")

    # Run each test
    for test_file in test_files:
        print(f"\n--- Running {test_file.name} ---\n")
        result = subprocess.run(
            [sys.executable, str(test_file)], capture_output=True, text=True
        )

        # Print output
        print(result.stdout)

        if result.stderr:
            print(f"ERRORS:\n{result.stderr}")

        if result.returncode != 0:
            print(f"Test {test_file.name} FAILED with exit code {result.returncode}")
        else:
            print(f"Test {test_file.name} PASSED")

    print("\n=== All tests completed ===\n")


if __name__ == "__main__":
    main()
