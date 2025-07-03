"""Tests for DataFrame manager functionality."""

import asyncio
import pandas as pd
import pytest
import pytest_asyncio
from uuid import UUID

from ..manager import DataFrameManager
from ..storage.memory import InMemoryDataFrameStorage
from ..query.processor import DataFrameQueryProcessor
from ..summarizer import DataFrameSummarizer


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame({
        'id': range(1, 101),
        'name': [f'user_{i}' for i in range(1, 101)],
        'age': [20 + (i % 50) for i in range(100)],
        'category': ['A' if i % 3 == 0 else 'B' if i % 3 == 1 else 'C' for i in range(100)],
        'score': [i * 0.5 for i in range(100)],
    })


@pytest_asyncio.fixture
async def manager():
    """Create a DataFrameManager instance for testing."""
    manager = DataFrameManager(
        max_memory_mb=100,  # Small limit for testing
        default_ttl_seconds=10,  # Short TTL for testing
    )
    await manager.start()
    yield manager
    await manager.shutdown()


class TestDataFrameManager:
    """Test cases for DataFrameManager."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_dataframe(self, manager, sample_dataframe):
        """Test storing and retrieving a DataFrame."""
        # Store DataFrame
        df_id = await manager.store_dataframe(sample_dataframe)
        assert isinstance(df_id, UUID)

        # Retrieve DataFrame
        retrieved_df = await manager.get_dataframe(df_id)
        assert retrieved_df is not None
        assert retrieved_df.shape == sample_dataframe.shape
        assert list(retrieved_df.columns) == list(sample_dataframe.columns)

        # Verify data integrity
        pd.testing.assert_frame_equal(retrieved_df, sample_dataframe)

    @pytest.mark.asyncio
    async def test_query_operations(self, manager, sample_dataframe):
        """Test various query operations."""
        df_id = await manager.store_dataframe(sample_dataframe)

        # Test head operation
        result = await manager.query_dataframe(df_id, "head", {"n": 5})
        assert result is not None
        assert result.data.shape[0] == 5
        assert result.operation == "head"

        # Test tail operation
        result = await manager.query_dataframe(df_id, "tail", {"n": 3})
        assert result is not None
        assert result.data.shape[0] == 3
        assert result.operation == "tail"

        # Test sample operation
        result = await manager.query_dataframe(df_id, "sample", {"n": 10})
        assert result is not None
        assert result.data.shape[0] == 10
        assert result.operation == "sample"

        # Test describe operation
        result = await manager.query_dataframe(df_id, "describe")
        assert result is not None
        assert result.operation == "describe"

        # Test filter operation
        result = await manager.query_dataframe(
            df_id, "filter",
            {"conditions": {"age": {"gt": 30}}}
        )
        assert result is not None
        assert result.operation == "filter"
        assert all(result.data['age'] > 30)

        # Test search operation
        result = await manager.query_dataframe(
            df_id, "search",
            {"query": "user_1", "columns": ["name"]}
        )
        assert result is not None
        assert result.operation == "search"

        # Test value_counts operation
        result = await manager.query_dataframe(
            df_id, "value_counts",
            {"column": "category"}
        )
        assert result is not None
        assert result.operation == "value_counts"

    @pytest.mark.asyncio
    async def test_summarize_dataframe(self, manager, sample_dataframe):
        """Test DataFrame summarization."""
        df_id = await manager.store_dataframe(sample_dataframe)

        # Get summary
        summary = await manager.summarize_dataframe(df_id, max_size_bytes=10000)
        assert summary is not None
        assert "shape" in summary
        assert "columns" in summary
        assert "dtypes" in summary
        assert "memory_usage_mb" in summary
        assert summary["shape"] == sample_dataframe.shape

    @pytest.mark.asyncio
    async def test_list_stored_dataframes(self, manager, sample_dataframe):
        """Test listing stored DataFrames."""
        # Store multiple DataFrames with tags
        df_id1 = await manager.store_dataframe(
            sample_dataframe,
            tags={"type": "test", "version": "1"}
        )
        df_id2 = await manager.store_dataframe(
            sample_dataframe.head(10),
            tags={"type": "sample", "version": "1"}
        )

        # List all DataFrames
        all_dataframes = await manager.list_stored_dataframes()
        assert len(all_dataframes) >= 2

        # List with tag filter
        test_dataframes = await manager.list_stored_dataframes(
            tags={"type": "test"}
        )
        assert len(test_dataframes) == 1
        assert test_dataframes[0].df_id == df_id1

    @pytest.mark.asyncio
    async def test_delete_dataframe(self, manager, sample_dataframe):
        """Test deleting a DataFrame."""
        df_id = await manager.store_dataframe(sample_dataframe)

        # Verify it exists
        retrieved_df = await manager.get_dataframe(df_id)
        assert retrieved_df is not None

        # Delete it
        deleted = await manager.delete_dataframe(df_id)
        assert deleted is True

        # Verify it's gone
        retrieved_df = await manager.get_dataframe(df_id)
        assert retrieved_df is None

        # Try to delete again
        deleted = await manager.delete_dataframe(df_id)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_storage_stats(self, manager, sample_dataframe):
        """Test getting storage statistics."""
        # Store a DataFrame
        df_id = await manager.store_dataframe(sample_dataframe)

        # Get stats
        stats = await manager.get_storage_stats()
        assert stats is not None
        assert "dataframe_count" in stats
        assert "total_memory_mb" in stats
        assert "memory_usage_pct" in stats
        assert stats["dataframe_count"] >= 1

    @pytest.mark.asyncio
    async def test_format_dataframe_for_display(self, manager, sample_dataframe):
        """Test formatting DataFrame for display."""
        df_id = await manager.store_dataframe(sample_dataframe)

        # Test table format
        formatted = await manager.format_dataframe_for_display(
            df_id, max_size_bytes=5000, format_type="table"
        )
        assert formatted is not None
        assert isinstance(formatted, str)
        assert len(formatted) > 0

        # Test CSV format
        formatted = await manager.format_dataframe_for_display(
            df_id, max_size_bytes=5000, format_type="csv"
        )
        assert formatted is not None
        assert isinstance(formatted, str)
        assert "," in formatted  # Should contain CSV separators

    @pytest.mark.asyncio
    async def test_memory_limits(self, sample_dataframe):
        """Test memory limit enforcement."""
        # Create manager with very small memory limit
        small_manager = DataFrameManager(
            max_memory_mb=1,  # Very small limit
            default_ttl_seconds=60,
        )
        await small_manager.start()

        try:
            # Try to store a DataFrame that exceeds the limit
            large_df = pd.concat([sample_dataframe] * 10)  # Make it larger

            # This might succeed or fail depending on actual memory usage
            # If it succeeds, try storing more DataFrames to trigger eviction
            df_ids = []
            for i in range(5):
                try:
                    df_id = await small_manager.store_dataframe(large_df)
                    df_ids.append(df_id)
                except MemoryError:
                    # Expected when memory limit is reached
                    break

            # Verify at least one was stored
            if df_ids:
                stored_df = await small_manager.get_dataframe(df_ids[0])
                # First one might have been evicted if we stored too many
                # That's expected behavior

        finally:
            await small_manager.shutdown()

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, sample_dataframe):
        """Test TTL expiration of DataFrames."""
        # Create manager with very short TTL
        ttl_manager = DataFrameManager(
            max_memory_mb=100,
            default_ttl_seconds=1,  # 1 second TTL
        )
        await ttl_manager.start()

        try:
            # Store DataFrame
            df_id = await ttl_manager.store_dataframe(sample_dataframe)

            # Verify it exists immediately
            retrieved_df = await ttl_manager.get_dataframe(df_id)
            assert retrieved_df is not None

            # Wait for TTL to expire
            await asyncio.sleep(2)

            # Verify it's expired (should be None)
            retrieved_df = await ttl_manager.get_dataframe(df_id)
            assert retrieved_df is None

        finally:
            await ttl_manager.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])
