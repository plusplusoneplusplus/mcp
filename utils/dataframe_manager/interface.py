"""Abstract interfaces for DataFrame management framework."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, TypeVar, Union
from uuid import UUID, uuid4

import pandas as pd

T = TypeVar("T")


class DataFrameMetadata:
    """Metadata for stored DataFrames."""

    def __init__(
        self,
        df_id: str,
        created_at: datetime,
        size_bytes: int,
        shape: tuple[int, int],
        dtypes: Dict[str, str],
        memory_usage: int,
        ttl_seconds: Optional[int] = None,
        tags: Optional[Dict[str, Any]] = None,
    ):
        self.df_id = df_id
        self.created_at = created_at
        self.size_bytes = size_bytes
        self.shape = shape
        self.dtypes = dtypes
        self.memory_usage = memory_usage
        self.ttl_seconds = ttl_seconds
        self.tags = tags or {}

    @property
    def expires_at(self) -> Optional[datetime]:
        """Calculate expiration time if TTL is set."""
        if self.ttl_seconds is None:
            return None
        from datetime import timedelta
        return self.created_at + timedelta(seconds=self.ttl_seconds)

    @property
    def is_expired(self) -> bool:
        """Check if DataFrame has expired."""
        expires_at = self.expires_at
        if expires_at is None:
            return False
        return datetime.now() > expires_at


class DataFrameQueryResult:
    """Result of a DataFrame query operation."""

    def __init__(
        self,
        data: pd.DataFrame,
        operation: str,
        parameters: Dict[str, Any],
        metadata: Dict[str, Any],
        execution_time_ms: float,
    ):
        self.data = data
        self.operation = operation
        self.parameters = parameters
        self.metadata = metadata
        self.execution_time_ms = execution_time_ms


class DataFrameStorageInterface(ABC):
    """Abstract interface for DataFrame storage backends."""

    @abstractmethod
    async def store(
        self,
        df: pd.DataFrame,
        df_id: str,
        ttl_seconds: Optional[int] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> DataFrameMetadata:
        """Store a DataFrame and return metadata."""
        pass

    @abstractmethod
    async def retrieve(self, df_id: str) -> Optional[pd.DataFrame]:
        """Retrieve a DataFrame by ID."""
        pass

    @abstractmethod
    async def get_metadata(self, df_id: str) -> Optional[DataFrameMetadata]:
        """Get metadata for a DataFrame."""
        pass

    @abstractmethod
    async def delete(self, df_id: str) -> bool:
        """Delete a DataFrame. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    async def list_dataframes(
        self,
        limit: Optional[int] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> List[DataFrameMetadata]:
        """List stored DataFrames with optional filtering."""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Remove expired DataFrames. Returns count of removed items."""
        pass

    @abstractmethod
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics (memory usage, count, etc.)."""
        pass

    @abstractmethod
    async def clear_all(self) -> int:
        """Clear all stored DataFrames. Returns count of removed items."""
        pass


class DataFrameQueryInterface(ABC):
    """Abstract interface for DataFrame query operations."""

    @abstractmethod
    async def head(
        self,
        df: pd.DataFrame,
        n: int = 5,
    ) -> DataFrameQueryResult:
        """Get first n rows."""
        pass

    @abstractmethod
    async def tail(
        self,
        df: pd.DataFrame,
        n: int = 5,
    ) -> DataFrameQueryResult:
        """Get last n rows."""
        pass

    @abstractmethod
    async def sample(
        self,
        df: pd.DataFrame,
        n: Optional[int] = None,
        frac: Optional[float] = None,
        random_state: Optional[int] = None,
    ) -> DataFrameQueryResult:
        """Get random sample of rows."""
        pass

    @abstractmethod
    async def describe(
        self,
        df: pd.DataFrame,
        include: Optional[Union[str, List[str]]] = None,
    ) -> DataFrameQueryResult:
        """Generate descriptive statistics."""
        pass

    @abstractmethod
    async def info(
        self,
        df: pd.DataFrame,
    ) -> DataFrameQueryResult:
        """Get DataFrame info (dtypes, memory usage, etc.)."""
        pass

    @abstractmethod
    async def query(
        self,
        df: pd.DataFrame,
        expr: str,
    ) -> DataFrameQueryResult:
        """Query DataFrame using pandas query syntax."""
        pass

    @abstractmethod
    async def filter(
        self,
        df: pd.DataFrame,
        conditions: Dict[str, Any],
    ) -> DataFrameQueryResult:
        """Filter DataFrame based on conditions."""
        pass

    @abstractmethod
    async def search(
        self,
        df: pd.DataFrame,
        query: str,
        columns: Optional[List[str]] = None,
    ) -> DataFrameQueryResult:
        """Search DataFrame for text matches."""
        pass

    @abstractmethod
    async def value_counts(
        self,
        df: pd.DataFrame,
        column: str,
        normalize: bool = False,
        dropna: bool = True,
    ) -> DataFrameQueryResult:
        """Get value counts for a column."""
        pass


class DataFrameSummarizerInterface(ABC):
    """Abstract interface for DataFrame summarization."""

    @abstractmethod
    async def summarize(
        self,
        df: pd.DataFrame,
        max_size_bytes: int,
        include_sample: bool = True,
        sample_size: int = 10,
    ) -> Dict[str, Any]:
        """Create intelligent summary of DataFrame."""
        pass

    @abstractmethod
    async def format_for_display(
        self,
        df: pd.DataFrame,
        max_size_bytes: int,
        format_type: str = "table",
    ) -> str:
        """Format DataFrame for display within size constraints."""
        pass


class DataFrameManagerInterface(ABC):
    """Main interface for DataFrame management."""

    @property
    @abstractmethod
    def storage(self) -> DataFrameStorageInterface:
        """Get the storage backend."""
        pass

    @property
    @abstractmethod
    def query_processor(self) -> DataFrameQueryInterface:
        """Get the query processor."""
        pass

    @property
    @abstractmethod
    def summarizer(self) -> DataFrameSummarizerInterface:
        """Get the summarizer."""
        pass

    @abstractmethod
    async def store_dataframe(
        self,
        df: pd.DataFrame,
        ttl_seconds: Optional[int] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a DataFrame and return its ID."""
        pass

    @abstractmethod
    async def get_dataframe(self, df_id: str) -> Optional[pd.DataFrame]:
        """Retrieve a stored DataFrame."""
        pass

    @abstractmethod
    async def query_dataframe(
        self,
        df_id: str,
        operation: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[DataFrameQueryResult]:
        """Execute a query operation on a stored DataFrame."""
        pass

    @abstractmethod
    async def summarize_dataframe(
        self,
        df_id: str,
        max_size_bytes: int,
        include_sample: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Get summary of stored DataFrame."""
        pass

    @abstractmethod
    async def list_stored_dataframes(
        self,
        tags: Optional[Dict[str, Any]] = None,
    ) -> List[DataFrameMetadata]:
        """List all stored DataFrames."""
        pass

    @abstractmethod
    async def delete_dataframe(self, df_id: str) -> bool:
        """Delete a stored DataFrame."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the manager (initialize background tasks, etc.)."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the manager gracefully."""
        pass
