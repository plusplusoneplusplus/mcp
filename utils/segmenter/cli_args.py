"""CLI argument parsing and validation for the segmenter module."""

import argparse
import os
from pathlib import Path
from typing import Optional

from utils.segmenter.types import SegmenterConfig, VectorStoreConfig, SearchConfig


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    # Get the scripts directory path for default persist path
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    default_persist_path = os.path.join(script_dir, "scripts", ".vector_store")

    parser = argparse.ArgumentParser(
        description="Segment markdown files and interact with a vector store."
    )

    parser.add_argument(
        "input_file",
        nargs="?",
        default=None,
        help='Path to the input markdown file (required for "segment" and "store" operations).',
    )

    parser.add_argument(
        "--operation",
        "-o",
        choices=["segment", "store", "search"],
        required=True,
        help='Operation to perform: "segment" (prints segments), "store" (segments and stores), or "search".',
    )

    # Vector Store Arguments
    parser.add_argument(
        "--collection-name",
        default="default_segments",
        help="Name of the collection in the vector store (default: default_segments).",
    )
    parser.add_argument(
        "--persist-directory",
        default=None,
        help=f"Directory for persistent vector store storage. If not provided, an in-memory DB is used. Use 'DEFAULT_PATH' for default location: {default_persist_path}",
    )

    # Segmenter Arguments
    parser.add_argument(
        "--model-name",
        default="all-MiniLM-L6-v2",
        help="SentenceTransformer model name for embeddings (default: all-MiniLM-L6-v2).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Maximum size of text chunks in characters (default: 1000).",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="Overlap between text chunks in characters (default: 200).",
    )
    parser.add_argument(
        "--table-max-rows",
        type=int,
        default=500,
        help="Maximum number of rows in a table before splitting (default: 500).",
    )

    # Search Arguments
    parser.add_argument(
        "--query", "-q", help='Search query (required for "search" operation).'
    )
    parser.add_argument(
        "--n-results",
        type=int,
        default=5,
        help='Number of search results to return (default: 5, for "search" operation).',
    )
    parser.add_argument(
        "--filter-type",
        choices=["text", "table"],
        default=None,
        help='Filter search results by segment type (text or table, for "search" operation).',
    )

    return parser


def validate_and_process_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> argparse.Namespace:
    """Validate and process parsed arguments, fixing the persist_directory issue."""
    # Validate arguments based on operation
    if args.operation in ["segment", "store"] and not args.input_file:
        parser.error('Input file is required for "segment" and "store" operations.')
    if args.operation == "search" and not args.query:
        parser.error('Query is required for "search" operation.')

    # Fix the persist_directory handling (this fixes the linter error)
    persist_directory = getattr(args, 'persist_directory', None)
    if persist_directory == "DEFAULT_PATH":
        # Get the scripts directory path for default persist path
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        default_persist_path = os.path.join(script_dir, "scripts", ".vector_store")
        setattr(args, 'persist_directory', default_persist_path)
        os.makedirs(default_persist_path, exist_ok=True)
        print(f"Using persistent vector store at: {default_persist_path}")
    elif persist_directory:
        os.makedirs(persist_directory, exist_ok=True)
        print(f"Using persistent vector store at: {persist_directory}")
    else:
        print("Using in-memory vector store.")

    return args


def args_to_configs(args: argparse.Namespace) -> tuple[SegmenterConfig, VectorStoreConfig, SearchConfig]:
    """Convert parsed arguments to configuration objects."""
    segmenter_config = SegmenterConfig(
        model_name=args.model_name,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        table_max_rows=args.table_max_rows,
    )

    vector_store_config = VectorStoreConfig(
        collection_name=args.collection_name,
        persist_directory=getattr(args, 'persist_directory', None),
    )

    search_config = SearchConfig(
        n_results=args.n_results,
        filter_type=getattr(args, 'filter_type', None),
    )

    return segmenter_config, vector_store_config, search_config
