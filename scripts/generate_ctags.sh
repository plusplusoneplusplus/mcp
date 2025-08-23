#!/bin/bash

# Generate ctags for code projects using Universal ctags
# This script provides a simple interface to the Python ctags generator

set -euo pipefail

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
SOURCE_PATH=""
OUTPUT_FILE=""
FORMAT="ndjson"
LANGUAGES=""
EXCLUDE_PATTERNS=()
INCLUDE_PATTERNS=()
EXTRA_OPTIONS=""
ABSOLUTE_PATHS=false
VERBOSE=false
LIST_LANGUAGES=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print usage information
usage() {
    cat << EOF
Generate ctags for code projects using Universal ctags

USAGE:
    $(basename "$0") [OPTIONS] <source_path>

ARGUMENTS:
    <source_path>          Path to the source code directory or file

OPTIONS:
    -o, --output FILE      Output file path (default: stdout for some formats)
    -f, --format FORMAT    Output format: ndjson, json, ctags, etags, xref (default: ndjson)
    -l, --languages LANGS  Comma-separated list of languages to include
    -e, --exclude PATTERN  Exclude pattern (can be used multiple times)
    -i, --include PATTERN  Include pattern (can be used multiple times)
    --extra-options OPTS   Additional ctags options as a string
    --absolute-paths       Use absolute paths in output (if supported by ctags version)
    -v, --verbose          Verbose output
    --list-languages       List supported languages and exit
    -h, --help             Show this help message

EXAMPLES:
    $(basename "$0") /path/to/project
    $(basename "$0") . --output tags.json
    $(basename "$0") src --languages "C++,Python"
    $(basename "$0") cpp/ --languages "C++" --output tags.json --extra-options "--fields=+n+S+a+K+Z+t --extras=+q"

Note: This script currently wraps the existing generator.py which has limited options.
      Some advanced features like exclude/include patterns and format selection
      are not yet supported and would require enhancing the underlying Python module.

ENVIRONMENT:
    The script will use 'uv run' if available, otherwise fall back to 'python3'

EOF
}

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -o|--output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            -f|--format)
                FORMAT="$2"
                shift 2
                ;;
            -l|--languages)
                LANGUAGES="$2"
                shift 2
                ;;
            -e|--exclude)
                EXCLUDE_PATTERNS+=("$2")
                shift 2
                ;;
            -i|--include)
                INCLUDE_PATTERNS+=("$2")
                shift 2
                ;;
            --extra-options)
                EXTRA_OPTIONS="$2"
                shift 2
                ;;
            --absolute-paths)
                ABSOLUTE_PATHS=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --list-languages)
                LIST_LANGUAGES=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            -*)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                if [[ -z "$SOURCE_PATH" ]]; then
                    SOURCE_PATH="$1"
                else
                    print_error "Multiple source paths specified"
                    exit 1
                fi
                shift
                ;;
        esac
    done
}

# Build the Python command
build_python_cmd() {
    local cmd=()

    # Choose Python runner
    if command_exists uv; then
        cmd+=("uv" "run")
    elif command_exists python3; then
        cmd+=("python3")
    elif command_exists python; then
        cmd+=("python")
    else
        print_error "No Python interpreter found"
        exit 1
    fi

    # Add the script path
    cmd+=("$PROJECT_ROOT/utils/code_indexing/generator.py")

    # Add arguments based on the existing generator.py interface
    if [[ "$LIST_LANGUAGES" == true ]]; then
        print_warning "--list-languages not supported by current generator"
        echo "${cmd[@]}"
        return
    fi

    if [[ -z "$SOURCE_PATH" ]]; then
        print_error "Source path is required"
        exit 1
    fi

    cmd+=("$SOURCE_PATH")

    if [[ -n "$OUTPUT_FILE" ]]; then
        cmd+=("--output" "$OUTPUT_FILE")
    fi

    if [[ -n "$LANGUAGES" ]]; then
        cmd+=("--languages" "$LANGUAGES")
    fi

    # Handle extra options by parsing them for --extras and --fields
    if [[ -n "$EXTRA_OPTIONS" ]]; then
        # Extract --extras and --fields from extra options
        if [[ "$EXTRA_OPTIONS" == *"--extras="* ]]; then
            local extras_val
            extras_val=$(echo "$EXTRA_OPTIONS" | grep -o '--extras=[^ ]*' | sed 's/--extras=//')
            if [[ -n "$extras_val" ]]; then
                cmd+=("--extras" "$extras_val")
            fi
        fi

        if [[ "$EXTRA_OPTIONS" == *"--fields="* ]]; then
            local fields_val
            fields_val=$(echo "$EXTRA_OPTIONS" | grep -o '--fields=[^ ]*' | sed 's/--fields=//')
            if [[ -n "$fields_val" ]]; then
                cmd+=("--fields" "$fields_val")
            fi
        fi
    fi

    # Note: Some options like exclude patterns, include patterns, format selection
    # are not directly supported by the current generator.py and would need enhancement

    echo "${cmd[@]}"
}

# Main function
main() {
    # Parse arguments
    parse_args "$@"

    # Check if the CLI module exists
    if [[ ! -f "$PROJECT_ROOT/utils/code_indexing/cli.py" ]]; then
        print_error "Code indexing CLI not found at $PROJECT_ROOT/utils/code_indexing/cli.py"
        exit 1
    fi

    # Build and run the command
    local cmd
    cmd=$(build_python_cmd)

    if [[ "$VERBOSE" == true ]]; then
        print_info "Running: $cmd"
    fi

    # Execute the command
    if eval "$cmd"; then
        if [[ "$LIST_LANGUAGES" != true ]]; then
            print_success "ctags generation completed"
        fi
    else
        print_error "ctags generation failed"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
