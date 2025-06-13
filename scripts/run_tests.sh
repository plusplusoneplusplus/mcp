#!/bin/bash
# Simple wrapper script to run all test component groups
# Usage:
#   ./run_tests.sh [test_pattern] [--parallel|-p] [max_jobs]

set +e

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Running all tests for MCP project ===${NC}"

# Get script directory and component group script path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPONENT_GROUP_SCRIPT="$SCRIPT_DIR/run_component_group.sh"

# Parse arguments
TEST_PATTERN="$1"
PARALLEL_MODE="$2"
MAX_JOBS="${3:-6}"

# Component groups to run
GROUPS=("core-group" "server-group" "utils-group-1" "utils-group-2" "plugins-group-1" "plugins-group-2")

# Initialize counters
total_failures=0

if [[ "$PARALLEL_MODE" == "--parallel" || "$PARALLEL_MODE" == "-p" ]]; then
    echo -e "${BLUE}Running ${#GROUPS[@]} component groups in parallel (max $MAX_JOBS jobs)...${NC}"

    # Run all groups in parallel and collect PIDs
    pids=()
    for group in "${GROUPS[@]}"; do
        if [ -n "$TEST_PATTERN" ]; then
            "$COMPONENT_GROUP_SCRIPT" "$group" "$TEST_PATTERN" &
        else
            "$COMPONENT_GROUP_SCRIPT" "$group" &
        fi
        pids+=($!)
    done

    # Wait for all and collect exit codes
    for pid in "${pids[@]}"; do
        wait $pid
        if [ $? -ne 0 ]; then
            total_failures=$((total_failures + 1))
        fi
    done
else
    echo -e "${BLUE}Running ${#GROUPS[@]} component groups sequentially...${NC}"

    # Run groups sequentially
    for group in "${GROUPS[@]}"; do
        if [ -n "$TEST_PATTERN" ]; then
            "$COMPONENT_GROUP_SCRIPT" "$group" "$TEST_PATTERN"
        else
            "$COMPONENT_GROUP_SCRIPT" "$group"
        fi
        if [ $? -ne 0 ]; then
            total_failures=$((total_failures + 1))
        fi
    done
fi

# Final summary
echo -e "${BLUE}=== Final Summary ===${NC}"
if [ $total_failures -eq 0 ]; then
    echo -e "${GREEN}All component groups completed successfully!${NC}"
    exit 0
else
    echo -e "${RED}${total_failures} component group(s) had failures!${NC}"
    exit 1
fi
