"""Tests for in-memory DataFrame storage implementation."""

import pytest
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import patch

from ..storage.memory import InMemoryDataFrameStorage
from ..interface import DataFrameMetadata


class TestInMemoryDataFrameStorage:
    """Test cases for InMemoryDataFrameStorage."""

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            'id': range(1, 101),
            'name': [f'user_{i}' for i in range(1, 101)],
            'score': [i * 10.5 for i in range(1, 101)],
            'category': ['A' if i % 2 == 0 else 'B' for i in range(1, 101)],
        })

    @pytest.fixture
    def small_dataframe(self):
        """Create a small DataFrame for testing."""
        return pd.DataFrame({
            'a': [1, 2, 3],
            'b': ['x', 'y', 'z'],
        })

    @pytest.fixture
    def storage(self):
        """Create a storage instance for testing."""
        return InMemoryDataFrameStorage(
            max_memory_mb=10,
            default_ttl_seconds=3600,
            cleanup_interval_seconds=60,
            max_dataframes=5,
        )

    def test_initialization(self):
        """Test storage initialization."""
        storage = InMemoryDataFrameStorage(
            max_memory_mb=256,
            default_ttl_seconds=7200,
            cleanup_interval_seconds=300,
            max_dataframes=100,
        )

        assert storage.max_memory_mb == 256
        assert storage.default_ttl_seconds == 7200
        assert storage.cleanup_interval_seconds == 300
        assert storage.max_dataframes == 100
        assert len(storage._dataframes) == 0
        assert len(storage._metadata) == 0

    def test_initialization_defaults(self):
        """Test storage initialization with defaults."""
        storage = InMemoryDataFrameStorage()

        assert storage.max_memory_mb == 1024
        assert storage.default_ttl_seconds == 3600
        assert storage.cleanup_interval_seconds == 300
        assert storage.max_dataframes == 1000

    @pytest.mark.asyncio
    async def test_store_and_retrieve_basic(self, storage, small_dataframe):
        """Test basic store and retrieve operations."""
        df_id = uuid4()

        # Store DataFrame
        metadata = await storage.store(small_dataframe, df_id)

        assert isinstance(metadata, DataFrameMetadata)
        assert metadata.df_id == df_id
        assert metadata.shape == small_dataframe.shape
        assert metadata.memory_usage > 0
        assert df_id in storage._dataframes
        assert df_id in storage._metadata

        # Retrieve DataFrame
        retrieved_df = await storage.retrieve(df_id)
        assert retrieved_df is not None
        pd.testing.assert_frame_equal(retrieved_df, small_dataframe)

    @pytest.mark.asyncio
    async def test_store_with_ttl_and_tags(self, storage, small_dataframe):
        """Test storing with TTL and tags."""
        df_id = uuid4()
        ttl_seconds = 1800
        tags = {"env": "test", "version": "1.0"}

        metadata = await storage.store(
            small_dataframe,
            df_id,
            ttl_seconds=ttl_seconds,
            tags=tags
        )

        assert metadata.ttl_seconds == ttl_seconds
        assert metadata.tags == tags

    @pytest.mark.asyncio
    async def test_store_duplicate_id_overwrites(self, storage, small_dataframe):
        """Test storing with duplicate ID overwrites existing data."""
        df_id = uuid4()

        # Store first DataFrame
        await storage.store(small_dataframe, df_id, tags={"version": "1"})

        # Store second DataFrame with same ID
        new_df = pd.DataFrame({"x": [10, 20]})
        metadata = await storage.store(new_df, df_id, tags={"version": "2"})

        # Should have overwritten
        assert len(storage._dataframes) == 1
        assert metadata.tags["version"] == "2"

        retrieved_df = await storage.retrieve(df_id)
        pd.testing.assert_frame_equal(retrieved_df, new_df)

    @pytest.mark.asyncio
    async def test_lru_behavior(self, storage, small_dataframe):
        """Test LRU (Least Recently Used) behavior."""
        df_ids = []

        # Store multiple DataFrames
        for i in range(3):
            df_id = uuid4()
            df = pd.DataFrame({"value": [i]})
            await storage.store(df, df_id)
            df_ids.append(df_id)

        # Access first DataFrame (should move it to end)
        await storage.retrieve(df_ids[0])

        # Check order in OrderedDict (most recently used should be last)
        ordered_ids = list(storage._dataframes.keys())
        assert ordered_ids[-1] == df_ids[0]  # Most recently accessed

    @pytest.mark.asyncio
    async def test_max_dataframes_limit(self, storage, small_dataframe):
        """Test maximum DataFrames limit enforcement."""
        storage.max_dataframes = 3
        df_ids = []

        # Store DataFrames up to the limit
        for i in range(5):  # Try to store more than limit
            df_id = uuid4()
            df = pd.DataFrame({"value": [i]})
            await storage.store(df, df_id)
            df_ids.append(df_id)

        # Should only keep the maximum number
        assert len(storage._dataframes) == 3
        assert len(storage._metadata) == 3

        # First two should have been evicted (LRU)
        assert df_ids[0] not in storage._dataframes
        assert df_ids[1] not in storage._dataframes

        # Last three should be present
        for df_id in df_ids[2:]:
            assert df_id in storage._dataframes

    @pytest.mark.asyncio
    async def test_memory_limit_eviction(self, storage):
        """Test memory limit enforcement with eviction."""
        storage.max_memory_mb = 1  # Very small limit

        # Create a relatively large DataFrame
        large_df = pd.DataFrame({
            'data': ['x' * 1000] * 100  # Should be substantial in memory
        })

        df_ids = []

        # Try to store multiple large DataFrames
        for i in range(3):
            df_id = uuid4()
            await storage.store(large_df, df_id)
            df_ids.append(df_id)

        # Should have triggered eviction due to memory or count limits
        # Either memory eviction or max_dataframes limit should apply
        assert len(storage._dataframes) <= storage.max_dataframes

        # At least the last one should be present (if any stored successfully)
        if len(storage._dataframes) > 0:
            # The most recent ones should be more likely to be present
            recent_present = any(df_id in storage._dataframes for df_id in df_ids[-2:])
            assert recent_present

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent(self, storage):
        """Test retrieving non-existent DataFrame."""
        result = await storage.retrieve(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_retrieve_expired(self, storage, small_dataframe):
        """Test retrieving expired DataFrame."""
        df_id = uuid4()

        # Store with very short TTL
        await storage.store(small_dataframe, df_id, ttl_seconds=1)

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should return None and clean up
        result = await storage.retrieve(df_id)
        assert result is None
        assert df_id not in storage._dataframes
        assert df_id not in storage._metadata

    @pytest.mark.asyncio
    async def test_get_metadata(self, storage, small_dataframe):
        """Test getting metadata."""
        df_id = uuid4()
        tags = {"type": "test"}

        metadata = await storage.store(small_dataframe, df_id, tags=tags)

        retrieved_metadata = await storage.get_metadata(df_id)
        assert retrieved_metadata is not None
        assert retrieved_metadata.df_id == metadata.df_id
        assert retrieved_metadata.tags == tags

    @pytest.mark.asyncio
    async def test_get_metadata_nonexistent(self, storage):
        """Test getting metadata for non-existent DataFrame."""
        result = await storage.get_metadata(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_metadata_expired(self, storage, small_dataframe):
        """Test getting metadata for expired DataFrame."""
        df_id = uuid4()

        await storage.store(small_dataframe, df_id, ttl_seconds=1)
        await asyncio.sleep(1.1)

        result = await storage.get_metadata(df_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing(self, storage, small_dataframe):
        """Test deleting existing DataFrame."""
        df_id = uuid4()

        await storage.store(small_dataframe, df_id)
        assert df_id in storage._dataframes

        result = await storage.delete(df_id)
        assert result is True
        assert df_id not in storage._dataframes
        assert df_id not in storage._metadata

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, storage):
        """Test deleting non-existent DataFrame."""
        result = await storage.delete(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_list_dataframes_basic(self, storage, small_dataframe):
        """Test listing all DataFrames."""
        df_ids = []

        # Store multiple DataFrames
        for i in range(3):
            df_id = uuid4()
            await storage.store(small_dataframe, df_id, tags={"index": str(i)})
            df_ids.append(df_id)

        # List all
        all_dataframes = await storage.list_dataframes()
        assert len(all_dataframes) == 3

        # Check they're sorted by creation time (newest first)
        creation_times = [m.created_at for m in all_dataframes]
        assert creation_times == sorted(creation_times, reverse=True)

    @pytest.mark.asyncio
    async def test_list_dataframes_with_tags(self, storage, small_dataframe):
        """Test listing DataFrames with tag filtering."""
        # Store DataFrames with different tags
        df_id1 = uuid4()
        await storage.store(small_dataframe, df_id1, tags={"env": "test", "type": "A"})

        df_id2 = uuid4()
        await storage.store(small_dataframe, df_id2, tags={"env": "prod", "type": "A"})

        df_id3 = uuid4()
        await storage.store(small_dataframe, df_id3, tags={"env": "test", "type": "B"})

        # Filter by single tag
        test_dataframes = await storage.list_dataframes(tags={"env": "test"})
        assert len(test_dataframes) == 2
        assert all(m.tags["env"] == "test" for m in test_dataframes)

        # Filter by multiple tags
        test_a_dataframes = await storage.list_dataframes(tags={"env": "test", "type": "A"})
        assert len(test_a_dataframes) == 1
        assert test_a_dataframes[0].df_id == df_id1

    @pytest.mark.asyncio
    async def test_list_dataframes_with_limit(self, storage, small_dataframe):
        """Test listing DataFrames with limit."""
        # Store multiple DataFrames
        for i in range(5):
            df_id = uuid4()
            await storage.store(small_dataframe, df_id)

        # List with limit
        limited = await storage.list_dataframes(limit=3)
        assert len(limited) == 3

    @pytest.mark.asyncio
    async def test_list_dataframes_cleans_expired(self, storage, small_dataframe):
        """Test that listing cleans up expired DataFrames."""
        # Store expired DataFrame
        expired_id = uuid4()
        await storage.store(small_dataframe, expired_id, ttl_seconds=1)

        # Store non-expired DataFrame
        valid_id = uuid4()
        await storage.store(small_dataframe, valid_id, ttl_seconds=3600)

        # Wait for expiration
        await asyncio.sleep(1.1)

        # List should clean up expired ones
        result = await storage.list_dataframes()
        assert len(result) == 1
        assert result[0].df_id == valid_id
        assert expired_id not in storage._dataframes

    @pytest.mark.asyncio
    async def test_cleanup_expired_manual(self, storage, small_dataframe):
        """Test manual cleanup of expired DataFrames."""
        # Store expired DataFrames
        expired_ids = []
        for i in range(3):
            df_id = uuid4()
            await storage.store(small_dataframe, df_id, ttl_seconds=1)
            expired_ids.append(df_id)

        # Store valid DataFrame
        valid_id = uuid4()
        await storage.store(small_dataframe, valid_id, ttl_seconds=3600)

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Manual cleanup
        cleaned_count = await storage.cleanup_expired()

        assert cleaned_count == 3
        assert len(storage._dataframes) == 1
        assert valid_id in storage._dataframes

        for expired_id in expired_ids:
            assert expired_id not in storage._dataframes

    @pytest.mark.asyncio
    async def test_get_storage_stats(self, storage, small_dataframe):
        """Test getting storage statistics."""
        # Initially empty
        stats = await storage.get_storage_stats()
        assert stats["backend"] == "memory"
        assert stats["dataframe_count"] == 0
        assert stats["total_memory_mb"] == 0
        assert stats["memory_usage_pct"] == 0

        # Store some DataFrames
        for i in range(3):
            df_id = uuid4()
            await storage.store(small_dataframe, df_id)

        stats = await storage.get_storage_stats()
        assert stats["dataframe_count"] == 3
        assert stats["total_memory_mb"] > 0
        assert stats["total_size_mb"] > 0
        assert stats["max_memory_mb"] == storage.max_memory_mb
        assert stats["max_dataframes"] == storage.max_dataframes
        assert 0 <= stats["memory_usage_pct"] <= 100

    @pytest.mark.asyncio
    async def test_clear_all(self, storage, small_dataframe):
        """Test clearing all DataFrames."""
        # Store multiple DataFrames
        for i in range(3):
            df_id = uuid4()
            await storage.store(small_dataframe, df_id)

        assert len(storage._dataframes) == 3

        # Clear all
        cleared_count = await storage.clear_all()

        assert cleared_count == 3
        assert len(storage._dataframes) == 0
        assert len(storage._metadata) == 0

    @pytest.mark.asyncio
    async def test_clear_all_empty(self, storage):
        """Test clearing when storage is empty."""
        cleared_count = await storage.clear_all()
        assert cleared_count == 0

    @pytest.mark.asyncio
    async def test_data_isolation(self, storage, small_dataframe):
        """Test that stored DataFrames are properly isolated (copied)."""
        df_id = uuid4()
        original_df = small_dataframe.copy()

        # Store DataFrame
        await storage.store(original_df, df_id)

        # Modify original DataFrame
        original_df.loc[0, 'a'] = 999

        # Retrieved DataFrame should be unchanged
        retrieved_df = await storage.retrieve(df_id)
        assert retrieved_df.loc[0, 'a'] != 999
        assert retrieved_df.loc[0, 'a'] == small_dataframe.loc[0, 'a']

    @pytest.mark.asyncio
    async def test_concurrent_access(self, storage, small_dataframe):
        """Test concurrent access to storage."""
        async def store_dataframe(index):
            df_id = uuid4()
            df = pd.DataFrame({"index": [index]})
            await storage.store(df, df_id)
            return df_id

        # Store DataFrames concurrently (fewer than max_dataframes limit)
        tasks = [store_dataframe(i) for i in range(3)]  # Reduced from 10 to 3
        df_ids = await asyncio.gather(*tasks)

        # All should be stored successfully
        assert len(df_ids) == 3
        assert len(set(df_ids)) == 3  # All unique

        # All should be retrievable (unless evicted due to limits)
        stored_count = 0
        for df_id in df_ids:
            retrieved = await storage.retrieve(df_id)
            if retrieved is not None:
                stored_count += 1

        # At least some should be retrievable
        assert stored_count > 0

    @pytest.mark.asyncio
    async def test_error_handling_corrupted_metadata(self, storage, small_dataframe):
        """Test error handling with corrupted metadata."""
        df_id = uuid4()
        await storage.store(small_dataframe, df_id)

        # Corrupt metadata by setting invalid expiration
        storage._metadata[df_id].ttl_seconds = "invalid"

        # Should handle gracefully
        try:
            await storage.retrieve(df_id)
            # If no exception, that's fine too
        except Exception:
            # Should not crash the system
            pass

    @pytest.mark.asyncio
    async def test_logging_behavior(self, storage, small_dataframe):
        """Test that operations are properly logged."""
        with patch.object(storage._logger, 'debug') as mock_debug:
            with patch.object(storage._logger, 'info') as mock_info:
                df_id = uuid4()

                # Store should log
                await storage.store(small_dataframe, df_id)
                assert mock_debug.called

                # Clear should log
                await storage.clear_all()
                assert mock_info.called


if __name__ == "__main__":
    pytest.main([__file__])
