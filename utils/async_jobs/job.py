"""
Abstract base class for async jobs.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from .models import JobState, JobResult, JobProgress

logger = logging.getLogger(__name__)


class AsyncJob(ABC):
    """
    Abstract base class for all async jobs.

    Provides cancellation support and state management for long-running operations.
    """

    def __init__(self, job_id: str):
        """
        Initialize the async job.

        Args:
            job_id: Unique identifier for the job
        """
        self.id = job_id
        self.state = JobState.QUEUED
        self._cancel_event = asyncio.Event()
        self._logger = logger.getChild(f"job.{job_id}")

    @abstractmethod
    async def execute(self) -> JobResult:
        """
        Execute the job and return the result.

        This method should be implemented by concrete job classes.
        It should check for cancellation periodically using self.is_cancelled.

        Returns:
            JobResult containing the outcome of the job execution
        """
        pass

    async def cancel(self) -> None:
        """
        Cancel the job.

        Sets the cancellation event and updates the job state.
        Subclasses can override this method to perform additional cleanup.
        """
        self._logger.info(f"Cancelling job {self.id}")
        self._cancel_event.set()
        self.state = JobState.CANCELLED

    def get_progress(self) -> JobProgress:
        """
        Get the current progress of the job.

        Default implementation returns no progress tracking.
        Subclasses should override this to provide meaningful progress information.

        Returns:
            JobProgress with current progress information
        """
        return JobProgress(current=0, total=1, message="No progress tracking available")

    @property
    def is_cancelled(self) -> bool:
        """Check if the job has been cancelled."""
        return self._cancel_event.is_set()

    def _check_cancelled(self) -> None:
        """
        Check if job is cancelled and raise exception if so.

        Raises:
            asyncio.CancelledError: If the job has been cancelled
        """
        if self.is_cancelled:
            raise asyncio.CancelledError(f"Job {self.id} was cancelled")

    async def _wait_cancellable(self, coro, timeout: Optional[float] = None):
        """
        Wait for a coroutine while checking for cancellation.

        Args:
            coro: Coroutine to wait for
            timeout: Optional timeout in seconds

        Returns:
            Result of the coroutine

        Raises:
            asyncio.CancelledError: If the job is cancelled
            asyncio.TimeoutError: If timeout is exceeded
        """
        cancel_task = asyncio.create_task(self._cancel_event.wait())
        main_task = asyncio.create_task(coro)

        try:
            if timeout:
                done, pending = await asyncio.wait(
                    [main_task, cancel_task],
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED
                )

                if not done:  # Timeout occurred
                    main_task.cancel()
                    cancel_task.cancel()
                    raise asyncio.TimeoutError(f"Job {self.id} timed out after {timeout}s")
            else:
                done, pending = await asyncio.wait(
                    [main_task, cancel_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

            # Cancel any pending tasks
            for task in pending:
                task.cancel()

            # Check which task completed first
            if cancel_task in done:
                main_task.cancel()
                raise asyncio.CancelledError(f"Job {self.id} was cancelled")

            return await main_task

        except Exception:
            # Ensure tasks are cancelled on any exception
            main_task.cancel()
            cancel_task.cancel()
            raise
