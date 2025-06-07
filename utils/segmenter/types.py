"""Type definitions and data structures for the segmenter module."""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass


@dataclass
class SegmenterConfig:
    """Configuration for the markdown segmenter."""
    model_name: str = "all-MiniLM-L6-v2"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    table_max_rows: int = 500


@dataclass
class VectorStoreConfig:
    """Configuration for the vector store."""
    collection_name: str = "default_segments"
    persist_directory: Optional[str] = None


@dataclass
class SearchConfig:
    """Configuration for search operations."""
    n_results: int = 5
    filter_type: Optional[str] = None


@dataclass
class SegmentationResult:
    """Result of a segmentation operation."""
    segments: List[Dict[str, Any]]
    total_count: int


@dataclass
class StorageResult:
    """Result of a storage operation."""
    total_stored: int
    segment_ids_by_type: Dict[str, List[str]]


@dataclass
class SearchResult:
    """Result of a search operation."""
    results: List[Dict[str, Any]]
    query: str
    total_found: int
