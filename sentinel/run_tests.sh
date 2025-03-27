#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run unit tests first
echo "Running unit tests..."
pytest "$SCRIPT_DIR/tests/test_browser_utils.py" -v

# Run integration tests
echo -e "\nRunning integration tests..."
pytest "$SCRIPT_DIR/tests/test_command_executor_integration.py" -v

# Run all tests with coverage, skip for now
# echo -e "\nRunning all tests with coverage..."
# pytest "$SCRIPT_DIR/tests" --cov=sentinel --cov-report=term-missing
