"""
Job manager for coordinating async job execution.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional
from datetime import datetime

from .job import AsyncJob
from .models import JobState, JobResult
from .store import JobStore, InMemoryJobStore

logger = logging.getLogger(__name__)


class JobManager:
    """
    Central coordinator for all async jobs.

    Manages job submission, execution, status tracking, and result storage.
    """

    def __init__(
        self,
        max_concurrent_jobs: int = 10,
        job_store: Optional[JobStore] = None,
        job_timeout: int = 300
    ):
        """
        Initialize the job manager.

        Args:
            max_concurrent_jobs: Maximum number of jobs to run concurrently
            job_store: Storage backend for job results
            job_timeout: Default timeout for jobs in seconds
        """
        self._jobs: Dict[str, AsyncJob] = {}
        self._job_tasks: Dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._job_store = job_store or InMemoryJobStore()
        self._job_timeout = job_timeout
        self._logger = logger.getChild("manager")
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the job manager and any background tasks."""
        if isinstance(self._job_store, InMemoryJobStore):
            await self._job_store.start_cleanup()
        self._logger.info("Job manager started")

    async def shutdown(self) -> None:
        """Shutdown the job manager and cleanup resources."""
        self._logger.info("Shutting down job manager...")
        self._shutdown_event.set()

        # Cancel all running jobs
        for token, task in self._job_tasks.items():
            if not task.done():
                self._logger.info(f"Cancelling job {token}")
                task.cancel()

        # Wait for all tasks to complete
        running_tasks = [task for task in self._job_tasks.values() if not task.done()]
        if running_tasks:
            await asyncio.gather(*running_tasks, return_exceptions=True)

        # Cleanup job store
        if isinstance(self._job_store, InMemoryJobStore):
            await self._job_store.stop_cleanup()

        self._logger.info("Job manager shutdown complete")

    async def submit(self, job: AsyncJob) -> str:
        """
        Submit a job for execution.

        Args:
            job: The async job to execute

        Returns:
            Token that can be used to track the job
        """
        token = str(uuid.uuid4())
        self._jobs[token] = job

        # Start job execution in background
        task = asyncio.create_task(self._execute_job(token, job))
        self._job_tasks[token] = task

        self._logger.info(f"Submitted job {job.id} with token {token}")
        return token

    async def get_status(self, token: str) -> Dict[str, any]:
        """
        Get the status of a job.

        Args:
            token: Job token

        Returns:
            Dictionary containing job status information

        Raises:
            ValueError: If the job token is not found
        """
        if token not in self._jobs:
            raise ValueError(f"Job {token} not found")

        job = self._jobs[token]
        progress = job.get_progress()

        return {
            "token": token,
            "job_id": job.id,
            "state": job.state.value,
            "progress": {
                "current": progress.current,
                "total": progress.total,
                "percentage": progress.percentage,
                "message": progress.message
            }
        }

    async def get_result(self, token: str) -> JobResult:
        """
        Get the result of a completed job.

        Args:
            token: Job token

        Returns:
            JobResult containing the job outcome

        Raises:
            ValueError: If the result is not available
        """
        if not await self._job_store.exists(token):
            # Check if job is still running
            if token in self._jobs and self._jobs[token].state in [JobState.QUEUED, JobState.RUNNING]:
                raise ValueError(f"Job {token} is still running")
            raise ValueError(f"Result for job {token} not available")

        return await self._job_store.retrieve(token)

    async def cancel_job(self, token: str) -> None:
        """
        Cancel a running job.

        Args:
            token: Job token
        """
        if token in self._jobs:
            await self._jobs[token].cancel()
            self._logger.info(f"Cancelled job {token}")
        else:
            raise ValueError(f"Job {token} not found")

    async def list_jobs(self) -> List[Dict[str, any]]:
        """
        List all jobs with their current status.

        Returns:
            List of job status dictionaries
        """
        jobs = []
        for token, job in self._jobs.items():
            jobs.append({
                "token": token,
                "job_id": job.id,
                "state": job.state.value,
                "progress": job.get_progress().percentage
            })
        return jobs

    async def cleanup_job(self, token: str) -> None:
        """
        Clean up a completed job and its result.

        Args:
            token: Job token
        """
        # Remove from active jobs
        if token in self._jobs:
            del self._jobs[token]

        # Cancel and cleanup task
        if token in self._job_tasks:
            task = self._job_tasks[token]
            if not task.done():
                task.cancel()
            del self._job_tasks[token]

        # Clean up stored result
        await self._job_store.cleanup(token)

        self._logger.debug(f"Cleaned up job {token}")

    async def _execute_job(self, token: str, job: AsyncJob) -> None:
        """
        Execute a job with concurrency control and error handling.

        Args:
            token: Job token
            job: The job to execute
        """
        async with self._semaphore:
            try:
                job.state = JobState.RUNNING
                self._logger.info(f"Starting execution of job {job.id}")

                # Execute job with timeout
                result = await asyncio.wait_for(
                    job.execute(),
                    timeout=self._job_timeout
                )

                job.state = JobState.COMPLETED
                await self._job_store.store(token, result)
                self._logger.info(f"Job {job.id} completed successfully")

            except asyncio.CancelledError:
                job.state = JobState.CANCELLED
                result = JobResult(
                    success=False,
                    error="Job was cancelled"
                )
                await self._job_store.store(token, result)
                self._logger.info(f"Job {job.id} was cancelled")

            except asyncio.TimeoutError:
                job.state = JobState.FAILED
                result = JobResult(
                    success=False,
                    error=f"Job timed out after {self._job_timeout} seconds"
                )
                await self._job_store.store(token, result)
                self._logger.error(f"Job {job.id} timed out")

            except Exception as e:
                job.state = JobState.FAILED
                result = JobResult(
                    success=False,
                    error=str(e),
                    metadata={"exception_type": type(e).__name__}
                )
                await self._job_store.store(token, result)
                self._logger.error(f"Job {job.id} failed with error: {e}")

    async def get_stats(self) -> Dict[str, any]:
        """
        Get statistics about the job manager.

        Returns:
            Dictionary containing various statistics
        """
        stats = {
            "total_jobs": len(self._jobs),
            "running_jobs": len([j for j in self._jobs.values() if j.state == JobState.RUNNING]),
            "queued_jobs": len([j for j in self._jobs.values() if j.state == JobState.QUEUED]),
            "completed_jobs": len([j for j in self._jobs.values() if j.state == JobState.COMPLETED]),
            "failed_jobs": len([j for j in self._jobs.values() if j.state == JobState.FAILED]),
            "cancelled_jobs": len([j for j in self._jobs.values() if j.state == JobState.CANCELLED]),
        }

        # Add store stats if available
        if hasattr(self._job_store, 'get_stats'):
            store_stats = await self._job_store.get_stats()
            stats.update(store_stats)

        return stats
