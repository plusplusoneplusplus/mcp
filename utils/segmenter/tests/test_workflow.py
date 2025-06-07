"""Tests for the segmenter workflow functionality."""

import pytest
import tempfile
import os
from pathlib import Path

from utils.segmenter import (
    SegmenterWorkflow,
    SegmenterConfig,
    VectorStoreConfig,
    SearchConfig,
    segment_file,
    store_segments,
    search_segments,
)


class TestSegmenterWorkflow:
    """Test cases for the SegmenterWorkflow class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.segmenter_config = SegmenterConfig(  # type: ignore
            model_name="all-MiniLM-L6-v2",
            chunk_size=500,
            chunk_overlap=100,
            table_max_rows=100,
        )
        self.vector_store_config = VectorStoreConfig(  # type: ignore
            collection_name="test_collection",
            persist_directory=None,  # Use in-memory for tests
        )
        self.search_config = SearchConfig(  # type: ignore
            n_results=3,
            filter_type=None,
        )

    def test_workflow_initialization(self):
        """Test that the workflow initializes correctly."""
        workflow = SegmenterWorkflow(self.segmenter_config, self.vector_store_config)
        assert workflow.segmenter_config == self.segmenter_config
        assert workflow.vector_store_config == self.vector_store_config
        assert workflow.vector_store is not None
        assert workflow.segmenter is not None

    def test_segment_content(self):
        """Test segmenting markdown content."""
        workflow = SegmenterWorkflow(self.segmenter_config, self.vector_store_config)

        markdown_content = """
# Test Document

This is a test paragraph with some content.

## Section 2

Another paragraph here.

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
| Value 3  | Value 4  |
"""

        result = workflow.segment_content(markdown_content)
        assert result.total_count > 0
        assert isinstance(result.segments, list)
        assert len(result.segments) == result.total_count

    def test_segment_file(self):
        """Test segmenting a markdown file."""
        workflow = SegmenterWorkflow(self.segmenter_config, self.vector_store_config)

        markdown_content = """
# Test File

This is test content for file segmentation.

## Another Section

More content here.
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(markdown_content)
            temp_file_path = f.name

        try:
            result = workflow.segment_file(temp_file_path)
            assert result.total_count > 0
            assert isinstance(result.segments, list)
        finally:
            os.unlink(temp_file_path)

    def test_segment_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent files."""
        workflow = SegmenterWorkflow(self.segmenter_config, self.vector_store_config)

        with pytest.raises(FileNotFoundError):
            workflow.segment_file("non_existent_file.md")

    def test_store_content(self):
        """Test storing markdown content."""
        workflow = SegmenterWorkflow(self.segmenter_config, self.vector_store_config)

        markdown_content = """
# Test Storage

This content will be stored in the vector store.

## Data Section

Some data to be indexed.
"""

        result = workflow.store_content(markdown_content)
        assert result.total_stored > 0
        assert isinstance(result.segment_ids_by_type, dict)

    def test_convenience_functions(self):
        """Test the convenience functions work correctly."""
        markdown_content = """
# Convenience Test

Testing the convenience functions.
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(markdown_content)
            temp_file_path = f.name

        try:
            # Test segment_file convenience function
            result = segment_file(temp_file_path)
            assert result.total_count > 0

            # Test store_segments convenience function
            store_result = store_segments(temp_file_path)
            assert store_result.total_stored > 0

        finally:
            os.unlink(temp_file_path)


class TestConfigurations:
    """Test cases for configuration classes."""

    def test_segmenter_config_defaults(self):
        """Test SegmenterConfig default values."""
        config = SegmenterConfig()
        assert config.model_name == "all-MiniLM-L6-v2"
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.table_max_rows == 500

    def test_vector_store_config_defaults(self):
        """Test VectorStoreConfig default values."""
        config = VectorStoreConfig()
        assert config.collection_name == "default_segments"
        assert config.persist_directory is None

    def test_search_config_defaults(self):
        """Test SearchConfig default values."""
        config = SearchConfig()
        assert config.n_results == 5
        assert config.filter_type is None
