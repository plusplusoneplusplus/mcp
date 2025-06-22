#!/bin/bash
# Script to run specific groups of test components for parallel CI execution
# This script is designed to work with the GitHub Actions matrix strategy
#
# Usage:
#   ./run_component_group.sh <group_name> [test_pattern]
#
# Groups:
#   core-group      - config, mcp_core, mcp_tools
#   server-group    - server, project tests
#   utils-group-1   - html_to_markdown, vector_store, secret_scanner
#   utils-group-2   - ocr_extractor, playwright, graph_interface
#   plugins-group-1 - azrepo, kusto
#   plugins-group-2 - git_tool, knowledge_indexer

# Don't exit immediately on error - we want to run all test suites in the group
set +e

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
GROUP_NAME="$1"
TEST_PATTERN="$2"

if [ -z "$GROUP_NAME" ]; then
    echo -e "${RED}Error: Group name is required${NC}"
    echo "Usage: $0 <group_name> [test_pattern]"
    echo "Available groups: core-group, server-group, utils-group-1, utils-group-2, plugins-group-1, plugins-group-2"
    exit 1
fi

echo -e "${BLUE}=== Running test group: ${GROUP_NAME} ===${NC}"
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
        # Use uv instead of python directly with parallel execution
        if [ -n "$test_pattern" ]; then
            output=$(uv run python -m pytest "$test_path" -k "$test_pattern" -n auto 2>&1)
        else
            output=$(uv run python -m pytest "$test_path" -n auto 2>&1)
        fi
        exit_code=$?

        # Print the output
        echo "$output"

        # Parse output to get test statistics
        if [[ "$output" == *"no tests ran"* ]]; then
            echo -e "${YELLOW}\u26a0 No tests ran for ${component}${NC}"
            skipped=$((skipped + 1))
        elif echo "$output" | grep -qE "collected [0-9]+ items / [0-9]+ deselected / 0 selected"; then
            # All tests were deselected, treat as skipped/ignored
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

# Define component groups
case "$GROUP_NAME" in
    "core-group")
        echo -e "${BLUE}Running core components: config, mcp_core, mcp_tools${NC}"
        echo ""
        run_component_tests "config" "config/tests" "$TEST_PATTERN"
        run_component_tests "mcp_core" "mcp_core/tests" "$TEST_PATTERN"
        run_component_tests "mcp_tools" "mcp_tools/tests" "$TEST_PATTERN"
        ;;

    "server-group")
        echo -e "${BLUE}Running server components: server, project tests${NC}"
        echo ""
        run_component_tests "server" "server/tests" "$TEST_PATTERN"
        # Run project-level tests if they exist
        if [ -d "tests" ]; then
            run_component_tests "project" "tests" "$TEST_PATTERN"
        fi
        ;;

    "utils-group-1")
        echo -e "${BLUE}Running utils group 1: html_to_markdown, vector_store, secret_scanner, memory${NC}"
        echo ""
        run_component_tests "utils.html_to_markdown" "utils/html_to_markdown/tests" "$TEST_PATTERN"
        run_component_tests "utils.vector_store" "utils/vector_store/tests" "$TEST_PATTERN"
        run_component_tests "utils.secret_scanner" "utils/secret_scanner/tests" "$TEST_PATTERN"
        run_component_tests "utils.memory" "utils/memory/tests" "$TEST_PATTERN"
        ;;

    "utils-group-2")
        echo -e "${BLUE}Running utils group 2: ocr_extractor, playwright, graph_interface${NC}"
        echo ""
        run_component_tests "utils.ocr_extractor" "utils/ocr_extractor/tests" "$TEST_PATTERN"
        run_component_tests "utils.playwright" "utils/playwright/tests" "$TEST_PATTERN"
        run_component_tests "utils.graph_interface" "utils/graph_interface/tests" "$TEST_PATTERN"
        ;;

    "plugins-group-1")
        echo -e "${BLUE}Running plugins group 1: azrepo, kusto${NC}"
        echo ""
        run_component_tests "plugins.azrepo" "plugins/azrepo/tests" "$TEST_PATTERN"
        run_component_tests "plugins.kusto" "plugins/kusto/tests" "$TEST_PATTERN"
        ;;

    "plugins-group-2")
        echo -e "${BLUE}Running plugins group 2: git_tool, knowledge_indexer${NC}"
        echo ""
        run_component_tests "plugins.git_tool" "plugins/git_tool/tests" "$TEST_PATTERN"
        run_component_tests "plugins.knowledge_indexer" "plugins/knowledge_indexer/tests" "$TEST_PATTERN"
        ;;

    *)
        echo -e "${RED}Error: Unknown group name '${GROUP_NAME}'${NC}"
        echo "Available groups: core-group, server-group, utils-group-1, utils-group-2, plugins-group-1, plugins-group-2"
        exit 1
        ;;
esac

# Print summary
echo -e "${BLUE}=== Test Group Summary: ${GROUP_NAME} ===${NC}"
if [ $failures -gt 0 ]; then
    echo -e "${RED}${failures} test component(s) had failures!${NC}"
elif [ $passed -eq 0 ]; then
    echo -e "${YELLOW}No test components were executed successfully.${NC}"
else
    echo -e "${GREEN}All ${passed} test component(s) completed successfully!${NC}"
fi

if [ $skipped -gt 0 ]; then
    echo -e "${YELLOW}${skipped} test component(s) were skipped.${NC}"
fi

# Exit with error code if any failures
if [ $failures -gt 0 ]; then
    exit 1
fi

exit 0
