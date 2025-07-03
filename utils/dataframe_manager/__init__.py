"""DataFrame management framework for large dataset handling."""

from .interface import (
    DataFrameManagerInterface,
    DataFrameStorageInterface,
    DataFrameQueryInterface,
    DataFrameSummarizerInterface,
    DataFrameMetadata,
    DataFrameQueryResult,
)

from .manager import (
    DataFrameManager,
    get_dataframe_manager,
    shutdown_global_manager,
)

from .storage.memory import InMemoryDataFrameStorage
from .query.processor import DataFrameQueryProcessor
from .summarizer import DataFrameSummarizer

__all__ = [
    # Interfaces
    "DataFrameManagerInterface",
    "DataFrameStorageInterface",
    "DataFrameQueryInterface",
    "DataFrameSummarizerInterface",
    "DataFrameMetadata",
    "DataFrameQueryResult",

    # Main manager
    "DataFrameManager",
    "get_dataframe_manager",
    "shutdown_global_manager",

    # Implementations
    "InMemoryDataFrameStorage",
    "DataFrameQueryProcessor",
    "DataFrameSummarizer",
]
