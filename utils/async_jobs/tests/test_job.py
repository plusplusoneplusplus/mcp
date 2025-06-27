"""Tests for AsyncJob base class."""

import asyncio
import pytest
from unittest.mock import Mock
from utils.async_jobs.job import AsyncJob
from utils.async_jobs.models import JobState, JobResult, JobProgress


class TestJob(AsyncJob):
    """Test implementation of AsyncJob."""

    def __init__(self, job_id: str, sleep_time: float = 0.1, should_fail: bool = False):
        super().__init__(job_id)
        self.sleep_time = sleep_time
        self.should_fail = should_fail
        self.execution_count = 0

    async def execute(self) -> JobResult:
        """Test execution that can be configured to fail or succeed."""
        self.execution_count += 1

        # Check for cancellation before starting
        self._check_cancelled()

        # Simulate work with cancellation checks
        for _ in range(int(self.sleep_time * 10)):
            await asyncio.sleep(0.01)
            self._check_cancelled()

        if self.should_fail:
            raise ValueError("Test job failed")

        return JobResult(success=True, data=f"Job {self.id} completed")

    def get_progress(self) -> JobProgress:
        """Return test progress."""
        return JobProgress(
            current=self.execution_count,
            total=1,
            message=f"Executing job {self.id}"
        )


class TestAsyncJob:
    """Test cases for AsyncJob base class."""

    def test_job_initialization(self):
        """Test job initialization."""
        job = TestJob("test_job")
        assert job.id == "test_job"
        assert job.state == JobState.QUEUED
        assert not job.is_cancelled

    @pytest.mark.asyncio
    async def test_job_execution_success(self):
        """Test successful job execution."""
        job = TestJob("test_job", sleep_time=0.01)
        result = await job.execute()

        assert result.success is True
        assert result.data == "Job test_job completed"
        assert job.execution_count == 1

    @pytest.mark.asyncio
    async def test_job_execution_failure(self):
        """Test job execution with failure."""
        job = TestJob("test_job", should_fail=True)

        with pytest.raises(ValueError, match="Test job failed"):
            await job.execute()

    @pytest.mark.asyncio
    async def test_job_cancellation(self):
        """Test job cancellation."""
        job = TestJob("test_job", sleep_time=1.0)  # Long running job

        # Start cancellation after a short delay
        async def cancel_after_delay():
            await asyncio.sleep(0.05)
            await job.cancel()

        cancel_task = asyncio.create_task(cancel_after_delay())

        # Job should raise CancelledError
        with pytest.raises(asyncio.CancelledError):
            await job.execute()

        await cancel_task
        assert job.is_cancelled
        assert job.state == JobState.CANCELLED

    @pytest.mark.asyncio
    async def test_wait_cancellable_success(self):
        """Test _wait_cancellable with successful completion."""
        job = TestJob("test_job")

        async def quick_task():
            await asyncio.sleep(0.01)
            return "completed"

        result = await job._wait_cancellable(quick_task())
        assert result == "completed"

    @pytest.mark.asyncio
    async def test_wait_cancellable_timeout(self):
        """Test _wait_cancellable with timeout."""
        job = TestJob("test_job")

        async def slow_task():
            await asyncio.sleep(1.0)
            return "completed"

        with pytest.raises(asyncio.TimeoutError):
            await job._wait_cancellable(slow_task(), timeout=0.05)

    @pytest.mark.asyncio
    async def test_wait_cancellable_cancellation(self):
        """Test _wait_cancellable with job cancellation."""
        job = TestJob("test_job")

        async def slow_task():
            await asyncio.sleep(1.0)
            return "completed"

        async def cancel_after_delay():
            await asyncio.sleep(0.05)
            await job.cancel()

        cancel_task = asyncio.create_task(cancel_after_delay())

        with pytest.raises(asyncio.CancelledError):
            await job._wait_cancellable(slow_task())

        await cancel_task

    def test_get_progress(self):
        """Test progress reporting."""
        job = TestJob("test_job")
        progress = job.get_progress()

        assert progress.current == 0  # No execution yet
        assert progress.total == 1
        assert progress.message == "Executing job test_job"
        assert progress.percentage == 0.0

    def test_check_cancelled(self):
        """Test cancellation checking."""
        job = TestJob("test_job")

        # Should not raise when not cancelled
        job._check_cancelled()

        # Should raise when cancelled
        job._cancel_event.set()
        with pytest.raises(asyncio.CancelledError):
            job._check_cancelled()
