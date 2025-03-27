# Get the directory where the script is located
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

# Run unit tests first
Write-Host "Running unit tests..."
pytest "$SCRIPT_DIR\tests\test_browser_utils.py" -v

# Run integration tests
Write-Host "`nRunning integration tests..."
pytest "$SCRIPT_DIR\tests\test_command_executor_integration.py" -v

# Run all tests with coverage, skip for now
# Write-Host "`nRunning all tests with coverage..."
# pytest "$SCRIPT_DIR\tests" --cov=sentinel --cov-report=term-missing 