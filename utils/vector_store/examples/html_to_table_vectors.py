#!/usr/bin/env python3
"""
Script to convert HTML to markdown, extract tables, and store them in a vector database.

This script demonstrates a complete workflow:
1. Convert HTML content to markdown
2. Extract tables from the markdown
3. Store tables in a vector database with embeddings
4. Perform semantic searches to retrieve relevant tables
"""

import os
import sys
import argparse
from pathlib import Path

# Add the project root to the path if needed
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from utils.html_to_markdown import html_to_markdown
from utils.vector_store.markdown_table_segmenter import MarkdownTableSegmenter


def process_html_file(html_file_path, persist_dir=None, collection_name="html_tables"):
    """
    Process an HTML file: convert to markdown, extract tables, and store in vector DB.

    Args:
        html_file_path: Path to the HTML file
        persist_dir: Directory to persist the vector database (None for in-memory)
        collection_name: Name of the collection in the vector database

    Returns:
        Tuple of (markdown content, table segmenter instance, number of tables)
    """
    # Read the HTML file
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Convert HTML to markdown
    markdown_content = html_to_markdown(html_content)
    if not markdown_content:
        print(f"Failed to convert HTML to markdown: {html_file_path}")
        return None, None, 0

    # Initialize the table segmenter
    segmenter = MarkdownTableSegmenter(
        collection_name=collection_name,
        persist_directory=persist_dir,  # None means in-memory database
    )

    # Extract and store tables
    num_tables, table_ids = segmenter.segment_and_store(markdown_content)

    return markdown_content, segmenter, num_tables


def interactive_search(segmenter):
    """
    Run an interactive search session with the table segmenter.

    Args:
        segmenter: MarkdownTableSegmenter instance
    """
    print("\n=== Interactive Table Search ===")
    print("Enter search queries to find relevant tables (type 'exit' to quit)")

    while True:
        query = input("\nSearch query: ")
        if query.lower() in ("exit", "quit", "q"):
            break

        results = segmenter.search_tables(query, n_results=3)

        if not results["documents"][0]:
            print("No matching tables found.")
            continue

        for i, (doc, metadata, distance) in enumerate(
            zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ):
            print(f"\nResult {i+1} (similarity: {1-distance:.4f}):")
            if metadata["heading"]:
                print(f"Heading: {metadata['heading']}")
            if metadata["context"]:
                context_preview = metadata["context"]
                if "..." in context_preview:
                    context_preview = context_preview.split("...")[0] + "..."
                print(f"Context: {context_preview}")
            print("-" * 50)
            print(doc)
            print("-" * 50)


def main():
    """Main function to run the HTML to table vectors script."""
    parser = argparse.ArgumentParser(
        description="Convert HTML to markdown, extract tables, and store in vector DB"
    )
    parser.add_argument("html_file", help="Path to the HTML file to process")
    parser.add_argument(
        "--persist-dir",
        help="Directory to persist the vector database (default: in-memory)",
    )
    parser.add_argument(
        "--collection",
        default="html_tables",
        help="Name of the collection in the vector database",
    )
    args = parser.parse_args()

    # Process the HTML file
    markdown_content, segmenter, num_tables = process_html_file(
        args.html_file,
        args.persist_dir,  # None by default, which means in-memory
        args.collection,
    )

    if not markdown_content or not segmenter:
        print("Failed to process the HTML file.")
        return 1

    # Print database type
    if args.persist_dir:
        print(f"Using persistent vector database at: {args.persist_dir}")
    else:
        print("Using in-memory vector database")

    print(f"Processed HTML file: {args.html_file}")
    print(f"Extracted and stored {num_tables} tables.")

    # Show table extraction details
    tables = segmenter.extract_tables(markdown_content)
    print("\n=== Extracted Tables ===")
    for i, table in enumerate(tables):
        print(f"\nTable {i+1}:")
        if table["heading"]:
            print(f"Heading: {table['heading']}")
        print("-" * 50)
        # Show just the first few lines of the table
        table_preview = "\n".join(table["content"].split("\n")[:5])
        if len(table["content"].split("\n")) > 5:
            table_preview += "\n..."
        print(table_preview)
        print("-" * 50)

    # Run interactive search if tables were found
    if num_tables > 0:
        interactive_search(segmenter)

    return 0


if __name__ == "__main__":
    sys.exit(main())
