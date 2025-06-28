#!/bin/bash

# Wu Wei Extension Test Runner
# Usage: ./scripts/test.sh [unit|integration|all|help]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[Wu Wei Tests]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[Wu Wei Tests]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[Wu Wei Tests]${NC} $1"
}

print_error() {
    echo -e "${RED}[Wu Wei Tests]${NC} $1"
}

# Function to show help
show_help() {
    echo "Wu Wei Extension Test Runner"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  unit         Run pure unit tests only (fast, ~5 seconds)"
    echo "  integration  Run VS Code integration tests (slower, ~30-60 seconds)"
    echo "  all          Run both unit and integration tests sequentially"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 unit                    # Quick unit tests during development"
    echo "  $0 integration            # Full VS Code environment tests"
    echo "  $0 all                    # Complete test suite"
    echo ""
    echo "NPM Script Equivalents:"
    echo "  npm run test:unit         # Same as '$0 unit'"
    echo "  npm run test:integration  # Same as '$0 integration'"
    echo "  npm run test:all          # Same as '$0 all'"
}

# Function to run unit tests
run_unit_tests() {
    print_status "Running pure unit tests..."
    print_status "These tests run quickly without VS Code environment"
    echo ""
    
    if npm run test:unit; then
        print_success "Unit tests completed successfully!"
        return 0
    else
        print_error "Unit tests failed!"
        return 1
    fi
}

# Function to run integration tests
run_integration_tests() {
    print_status "Running VS Code integration tests..."
    print_status "These tests require VS Code environment and take longer"
    echo ""
    
    if npm run test:integration; then
        print_success "Integration tests completed successfully!"
        return 0
    else
        print_error "Integration tests failed!"
        return 1
    fi
}

# Function to run all tests
run_all_tests() {
    print_status "Running complete test suite..."
    print_status "This will run unit tests first, then integration tests"
    echo ""
    
    local unit_result=0
    local integration_result=0
    
    # Run unit tests first
    print_status "Step 1/2: Running unit tests..."
    if ! run_unit_tests; then
        unit_result=1
        print_warning "Unit tests failed, but continuing with integration tests..."
    fi
    
    echo ""
    print_status "Step 2/2: Running integration tests..."
    if ! run_integration_tests; then
        integration_result=1
    fi
    
    # Summary
    echo ""
    print_status "Test Summary:"
    if [ $unit_result -eq 0 ]; then
        print_success "✓ Unit tests: PASSED"
    else
        print_error "✗ Unit tests: FAILED"
    fi
    
    if [ $integration_result -eq 0 ]; then
        print_success "✓ Integration tests: PASSED"
    else
        print_error "✗ Integration tests: FAILED"
    fi
    
    if [ $unit_result -eq 0 ] && [ $integration_result -eq 0 ]; then
        print_success "All tests completed successfully!"
        return 0
    else
        print_error "Some tests failed!"
        return 1
    fi
}

# Main script logic
case "${1:-help}" in
    "unit")
        run_unit_tests
        ;;
    "integration")
        run_integration_tests
        ;;
    "all")
        run_all_tests
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac 