"""Tests for JobManager."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from utils.async_jobs.manager import JobManager
from utils.async_jobs.job import AsyncJob
from utils.async_jobs.models import JobState, JobResult, JobProgress
from utils.async_jobs.store import InMemoryJobStore


class TestJob(AsyncJob):
    """Test implementation of AsyncJob."""

    def __init__(self, job_id: str, sleep_time: float = 0.1, should_fail: bool = False):
        super().__init__(job_id)
        self.sleep_time = sleep_time
        self.should_fail = should_fail
        self.execution_started = False
        self.execution_completed = False

    async def execute(self) -> JobResult:
        """Test execution."""
        self.execution_started = True

        # Check for cancellation
        self._check_cancelled()

        # Simulate work
        await asyncio.sleep(self.sleep_time)

        if self.should_fail:
            raise ValueError("Test job failed")

        self.execution_completed = True
        return JobResult(success=True, data=f"Job {self.id} completed")

    def get_progress(self) -> JobProgress:
        """Return test progress."""
        current = 1 if self.execution_completed else 0
        return JobProgress(current=current, total=1, message=f"Job {self.id} progress")


class TestJobManager:
    """Test cases for JobManager."""

    @pytest.fixture
    async def manager(self):
        """Create a test job manager."""
        manager = JobManager(max_concurrent_jobs=2, job_timeout=1.0)
        await manager.start()
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_job_submission(self, manager):
        """Test job submission and token generation."""
        job = TestJob("test_job", sleep_time=0.01)
        token = await manager.submit(job)

        assert isinstance(token, str)
        assert len(token) > 0
        assert token in manager._jobs

    @pytest.mark.asyncio
    async def test_job_execution_success(self, manager):
        """Test successful job execution."""
        job = TestJob("test_job", sleep_time=0.05)
        token = await manager.submit(job)

        # Wait for completion
        await asyncio.sleep(0.1)

        # Check status
        status = await manager.get_status(token)
        assert status["state"] == JobState.COMPLETED.value

        # Get result
        result = await manager.get_result(token)
        assert result.success is True
        assert result.data == "Job test_job completed"

    @pytest.mark.asyncio
    async def test_job_execution_failure(self, manager):
        """Test job execution with failure."""
        job = TestJob("test_job", sleep_time=0.05, should_fail=True)
        token = await manager.submit(job)

        # Wait for completion
        await asyncio.sleep(0.1)

        # Check status
        status = await manager.get_status(token)
        assert status["state"] == JobState.FAILED.value

        # Get result
        result = await manager.get_result(token)
        assert result.success is False
        assert "Test job failed" in result.error

    @pytest.mark.asyncio
    async def test_job_cancellation(self, manager):
        """Test job cancellation."""
        job = TestJob("test_job", sleep_time=0.5)  # Long running
        token = await manager.submit(job)

        # Wait a bit for job to start
        await asyncio.sleep(0.05)

        # Cancel the job
        await manager.cancel_job(token)

        # Wait for cancellation to take effect
        await asyncio.sleep(0.1)

        # Check status
        status = await manager.get_status(token)
        assert status["state"] == JobState.CANCELLED.value

    @pytest.mark.asyncio
    async def test_job_timeout(self, manager):
        """Test job timeout handling."""
        # Create manager with very short timeout
        short_timeout_manager = JobManager(job_timeout=0.05)
        await short_timeout_manager.start()

        try:
            job = TestJob("test_job", sleep_time=0.2)  # Longer than timeout
            token = await short_timeout_manager.submit(job)

            # Wait for timeout
            await asyncio.sleep(0.1)

            # Check status
            status = await short_timeout_manager.get_status(token)
            assert status["state"] == JobState.FAILED.value

            # Get result
            result = await short_timeout_manager.get_result(token)
            assert result.success is False
            assert "timed out" in result.error

        finally:
            await short_timeout_manager.shutdown()

    @pytest.mark.asyncio
    async def test_get_status_nonexistent(self, manager):
        """Test getting status of non-existent job."""
        with pytest.raises(ValueError, match="Job nonexistent not found"):
            await manager.get_status("nonexistent")

    @pytest.mark.asyncio
    async def test_get_result_not_available(self, manager):
        """Test getting result when not available."""
        with pytest.raises(ValueError, match="Result for job nonexistent not available"):
            await manager.get_result("nonexistent")

    @pytest.mark.asyncio
    async def test_get_result_job_still_running(self, manager):
        """Test getting result of still running job."""
        job = TestJob("test_job", sleep_time=0.5)
        token = await manager.submit(job)

        # Try to get result immediately
        with pytest.raises(ValueError, match="is still running"):
            await manager.get_result(token)

    @pytest.mark.asyncio
    async def test_list_jobs(self, manager):
        """Test listing all jobs."""
        # Initially empty
        jobs = await manager.list_jobs()
        assert len(jobs) == 0

        # Add some jobs
        job1 = TestJob("job1", sleep_time=0.1)
        job2 = TestJob("job2", sleep_time=0.1)

        token1 = await manager.submit(job1)
        token2 = await manager.submit(job2)

        # List jobs
        jobs = await manager.list_jobs()
        assert len(jobs) == 2

        tokens = [job["token"] for job in jobs]
        assert token1 in tokens
        assert token2 in tokens

    @pytest.mark.asyncio
    async def test_concurrency_limit(self, manager):
        """Test that concurrency limit is respected."""
        # Submit more jobs than the limit (2)
        jobs = []
        tokens = []

        for i in range(4):
            job = TestJob(f"job{i}", sleep_time=0.2)
            jobs.append(job)
            token = await manager.submit(job)
            tokens.append(token)

        # Wait a bit for jobs to start
        await asyncio.sleep(0.05)

        # Check that only 2 jobs are running
        running_count = 0
        for job in jobs:
            if job.execution_started:
                running_count += 1

        assert running_count <= 2

        # Wait for all jobs to complete
        await asyncio.sleep(0.5)

        # All jobs should eventually complete
        for token in tokens:
            status = await manager.get_status(token)
            assert status["state"] == JobState.COMPLETED.value

    @pytest.mark.asyncio
    async def test_cleanup_job(self, manager):
        """Test job cleanup."""
        job = TestJob("test_job", sleep_time=0.05)
        token = await manager.submit(job)

        # Wait for completion
        await asyncio.sleep(0.1)

        # Cleanup job
        await manager.cleanup_job(token)

        # Job should be removed from active jobs
        assert token not in manager._jobs
        assert token not in manager._job_tasks

    @pytest.mark.asyncio
    async def test_get_stats(self, manager):
        """Test statistics collection."""
        # Initially empty
        stats = await manager.get_stats()
        assert stats["total_jobs"] == 0
        assert stats["running_jobs"] == 0

        # Add jobs in different states
        success_job = TestJob("success_job", sleep_time=0.05)
        fail_job = TestJob("fail_job", sleep_time=0.05, should_fail=True)

        await manager.submit(success_job)
        await manager.submit(fail_job)

        # Wait for completion
        await asyncio.sleep(0.1)

        stats = await manager.get_stats()
        assert stats["total_jobs"] == 2
        assert stats["completed_jobs"] == 1
        assert stats["failed_jobs"] == 1

    @pytest.mark.asyncio
    async def test_manager_shutdown(self):
        """Test manager shutdown and cleanup."""
        manager = JobManager()
        await manager.start()

        # Submit a long-running job
        job = TestJob("test_job", sleep_time=1.0)
        token = await manager.submit(job)

        # Wait for job to start
        await asyncio.sleep(0.05)

        # Shutdown should cancel running jobs
        await manager.shutdown()

        # Job should be cancelled
        assert job.is_cancelled
