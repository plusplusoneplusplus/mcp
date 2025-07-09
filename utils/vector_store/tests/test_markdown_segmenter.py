#!/usr/bin/env python3
"""
Test cases for the markdown segmenter.

This module contains tests for:
1. Text chunking
2. Table extraction
3. Table splitting
4. Heading association
5. Edge cases that might cause infinite loops
"""

import sys
import os
import unittest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Import the fixed segmenter
from utils.vector_store.markdown_segmenter import MarkdownSegmenter
from utils.vector_store.vector_store import ChromaVectorStore


class TestMarkdownSegmenter(unittest.TestCase):
    """Test cases for the MarkdownSegmenter."""

    def setUp(self):
        """Set up the segmenter for each test."""
        # Create an in-memory vector store for testing
        self.test_collection_name = "test_markdown_segments"
        self.vector_store = ChromaVectorStore(
            collection_name=self.test_collection_name,
            persist_directory=None,  # In-memory
        )
        self.segmenter = MarkdownSegmenter(
            vector_store=self.vector_store,
            chunk_size=200,
            chunk_overlap=50,
            table_max_rows=3,
        )

    def tearDown(self):
        """Clean up the vector store after each test if necessary."""
        # This ensures the collection is cleaned up, especially if it were persisted.
        # For an in-memory store, this might not be strictly necessary for cleanup
        # but good practice if tests were to involve adding data.
        # Chroma's delete_collection might be an option, or re-creating the store.
        # For now, since tests primarily focus on segmentation logic before storage,
        # we can skip explicit cleanup for in-memory, or manage it if issues arise.
        # If the collection was persisted, os.rmdir or similar would be needed.
        # Let's try to delete the collection to be safe.
        try:
            # Chroma client is usually accessible via vector_store.client
            if hasattr(self.vector_store, "client") and self.vector_store.client:
                self.vector_store.client.delete_collection(
                    name=self.test_collection_name
                )
        except Exception:
            # pass # Or log an error if deletion fails
            # It's possible the collection doesn't exist if a test failed before its creation
            # or if client is not exposed in a way that allows direct deletion.
            # For in-memory, it's often sufficient that the instance goes out of scope.
            pass

    def test_basic_text_chunking(self):
        """Test basic text chunking functionality."""
        text = "This is a simple text without any tables or headings."
        segments = self.segmenter._chunk_text(text)

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["type"], "text")
        self.assertEqual(segments[0]["content"], text)

    def test_text_with_headings(self):
        """Test text chunking with headings."""
        text = """# Main Heading

## Subheading

This is some content under the subheading.
"""
        segments = self.segmenter._chunk_text(text)

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["heading"], "Main Heading")
        self.assertTrue("Subheading" in segments[0]["content"])

    def test_long_text_chunking(self):
        """Test chunking of long text."""
        # Create a text longer than the chunk size
        long_text = "This is sentence number " + " ".join(
            [f"{i}." for i in range(1, 50)]
        )

        segments = self.segmenter._chunk_text(long_text)

        self.assertGreater(len(segments), 1)
        # Check that each chunk is smaller than or equal to chunk_size
        for segment in segments:
            self.assertLessEqual(len(segment["content"]), self.segmenter.chunk_size)

    def test_table_extraction(self):
        """Test extraction of tables from markdown."""
        markdown = """
# Test Table

Here's a simple table:

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
| Value 3  | Value 4  |
"""
        segments = self.segmenter.segment_markdown(markdown)

        # Should have at least one text segment and one table segment
        self.assertGreater(len(segments), 1)

        # Check if there's a table segment
        table_segments = [s for s in segments if s["type"] == "table"]
        self.assertEqual(len(table_segments), 1)

        # Check table content
        self.assertIn("Column 1", table_segments[0]["content"])
        self.assertIn("Value 1", table_segments[0]["content"])

    def test_large_table_splitting(self):
        """Test splitting of large tables."""
        # Create a table with more rows than table_max_rows
        table_rows = ["| Column 1 | Column 2 |", "|----------|----------|"]
        for i in range(1, 10):  # 9 data rows
            table_rows.append(f"| Value {i} | Value {i*2} |")

        # Join the table rows beforehand to avoid backslash in f-string
        table_content = "\n".join(table_rows)
        markdown = f"""
# Large Table Test

{table_content}
"""
        segments = self.segmenter.segment_markdown(markdown)

        # Find table segments
        table_segments = [s for s in segments if s["type"] == "table"]

        # Should have multiple table segments (chunks)
        self.assertGreater(len(table_segments), 1)

        # Check if chunks have the right metadata
        for segment in table_segments:
            self.assertIn("is_chunk", segment)
            self.assertIn("chunk_index", segment)
            self.assertIn("total_chunks", segment)
            self.assertIn("parent_id", segment)

    def test_text_between_tables(self):
        """Test extraction of text between tables."""
        markdown = """
# Multiple Tables

## First Table

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |

Some text between tables.

## Second Table

| Column A | Column B |
|----------|----------|
| Value A  | Value B  |
"""
        segments = self.segmenter.segment_markdown(markdown)

        # Find text segments
        text_segments = [s for s in segments if s["type"] == "text"]
        text_content = " ".join([s["content"] for s in text_segments])

        # Check if the text between tables is captured
        self.assertIn("Some text between tables", text_content)

        # Check if we have two table segments
        table_segments = [s for s in segments if s["type"] == "table"]
        self.assertEqual(len(table_segments), 2)

    def test_edge_case_tiny_chunk_size(self):
        """Test with a very small chunk size that could cause issues."""
        tiny_vector_store = ChromaVectorStore(
            collection_name="tiny_chunk_test", persist_directory=None
        )
        tiny_segmenter = MarkdownSegmenter(
            vector_store=tiny_vector_store,
            chunk_size=10,  # Very small chunk size
            chunk_overlap=5,
            table_max_rows=3,
        )

        text = "This is a longer text that should be split into many tiny chunks."
        segments = tiny_segmenter._chunk_text(text)

        # Should have multiple chunks
        self.assertGreater(len(segments), 3)

        # Each chunk should be small
        for segment in segments:
            self.assertLessEqual(len(segment["content"]), 10)

    def test_edge_case_overlap_equals_chunk_size(self):
        """Test with overlap equal to chunk size (potential infinite loop case)."""
        problematic_vector_store = ChromaVectorStore(
            collection_name="overlap_equals_test", persist_directory=None
        )
        problematic_segmenter = MarkdownSegmenter(
            vector_store=problematic_vector_store,
            chunk_size=100,
            chunk_overlap=100,  # Equal to chunk size
            table_max_rows=3,
        )

        text = "This is a text that would cause an infinite loop in the original implementation."
        segments = problematic_segmenter._chunk_text(text)

        # Should still produce segments without infinite loop
        self.assertGreater(len(segments), 0)

    def test_edge_case_overlap_greater_than_chunk_size(self):
        """Test with overlap greater than chunk size (potential infinite loop case)."""
        problematic_vector_store = ChromaVectorStore(
            collection_name="overlap_greater_test", persist_directory=None
        )
        problematic_segmenter = MarkdownSegmenter(
            vector_store=problematic_vector_store,
            chunk_size=50,
            chunk_overlap=100,  # Greater than chunk size
            table_max_rows=3,
        )

        text = "This is another text that would cause an infinite loop in the original implementation."
        segments = problematic_segmenter._chunk_text(text)

        # Should still produce segments without infinite loop
        self.assertGreater(len(segments), 0)

    def test_empty_markdown(self):
        """Test with empty markdown."""
        segments = self.segmenter.segment_markdown("")

        # Should return an empty list
        self.assertEqual(len(segments), 0)

    def test_markdown_with_only_tables(self):
        """Test markdown with only tables and no text."""
        markdown = """
| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |

| Column A | Column B |
|----------|----------|
| Value A  | Value B  |
"""
        segments = self.segmenter.segment_markdown(markdown)

        # Should have only table segments
        table_segments = [s for s in segments if s["type"] == "table"]
        self.assertEqual(len(table_segments), 2)
        self.assertEqual(len(segments), 2)

    def test_markdown_with_only_text(self):
        """Test markdown with only text and no tables."""
        markdown = """
# Heading

This is some text.

## Subheading

More text here.
"""
        segments = self.segmenter.segment_markdown(markdown)

        # Should have only text segments
        text_segments = [s for s in segments if s["type"] == "text"]
        self.assertEqual(len(segments), len(text_segments))
        self.assertGreater(len(segments), 0)

    def test_complex_markdown(self):
        """Test with complex markdown containing multiple headings, tables, and text."""

        original_chunk_size = self.segmenter.chunk_size
        original_overlap = self.segmenter.chunk_overlap
        # Temporarily reduce chunk_size to ensure finer granularity for this test
        self.segmenter.chunk_size = 60
        # Ensure overlap is valid with new chunk_size (from __init__ logic)
        if self.segmenter.chunk_overlap >= self.segmenter.chunk_size:
            self.segmenter.chunk_overlap = max(0, self.segmenter.chunk_size - 1)

        try:
            markdown = """
# Main Document

## Introduction

This is an introduction paragraph.

### First Section

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Value 4  | Value 5  | Value 6  |
| Value 7  | Value 8  | Value 9  |
| Value 10 | Value 11 | Value 12 |

Some text after the first table.

## Second Section

More content here.

| Header A | Header B |
|----------|----------|
| Item A   | Item B   |

### Final Thoughts

Concluding remarks.
"""
            segments = self.segmenter.segment_markdown(markdown)

            # Should have both text and table segments
            text_segments = [s for s in segments if s["type"] == "text"]
            table_segments = [s for s in segments if s["type"] == "table"]

            self.assertGreater(len(text_segments), 0)
            self.assertGreater(len(table_segments), 0)

            # Check if the first table was split (it has more than 3 rows)
            table_chunks = [s for s in table_segments if s.get("is_chunk", False)]
            self.assertGreater(len(table_chunks), 0)

            # Check heading association
            intro_segments = [
                s for s in text_segments if s["heading"] == "Introduction"
            ]
            self.assertGreater(
                len(intro_segments),
                0,
                "Should find segments under 'Introduction' heading",
            )
            # Optionally, check content of intro_segments if needed
            # self.assertTrue(any("This is an introduction paragraph." in s['content'] for s in intro_segments))

        finally:
            # Restore original chunk_size and overlap
            self.segmenter.chunk_size = original_chunk_size
            self.segmenter.chunk_overlap = original_overlap

    def test_small_file_no_chunking(self):
        """Test that files with less than 500 lines are not chunked."""
        # Create markdown content with less than 500 lines
        small_markdown = """# Small Document

## Introduction

This is a small document with fewer than 500 lines.
It should not be chunked but returned as a single segment.

### Section 1

Some content here.

### Section 2

More content here.

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
| Value 3  | Value 4  |

Final content.
"""

        # Verify the markdown has less than 500 lines
        line_count = len(small_markdown.splitlines())
        self.assertLess(line_count, 500, f"Test markdown should have less than 500 lines, but has {line_count}")

        segments = self.segmenter.segment_markdown(small_markdown)

        # Should have exactly 2 segments: 1 text segment (whole file) + 1 table segment
        self.assertEqual(len(segments), 2)

        # Find text and table segments
        text_segments = [s for s in segments if s["type"] == "text"]
        table_segments = [s for s in segments if s["type"] == "table"]

        # Should have exactly 1 text segment and 1 table segment
        self.assertEqual(len(text_segments), 1)
        self.assertEqual(len(table_segments), 1)

        # The text segment should contain most of the content (excluding the table)
        text_segment = text_segments[0]
        self.assertIn("Small Document", text_segment["content"])
        self.assertIn("This is a small document", text_segment["content"])
        self.assertIn("Final content", text_segment["content"])

        # The text segment should NOT contain the table content
        self.assertNotIn("| Column 1 | Column 2 |", text_segment["content"])

        # The table segment should contain the table
        table_segment = table_segments[0]
        self.assertIn("| Column 1 | Column 2 |", table_segment["content"])
        self.assertIn("| Value 1  | Value 2  |", table_segment["content"])

    def test_large_file_with_chunking(self):
        """Test that files with 500+ lines are chunked normally."""
        # Create markdown content with 500+ lines
        lines = ["# Large Document", ""]
        for i in range(1, 501):  # Create 500+ lines
            lines.append(f"This is line {i} of content in the large document.")
            if i % 50 == 0:  # Add some headers
                lines.append(f"## Section {i//50}")
                lines.append("")

        large_markdown = "\n".join(lines)

        # Verify the markdown has 500+ lines
        line_count = len(large_markdown.splitlines())
        self.assertGreaterEqual(line_count, 500, f"Test markdown should have 500+ lines, but has {line_count}")

        segments = self.segmenter.segment_markdown(large_markdown)

        # Should have multiple segments due to chunking
        text_segments = [s for s in segments if s["type"] == "text"]
        self.assertGreater(len(text_segments), 1, "Large file should be chunked into multiple segments")

    def test_configurable_line_threshold(self):
        """Test that the line count threshold can be configured."""
        # Create content with 100 lines
        lines = ["# Document with 100 lines", ""]
        for i in range(1, 99):  # Create ~100 lines total
            lines.append(f"This is line {i} of content.")

        content_100_lines = "\n".join(lines)
        line_count = len(content_100_lines.splitlines())

        # Test with default threshold (500) - should NOT chunk
        default_segmenter = MarkdownSegmenter(
            vector_store=self.vector_store,
            chunk_size=200,
            chunk_overlap=50
        )
        segments_default = default_segmenter.segment_markdown(content_100_lines)
        text_segments_default = [s for s in segments_default if s["type"] == "text"]
        self.assertEqual(len(text_segments_default), 1, "With default threshold (500), should have 1 segment")

        # Test with custom threshold (50) - should chunk
        custom_segmenter = MarkdownSegmenter(
            vector_store=self.vector_store,
            chunk_size=200,
            chunk_overlap=50,
            line_count_threshold=50
        )
        segments_custom = custom_segmenter.segment_markdown(content_100_lines)
        text_segments_custom = [s for s in segments_custom if s["type"] == "text"]
        self.assertGreater(len(text_segments_custom), 1, f"With threshold 50, should chunk {line_count}-line content")


if __name__ == "__main__":
    unittest.main()
