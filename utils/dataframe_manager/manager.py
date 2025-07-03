"""Main DataFrame manager implementation."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import pandas as pd

from .interface import (
    DataFrameManagerInterface,
    DataFrameStorageInterface,
    DataFrameQueryInterface,
    DataFrameSummarizerInterface,
    DataFrameMetadata,
    DataFrameQueryResult,
)
from .storage.memory import InMemoryDataFrameStorage
from .query.processor import DataFrameQueryProcessor
from .summarizer import DataFrameSummarizer

logger = logging.getLogger(__name__)


class DataFrameManager(DataFrameManagerInterface):
    """Main orchestrator for DataFrame management operations."""

    def __init__(
        self,
        storage: Optional[DataFrameStorageInterface] = None,
        query_processor: Optional[DataFrameQueryInterface] = None,
        summarizer: Optional[DataFrameSummarizerInterface] = None,
        max_memory_mb: int = 1024,
        default_ttl_seconds: int = 3600,
    ):
        self._storage = storage or InMemoryDataFrameStorage(
            max_memory_mb=max_memory_mb,
            default_ttl_seconds=default_ttl_seconds,
        )
        self._query_processor = query_processor or DataFrameQueryProcessor()
        self._summarizer = summarizer or DataFrameSummarizer()

        self._logger = logger.getChild(self.__class__.__name__)
        self._started = False

    @property
    def storage(self) -> DataFrameStorageInterface:
        """Get the storage backend."""
        return self._storage

    @property
    def query_processor(self) -> DataFrameQueryInterface:
        """Get the query processor."""
        return self._query_processor

    @property
    def summarizer(self) -> DataFrameSummarizerInterface:
        """Get the summarizer."""
        return self._summarizer

    async def start(self) -> None:
        """Start the manager (initialize background tasks, etc.)."""
        if self._started:
            return

        try:
            # Start storage backend if it has a start method
            if hasattr(self._storage, 'start'):
                await self._storage.start()

            self._started = True
            self._logger.info("DataFrame manager started successfully")

        except Exception as e:
            self._logger.error(f"Failed to start DataFrame manager: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the manager gracefully."""
        if not self._started:
            return

        try:
            # Shutdown storage backend if it has a shutdown method
            if hasattr(self._storage, 'shutdown'):
                await self._storage.shutdown()

            self._started = False
            self._logger.info("DataFrame manager shutdown completed")

        except Exception as e:
            self._logger.error(f"Error during DataFrame manager shutdown: {e}")
            raise

    async def store_dataframe(
        self,
        df: pd.DataFrame,
        ttl_seconds: Optional[int] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a DataFrame and return its ID."""
        if not self._started:
            await self.start()

        if df.empty:
            raise ValueError("Cannot store empty DataFrame")

        # Generate human-friendly DataFrame ID
        df_id = f"dataframe-{str(uuid4())[:8]}"

        try:
            metadata = await self._storage.store(
                df=df,
                df_id=df_id,
                ttl_seconds=ttl_seconds,
                tags=tags,
            )

            self._logger.info(
                f"Stored DataFrame {df_id} with shape {df.shape}, "
                f"memory: {metadata.memory_usage / (1024*1024):.2f}MB"
            )

            return df_id

        except Exception as e:
            self._logger.error(f"Failed to store DataFrame {df_id}: {e}")
            raise

    async def get_dataframe(self, df_id: str) -> Optional[pd.DataFrame]:
        """Retrieve a stored DataFrame."""
        if not self._started:
            await self.start()

        try:
            df = await self._storage.retrieve(df_id)
            if df is not None:
                self._logger.debug(f"Retrieved DataFrame {df_id} with shape {df.shape}")
            else:
                self._logger.debug(f"DataFrame {df_id} not found or expired")

            return df

        except Exception as e:
            self._logger.error(f"Failed to retrieve DataFrame {df_id}: {e}")
            raise

    async def query_dataframe(
        self,
        df_id: str,
        operation: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[DataFrameQueryResult]:
        """Execute a query operation on a stored DataFrame."""
        if not self._started:
            await self.start()

        # Retrieve the DataFrame
        df = await self.get_dataframe(df_id)
        if df is None:
            return None

        parameters = parameters or {}

        try:
            # Execute the requested operation
            if operation == "head":
                result = await self._query_processor.head(df, **parameters)
            elif operation == "tail":
                result = await self._query_processor.tail(df, **parameters)
            elif operation == "sample":
                result = await self._query_processor.sample(df, **parameters)
            elif operation == "describe":
                result = await self._query_processor.describe(df, **parameters)
            elif operation == "info":
                result = await self._query_processor.info(df, **parameters)
            elif operation == "filter":
                result = await self._query_processor.filter(df, **parameters)
            elif operation == "search":
                result = await self._query_processor.search(df, **parameters)
            elif operation == "value_counts":
                result = await self._query_processor.value_counts(df, **parameters)
            else:
                raise ValueError(f"Unknown query operation: {operation}")

            self._logger.debug(
                f"Executed {operation} on DataFrame {df_id} in "
                f"{result.execution_time_ms:.1f}ms"
            )

            return result

        except Exception as e:
            self._logger.error(
                f"Failed to execute {operation} on DataFrame {df_id}: {e}"
            )
            raise

    async def summarize_dataframe(
        self,
        df_id: str,
        max_size_bytes: int,
        include_sample: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Get summary of stored DataFrame."""
        if not self._started:
            await self.start()

        # Retrieve the DataFrame
        df = await self.get_dataframe(df_id)
        if df is None:
            return None

        try:
            summary = await self._summarizer.summarize(
                df=df,
                max_size_bytes=max_size_bytes,
                include_sample=include_sample,
            )

            # Add DataFrame ID to summary
            summary["df_id"] = str(df_id)

            self._logger.debug(f"Generated summary for DataFrame {df_id}")

            return summary

        except Exception as e:
            self._logger.error(f"Failed to summarize DataFrame {df_id}: {e}")
            raise

    async def list_stored_dataframes(
        self,
        tags: Optional[Dict[str, Any]] = None,
    ) -> List[DataFrameMetadata]:
        """List all stored DataFrames."""
        if not self._started:
            await self.start()

        try:
            dataframes = await self._storage.list_dataframes(tags=tags)
            self._logger.debug(f"Listed {len(dataframes)} stored DataFrames")
            return dataframes

        except Exception as e:
            self._logger.error(f"Failed to list DataFrames: {e}")
            raise

    async def delete_dataframe(self, df_id: str) -> bool:
        """Delete a stored DataFrame."""
        if not self._started:
            await self.start()

        try:
            deleted = await self._storage.delete(df_id)
            if deleted:
                self._logger.info(f"Deleted DataFrame {df_id}")
            else:
                self._logger.debug(f"DataFrame {df_id} not found for deletion")

            return deleted

        except Exception as e:
            self._logger.error(f"Failed to delete DataFrame {df_id}: {e}")
            raise

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        if not self._started:
            await self.start()

        try:
            stats = await self._storage.get_storage_stats()
            return stats

        except Exception as e:
            self._logger.error(f"Failed to get storage stats: {e}")
            raise

    async def cleanup_expired(self) -> int:
        """Manually trigger cleanup of expired DataFrames."""
        if not self._started:
            await self.start()

        try:
            removed_count = await self._storage.cleanup_expired()
            if removed_count > 0:
                self._logger.info(f"Cleaned up {removed_count} expired DataFrames")
            return removed_count

        except Exception as e:
            self._logger.error(f"Failed to cleanup expired DataFrames: {e}")
            raise

    async def format_dataframe_for_display(
        self,
        df_id: str,
        max_size_bytes: int,
        format_type: str = "table",
    ) -> Optional[str]:
        """Format a stored DataFrame for display."""
        if not self._started:
            await self.start()

        # Retrieve the DataFrame
        df = await self.get_dataframe(df_id)
        if df is None:
            return None

        try:
            formatted = await self._summarizer.format_for_display(
                df=df,
                max_size_bytes=max_size_bytes,
                format_type=format_type,
            )

            self._logger.debug(
                f"Formatted DataFrame {df_id} as {format_type} "
                f"({len(formatted)} chars)"
            )

            return formatted

        except Exception as e:
            self._logger.error(
                f"Failed to format DataFrame {df_id} for display: {e}"
            )
            raise


# Global instance for easy access
_global_manager: Optional[DataFrameManager] = None


def get_dataframe_manager(
    max_memory_mb: Optional[int] = None,
    default_ttl_seconds: Optional[int] = None,
) -> DataFrameManager:
    """Get or create the global DataFrame manager instance."""
    global _global_manager

    if _global_manager is None:
        # Try to import config manager, fall back to defaults if not available
        try:
            from config.manager import env_manager
            max_memory_mb = max_memory_mb or env_manager.get_setting("dataframe_max_memory_mb", 1024)
            default_ttl_seconds = default_ttl_seconds or env_manager.get_setting("dataframe_default_ttl_seconds", 3600)
        except ImportError:
            max_memory_mb = max_memory_mb or 1024
            default_ttl_seconds = default_ttl_seconds or 3600

        _global_manager = DataFrameManager(
            max_memory_mb=max_memory_mb,
            default_ttl_seconds=default_ttl_seconds,
        )

    return _global_manager


async def shutdown_global_manager() -> None:
    """Shutdown the global DataFrame manager if it exists."""
    global _global_manager

    if _global_manager is not None:
        await _global_manager.shutdown()
        _global_manager = None
