"""Tests for base DataFrame storage implementation."""

import pytest
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock

from ..storage.base import BaseDataFrameStorage
from ..interface import DataFrameMetadata


class ConcreteStorage(BaseDataFrameStorage):
    """Concrete implementation for testing the base class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data = {}
        self._metadata_store = {}

    async def store(self, df, df_id, ttl_seconds=None, tags=None):
        metadata = self._create_metadata(df, df_id, ttl_seconds, tags)
        self._data[df_id] = df.copy()
        self._metadata_store[df_id] = metadata
        return metadata

    async def retrieve(self, df_id):
        return self._data.get(df_id)

    async def get_metadata(self, df_id):
        return self._metadata_store.get(df_id)

    async def delete(self, df_id):
        if df_id in self._data:
            del self._data[df_id]
            del self._metadata_store[df_id]
            return True
        return False

    async def list_dataframes(self, limit=None, tags=None):
        metadata_list = []
        for metadata in self._metadata_store.values():
            if self._matches_tags(metadata, tags or {}):
                metadata_list.append(metadata)
        return metadata_list[:limit] if limit else metadata_list

    async def cleanup_expired(self):
        expired_ids = []
        for df_id, metadata in self._metadata_store.items():
            if metadata.is_expired:
                expired_ids.append(df_id)

        for df_id in expired_ids:
            await self.delete(df_id)

        return len(expired_ids)

    async def get_storage_stats(self):
        total_memory = sum(m.memory_usage for m in self._metadata_store.values())
        return {
            "dataframe_count": len(self._data),
            "total_memory_mb": total_memory / (1024 * 1024),
        }

    async def clear_all(self):
        count = len(self._data)
        self._data.clear()
        self._metadata_store.clear()
        return count


class TestBaseDataFrameStorage:
    """Test cases for BaseDataFrameStorage."""

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            'id': range(1, 11),
            'name': [f'user_{i}' for i in range(1, 11)],
            'score': [i * 10.5 for i in range(1, 11)],
        })

    @pytest.fixture
    def storage(self):
        """Create a storage instance for testing."""
        return ConcreteStorage(
            max_memory_mb=100,
            default_ttl_seconds=3600,
            cleanup_interval_seconds=60,
        )

    def test_initialization(self):
        """Test storage initialization."""
        storage = ConcreteStorage(
            max_memory_mb=512,
            default_ttl_seconds=7200,
            cleanup_interval_seconds=300,
        )

        assert storage.max_memory_mb == 512
        assert storage.default_ttl_seconds == 7200
        assert storage.cleanup_interval_seconds == 300
        assert storage._cleanup_task is None
        assert hasattr(storage, '_lock')
        assert hasattr(storage, '_logger')

    def test_initialization_defaults(self):
        """Test storage initialization with defaults."""
        storage = ConcreteStorage()

        assert storage.max_memory_mb == 1024
        assert storage.default_ttl_seconds == 3600
        assert storage.cleanup_interval_seconds == 300

    @pytest.mark.asyncio
    async def test_start_cleanup_task(self, storage):
        """Test starting the cleanup task."""
        await storage.start()

        assert storage._cleanup_task is not None
        assert not storage._cleanup_task.done()

        # Cleanup
        await storage.shutdown()

    @pytest.mark.asyncio
    async def test_start_already_running(self, storage):
        """Test starting when cleanup task is already running."""
        await storage.start()
        first_task = storage._cleanup_task

        await storage.start()  # Should not create a new task
        assert storage._cleanup_task is first_task

        # Cleanup
        await storage.shutdown()

    @pytest.mark.asyncio
    async def test_start_after_done_task(self, storage):
        """Test starting after a task has completed."""
        await storage.start()
        first_task = storage._cleanup_task

        # Simulate task completion
        first_task.cancel()
        try:
            await first_task
        except asyncio.CancelledError:
            pass

        await storage.start()  # Should create a new task
        assert storage._cleanup_task is not first_task

        # Cleanup
        await storage.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown(self, storage):
        """Test shutting down the storage."""
        await storage.start()
        task = storage._cleanup_task

        await storage.shutdown()

        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_shutdown_no_task(self, storage):
        """Test shutting down when no task is running."""
        # Should not raise an exception
        await storage.shutdown()

    @pytest.mark.asyncio
    async def test_cleanup_loop(self, storage):
        """Test the cleanup loop functionality."""
        cleanup_call_count = 0

        async def mock_cleanup():
            nonlocal cleanup_call_count
            cleanup_call_count += 1
            return cleanup_call_count

        with patch.object(storage, 'cleanup_expired', side_effect=mock_cleanup):
            storage.cleanup_interval_seconds = 0.1  # Fast cleanup for testing
            await storage.start()

            # Wait for a few cleanup cycles
            await asyncio.sleep(0.3)

            await storage.shutdown()

            assert cleanup_call_count >= 2

    @pytest.mark.asyncio
    async def test_cleanup_loop_error_handling(self, storage):
        """Test cleanup loop handles errors gracefully."""
        error_count = 0

        async def failing_cleanup():
            nonlocal error_count
            error_count += 1
            if error_count <= 2:
                raise Exception("Test error")
            return 0

        with patch.object(storage, 'cleanup_expired', side_effect=failing_cleanup):
            with patch.object(storage._logger, 'error') as mock_logger:
                storage.cleanup_interval_seconds = 0.1
                await storage.start()

                # Wait for error to occur and recovery
                await asyncio.sleep(0.4)

                await storage.shutdown()

                # Should have logged errors but continued running
                assert mock_logger.call_count >= 2

    def test_create_metadata(self, storage, sample_dataframe):
        """Test metadata creation."""
        df_id = uuid4()
        ttl_seconds = 1800
        tags = {"type": "test", "source": "unit_test"}

        metadata = storage._create_metadata(
            sample_dataframe,
            df_id,
            ttl_seconds,
            tags
        )

        assert isinstance(metadata, DataFrameMetadata)
        assert metadata.df_id == df_id
        assert metadata.ttl_seconds == ttl_seconds
        assert metadata.tags == tags
        assert metadata.shape == sample_dataframe.shape
        assert metadata.size_bytes > 0
        assert metadata.memory_usage > 0
        assert len(metadata.dtypes) == len(sample_dataframe.columns)

        # Check dtype conversion
        for col, dtype in metadata.dtypes.items():
            assert isinstance(dtype, str)
            assert col in sample_dataframe.columns

    def test_create_metadata_defaults(self, storage, sample_dataframe):
        """Test metadata creation with default values."""
        df_id = uuid4()

        metadata = storage._create_metadata(sample_dataframe, df_id)

        assert metadata.ttl_seconds == storage.default_ttl_seconds
        assert metadata.tags == {}

    def test_matches_tags_empty_filter(self, storage, sample_dataframe):
        """Test tag matching with empty filter."""
        metadata = DataFrameMetadata(
            df_id=uuid4(),
            created_at=datetime.now(),
            size_bytes=1024,
            shape=(10, 3),
            dtypes={"id": "int64"},
            memory_usage=512,
            tags={"env": "test"}
        )

        # Empty filter should match any metadata
        assert storage._matches_tags(metadata, {})

    def test_matches_tags_exact_match(self, storage):
        """Test tag matching with exact match."""
        metadata = DataFrameMetadata(
            df_id=uuid4(),
            created_at=datetime.now(),
            size_bytes=1024,
            shape=(10, 3),
            dtypes={"id": "int64"},
            memory_usage=512,
            tags={"env": "test", "version": "1.0"}
        )

        assert storage._matches_tags(metadata, {"env": "test"})
        assert storage._matches_tags(metadata, {"version": "1.0"})
        assert storage._matches_tags(metadata, {"env": "test", "version": "1.0"})

    def test_matches_tags_no_match(self, storage):
        """Test tag matching with no match."""
        metadata = DataFrameMetadata(
            df_id=uuid4(),
            created_at=datetime.now(),
            size_bytes=1024,
            shape=(10, 3),
            dtypes={"id": "int64"},
            memory_usage=512,
            tags={"env": "test", "version": "1.0"}
        )

        assert not storage._matches_tags(metadata, {"env": "prod"})
        assert not storage._matches_tags(metadata, {"missing": "key"})
        assert not storage._matches_tags(metadata, {"env": "test", "version": "2.0"})

    def test_matches_tags_empty_metadata_tags(self, storage):
        """Test tag matching when metadata has no tags."""
        metadata = DataFrameMetadata(
            df_id=uuid4(),
            created_at=datetime.now(),
            size_bytes=1024,
            shape=(10, 3),
            dtypes={"id": "int64"},
            memory_usage=512,
            tags={}
        )

        assert storage._matches_tags(metadata, {})
        assert not storage._matches_tags(metadata, {"env": "test"})

    @pytest.mark.asyncio
    async def test_check_memory_limits_within_limit(self, storage):
        """Test memory limit check when within limit."""
        # Mock storage stats to return low memory usage
        with patch.object(storage, 'get_storage_stats', return_value={"total_memory_mb": 10}):
            new_memory = 50 * 1024 * 1024  # 50MB
            result = await storage._check_memory_limits(new_memory)
            assert result is True

    @pytest.mark.asyncio
    async def test_check_memory_limits_exceeds_limit(self, storage):
        """Test memory limit check when exceeding limit."""
        # Mock storage stats to return high memory usage
        with patch.object(storage, 'get_storage_stats', return_value={"total_memory_mb": 80}):
            new_memory = 50 * 1024 * 1024  # 50MB (would exceed 100MB limit)
            result = await storage._check_memory_limits(new_memory)
            assert result is False

    @pytest.mark.asyncio
    async def test_check_memory_limits_exactly_at_limit(self, storage):
        """Test memory limit check when exactly at limit."""
        # Mock storage stats to return memory usage that exactly hits limit
        with patch.object(storage, 'get_storage_stats', return_value={"total_memory_mb": 50}):
            new_memory = 50 * 1024 * 1024  # 50MB (exactly 100MB total)
            result = await storage._check_memory_limits(new_memory)
            assert result is True

    @pytest.mark.asyncio
    async def test_integration_store_and_retrieve(self, storage, sample_dataframe):
        """Test integration of store and retrieve operations."""
        df_id = uuid4()

        # Store DataFrame
        metadata = await storage.store(sample_dataframe, df_id, ttl_seconds=1800)
        assert metadata.df_id == df_id

        # Retrieve DataFrame
        retrieved_df = await storage.retrieve(df_id)
        assert retrieved_df is not None
        pd.testing.assert_frame_equal(retrieved_df, sample_dataframe)

    @pytest.mark.asyncio
    async def test_integration_metadata_operations(self, storage, sample_dataframe):
        """Test integration of metadata operations."""
        df_id = uuid4()
        tags = {"env": "test"}

        # Store with tags
        await storage.store(sample_dataframe, df_id, tags=tags)

        # Get metadata
        metadata = await storage.get_metadata(df_id)
        assert metadata is not None
        assert metadata.df_id == df_id
        assert metadata.tags == tags

        # List with tag filter
        matching = await storage.list_dataframes(tags={"env": "test"})
        assert len(matching) == 1
        assert matching[0].df_id == df_id

        # List with non-matching tag
        non_matching = await storage.list_dataframes(tags={"env": "prod"})
        assert len(non_matching) == 0


if __name__ == "__main__":
    pytest.main([__file__])
