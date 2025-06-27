"""
Storage backends for job results.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional
from datetime import datetime, timedelta

from .models import JobResult

logger = logging.getLogger(__name__)


class JobStore(ABC):
    """Abstract base class for job result storage."""

    @abstractmethod
    async def store(self, token: str, result: JobResult) -> None:
        """Store a job result."""
        pass

    @abstractmethod
    async def retrieve(self, token: str) -> JobResult:
        """Retrieve a job result."""
        pass

    @abstractmethod
    async def cleanup(self, token: str) -> None:
        """Clean up a job result."""
        pass

    @abstractmethod
    async def exists(self, token: str) -> bool:
        """Check if a result exists for the given token."""
        pass


class InMemoryJobStore(JobStore):
    """In-memory storage for job results."""

    def __init__(self, cleanup_interval: int = 300, result_ttl: int = 3600):
        """
        Initialize the in-memory job store.

        Args:
            cleanup_interval: How often to run cleanup (seconds)
            result_ttl: How long to keep results (seconds)
        """
        self._store: Dict[str, JobResult] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._cleanup_interval = cleanup_interval
        self._result_ttl = result_ttl
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._logger = logger.getChild("memory_store")

    async def start_cleanup(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._logger.info("Started cleanup task")

    async def stop_cleanup(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._logger.info("Stopped cleanup task")

    async def store(self, token: str, result: JobResult) -> None:
        """Store a job result."""
        async with self._lock:
            self._store[token] = result
            self._timestamps[token] = datetime.now()
            self._logger.debug(f"Stored result for token {token}")

    async def retrieve(self, token: str) -> JobResult:
        """Retrieve a job result."""
        async with self._lock:
            if token not in self._store:
                raise ValueError(f"Result for token {token} not found")

            # Update timestamp on access
            self._timestamps[token] = datetime.now()
            return self._store[token]

    async def cleanup(self, token: str) -> None:
        """Clean up a specific job result."""
        async with self._lock:
            self._store.pop(token, None)
            self._timestamps.pop(token, None)
            self._logger.debug(f"Cleaned up result for token {token}")

    async def exists(self, token: str) -> bool:
        """Check if a result exists for the given token."""
        async with self._lock:
            return token in self._store

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop to remove expired results."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error during cleanup: {e}")

    async def _cleanup_expired(self) -> None:
        """Remove expired results."""
        cutoff_time = datetime.now() - timedelta(seconds=self._result_ttl)
        expired_tokens = []

        async with self._lock:
            for token, timestamp in self._timestamps.items():
                if timestamp < cutoff_time:
                    expired_tokens.append(token)

            for token in expired_tokens:
                self._store.pop(token, None)
                self._timestamps.pop(token, None)

        if expired_tokens:
            self._logger.info(f"Cleaned up {len(expired_tokens)} expired results")

    async def get_stats(self) -> Dict[str, int]:
        """Get storage statistics."""
        async with self._lock:
            return {
                "total_results": len(self._store),
                "oldest_result_age": int(
                    (datetime.now() - min(self._timestamps.values())).total_seconds()
                ) if self._timestamps else 0
            }
