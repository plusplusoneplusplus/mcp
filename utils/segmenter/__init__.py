"""Segmenter module for markdown segmentation and vector store operations."""

from utils.segmenter.workflow import (
    SegmenterWorkflow,
    segment_file,
    store_segments,
    search_segments,
)
from utils.segmenter.types import (
    SegmenterConfig,
    VectorStoreConfig,
    SearchConfig,
    SegmentationResult,
    StorageResult,
    SearchResult,
)
from utils.segmenter.cli_args import (
    create_parser,
    validate_and_process_args,
    args_to_configs,
)

__all__ = [
    "SegmenterWorkflow",
    "segment_file",
    "store_segments",
    "search_segments",
    "SegmenterConfig",
    "VectorStoreConfig",
    "SearchConfig",
    "SegmentationResult",
    "StorageResult",
    "SearchResult",
    "create_parser",
    "validate_and_process_args",
    "args_to_configs",
]
