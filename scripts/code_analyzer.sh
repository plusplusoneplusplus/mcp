#!/bin/bash

# Code Analyzer - Generate code analysis using ctags or tree-sitter
# This script provides a unified interface for multiple code analysis tools

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
ANALYZER="ctags"  # ctags or treesitter
BUILD_CALL_GRAPH=false
RESOLVE_CALLS=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print usage information
usage() {
    cat << EOF
Code Analyzer - Generate code analysis using ctags or tree-sitter

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

ANALYZER OPTIONS:
    -a, --analyzer TYPE    Analysis engine: ctags, treesitter (default: ctags)
    --call-graph           Generate call graph (tree-sitter only)
    --resolve-calls        Resolve function calls to definitions (tree-sitter only)

EXAMPLES:
    # Basic ctags generation
    $(basename "$0") /path/to/project
    $(basename "$0") . --output tags.json
    $(basename "$0") src --languages "C++,Python"

    # Advanced ctags with custom options
    $(basename "$0") cpp/ --languages "C++" --output tags.json --extra-options "--fields=+n+S+a+K+Z+t --extras=+q"

    # Tree-sitter analysis
    $(basename "$0") . --analyzer treesitter --output analysis.json
    $(basename "$0") src --analyzer treesitter --call-graph --resolve-calls
    $(basename "$0") . --analyzer treesitter --languages "python,javascript" --call-graph

SUPPORTED LANGUAGES:
    ctags:      Most languages supported by Universal ctags
    treesitter: C++, Python, JavaScript, Java

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
            -a|--analyzer)
                ANALYZER="$2"
                if [[ "$ANALYZER" != "ctags" && "$ANALYZER" != "treesitter" ]]; then
                    print_error "Invalid analyzer: $ANALYZER. Must be 'ctags' or 'treesitter'"
                    exit 1
                fi
                shift 2
                ;;
            --call-graph)
                BUILD_CALL_GRAPH=true
                shift
                ;;
            --resolve-calls)
                RESOLVE_CALLS=true
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

# Build the ctags command
build_ctags_cmd() {
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

    echo "${cmd[@]}"
}

# Build the tree-sitter command
build_treesitter_cmd() {
    local cmd=()
    local python_script=""

    # Choose Python runner
    if command_exists uv; then
        cmd+=("uv" "run" "python")
    elif command_exists python3; then
        cmd+=("python3")
    elif command_exists python; then
        cmd+=("python")
    else
        print_error "No Python interpreter found"
        exit 1
    fi

    # Create a temporary Python script for tree-sitter analysis
    python_script=$(cat << 'PYTHON_SCRIPT'
import sys
import json
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.code_indexing.tree_sitter_parser import MultiLanguageParser

def main():
    parser = argparse.ArgumentParser(description='Tree-sitter code analysis')
    parser.add_argument('source_path', help='Source directory or file')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--languages', '-l', help='Comma-separated list of languages')
    parser.add_argument('--call-graph', action='store_true', help='Generate call graph')
    parser.add_argument('--resolve-calls', action='store_true', help='Resolve function calls')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    ts_parser = MultiLanguageParser()

    if args.call_graph:
        # Build call graph
        symbol_table, edges = ts_parser.build_call_graph(args.source_path)

        if args.resolve_calls:
            edges = ts_parser.resolve_calls(symbol_table, edges)

        result = {
            'type': 'call_graph',
            'symbol_table': [
                {
                    'file': file_path,
                    'language': data['language'],
                    'definitions': data['definitions']
                }
                for file_path, data in symbol_table
            ],
            'call_edges': edges
        }
    else:
        # Just parse definitions
        result = {
            'type': 'definitions',
            'files': []
        }

        if Path(args.source_path).is_file():
            files_to_process = [args.source_path]
        else:
            files_to_process = list(ts_parser.walk_files(args.source_path))

        for file_path, src in (files_to_process if not Path(args.source_path).is_file()
                               else [(args.source_path, open(args.source_path, 'rb').read())]):
            language = ts_parser.get_file_language(file_path)
            if language:
                # Filter by languages if specified
                if args.languages:
                    allowed_langs = [l.strip().lower() for l in args.languages.split(',')]
                    if language.lower() not in allowed_langs:
                        continue

                definitions = ts_parser.parse_definitions(src, language)
                result['files'].append({
                    'file': file_path,
                    'language': language,
                    'functions': definitions['functions'],
                    'classes': definitions['classes']
                })

    # Output results
    output_text = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_text)
        if args.verbose:
            print(f"Analysis written to {args.output}", file=sys.stderr)
    else:
        print(output_text)

if __name__ == '__main__':
    main()
PYTHON_SCRIPT
)

    # Write the Python script to a temporary file
    local temp_script="/tmp/treesitter_analysis.py"
    echo "$python_script" > "$temp_script"

    cmd+=("$temp_script")

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

    if [[ "$BUILD_CALL_GRAPH" == true ]]; then
        cmd+=("--call-graph")
    fi

    if [[ "$RESOLVE_CALLS" == true ]]; then
        cmd+=("--resolve-calls")
    fi

    if [[ "$VERBOSE" == true ]]; then
        cmd+=("--verbose")
    fi

    echo "${cmd[@]}"
}

# Validate tree-sitter specific options
validate_treesitter_options() {
    if [[ "$ANALYZER" == "treesitter" ]]; then
        # Check if call graph options are used without tree-sitter
        if [[ "$BUILD_CALL_GRAPH" == true || "$RESOLVE_CALLS" == true ]]; then
            return 0  # Valid for tree-sitter
        fi
    else
        # Check if tree-sitter specific options are used with ctags
        if [[ "$BUILD_CALL_GRAPH" == true ]]; then
            print_error "--call-graph option is only available with --analyzer treesitter"
            exit 1
        fi
        if [[ "$RESOLVE_CALLS" == true ]]; then
            print_error "--resolve-calls option is only available with --analyzer treesitter"
            exit 1
        fi
    fi
}

# Main function
main() {
    # Parse arguments
    parse_args "$@"

    # Validate options
    validate_treesitter_options

    # Check if required modules exist
    if [[ "$ANALYZER" == "ctags" ]]; then
        if [[ ! -f "$PROJECT_ROOT/utils/code_indexing/generator.py" ]]; then
            print_error "ctags generator not found at $PROJECT_ROOT/utils/code_indexing/generator.py"
            exit 1
        fi
    else
        if [[ ! -f "$PROJECT_ROOT/utils/code_indexing/tree_sitter_parser.py" ]]; then
            print_error "tree-sitter parser not found at $PROJECT_ROOT/utils/code_indexing/tree_sitter_parser.py"
            exit 1
        fi
    fi

    # Build and run the appropriate command
    local cmd
    if [[ "$ANALYZER" == "ctags" ]]; then
        cmd=$(build_ctags_cmd)
        if [[ "$VERBOSE" == true ]]; then
            print_info "Using ctags analyzer"
        fi
    else
        cmd=$(build_treesitter_cmd)
        if [[ "$VERBOSE" == true ]]; then
            print_info "Using tree-sitter analyzer"
        fi
    fi

    if [[ "$VERBOSE" == true ]]; then
        print_info "Running: $cmd"
    fi

    # Execute the command
    if eval "$cmd"; then
        if [[ "$LIST_LANGUAGES" != true ]]; then
            print_success "Code analysis completed"
        fi
    else
        print_error "Code analysis failed"
        exit 1
    fi

    # Clean up temporary files for tree-sitter
    if [[ "$ANALYZER" == "treesitter" && -f "/tmp/treesitter_analysis.py" ]]; then
        rm -f "/tmp/treesitter_analysis.py"
    fi
}

# Run main function with all arguments
main "$@"
