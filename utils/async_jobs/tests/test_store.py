"""Tests for job storage backends."""

import asyncio
import pytest
from datetime import datetime, timedelta
from utils.async_jobs.store import InMemoryJobStore
from utils.async_jobs.models import JobResult


class TestInMemoryJobStore:
    """Test cases for InMemoryJobStore."""

    @pytest.fixture
    async def store(self):
        """Create a test store instance."""
        store = InMemoryJobStore(cleanup_interval=0.1, result_ttl=0.2)
        await store.start_cleanup()
        yield store
        await store.stop_cleanup()

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, store):
        """Test basic store and retrieve operations."""
        result = JobResult(success=True, data="test_data")
        token = "test_token"

        # Store result
        await store.store(token, result)
        assert await store.exists(token)

        # Retrieve result
        retrieved = await store.retrieve(token)
        assert retrieved.success == result.success
        assert retrieved.data == result.data

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent(self, store):
        """Test retrieving non-existent result."""
        with pytest.raises(ValueError, match="Result for token nonexistent not found"):
            await store.retrieve("nonexistent")

    @pytest.mark.asyncio
    async def test_exists(self, store):
        """Test exists check."""
        token = "test_token"
        result = JobResult(success=True)

        assert not await store.exists(token)

        await store.store(token, result)
        assert await store.exists(token)

    @pytest.mark.asyncio
    async def test_cleanup_specific(self, store):
        """Test cleanup of specific token."""
        result = JobResult(success=True, data="test_data")
        token = "test_token"

        await store.store(token, result)
        assert await store.exists(token)

        await store.cleanup(token)
        assert not await store.exists(token)

    @pytest.mark.asyncio
    async def test_automatic_cleanup(self):
        """Test automatic cleanup of expired results."""
        store = InMemoryJobStore(cleanup_interval=0.05, result_ttl=0.1)
        await store.start_cleanup()

        try:
            result = JobResult(success=True, data="test_data")
            token = "test_token"

            # Store result
            await store.store(token, result)
            assert await store.exists(token)

            # Wait for expiration and cleanup
            await asyncio.sleep(0.2)

            # Result should be cleaned up
            assert not await store.exists(token)

        finally:
            await store.stop_cleanup()

    @pytest.mark.asyncio
    async def test_get_stats(self, store):
        """Test statistics collection."""
        # Initially empty
        stats = await store.get_stats()
        assert stats["total_results"] == 0
        assert stats["oldest_result_age"] == 0

        # Add some results
        for i in range(3):
            result = JobResult(success=True, data=f"data_{i}")
            await store.store(f"token_{i}", result)

        stats = await store.get_stats()
        assert stats["total_results"] == 3
        assert stats["oldest_result_age"] >= 0

    @pytest.mark.asyncio
    async def test_timestamp_update_on_access(self, store):
        """Test that timestamp is updated when result is accessed."""
        result = JobResult(success=True, data="test_data")
        token = "test_token"

        await store.store(token, result)

        # Wait a bit then access
        await asyncio.sleep(0.05)
        await store.retrieve(token)

        # The timestamp should be updated, preventing immediate cleanup
        stats = await store.get_stats()
        assert stats["oldest_result_age"] < 0.05  # Should be very recent

    @pytest.mark.asyncio
    async def test_concurrent_access(self, store):
        """Test concurrent access to the store."""
        result = JobResult(success=True, data="test_data")

        async def store_worker(worker_id):
            token = f"token_{worker_id}"
            await store.store(token, result)
            retrieved = await store.retrieve(token)
            assert retrieved.data == "test_data"
            await store.cleanup(token)

        # Run multiple workers concurrently
        workers = [store_worker(i) for i in range(10)]
        await asyncio.gather(*workers)

        # All should be cleaned up
        stats = await store.get_stats()
        assert stats["total_results"] == 0
