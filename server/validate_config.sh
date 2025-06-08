#!/bin/bash

# validate_config.sh - Configuration validation script
# This script demonstrates the post_processing feature by generating both stdout and stderr

CONFIG_FILE="${1:-config.yaml}"

echo "Starting configuration validation for: $CONFIG_FILE"
echo "Validation timestamp: $(date)"

# Simulate validation process with verbose output to stdout
echo "Checking file existence..."
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file '$CONFIG_FILE' not found" >&2
    exit 1
fi

echo "Parsing YAML structure..."
echo "Validating required fields..."
echo "Checking data types..."

# Simulate some warnings to stderr (these should be filtered out with attach_stderr: false)
echo "WARNING: Deprecated field 'old_setting' found in config" >&2
echo "INFO: Using default value for optional field 'timeout'" >&2

# Simulate validation results
if [[ "$CONFIG_FILE" == *"invalid"* ]]; then
    echo "VALIDATION FAILED: Invalid configuration detected" >&2
    echo "ERROR: Missing required field 'database.host'" >&2
    echo "ERROR: Invalid value for 'port': must be a number" >&2
    exit 1
else
    echo "Configuration validation completed successfully"
    echo "All required fields present and valid"
    exit 0
fi
