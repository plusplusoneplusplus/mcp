#!/usr/bin/env python3
"""
CLI tool for segmenting markdown files and interacting with a vector store.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to sys.path to allow importing from utils and mcp_tools
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from utils.segmenter import (
    SegmenterWorkflow,
    create_parser,
    validate_and_process_args,
    args_to_configs,
)


async def main():
    """Main CLI function."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Validate and process arguments (fixes the persist_directory linter error)
        args = validate_and_process_args(parser, args)

        # Convert arguments to configuration objects
        segmenter_config, vector_store_config, search_config = args_to_configs(args)

        # Initialize the workflow
        workflow = SegmenterWorkflow(segmenter_config, vector_store_config)

        if args.operation == "segment":
            print(f"Segmenting markdown file: {args.input_file}...")
            result = workflow.segment_file(args.input_file)
            print(f"Found {result.total_count} segments.")
            print(json.dumps(result.segments, indent=2))

        elif args.operation == "store":
            print(
                f"Segmenting and storing markdown file: {args.input_file} into collection '{vector_store_config.collection_name}'..."
            )
            result = workflow.store_file(args.input_file)
            print(f"Successfully stored {result.total_stored} segments.")
            print(f"Text segments stored: {len(result.segment_ids_by_type.get('text', []))}")
            print(f"Table segments stored: {len(result.segment_ids_by_type.get('table', []))}")
            print(f"Segment IDs: {json.dumps(result.segment_ids_by_type, indent=2)}")

        elif args.operation == "search":
            print(
                f"Searching collection '{vector_store_config.collection_name}' with query: '{args.query}'..."
            )
            result = workflow.search(search_config, args.query)
            print("Search results:")
            print(json.dumps(result.results, indent=2))

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    # Keep async for potential future async operations in underlying libs
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
