"""In-memory DataFrame storage implementation."""

import asyncio
from collections import OrderedDict
from typing import Any, Dict, List, Optional
from uuid import UUID

import pandas as pd

from ..interface import DataFrameMetadata
from .base import BaseDataFrameStorage


class InMemoryDataFrameStorage(BaseDataFrameStorage):
    """In-memory storage for DataFrames with TTL and memory management."""

    def __init__(
        self,
        max_memory_mb: int = 1024,
        default_ttl_seconds: int = 3600,
        cleanup_interval_seconds: int = 300,
        max_dataframes: int = 1000,
    ):
        # Initialize the parent class but don't start cleanup automatically
        self.max_memory_mb = max_memory_mb
        self.default_ttl_seconds = default_ttl_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

        import logging
        logger = logging.getLogger(__name__)
        self._logger = logger.getChild(self.__class__.__name__)

        self.max_dataframes = max_dataframes

        # Use OrderedDict for LRU behavior
        self._dataframes: OrderedDict[str, pd.DataFrame] = OrderedDict()
        self._metadata: Dict[str, DataFrameMetadata] = {}

    async def store(
        self,
        df: pd.DataFrame,
        df_id: str,
        ttl_seconds: Optional[int] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> DataFrameMetadata:
        """Store a DataFrame in memory."""
        async with self._lock:
            # Create simplified metadata to avoid expensive operations
            memory_usage = df.memory_usage(deep=True).sum()
            dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}

            from datetime import datetime
            metadata = DataFrameMetadata(
                df_id=df_id,
                created_at=datetime.now(),
                size_bytes=memory_usage,  # Use memory_usage as approximation for size
                shape=df.shape,
                dtypes=dtypes,
                memory_usage=memory_usage,
                ttl_seconds=ttl_seconds or self.default_ttl_seconds,
                tags=tags,
            )

            # Simple memory check - skip complex checks for now
            total_memory = sum(m.memory_usage for m in self._metadata.values())
            if (total_memory + memory_usage) > (self.max_memory_mb * 1024 * 1024):
                # Simple eviction: remove oldest items
                while len(self._dataframes) > 0 and (total_memory + memory_usage) > (self.max_memory_mb * 1024 * 1024):
                    oldest_id = next(iter(self._dataframes))
                    oldest_meta = self._metadata.get(oldest_id)
                    if oldest_meta:
                        total_memory -= oldest_meta.memory_usage
                    self._dataframes.pop(oldest_id, None)
                    self._metadata.pop(oldest_id, None)

            # Check dataframe limit
            if len(self._dataframes) >= self.max_dataframes:
                # Remove oldest
                oldest_id = next(iter(self._dataframes))
                self._dataframes.pop(oldest_id, None)
                self._metadata.pop(oldest_id, None)

            # Store the DataFrame and metadata
            self._dataframes[df_id] = df.copy()
            self._metadata[df_id] = metadata

            # Move to end (most recently used)
            self._dataframes.move_to_end(df_id)

            self._logger.debug(
                f"Stored DataFrame {df_id} with shape {df.shape}, "
                f"memory usage: {metadata.memory_usage / (1024*1024):.2f}MB"
            )

            return metadata

    async def retrieve(self, df_id: str) -> Optional[pd.DataFrame]:
        """Retrieve a DataFrame from memory."""
        async with self._lock:
            if df_id not in self._dataframes:
                return None

            # Check if expired
            metadata = self._metadata.get(df_id)
            if metadata and metadata.is_expired:
                await self._remove_dataframe(df_id)
                return None

            # Move to end (most recently used)
            self._dataframes.move_to_end(df_id)

            return self._dataframes[df_id].copy()

    async def get_metadata(self, df_id: str) -> Optional[DataFrameMetadata]:
        """Get metadata for a DataFrame."""
        async with self._lock:
            metadata = self._metadata.get(df_id)
            if metadata and metadata.is_expired:
                await self._remove_dataframe(df_id)
                return None
            return metadata

    async def delete(self, df_id: str) -> bool:
        """Delete a DataFrame from memory."""
        async with self._lock:
            return await self._remove_dataframe(df_id)

    async def list_dataframes(
        self,
        limit: Optional[int] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> List[DataFrameMetadata]:
        """List stored DataFrames with optional filtering."""
        async with self._lock:
            # Clean up expired first
            await self._cleanup_expired_internal()

            # Filter by tags if specified
            metadata_list = []
            for metadata in self._metadata.values():
                if self._matches_tags(metadata, tags or {}):
                    metadata_list.append(metadata)

            # Sort by creation time (newest first)
            metadata_list.sort(key=lambda m: m.created_at, reverse=True)

            # Apply limit
            if limit is not None:
                metadata_list = metadata_list[:limit]

            return metadata_list

    async def cleanup_expired(self) -> int:
        """Remove expired DataFrames."""
        async with self._lock:
            return await self._cleanup_expired_internal()

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        async with self._lock:
            total_memory = sum(
                metadata.memory_usage for metadata in self._metadata.values()
            )
            total_size = sum(
                metadata.size_bytes for metadata in self._metadata.values()
            )

            return {
                "backend": "memory",
                "dataframe_count": len(self._dataframes),
                "total_memory_mb": total_memory / (1024 * 1024),
                "total_size_mb": total_size / (1024 * 1024),
                "max_memory_mb": self.max_memory_mb,
                "max_dataframes": self.max_dataframes,
                "memory_usage_pct": (total_memory / (1024 * 1024)) / self.max_memory_mb * 100,
            }

    async def clear_all(self) -> int:
        """Clear all stored DataFrames."""
        async with self._lock:
            count = len(self._dataframes)
            self._dataframes.clear()
            self._metadata.clear()
            self._logger.info(f"Cleared all {count} DataFrames from memory")
            return count

    async def _remove_dataframe(self, df_id: str) -> bool:
        """Remove a DataFrame and its metadata (internal, assumes lock held)."""
        if df_id in self._dataframes:
            del self._dataframes[df_id]
            del self._metadata[df_id]
            self._logger.debug(f"Removed DataFrame {df_id}")
            return True
        return False

    async def _cleanup_expired_internal(self) -> int:
        """Internal cleanup of expired DataFrames (assumes lock held)."""
        expired_ids = []
        for df_id, metadata in self._metadata.items():
            if metadata.is_expired:
                expired_ids.append(df_id)

        for df_id in expired_ids:
            await self._remove_dataframe(df_id)

        return len(expired_ids)

    async def _evict_lru_if_needed(self, required_memory: int) -> None:
        """Evict LRU DataFrames if needed to make space (assumes lock held)."""
        stats = await self.get_storage_stats()
        current_memory = stats["total_memory_mb"] * 1024 * 1024
        required_memory_mb = required_memory / (1024 * 1024)
        max_memory = self.max_memory_mb * 1024 * 1024

        # Calculate how much memory we need to free
        memory_to_free = (current_memory + required_memory) - max_memory

        if memory_to_free <= 0:
            return

        # Evict LRU items until we have enough space
        freed_memory = 0
        evicted_count = 0

        # Iterate from least recently used (beginning of OrderedDict)
        for df_id in list(self._dataframes.keys()):
            if freed_memory >= memory_to_free:
                break

            metadata = self._metadata.get(df_id)
            if metadata:
                freed_memory += metadata.memory_usage
                await self._remove_dataframe(df_id)
                evicted_count += 1

        if evicted_count > 0:
            self._logger.info(
                f"Evicted {evicted_count} LRU DataFrames to free "
                f"{freed_memory / (1024*1024):.2f}MB"
            )

    async def _evict_lru_dataframes(self, count: int) -> None:
        """Evict a specific number of LRU DataFrames (assumes lock held)."""
        evicted = 0
        for df_id in list(self._dataframes.keys()):
            if evicted >= count:
                break
            await self._remove_dataframe(df_id)
            evicted += 1
