"""Base storage implementation for DataFrame management."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import pandas as pd

from ..interface import DataFrameStorageInterface, DataFrameMetadata

logger = logging.getLogger(__name__)


class BaseDataFrameStorage(DataFrameStorageInterface):
    """Base implementation with common functionality for DataFrame storage."""

    def __init__(
        self,
        max_memory_mb: int = 1024,
        default_ttl_seconds: int = 3600,
        cleanup_interval_seconds: int = 300,
    ):
        self.max_memory_mb = max_memory_mb
        self.default_ttl_seconds = default_ttl_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._logger = logger.getChild(self.__class__.__name__)

    async def start(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._logger.info("Started DataFrame storage cleanup task")

    async def shutdown(self) -> None:
        """Shutdown storage and cleanup resources."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        self._logger.info("DataFrame storage shutdown completed")

    async def _cleanup_loop(self) -> None:
        """Background cleanup task for expired DataFrames."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_seconds)
                removed_count = await self.cleanup_expired()
                if removed_count > 0:
                    self._logger.info(f"Cleaned up {removed_count} expired DataFrames")
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in cleanup loop: {e}")

    def _create_metadata(
        self,
        df: pd.DataFrame,
        df_id: str,
        ttl_seconds: Optional[int] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> DataFrameMetadata:
        """Create metadata for a DataFrame."""
        # Calculate size and memory usage
        size_bytes = len(df.to_string().encode('utf-8'))
        memory_usage = df.memory_usage(deep=True).sum()

        # Get dtypes as strings
        dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}

        return DataFrameMetadata(
            df_id=df_id,
            created_at=datetime.now(),
            size_bytes=size_bytes,
            shape=df.shape,
            dtypes=dtypes,
            memory_usage=memory_usage,
            ttl_seconds=ttl_seconds or self.default_ttl_seconds,
            tags=tags,
        )

    def _matches_tags(
        self,
        metadata: DataFrameMetadata,
        tag_filter: Dict[str, Any],
    ) -> bool:
        """Check if metadata matches tag filter."""
        if not tag_filter:
            return True

        for key, value in tag_filter.items():
            if key not in metadata.tags or metadata.tags[key] != value:
                return False
        return True

    async def _check_memory_limits(self, new_memory_usage: int) -> bool:
        """Check if adding new DataFrame would exceed memory limits."""
        stats = await self.get_storage_stats()
        current_memory_mb = stats.get("total_memory_mb", 0)
        new_memory_mb = new_memory_usage / (1024 * 1024)

        return (current_memory_mb + new_memory_mb) <= self.max_memory_mb
