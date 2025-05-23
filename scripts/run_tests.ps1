# Script to run all tests in the MCP project
# This will run tests for mcp_core, mcp_tools, and any other tests in the project
#
# Usage:
#   ./run_tests.ps1 [partial_test_name]
#   If [partial_test_name] is provided, only tests matching that pattern will run.

# We'll continue execution even if a test fails
$ErrorActionPreference = "Continue"

# Define colors for output
function Write-ColorMessage {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    
    $originalColor = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $Color
    Write-Host $Message
    $host.UI.RawUI.ForegroundColor = $originalColor
}

Write-ColorMessage "=== Running all tests for MCP project ===" "Blue"
Write-Host ""

# Initialize counters
$failures = 0
$passed = 0
$skipped = 0

# Function to run tests for a specific component
function Run-ComponentTests {
    param(
        [string]$Component,
        [string]$TestPath,
        [string]$TestPattern = ""
    )
    
    if (Test-Path $TestPath -PathType Container) {
        Write-ColorMessage "Running tests for $Component..." "Blue"
        
        # Run the tests and capture output
        try {
            # Use uv instead of python directly
            if ($TestPattern -ne "") {
                $output = & uv run python -m pytest "$TestPath" -k "$TestPattern" 2>&1 | Out-String
            } else {
                $output = & uv run python -m pytest "$TestPath" 2>&1 | Out-String
            }
            $exitCode = $LASTEXITCODE
            
            # Print the output
            Write-Host $output
            
            # Parse output to get test statistics
            if ($output -match "no tests ran") {
                Write-ColorMessage "! No tests ran for $Component" "Yellow"
                $script:skipped++
            }
            elseif ($output -match "collected \d+ items / \d+ deselected / 0 selected") {
                Write-ColorMessage "No matching tests for $Component, skipping." "Yellow"
                $script:skipped++
            }
            elseif (($exitCode -ne 0) -or ($output -match "ERROR") -or ($output -match "FAILED")) {
                # Get summary of failures/passed/skipped from the output
                if ($output -match "(\d+) failed, (\d+) passed, (\d+) skipped") {
                    $summary = $Matches[0]
                    Write-ColorMessage "X Some tests for $Component failed: $summary" "Red"
                }
                elseif (($output -match "ERROR") -and ($output -match "Interrupted")) {
                    Write-ColorMessage "X Tests for $Component failed due to import errors or collection failures" "Red"
                }
                else {
                    Write-ColorMessage "X Tests for $Component failed!" "Red"
                }
                $script:failures++
            }
            else {
                Write-ColorMessage "+ All tests for $Component passed!" "Green"
                $script:passed++
            }
        }
        catch {
            $errorMessage = $_.Exception.Message
            Write-ColorMessage "X Error running tests for ${Component}: $errorMessage" "Red"
            $script:failures++
        }
        Write-Host ""
    }
    else {
        Write-ColorMessage "No tests found for $Component at $TestPath" "Yellow"
        Write-Host ""
        $script:skipped++
    }
}

# Parse optional test pattern argument
$TestPattern = if ($args.Count -ge 1) { $args[0] } else { "" }

# Run tests for each component
Run-ComponentTests "config" "config/tests" $TestPattern
Run-ComponentTests "mcp_core" "mcp_core/tests" $TestPattern
Run-ComponentTests "mcp_tools" "mcp_tools/tests" $TestPattern
Run-ComponentTests "server" "server/tests" $TestPattern
Run-ComponentTests "utils.html_to_markdown" "utils/html_to_markdown/tests" $TestPattern
Run-ComponentTests "utils.vector_store" "utils/vector_store/tests" $TestPattern
Run-ComponentTests "utils.secret_scanner" "utils/secret_scanner/tests" $TestPattern
Run-ComponentTests "utils.ocr_extractor" "utils/ocr_extractor/tests" $TestPattern
Run-ComponentTests "utils.playwright" "utils/playwright/tests" $TestPattern

# Run tests for plugins
Run-ComponentTests "plugins.azrepo" "plugins/azrepo/tests" $TestPattern
Run-ComponentTests "plugins.kusto" "plugins/kusto/tests" $TestPattern
# Add more plugin components as needed

# Run project-level tests if they exist
if (Test-Path "tests" -PathType Container) {
    Run-ComponentTests "project" "tests" $TestPattern
}

# Print summary
Write-ColorMessage "=== Test Summary ===" "Blue"
if ($failures -gt 0) {
    Write-ColorMessage "$failures test suite(s) had failures!" "Red"
}
elseif ($passed -eq 0) {
    Write-ColorMessage "No test suites were executed successfully." "Yellow"
}
else {
    Write-ColorMessage "All $passed test suite(s) completed successfully!" "Green"
}

if ($skipped -gt 0) {
    Write-ColorMessage "$skipped test suite(s) were skipped." "Yellow"
}

# Exit with error code if any failures
if ($failures -gt 0) {
    exit 1
}

exit 0 