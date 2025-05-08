#!/usr/bin/env python3
"""
CLI tool for segmenting markdown files and interacting with a vector store.
"""

import os
import argparse
import asyncio
import json
from pathlib import Path
import sys

# Add project root to sys.path to allow importing from utils and mcp_tools
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from utils.vector_store.vector_store import ChromaVectorStore
from utils.vector_store.markdown_segmenter import MarkdownSegmenter

async def main():
    # Get the scripts directory path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_persist_path = os.path.join(script_dir, '.vector_store')

    parser = argparse.ArgumentParser(description='Segment markdown files and interact with a vector store.')
    
    parser.add_argument('input_file', nargs='?', default=None, help='Path to the input markdown file (required for "segment" and "store" operations).')
    
    parser.add_argument('--operation', '-o', choices=['segment', 'store', 'search'], required=True,
                        help='Operation to perform: "segment" (prints segments), "store" (segments and stores), or "search".')
    
    # Vector Store Arguments
    parser.add_argument('--collection-name', default='default_segments',
                        help='Name of the collection in the vector store (default: default_segments).')
    parser.add_argument('--persist-directory', default=None,
                        help=f'Directory for persistent vector store storage. If not provided, an in-memory DB is used. Default for new persistent DB: {default_persist_path}')
    
    # Segmenter Arguments
    parser.add_argument('--model-name', default='all-MiniLM-L6-v2',
                        help='SentenceTransformer model name for embeddings (default: all-MiniLM-L6-v2).')
    parser.add_argument('--chunk-size', type=int, default=1000,
                        help='Maximum size of text chunks in characters (default: 1000).')
    parser.add_argument('--chunk-overlap', type=int, default=200,
                        help='Overlap between text chunks in characters (default: 200).')
    parser.add_argument('--table-max-rows', type=int, default=500,
                        help='Maximum number of rows in a table before splitting (default: 500).')
                        
    # Search Arguments
    parser.add_argument('--query', '-q', help='Search query (required for "search" operation).')
    parser.add_argument('--n-results', type=int, default=5,
                        help='Number of search results to return (default: 5, for "search" operation).')
    parser.add_argument('--filter-type', choices=['text', 'table'], default=None,
                        help='Filter search results by segment type (text or table, for "search" operation).')

    args = parser.parse_args()

    # Validate arguments based on operation
    if args.operation in ['segment', 'store'] and not args.input_file:
        parser.error('Input file is required for "segment" and "store" operations.')
    if args.operation == 'search' and not args.query:
        parser.error('Query is required for "search" operation.')
        
    if args.persist_directory == "DEFAULT_PATH": # Special value to use default if user wants persistence
        args.persist_directory = default_persist_path
        os.makedirs(args.persist_directory, exist_ok=True)
        print(f"Using persistent vector store at: {args.persist_directory}")
    elif args.persist_directory:
        os.makedirs(args.persist_directory, exist_ok=True)
        print(f"Using persistent vector store at: {args.persist_directory}")
    else:
        print("Using in-memory vector store.")

    try:
        # Initialize ChromaVectorStore
        vector_store = ChromaVectorStore(
            collection_name=args.collection_name,
            persist_directory=args.persist_directory
        )

        # Initialize MarkdownSegmenter
        segmenter = MarkdownSegmenter(
            vector_store=vector_store,
            model_name=args.model_name,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            table_max_rows=args.table_max_rows
        )

        if args.operation == 'segment':
            if not os.path.exists(args.input_file):
                print(f"Error: Input file not found: {args.input_file}")
                return 1
            with open(args.input_file, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            print(f"Segmenting markdown file: {args.input_file}...")
            segments = segmenter.segment_markdown(markdown_content)
            print(f"Found {len(segments)} segments.")
            print(json.dumps(segments, indent=2))

        elif args.operation == 'store':
            if not os.path.exists(args.input_file):
                print(f"Error: Input file not found: {args.input_file}")
                return 1
            with open(args.input_file, 'r', encoding='utf-8') as f:
                markdown_content = f.read()

            print(f"Segmenting and storing markdown file: {args.input_file} into collection '{args.collection_name}'...")
            total_stored, segment_ids_by_type = segmenter.segment_and_store(markdown_content)
            print(f"Successfully stored {total_stored} segments.")
            print(f"Text segments stored: {len(segment_ids_by_type.get('text', []))}")
            print(f"Table segments stored: {len(segment_ids_by_type.get('table', []))}")
            print(f"Segment IDs: {json.dumps(segment_ids_by_type, indent=2)}")

        elif args.operation == 'search':
            print(f"Searching collection '{args.collection_name}' with query: '{args.query}'...")
            search_results = segmenter.search(
                query=args.query,
                n_results=args.n_results,
                filter_by_type=args.filter_type
            )
            print("Search results:")
            print(json.dumps(search_results, indent=2))

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    # asyncio.run(main()) # Not using async features directly in segmenter, so direct call is fine.
    # For consistency with browser_cli, we can keep it, but it's not strictly necessary here.
    # If any part of MarkdownSegmenter or ChromaVectorStore becomes async, this will be needed.
    # For now, let's assume synchronous operations for simplicity in this CLI.
    exit_code = asyncio.run(main()) # Keep async for potential future async operations in underlying libs
    sys.exit(exit_code) 