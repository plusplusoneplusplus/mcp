"""Integration tests for the async jobs framework."""

import asyncio
import pytest
from utils.async_jobs.manager import JobManager
from utils.async_jobs.job import AsyncJob
from utils.async_jobs.models import JobResult, JobProgress
from utils.async_jobs.store import InMemoryJobStore


class CommandJob(AsyncJob):
    """Example job that simulates command execution."""

    def __init__(self, command: str):
        super().__init__(f"cmd_{command}")
        self.command = command
        self.progress_current = 0
        self.progress_total = 3

    async def execute(self) -> JobResult:
        """Simulate command execution with progress tracking."""
        try:
            self.progress_current = 0

            # Step 1: Parse command
            self._check_cancelled()
            await asyncio.sleep(0.02)
            self.progress_current = 1

            # Step 2: Execute command
            self._check_cancelled()
            await asyncio.sleep(0.02)
            self.progress_current = 2

            # Step 3: Process output
            self._check_cancelled()
            await asyncio.sleep(0.02)
            self.progress_current = 3

            # Simulate different command outcomes
            if self.command == "fail":
                raise RuntimeError("Command failed")
            elif self.command == "slow":
                await asyncio.sleep(0.5)  # This might timeout

            return JobResult(
                success=True,
                data=f"Command '{self.command}' executed successfully",
                metadata={"command": self.command, "exit_code": 0}
            )

        except Exception as e:
            if not isinstance(e, asyncio.CancelledError):
                return JobResult(
                    success=False,
                    error=str(e),
                    metadata={"command": self.command, "exit_code": 1}
                )
            raise

    def get_progress(self) -> JobProgress:
        """Return current progress."""
        messages = {
            0: "Starting command execution",
            1: "Parsing command",
            2: "Executing command",
            3: "Processing output"
        }
        return JobProgress(
            current=self.progress_current,
            total=self.progress_total,
            message=messages.get(self.progress_current, "Unknown")
        )


class DataProcessingJob(AsyncJob):
    """Example job that processes data in batches."""

    def __init__(self, data_size: int):
        super().__init__(f"data_proc_{data_size}")
        self.data_size = data_size
        self.processed = 0

    async def execute(self) -> JobResult:
        """Process data in batches."""
        batch_size = max(1, self.data_size // 10)

        while self.processed < self.data_size:
            self._check_cancelled()

            # Process a batch
            batch_end = min(self.processed + batch_size, self.data_size)
            await asyncio.sleep(0.01)  # Simulate processing time
            self.processed = batch_end

        return JobResult(
            success=True,
            data=f"Processed {self.data_size} items",
            metadata={
                "items_processed": self.data_size,
                "batch_size": batch_size
            }
        )

    def get_progress(self) -> JobProgress:
        """Return processing progress."""
        return JobProgress(
            current=self.processed,
            total=self.data_size,
            message=f"Processed {self.processed}/{self.data_size} items"
        )


class TestAsyncJobsIntegration:
    """Integration tests for the complete async jobs framework."""

    @pytest.fixture
    async def manager(self):
        """Create a job manager for testing."""
        store = InMemoryJobStore(cleanup_interval=0.1, result_ttl=1.0)
        manager = JobManager(
            max_concurrent_jobs=3,
            job_store=store,
            job_timeout=0.5
        )
        await manager.start()
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_command_job_success(self, manager):
        """Test successful command job execution."""
        job = CommandJob("echo hello")
        token = await manager.submit(job)

        # Monitor progress
        for _ in range(10):  # Max 10 checks
            status = await manager.get_status(token)
            if status["state"] == "completed":
                break
            await asyncio.sleep(0.01)

        # Verify final result
        status = await manager.get_status(token)
        assert status["state"] == "completed"
        assert status["progress"]["percentage"] == 100.0

        result = await manager.get_result(token)
        assert result.success is True
        assert "executed successfully" in result.data
        assert result.metadata["command"] == "echo hello"

    @pytest.mark.asyncio
    async def test_command_job_failure(self, manager):
        """Test command job with failure."""
        job = CommandJob("fail")
        token = await manager.submit(job)

        # Wait for completion
        await asyncio.sleep(0.1)

        status = await manager.get_status(token)
        assert status["state"] == "failed"

        result = await manager.get_result(token)
        assert result.success is False
        assert "Command failed" in result.error

    @pytest.mark.asyncio
    async def test_data_processing_job(self, manager):
        """Test data processing job with progress tracking."""
        job = DataProcessingJob(data_size=50)
        token = await manager.submit(job)

        # Monitor progress
        progress_values = []
        for _ in range(20):  # Max 20 checks
            status = await manager.get_status(token)
            progress_values.append(status["progress"]["percentage"])

            if status["state"] == "completed":
                break
            await asyncio.sleep(0.01)

        # Verify progress increased over time
        assert len(progress_values) > 1
        assert progress_values[0] < progress_values[-1]
        assert progress_values[-1] == 100.0

        result = await manager.get_result(token)
        assert result.success is True
        assert result.metadata["items_processed"] == 50

    @pytest.mark.asyncio
    async def test_job_cancellation_during_execution(self, manager):
        """Test cancelling a job while it's executing."""
        job = DataProcessingJob(data_size=1000)  # Large job
        token = await manager.submit(job)

        # Wait for job to start
        await asyncio.sleep(0.02)

        # Cancel the job
        await manager.cancel_job(token)

        # Wait for cancellation to take effect
        await asyncio.sleep(0.05)

        status = await manager.get_status(token)
        assert status["state"] == "cancelled"

    @pytest.mark.asyncio
    async def test_multiple_concurrent_jobs(self, manager):
        """Test multiple jobs running concurrently."""
        jobs = []
        tokens = []

        # Submit multiple jobs
        for i in range(5):
            job = DataProcessingJob(data_size=20)
            token = await manager.submit(job)
            jobs.append(job)
            tokens.append(token)

        # Wait for all to complete
        await asyncio.sleep(0.2)

        # Check all completed successfully
        for token in tokens:
            status = await manager.get_status(token)
            assert status["state"] == "completed"

            result = await manager.get_result(token)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_job_timeout_handling(self, manager):
        """Test job timeout behavior."""
        job = CommandJob("slow")  # Will take longer than timeout
        token = await manager.submit(job)

        # Wait for timeout
        await asyncio.sleep(0.6)

        status = await manager.get_status(token)
        assert status["state"] == "failed"

        result = await manager.get_result(token)
        assert result.success is False
        assert "timed out" in result.error

    @pytest.mark.asyncio
    async def test_job_lifecycle_management(self, manager):
        """Test complete job lifecycle from submission to cleanup."""
        job = CommandJob("test")
        token = await manager.submit(job)

        # Job should be queued initially
        status = await manager.get_status(token)
        assert status["state"] in ["queued", "running"]

        # Wait for completion
        await asyncio.sleep(0.1)

        # Should be completed
        status = await manager.get_status(token)
        assert status["state"] == "completed"

        # Result should be available
        result = await manager.get_result(token)
        assert result is not None

        # Cleanup job
        await manager.cleanup_job(token)

        # Job should be removed from active jobs
        assert token not in manager._jobs

    @pytest.mark.asyncio
    async def test_manager_statistics(self, manager):
        """Test manager statistics collection."""
        # Initial stats
        stats = await manager.get_stats()
        initial_total = stats["total_jobs"]

        # Submit jobs with different outcomes
        success_job = CommandJob("success")
        fail_job = CommandJob("fail")

        token1 = await manager.submit(success_job)
        token2 = await manager.submit(fail_job)

        # Wait for completion
        await asyncio.sleep(0.1)

        # Check updated stats
        stats = await manager.get_stats()
        assert stats["total_jobs"] == initial_total + 2
        assert stats["completed_jobs"] >= 1
        assert stats["failed_jobs"] >= 1

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, manager):
        """Test error handling and system recovery."""
        # Submit a mix of good and bad jobs
        jobs_data = [
            ("good1", False),
            ("fail1", True),
            ("good2", False),
            ("fail2", True),
        ]

        tokens = []
        for name, should_fail in jobs_data:
            command = "fail" if should_fail else name
            job = CommandJob(command)
            token = await manager.submit(job)
            tokens.append((token, should_fail))

        # Wait for all to complete
        await asyncio.sleep(0.2)

        # Verify results match expectations
        for token, should_fail in tokens:
            result = await manager.get_result(token)
            if should_fail:
                assert result.success is False
            else:
                assert result.success is True

        # Manager should still be functional
        test_job = CommandJob("final_test")
        final_token = await manager.submit(test_job)
        await asyncio.sleep(0.1)

        final_result = await manager.get_result(final_token)
        assert final_result.success is True
