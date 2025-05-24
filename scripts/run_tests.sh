#!/bin/bash
# Script to run all tests in the MCP project
# This will run tests for mcp_core, mcp_tools, and any other tests in the project

# Don't exit immediately on error - we want to run all test suites
set +e

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Running all tests for MCP project ===${NC}"
echo ""

# Initialize counters
failures=0
passed=0
skipped=0

# Function to run tests for a specific component
run_component_tests() {
    component=$1
    test_path=$2
    test_pattern=$3
    
    if [ -d "$test_path" ]; then
        echo -e "${BLUE}Running tests for ${component}...${NC}"
        
        # Run the tests and capture both exit code and output
        # Use uv instead of python directly
        if [ -n "$test_pattern" ]; then
            output=$(uv run python -m pytest "$test_path" -k "$test_pattern" 2>&1)
        else
            output=$(uv run python -m pytest "$test_path" 2>&1)
        fi
        exit_code=$?
        
        # Print the output
        echo "$output"
        
        # Parse output to get test statistics
        if [[ "$output" == *"no tests ran"* ]]; then
            echo -e "${YELLOW}\u26a0 No tests ran for ${component}${NC}"
            skipped=$((skipped + 1))
        elif echo "$output" | grep -qE "collected [0-9]+ items / [0-9]+ deselected / 0 selected"; then
            # All tests were deselected, treat as skipped/ignored, no arrow
            echo -e "${YELLOW}No matching tests for ${component}, skipping.${NC}"
            skipped=$((skipped + 1))
        elif [[ $exit_code -ne 0 || "$output" == *"ERROR"* || "$output" == *"FAILED"* ]]; then
            # Get summary of failures/passed/skipped from the output
            if [[ "$output" == *"failed"*"passed"* ]]; then
                # Extract numbers from the test summary line
                summary=$(echo "$output" | grep -o '[0-9]* failed, [0-9]* passed, [0-9]* skipped' | head -1)
                echo -e "${RED}\u2717 Some tests for ${component} failed: ${summary}${NC}"
            elif [[ "$output" == *"ERROR"* && "$output" == *"Interrupted"* ]]; then
                echo -e "${RED}\u2717 Tests for ${component} failed due to import errors or collection failures${NC}"
            else
                echo -e "${RED}\u2717 Tests for ${component} failed!${NC}"
            fi
            failures=$((failures + 1))
        else
            echo -e "${GREEN}\u2713 All tests for ${component} passed!${NC}"
            passed=$((passed + 1))
        fi
        echo ""
    else
        echo -e "${YELLOW}No tests found for ${component} at ${test_path}${NC}"
        echo ""
        skipped=$((skipped + 1))
    fi
}

# Parse optional test pattern argument
TEST_PATTERN="$1"

# Run tests for each component
run_component_tests "config" "config/tests" "$TEST_PATTERN"
run_component_tests "mcp_core" "mcp_core/tests" "$TEST_PATTERN"
run_component_tests "mcp_tools" "mcp_tools/tests" "$TEST_PATTERN"
run_component_tests "server" "server/tests" "$TEST_PATTERN"
run_component_tests "utils.html_to_markdown" "utils/html_to_markdown/tests" "$TEST_PATTERN"
run_component_tests "utils.vector_store" "utils/vector_store/tests" "$TEST_PATTERN"
run_component_tests "utils.secret_scanner" "utils/secret_scanner/tests" "$TEST_PATTERN"
run_component_tests "utils.ocr_extractor" "utils/ocr_extractor/tests" "$TEST_PATTERN"
run_component_tests "utils.playwright" "utils/playwright/tests" "$TEST_PATTERN"

# Run tests for plugins
run_component_tests "plugins.azrepo" "plugins/azrepo/tests" "$TEST_PATTERN"
run_component_tests "plugins.kusto" "plugins/kusto/tests" "$TEST_PATTERN"
# Add more plugin components as needed

# Run project-level tests if they exist
if [ -d "tests" ]; then
    run_component_tests "project" "tests" "$TEST_PATTERN"
fi

# Print summary
echo -e "${BLUE}=== Test Summary ===${NC}"
if [ $failures -gt 0 ]; then
    echo -e "${RED}${failures} test suite(s) had failures!${NC}"
elif [ $passed -eq 0 ]; then
    echo -e "${YELLOW}No test suites were executed successfully.${NC}"
else
    echo -e "${GREEN}All ${passed} test suite(s) completed successfully!${NC}"
fi

if [ $skipped -gt 0 ]; then
    echo -e "${YELLOW}${skipped} test suite(s) were skipped.${NC}"
fi

# Exit with error code if any failures
if [ $failures -gt 0 ]; then
    exit 1
fi

exit 0 