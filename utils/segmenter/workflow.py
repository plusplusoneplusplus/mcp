"""Core segmentation workflow logic for the segmenter module."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, List, Any

from utils.vector_store.vector_store import ChromaVectorStore
from utils.vector_store.markdown_segmenter import MarkdownSegmenter
from utils.segmenter.types import (
    SegmenterConfig,
    VectorStoreConfig,
    SearchConfig,
    SegmentationResult,
    StorageResult,
    SearchResult,
)


class SegmenterWorkflow:
    """Main workflow class for markdown segmentation operations."""

    def __init__(
        self,
        segmenter_config: SegmenterConfig,
        vector_store_config: VectorStoreConfig,
    ):
        """Initialize the segmenter workflow with configurations."""
        self.segmenter_config = segmenter_config
        self.vector_store_config = vector_store_config

        # Initialize ChromaVectorStore
        self.vector_store = ChromaVectorStore(
            collection_name=vector_store_config.collection_name,
            persist_directory=vector_store_config.persist_directory,
        )

        # Initialize MarkdownSegmenter
        self.segmenter = MarkdownSegmenter(
            vector_store=self.vector_store,
            model_name=segmenter_config.model_name,
            chunk_size=segmenter_config.chunk_size,
            chunk_overlap=segmenter_config.chunk_overlap,
            table_max_rows=segmenter_config.table_max_rows,
        )

    def segment_file(self, file_path: str) -> SegmentationResult:
        """Segment a markdown file and return the segments."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        segments = self.segmenter.segment_markdown(markdown_content)
        return SegmentationResult(
            segments=segments,
            total_count=len(segments)
        )

    def segment_content(self, markdown_content: str) -> SegmentationResult:
        """Segment markdown content and return the segments."""
        segments = self.segmenter.segment_markdown(markdown_content)
        return SegmentationResult(
            segments=segments,
            total_count=len(segments)
        )

    def store_file(self, file_path: str) -> StorageResult:
        """Segment and store a markdown file in the vector store."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        return self.store_content(markdown_content)

    def store_content(self, markdown_content: str) -> StorageResult:
        """Segment and store markdown content in the vector store."""
        total_stored, segment_ids_by_type = self.segmenter.segment_and_store(
            markdown_content
        )
        return StorageResult(
            total_stored=total_stored,
            segment_ids_by_type=segment_ids_by_type
        )

    def search(self, search_config: SearchConfig, query: str) -> SearchResult:
        """Search the vector store with the given query."""
        search_results = self.segmenter.search(
            query=query,
            n_results=search_config.n_results,
            filter_by_type=search_config.filter_type,
        )
        # Ensure search_results is a list
        if isinstance(search_results, dict):
            results_list = [search_results]
        elif isinstance(search_results, list):
            results_list = search_results
        else:
            results_list = []

        return SearchResult(
            results=results_list,
            query=query,
            total_found=len(results_list)
        )


# Convenience functions for direct usage
def segment_file(
    file_path: str,
    segmenter_config: Optional[SegmenterConfig] = None,
    vector_store_config: Optional[VectorStoreConfig] = None,
) -> SegmentationResult:
    """Convenience function to segment a file with default configurations."""
    if segmenter_config is None:
        segmenter_config = SegmenterConfig()
    if vector_store_config is None:
        vector_store_config = VectorStoreConfig()

    workflow = SegmenterWorkflow(segmenter_config, vector_store_config)
    return workflow.segment_file(file_path)


def store_segments(
    file_path: str,
    segmenter_config: Optional[SegmenterConfig] = None,
    vector_store_config: Optional[VectorStoreConfig] = None,
) -> StorageResult:
    """Convenience function to segment and store a file with default configurations."""
    if segmenter_config is None:
        segmenter_config = SegmenterConfig()
    if vector_store_config is None:
        vector_store_config = VectorStoreConfig()

    workflow = SegmenterWorkflow(segmenter_config, vector_store_config)
    return workflow.store_file(file_path)


def search_segments(
    query: str,
    search_config: Optional[SearchConfig] = None,
    segmenter_config: Optional[SegmenterConfig] = None,
    vector_store_config: Optional[VectorStoreConfig] = None,
) -> SearchResult:
    """Convenience function to search segments with default configurations."""
    if search_config is None:
        search_config = SearchConfig()
    if segmenter_config is None:
        segmenter_config = SegmenterConfig()
    if vector_store_config is None:
        vector_store_config = VectorStoreConfig()

    workflow = SegmenterWorkflow(segmenter_config, vector_store_config)
    return workflow.search(search_config, query)
