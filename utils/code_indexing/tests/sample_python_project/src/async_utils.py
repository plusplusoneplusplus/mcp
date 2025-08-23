"""
Async utilities and processing framework.

This module demonstrates:
- Async/await patterns
- Type hints with async functions
- Context managers
- Enum usage
- Dataclasses with async methods
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, AsyncIterator, Callable, Coroutine, List, Optional, Union
from contextlib import asynccontextmanager


class JobStatus(Enum):
    """Status enumeration for processing jobs."""

    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class Priority(Enum):
    """Priority levels for job processing."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ProcessingJob:
    """Represents an async processing job."""

    id: str
    task: Callable[..., Coroutine[Any, Any, Any]]
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    timeout: Optional[float] = None
    retry_count: int = 3

    # Status tracking
    status: JobStatus = field(default=JobStatus.PENDING, init=False)
    result: Any = field(default=None, init=False)
    error: Optional[Exception] = field(default=None, init=False)
    start_time: Optional[float] = field(default=None, init=False)
    end_time: Optional[float] = field(default=None, init=False)
    attempts: int = field(default=0, init=False)

    @property
    def duration(self) -> Optional[float]:
        """Get job execution duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def is_completed(self) -> bool:
        """Check if job is completed (successfully or with error)."""
        return self.status in (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        )

    @property
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == JobStatus.RUNNING

    async def execute(self) -> Any:
        """Execute the job task."""
        self.status = JobStatus.RUNNING
        self.start_time = time.time()
        self.attempts += 1

        try:
            if self.timeout:
                self.result = await asyncio.wait_for(
                    self.task(*self.args, **self.kwargs), timeout=self.timeout
                )
            else:
                self.result = await self.task(*self.args, **self.kwargs)

            self.status = JobStatus.COMPLETED
            return self.result

        except Exception as e:
            self.error = e
            self.status = JobStatus.FAILED
            raise
        finally:
            self.end_time = time.time()

    def cancel(self) -> None:
        """Cancel the job."""
        if not self.is_completed:
            self.status = JobStatus.CANCELLED
            self.end_time = time.time()


class AsyncProcessor:
    """Async job processor with queue management."""

    def __init__(self, max_workers: int = 5, queue_size: int = 100):
        self.max_workers = max_workers
        self.queue_size = queue_size
        self._job_queue: asyncio.Queue[ProcessingJob] = asyncio.Queue(
            maxsize=queue_size
        )
        self._active_jobs: dict[str, ProcessingJob] = {}
        self._completed_jobs: List[ProcessingJob] = []
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._stats = {
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "cancelled_jobs": 0,
        }

    @property
    def is_running(self) -> bool:
        """Check if processor is running."""
        return self._running

    @property
    def active_job_count(self) -> int:
        """Get number of active jobs."""
        return len(self._active_jobs)

    @property
    def queue_size_current(self) -> int:
        """Get current queue size."""
        return self._job_queue.qsize()

    @property
    def stats(self) -> dict:
        """Get processing statistics."""
        return self._stats.copy()

    async def start(self) -> None:
        """Start the processor workers."""
        if self._running:
            return

        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(f"worker-{i}"))
            for i in range(self.max_workers)
        ]

    async def stop(self, timeout: Optional[float] = None) -> None:
        """Stop the processor and wait for workers."""
        self._running = False

        # Cancel all workers
        for worker in self._workers:
            worker.cancel()

        # Wait for workers to finish
        if timeout:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._workers, return_exceptions=True),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                pass
        else:
            await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()

    async def submit_job(self, job: ProcessingJob) -> str:
        """Submit a job for processing."""
        if not self._running:
            raise RuntimeError("Processor is not running")

        await self._job_queue.put(job)
        self._stats["total_jobs"] += 1
        return job.id

    async def create_and_submit_job(
        self,
        job_id: str,
        task: Callable[..., Coroutine[Any, Any, Any]],
        *args,
        priority: Priority = Priority.NORMAL,
        timeout: Optional[float] = None,
        retry_count: int = 3,
        **kwargs,
    ) -> str:
        """Create and submit a job."""
        job = ProcessingJob(
            id=job_id,
            task=task,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            retry_count=retry_count,
        )
        return await self.submit_job(job)

    async def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get status of a specific job."""
        if job_id in self._active_jobs:
            return self._active_jobs[job_id].status

        for job in self._completed_jobs:
            if job.id == job_id:
                return job.status

        return None

    async def get_job_result(self, job_id: str) -> Any:
        """Get result of a completed job."""
        for job in self._completed_jobs:
            if job.id == job_id:
                if job.status == JobStatus.COMPLETED:
                    return job.result
                elif job.status == JobStatus.FAILED:
                    raise job.error
                else:
                    raise RuntimeError(f"Job {job_id} is not completed")

        if job_id in self._active_jobs:
            raise RuntimeError(f"Job {job_id} is still running")

        raise KeyError(f"Job {job_id} not found")

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a specific job."""
        if job_id in self._active_jobs:
            self._active_jobs[job_id].cancel()
            return True
        return False

    async def wait_for_job(self, job_id: str, timeout: Optional[float] = None) -> Any:
        """Wait for a job to complete and return its result."""
        start_time = time.time()

        while True:
            status = await self.get_job_status(job_id)

            if status is None:
                raise KeyError(f"Job {job_id} not found")

            if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                return await self.get_job_result(job_id)

            if timeout and (time.time() - start_time) > timeout:
                raise asyncio.TimeoutError(f"Timeout waiting for job {job_id}")

            await asyncio.sleep(0.1)

    async def _worker(self, worker_name: str) -> None:
        """Worker coroutine that processes jobs from the queue."""
        while self._running:
            try:
                # Get job with timeout to allow checking _running flag
                job = await asyncio.wait_for(self._job_queue.get(), timeout=1.0)

                self._active_jobs[job.id] = job

                try:
                    await self._process_job_with_retry(job)
                finally:
                    # Move job from active to completed
                    if job.id in self._active_jobs:
                        del self._active_jobs[job.id]
                    self._completed_jobs.append(job)

                    # Update stats
                    if job.status == JobStatus.COMPLETED:
                        self._stats["completed_jobs"] += 1
                    elif job.status == JobStatus.FAILED:
                        self._stats["failed_jobs"] += 1
                    elif job.status == JobStatus.CANCELLED:
                        self._stats["cancelled_jobs"] += 1

                    self._job_queue.task_done()

            except asyncio.TimeoutError:
                # Timeout waiting for job - continue loop to check _running
                continue
            except Exception as e:
                print(f"Worker {worker_name} error: {e}")

    async def _process_job_with_retry(self, job: ProcessingJob) -> None:
        """Process a job with retry logic."""
        last_error = None

        for attempt in range(job.retry_count):
            if job.status == JobStatus.CANCELLED:
                break

            try:
                await job.execute()
                return  # Success, exit retry loop
            except Exception as e:
                last_error = e
                if attempt < job.retry_count - 1:
                    # Reset for retry
                    job.status = JobStatus.PENDING
                    job.error = None
                    await asyncio.sleep(2**attempt)  # Exponential backoff

        # All retries failed
        if job.status != JobStatus.CANCELLED:
            job.status = JobStatus.FAILED
            job.error = last_error

    async def process_batch(
        self, tasks: List[Callable[..., Coroutine[Any, Any, Any]]], batch_size: int = 10
    ) -> List[Any]:
        """Process a batch of tasks concurrently."""
        if not self._running:
            raise RuntimeError("Processor is not running")

        results = []

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            batch_jobs = []

            # Submit batch jobs
            for j, task in enumerate(batch):
                job_id = f"batch-{i}-{j}"
                await self.create_and_submit_job(job_id, task)
                batch_jobs.append(job_id)

            # Wait for batch completion
            batch_results = []
            for job_id in batch_jobs:
                try:
                    result = await self.wait_for_job(job_id)
                    batch_results.append(result)
                except Exception as e:
                    batch_results.append(e)

            results.extend(batch_results)

        return results

    @asynccontextmanager
    async def managed_processing(self):
        """Context manager for automatic start/stop."""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()

    async def get_active_jobs(self) -> List[ProcessingJob]:
        """Get list of currently active jobs."""
        return list(self._active_jobs.values())

    async def get_completed_jobs(self) -> List[ProcessingJob]:
        """Get list of completed jobs."""
        return self._completed_jobs.copy()

    async def clear_completed_jobs(self) -> None:
        """Clear the completed jobs list."""
        self._completed_jobs.clear()


# Async utility functions
async def async_timer(duration: float) -> None:
    """Async timer that waits for specified duration."""
    await asyncio.sleep(duration)


async def async_retry(
    coro: Coroutine[Any, Any, Any],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> Any:
    """Retry an async operation with exponential backoff."""
    last_error = None
    current_delay = delay

    for attempt in range(max_attempts):
        try:
            return await coro
        except Exception as e:
            last_error = e
            if attempt < max_attempts - 1:
                await asyncio.sleep(current_delay)
                current_delay *= backoff_factor

    raise last_error


async def async_map(
    func: Callable[[Any], Coroutine[Any, Any, Any]],
    items: List[Any],
    concurrency: int = 10,
) -> List[Any]:
    """Apply async function to items with limited concurrency."""
    semaphore = asyncio.Semaphore(concurrency)

    async def process_item(item):
        async with semaphore:
            return await func(item)

    tasks = [process_item(item) for item in items]
    return await asyncio.gather(*tasks)


async def async_filter(
    predicate: Callable[[Any], Coroutine[Any, Any, bool]], items: List[Any]
) -> List[Any]:
    """Filter items using async predicate."""
    results = await async_map(predicate, items)
    return [item for item, keep in zip(items, results) if keep]


async def async_reduce(
    func: Callable[[Any, Any], Coroutine[Any, Any, Any]],
    items: List[Any],
    initial: Any = None,
) -> Any:
    """Async reduce operation."""
    if not items:
        return initial

    if initial is None:
        result = items[0]
        items = items[1:]
    else:
        result = initial

    for item in items:
        result = await func(result, item)

    return result


async def async_generator_example() -> AsyncIterator[int]:
    """Example async generator."""
    for i in range(10):
        await asyncio.sleep(0.1)
        yield i


async def process_async_stream(stream: AsyncIterator[Any]) -> List[Any]:
    """Process items from an async stream."""
    results = []
    async for item in stream:
        # Process each item
        processed = item * 2 if isinstance(item, (int, float)) else str(item)
        results.append(processed)
    return results


# Example async tasks for testing
async def simple_task(duration: float = 1.0, value: Any = "result") -> Any:
    """Simple async task that waits and returns a value."""
    await asyncio.sleep(duration)
    return value


async def failing_task(message: str = "Task failed") -> None:
    """Task that always fails."""
    await asyncio.sleep(0.1)
    raise RuntimeError(message)


async def cpu_intensive_task(n: int = 1000000) -> int:
    """Simulate CPU-intensive async task."""
    result = 0
    for i in range(n):
        result += i
        if i % 10000 == 0:
            await asyncio.sleep(0)  # Yield control
    return result
