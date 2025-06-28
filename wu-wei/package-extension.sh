#!/bin/bash

# Wu Wei VS Code Extension Packaging Script
# This script builds and packages the Wu Wei VS Code extension

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_NAME="wu-wei"
OUTPUT_DIR="$SCRIPT_DIR/dist"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
check_directory() {
    if [[ ! -f "package.json" ]]; then
        log_error "package.json not found. Please run this script from the wu-wei extension root directory."
        exit 1
    fi

    if [[ ! $(grep -q "wu-wei" package.json) ]]; then
        log_warning "This doesn't appear to be the wu-wei extension directory."
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed. Please install Node.js first."
        exit 1
    fi

    # Check npm
    if ! command -v npm &> /dev/null; then
        log_error "npm is not installed. Please install npm first."
        exit 1
    fi

    # Check if vsce is installed globally, if not suggest installation
    if ! command -v vsce &> /dev/null; then
        log_warning "vsce (Visual Studio Code Extension manager) is not installed globally."
        log_info "Installing vsce locally for this build..."
        npm install --no-save @vscode/vsce
        VSCE_CMD="npx vsce"
    else
        VSCE_CMD="vsce"
    fi

    log_success "Prerequisites check passed."
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies..."
    
    if [[ -f "package-lock.json" ]]; then
        npm ci
    else
        npm install
    fi
    
    log_success "Dependencies installed."
}

# Clean previous builds
clean_build() {
    log_info "Cleaning previous builds..."
    
    # Clean npm build artifacts
    npm run clean 2>/dev/null || true
    
    # Remove dist directory
    rm -rf "$OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
    
    # Remove any existing .vsix files
    rm -f *.vsix
    
    log_success "Build artifacts cleaned."
}

# Run linting
run_lint() {
    log_info "Running linter..."
    
    if npm run lint; then
        log_success "Linting passed."
    else
        log_warning "Linting failed, but continuing with build..."
    fi
}

# Run tests
run_tests() {
    log_info "Running tests..."
    
    if npm test 2>/dev/null; then
        log_success "Tests passed."
    else
        log_warning "Tests failed or not configured, but continuing with build..."
    fi
}

# Build the extension
build_extension() {
    log_info "Building extension..."
    
    # Run the package script which includes TypeScript compilation and webview copying
    npm run package
    
    log_success "Extension built successfully."
}

# Package the extension
package_extension() {
    log_info "Packaging extension with vsce..."
    
    # Get version from package.json
    VERSION=$(node -p "require('./package.json').version")
    
    # Package the extension
    $VSCE_CMD package --out "$OUTPUT_DIR/${PACKAGE_NAME}-${VERSION}.vsix"
    
    # Also create a copy without version for easy access
    cp "$OUTPUT_DIR/${PACKAGE_NAME}-${VERSION}.vsix" "$OUTPUT_DIR/${PACKAGE_NAME}-latest.vsix"
    
    log_success "Extension packaged: $OUTPUT_DIR/${PACKAGE_NAME}-${VERSION}.vsix"
}

# Validate the package
validate_package() {
    log_info "Validating package..."
    
    local vsix_file="$OUTPUT_DIR/${PACKAGE_NAME}-latest.vsix"
    
    if [[ -f "$vsix_file" ]]; then
        local file_size=$(stat -f%z "$vsix_file" 2>/dev/null || stat -c%s "$vsix_file" 2>/dev/null || echo "unknown")
        log_success "Package created successfully:"
        log_info "  File: $vsix_file"
        log_info "  Size: $file_size bytes"
        
        # Basic validation using vsce
        if $VSCE_CMD ls "$vsix_file" > /dev/null 2>&1; then
            log_success "Package validation passed."
        else
            log_warning "Package validation had issues, but file was created."
        fi
    else
        log_error "Package file not found!"
        exit 1
    fi
}

# Display usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -s, --skip-tests        Skip running tests"
    echo "  -l, --skip-lint         Skip linting"
    echo "  -c, --clean-only        Only clean build artifacts"
    echo "  -q, --quick             Quick build (skip tests and linting)"
    echo "  -v, --verbose           Enable verbose output"
    echo ""
    echo "Examples:"
    echo "  $0                      Full build with tests and linting"
    echo "  $0 --quick              Quick build without tests and linting"
    echo "  $0 --clean-only         Only clean previous builds"
}

# Main function
main() {
    local skip_tests=false
    local skip_lint=false
    local clean_only=false
    local verbose=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -s|--skip-tests)
                skip_tests=true
                shift
                ;;
            -l|--skip-lint)
                skip_lint=true
                shift
                ;;
            -c|--clean-only)
                clean_only=true
                shift
                ;;
            -q|--quick)
                skip_tests=true
                skip_lint=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                set -x
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    log_info "Starting Wu Wei VS Code Extension packaging..."
    log_info "Working directory: $SCRIPT_DIR"

    # Check directory and prerequisites
    check_directory
    check_prerequisites

    # Clean build artifacts
    clean_build

    # If clean-only mode, exit here
    if [[ "$clean_only" == "true" ]]; then
        log_success "Clean completed."
        exit 0
    fi

    # Install dependencies
    install_dependencies

    # Run linting (unless skipped)
    if [[ "$skip_lint" != "true" ]]; then
        run_lint
    fi

    # Run tests (unless skipped)
    if [[ "$skip_tests" != "true" ]]; then
        run_tests
    fi

    # Build and package
    build_extension
    package_extension
    validate_package

    log_success "🎉 Wu Wei VS Code Extension packaging completed!"
    log_info "📦 Package location: $OUTPUT_DIR"
    log_info ""
    log_info "To install the extension:"
    log_info "  code --install-extension $OUTPUT_DIR/${PACKAGE_NAME}-latest.vsix"
    log_info ""
    log_info "To publish to the marketplace:"
    log_info "  $VSCE_CMD publish --packagePath $OUTPUT_DIR/${PACKAGE_NAME}-latest.vsix"
}

# Run main function with all arguments
main "$@"
