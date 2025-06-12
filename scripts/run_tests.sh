#!/bin/bash
# Script to run all tests in the MCP project
# This will run tests for mcp_core, mcp_tools, and any other tests in the project
#
# Usage:
#   ./run_tests.sh [test_pattern] [--parallel|-p] [max_jobs]
#
#   test_pattern: Optional pytest pattern to filter tests (e.g., "test_async")
#   --parallel|-p: Run test components in parallel for faster execution
#   max_jobs: Maximum number of concurrent test components (default: 4)
#
# Examples:
#   ./run_tests.sh                    # Run all tests sequentially
#   ./run_tests.sh "" --parallel      # Run all tests in parallel (4 jobs)
#   ./run_tests.sh "" -p 8            # Run all tests in parallel (8 jobs)
#   ./run_tests.sh "test_async" -p 2  # Run async tests in parallel (2 jobs)

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

# Function to run tests for a specific component in parallel
run_component_tests_parallel() {
    component=$1
    test_path=$2
    test_pattern=$3
    result_file=$4

    if [ -d "$test_path" ]; then
        echo -e "${BLUE}Starting tests for ${component}...${NC}"

        # Run the tests and capture both exit code and output
        # Use uv instead of python directly with parallel execution
        if [ -n "$test_pattern" ]; then
            output=$(uv run python -m pytest "$test_path" -k "$test_pattern" -n auto 2>&1)
        else
            output=$(uv run python -m pytest "$test_path" -n auto 2>&1)
        fi
        exit_code=$?

        # Write results to temporary file
        echo "COMPONENT:$component" > "$result_file"
        echo "EXIT_CODE:$exit_code" >> "$result_file"
        echo "OUTPUT_START" >> "$result_file"
        echo "$output" >> "$result_file"
        echo "OUTPUT_END" >> "$result_file"
    else
        echo "COMPONENT:$component" > "$result_file"
        echo "EXIT_CODE:404" >> "$result_file"
        echo "OUTPUT_START" >> "$result_file"
        echo "No tests found for ${component} at ${test_path}" >> "$result_file"
        echo "OUTPUT_END" >> "$result_file"
    fi
}

# Function to process results from parallel execution
process_parallel_results() {
    result_file=$1
    component=$(grep "^COMPONENT:" "$result_file" | cut -d: -f2)
    exit_code=$(grep "^EXIT_CODE:" "$result_file" | cut -d: -f2)

    # Extract output between OUTPUT_START and OUTPUT_END
    output=$(sed -n '/^OUTPUT_START$/,/^OUTPUT_END$/p' "$result_file" | sed '1d;$d')

    echo -e "${BLUE}Results for ${component}:${NC}"
    echo "$output"

    if [[ "$exit_code" == "404" ]]; then
        echo -e "${YELLOW}No tests found for ${component}${NC}"
        skipped=$((skipped + 1))
    elif [[ "$output" == *"no tests ran"* ]]; then
        echo -e "${YELLOW}\u26a0 No tests ran for ${component}${NC}"
        skipped=$((skipped + 1))
    elif echo "$output" | grep -qE "collected [0-9]+ items / [0-9]+ deselected / 0 selected"; then
        echo -e "${YELLOW}No matching tests for ${component}, skipping.${NC}"
        skipped=$((skipped + 1))
    elif [[ $exit_code -ne 0 || "$output" == *"ERROR"* || "$output" == *"FAILED"* ]]; then
        if [[ "$output" == *"failed"*"passed"* ]]; then
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
}

# Parse arguments - handle different orders and combinations
TEST_PATTERN=""
PARALLEL_MODE=""
MAX_PARALLEL_JOBS="4"

# Parse all arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --parallel|-p)
            PARALLEL_MODE="--parallel"
            shift
            # Check if next argument is a number (max jobs)
            if [[ $1 =~ ^[0-9]+$ ]]; then
                MAX_PARALLEL_JOBS="$1"
                shift
            fi
            ;;
        *)
            # If it's not a flag and we don't have a test pattern yet, use it as test pattern
            if [[ -z "$TEST_PATTERN" ]]; then
                TEST_PATTERN="$1"
            fi
            shift
            ;;
    esac
done

# Check if parallel mode is requested
if [[ "$PARALLEL_MODE" == "--parallel" || "$PARALLEL_MODE" == "-p" ]]; then
    echo -e "${BLUE}Running tests in parallel mode (max $MAX_PARALLEL_JOBS concurrent jobs)...${NC}"
    echo ""

    # Create temporary directory for results
    temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" EXIT

    # Array to store background process PIDs and result files
    declare -a pids=()
    declare -a result_files=()

    # Start all test components in parallel
    components=(
        "config:config/tests"
        "mcp_core:mcp_core/tests"
        "mcp_tools:mcp_tools/tests"
        "server:server/tests"
        "utils.html_to_markdown:utils/html_to_markdown/tests"
        "utils.vector_store:utils/vector_store/tests"
        "utils.secret_scanner:utils/secret_scanner/tests"
        "utils.ocr_extractor:utils/ocr_extractor/tests"
        "utils.playwright:utils/playwright/tests"
        "utils.graph_interface:utils/graph_interface/tests"
        "plugins.azrepo:plugins/azrepo/tests"
        "plugins.kusto:plugins/kusto/tests"
        "plugins.git_tool:plugins/git_tool/tests"
        "plugins.knowledge_indexer:plugins/knowledge_indexer/tests"
    )

    # Add project-level tests if they exist
    if [ -d "tests" ]; then
        components+=("project:tests")
    fi

    # Function to wait for available slot
    wait_for_slot() {
        while [ ${#pids[@]} -ge $MAX_PARALLEL_JOBS ]; do
            # Check if any process has completed
            for i in "${!pids[@]}"; do
                if ! kill -0 "${pids[$i]}" 2>/dev/null; then
                    # Process completed, remove from array
                    unset pids[$i]
                fi
            done
            # Rebuild array to remove gaps
            pids=("${pids[@]}")

            # If still at max capacity, wait a bit
            if [ ${#pids[@]} -ge $MAX_PARALLEL_JOBS ]; then
                sleep 0.1
            fi
        done
    }

    # Start background processes with thread limiting
    for component_info in "${components[@]}"; do
        component=$(echo "$component_info" | cut -d: -f1)
        test_path=$(echo "$component_info" | cut -d: -f2)
        result_file="$temp_dir/result_${component//[.\/]/_}.txt"
        result_files+=("$result_file")

        # Wait for available slot before starting new process
        wait_for_slot

        echo -e "${BLUE}Starting ${component} (${#pids[@]}/$MAX_PARALLEL_JOBS slots used)...${NC}"
        run_component_tests_parallel "$component" "$test_path" "$TEST_PATTERN" "$result_file" &
        pids+=($!)
    done

    # Wait for all background processes to complete
    echo -e "${BLUE}Waiting for all test suites to complete...${NC}"
    for pid in "${pids[@]}"; do
        wait $pid
    done

    # Process and display results
    echo -e "${BLUE}Processing results...${NC}"
    echo ""
    for result_file in "${result_files[@]}"; do
        if [ -f "$result_file" ]; then
            process_parallel_results "$result_file"
        fi
    done

else
    # Original sequential mode
    echo -e "${BLUE}Running tests in sequential mode...${NC}"
    echo ""

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
    run_component_tests "utils.graph_interface" "utils/graph_interface/tests" "$TEST_PATTERN"

    # Run tests for plugins
    run_component_tests "plugins.azrepo" "plugins/azrepo/tests" "$TEST_PATTERN"
    run_component_tests "plugins.kusto" "plugins/kusto/tests" "$TEST_PATTERN"
    run_component_tests "plugins.git_tool" "plugins/git_tool/tests" "$TEST_PATTERN"
    run_component_tests "plugins.knowledge_indexer" "plugins/knowledge_indexer/tests" "$TEST_PATTERN"
    # Add more plugin components as needed

    # Run project-level tests if they exist
    if [ -d "tests" ]; then
        run_component_tests "project" "tests" "$TEST_PATTERN"
    fi
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
