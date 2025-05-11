#!/usr/bin/env python3
"""
Demonstration of markdown table segmentation and semantic search.

This script shows how to:
1. Extract tables from markdown content
2. Store them in a vector database
3. Perform semantic search to retrieve relevant tables
"""

import os
import sys
from pathlib import Path

# Add the project root to the path if needed
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from utils.vector_store.markdown_table_segmenter import MarkdownTableSegmenter

# Sample markdown content with multiple tables
SAMPLE_MARKDOWN = """
# Product Comparison Report

## Laptop Specifications

This table compares the specifications of different laptop models:

| Model | CPU | RAM | Storage | Price |
|-------|-----|-----|---------|-------|
| MacBook Pro | M2 Pro | 16GB | 512GB SSD | $1,999 |
| Dell XPS 15 | i7-12700H | 32GB | 1TB SSD | $1,899 |
| HP Spectre | i7-1260P | 16GB | 512GB SSD | $1,499 |
| Lenovo ThinkPad | i5-1240P | 16GB | 256GB SSD | $1,299 |

## Performance Benchmarks

The following table shows benchmark results for each laptop model:

| Model | Geekbench Score | Cinebench R23 | Battery Life (hrs) |
|-------|----------------|--------------|-------------------|
| MacBook Pro | 12,345 | 12,567 | 14.5 |
| Dell XPS 15 | 10,234 | 11,345 | 8.5 |
| HP Spectre | 9,876 | 10,234 | 10.0 |
| Lenovo ThinkPad | 8,765 | 9,876 | 12.0 |

## Price Comparison

This table shows the price breakdown by configuration:

| Model | Base Price | 32GB RAM Upgrade | 1TB Storage Upgrade | Total |
|-------|------------|-----------------|---------------------|-------|
| MacBook Pro | $1,999 | $400 | $200 | $2,599 |
| Dell XPS 15 | $1,699 | $200 | Included | $1,899 |
| HP Spectre | $1,499 | $300 | $200 | $1,999 |
| Lenovo ThinkPad | $1,299 | $250 | $150 | $1,699 |

## Customer Satisfaction Ratings

| Model | Design | Performance | Support | Overall |
|-------|--------|------------|---------|---------|
| MacBook Pro | 4.8/5 | 4.9/5 | 4.5/5 | 4.7/5 |
| Dell XPS 15 | 4.6/5 | 4.7/5 | 3.8/5 | 4.4/5 |
| HP Spectre | 4.7/5 | 4.3/5 | 4.0/5 | 4.3/5 |
| Lenovo ThinkPad | 4.2/5 | 4.4/5 | 4.6/5 | 4.4/5 |
"""


def main():
    """Run the table segmentation and search demonstration."""
    # Initialize the table segmenter with in-memory database (no persist_directory)
    segmenter = MarkdownTableSegmenter(
        collection_name="laptop_comparison"
        # No persist_directory means in-memory database
    )

    print("Using in-memory vector database")

    # Segment and store tables
    num_tables, table_ids = segmenter.segment_and_store(SAMPLE_MARKDOWN)
    print(f"Extracted and stored {num_tables} tables.")

    # Show the extracted tables
    tables = segmenter.extract_tables(SAMPLE_MARKDOWN)
    print("\n=== Extracted Tables ===")
    for i, table in enumerate(tables):
        print(f"\nTable {i+1}:")
        print(f"Heading: {table['heading']}")
        print(f"ID: {table['id']}")
        print("-" * 50)
        print(table["content"])
        print("-" * 50)

    # Perform semantic searches
    search_queries = [
        "Which laptop has the best battery life?",
        "What are the prices of the laptops?",
        "How much does RAM upgrade cost?",
        "Which laptop has the best customer support?",
        "What are the performance benchmarks?",
    ]

    print("\n=== Semantic Search Results ===")
    for query in search_queries:
        print(f"\nQuery: {query}")
        results = segmenter.search_tables(query, n_results=2)

        for i, (doc, metadata, distance) in enumerate(
            zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ):
            print(f"\nResult {i+1} (similarity: {1-distance:.4f}):")
            print(f"Heading: {metadata['heading']}")
            print("-" * 50)
            print(doc)
            print("-" * 50)


if __name__ == "__main__":
    main()
