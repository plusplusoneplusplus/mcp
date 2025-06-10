"""
Temporary file manager for CommandExecutor with improved cleanup coordination,
orphan detection, and enhanced error recovery.

This module addresses the race conditions and cleanup issues identified in GitHub issue #142.
"""

import asyncio
import os
import tempfile
import time
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, UTC
import json
import psutil

# Import config manager - using relative import from project root
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config import env_manager
except ImportError:
    # Fallback for testing or standalone usage
    env_manager = None

# Create logger with the module name
logger = logging.getLogger(__name__)


def _log_with_context(log_level: int, msg: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Helper function for structured logging with context

    Args:
        log_level: The logging level to use
        msg: The message to log
        context: Optional dictionary of contextual information
    """
    if context is None:
        context = {}

    # Add timestamp in ISO format using timezone-aware UTC
    context["timestamp"] = datetime.now(UTC).isoformat()

    # Format the log message with context
    structured_msg = f"{msg} | Context: {json.dumps(context, default=str)}"
    logger.log(log_level, structured_msg)


class TempFileManager:
    """
    Enhanced temporary file manager with improved cleanup coordination,
    orphan detection, and error recovery mechanisms.

    Features:
    - Non-blocking cleanup coordination using queue-based approach
    - Retry mechanism for failed cleanup operations with exponential backoff
    - Orphaned file detection and cleanup
    - Enhanced error recovery with fallback temp directories
    - Monitoring and metrics for temp file operations
    """

    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize the TempFileManager.

        Args:
            temp_dir: Optional custom temp directory path
        """
        # Load configuration
        if env_manager:
            env_manager.load()

        # Temp file management settings with fallback defaults
        self.temp_cleanup_retry_attempts = (
            env_manager.get_setting("temp_cleanup_retry_attempts", 3)
            if env_manager else 3
        )
        self.temp_cleanup_retry_delay = (
            env_manager.get_setting("temp_cleanup_retry_delay", 1.0)
            if env_manager else 1.0
        )
        self.orphan_cleanup_interval = (
            env_manager.get_setting("orphan_cleanup_interval", 3600)
            if env_manager else 3600  # 1 hour
        )
        self.orphan_file_max_age = (
            env_manager.get_setting("orphan_file_max_age", 7200)
            if env_manager else 7200  # 2 hours
        )
        self.temp_dir_max_size_mb = (
            env_manager.get_setting("temp_dir_max_size_mb", 1024)
            if env_manager else 1024  # 1GB limit
        )
        self.temp_file_creation_retry_attempts = (
            env_manager.get_setting("temp_file_creation_retry_attempts", 3)
            if env_manager else 3
        )

        # Set up temp directory
        self.temp_dir = Path(temp_dir if temp_dir else tempfile.gettempdir())
        self.fallback_temp_dirs = [
            Path(tempfile.gettempdir()),
            Path.home() / ".tmp",
            Path("/tmp") if os.name != "nt" else Path(os.environ.get("TEMP", "C:\\temp"))
        ]

        # Ensure temp directory exists
        self._ensure_temp_dir_exists()

        # Cleanup coordination
        self.cleanup_queue: asyncio.Queue = asyncio.Queue()
        self.cleanup_worker_task: Optional[asyncio.Task] = None
        self.orphan_cleanup_task: Optional[asyncio.Task] = None

        # Track temp files: PID -> (stdout_path, stderr_path, creation_time)
        self.temp_files: Dict[int, Tuple[str, str, float]] = {}

        # Metrics
        self.metrics = {
            "files_created": 0,
            "files_cleaned": 0,
            "cleanup_failures": 0,
            "orphans_cleaned": 0,
            "creation_failures": 0,
            "retry_successes": 0,
        }

        _log_with_context(
            logging.INFO,
            "Initialized TempFileManager",
            {
                "temp_dir": str(self.temp_dir),
                "cleanup_retry_attempts": self.temp_cleanup_retry_attempts,
                "cleanup_retry_delay": self.temp_cleanup_retry_delay,
                "orphan_cleanup_interval": self.orphan_cleanup_interval,
                "orphan_file_max_age": self.orphan_file_max_age,
                "temp_dir_max_size_mb": self.temp_dir_max_size_mb,
            }
        )

        # Start background tasks
        self.start_background_tasks()

    def _ensure_temp_dir_exists(self) -> None:
        """Ensure the temp directory exists, with fallback options."""
        for temp_dir in [self.temp_dir] + self.fallback_temp_dirs:
            try:
                temp_dir.mkdir(parents=True, exist_ok=True)
                if temp_dir.is_dir() and os.access(temp_dir, os.W_OK):
                    self.temp_dir = temp_dir
                    return
            except Exception as e:
                _log_with_context(
                    logging.WARNING,
                    f"Failed to create/access temp directory: {temp_dir}",
                    {"error": str(e), "temp_dir": str(temp_dir)}
                )
                continue

        # If all fallbacks fail, use system default
        self.temp_dir = Path(tempfile.gettempdir())
        _log_with_context(
            logging.WARNING,
            "Using system default temp directory as fallback",
            {"temp_dir": str(self.temp_dir)}
        )

    async def create_temp_files_with_retry(self, prefix: str = "cmd_") -> Tuple[str, str, object, object]:
        """Create temporary files with retry logic and enhanced error recovery.

        Args:
            prefix: Prefix for the temporary files

        Returns:
            Tuple of (stdout_path, stderr_path, stdout_file, stderr_file)

        Raises:
            OSError: If temp file creation fails after all retries
        """
        for attempt in range(self.temp_file_creation_retry_attempts):
            try:
                return await self._create_temp_files(prefix)
            except OSError as e:
                _log_with_context(
                    logging.WARNING,
                    f"Temp file creation attempt {attempt + 1} failed",
                    {
                        "attempt": attempt + 1,
                        "max_attempts": self.temp_file_creation_retry_attempts,
                        "error": str(e),
                        "temp_dir": str(self.temp_dir)
                    }
                )

                if attempt == self.temp_file_creation_retry_attempts - 1:
                    self.metrics["creation_failures"] += 1
                    # Try fallback directories
                    for fallback_dir in self.fallback_temp_dirs:
                        if fallback_dir != self.temp_dir:
                            try:
                                old_temp_dir = self.temp_dir
                                self.temp_dir = fallback_dir
                                result = await self._create_temp_files(prefix)
                                _log_with_context(
                                    logging.INFO,
                                    f"Successfully created temp files using fallback directory",
                                    {"fallback_dir": str(fallback_dir), "original_dir": str(old_temp_dir)}
                                )
                                return result
                            except Exception as fallback_error:
                                _log_with_context(
                                    logging.WARNING,
                                    f"Fallback temp directory also failed",
                                    {"fallback_dir": str(fallback_dir), "error": str(fallback_error)}
                                )
                                continue
                    raise e

                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

        # This should never be reached, but just in case
        raise OSError("Failed to create temp files after all retries and fallbacks")

    async def _create_temp_files(self, prefix: str = "cmd_") -> Tuple[str, str, object, object]:
        """Create temporary files for stdout and stderr.

        Args:
            prefix: Prefix for the temporary files

        Returns:
            Tuple of (stdout_path, stderr_path, stdout_file, stderr_file)
        """
        stdout_fd, stdout_path = tempfile.mkstemp(
            prefix=f"{prefix}out_", dir=str(self.temp_dir), text=True
        )
        stderr_fd, stderr_path = tempfile.mkstemp(
            prefix=f"{prefix}err_", dir=str(self.temp_dir), text=True
        )

        # Convert file descriptors to file objects
        stdout_file = os.fdopen(stdout_fd, "w")
        stderr_file = os.fdopen(stderr_fd, "w")

        self.metrics["files_created"] += 2

        _log_with_context(
            logging.DEBUG,
            "Created temp files",
            {"stdout_path": stdout_path, "stderr_path": stderr_path}
        )

        return stdout_path, stderr_path, stdout_file, stderr_file

    def register_temp_files(self, pid: int, stdout_path: str, stderr_path: str) -> None:
        """Register temp files for a process.

        Args:
            pid: Process ID
            stdout_path: Path to stdout temp file
            stderr_path: Path to stderr temp file
        """
        self.temp_files[pid] = (stdout_path, stderr_path, time.time())

        _log_with_context(
            logging.DEBUG,
            "Registered temp files for process",
            {"pid": pid, "stdout_path": stdout_path, "stderr_path": stderr_path}
        )

    async def schedule_cleanup(self, pid: int) -> None:
        """Schedule cleanup without blocking.

        Args:
            pid: Process ID to clean up temp files for
        """
        if pid in self.temp_files:
            await self.cleanup_queue.put(pid)
            _log_with_context(
                logging.DEBUG,
                "Scheduled temp file cleanup",
                {"pid": pid}
            )

    async def _cleanup_worker(self) -> None:
        """Background worker for cleanup operations."""
        try:
            while True:
                pid = await self.cleanup_queue.get()
                await self._safe_cleanup(pid)
                self.cleanup_queue.task_done()
        except asyncio.CancelledError:
            _log_with_context(
                logging.INFO,
                "Cleanup worker task cancelled",
                {}
            )
            raise
        except Exception as e:
            _log_with_context(
                logging.ERROR,
                "Error in cleanup worker",
                {"error": str(e)}
            )

    async def _safe_cleanup(self, pid: int) -> None:
        """Safely clean up temp files with retry mechanism.

        Args:
            pid: Process ID to clean up temp files for
        """
        if pid not in self.temp_files:
            return

        stdout_path, stderr_path, _ = self.temp_files[pid]

        # Try cleanup with retries
        for attempt in range(self.temp_cleanup_retry_attempts):
            try:
                success = True

                # Remove stdout file
                if os.path.exists(stdout_path):
                    os.remove(stdout_path)
                    _log_with_context(
                        logging.DEBUG,
                        "Removed stdout temp file",
                        {"pid": pid, "path": stdout_path}
                    )

                # Remove stderr file
                if os.path.exists(stderr_path):
                    os.remove(stderr_path)
                    _log_with_context(
                        logging.DEBUG,
                        "Removed stderr temp file",
                        {"pid": pid, "path": stderr_path}
                    )

                # Remove from tracking
                del self.temp_files[pid]
                self.metrics["files_cleaned"] += 2

                if attempt > 0:
                    self.metrics["retry_successes"] += 1

                _log_with_context(
                    logging.DEBUG,
                    "Successfully cleaned up temp files",
                    {"pid": pid, "attempt": attempt + 1}
                )
                return

            except Exception as e:
                _log_with_context(
                    logging.WARNING,
                    f"Cleanup attempt {attempt + 1} failed",
                    {
                        "pid": pid,
                        "attempt": attempt + 1,
                        "max_attempts": self.temp_cleanup_retry_attempts,
                        "error": str(e)
                    }
                )

                if attempt == self.temp_cleanup_retry_attempts - 1:
                    # Final attempt failed
                    self.metrics["cleanup_failures"] += 1
                    _log_with_context(
                        logging.ERROR,
                        "Failed to clean up temp files after all retries",
                        {"pid": pid, "stdout_path": stdout_path, "stderr_path": stderr_path}
                    )
                else:
                    # Wait before retry with exponential backoff
                    await asyncio.sleep(self.temp_cleanup_retry_delay * (2 ** attempt))

    async def cleanup_orphaned_files(self) -> int:
        """Find and clean up orphaned temp files.

        Returns:
            Number of orphaned files cleaned up
        """
        cleaned_count = 0
        current_time = time.time()

        try:
            # Find all temp files in the directory
            pattern_prefixes = ["cmd_out_", "cmd_err_"]
            orphaned_files = []

            for file_path in self.temp_dir.glob("*"):
                if file_path.is_file() and any(file_path.name.startswith(prefix) for prefix in pattern_prefixes):
                    if self._is_orphaned(file_path, current_time):
                        orphaned_files.append(file_path)

            # Clean up orphaned files
            for file_path in orphaned_files:
                try:
                    file_path.unlink()
                    cleaned_count += 1
                    _log_with_context(
                        logging.INFO,
                        "Cleaned up orphaned temp file",
                        {"file_path": str(file_path)}
                    )
                except Exception as e:
                    _log_with_context(
                        logging.WARNING,
                        "Failed to clean up orphaned temp file",
                        {"file_path": str(file_path), "error": str(e)}
                    )

            if cleaned_count > 0:
                self.metrics["orphans_cleaned"] += cleaned_count
                _log_with_context(
                    logging.INFO,
                    "Orphaned file cleanup completed",
                    {"cleaned_count": cleaned_count}
                )

        except Exception as e:
            _log_with_context(
                logging.ERROR,
                "Error during orphaned file cleanup",
                {"error": str(e)}
            )

        return cleaned_count

    def _is_orphaned(self, file_path: Path, current_time: float) -> bool:
        """Check if a temp file is orphaned.

        Args:
            file_path: Path to the temp file
            current_time: Current timestamp

        Returns:
            True if the file is considered orphaned
        """
        try:
            # Check file age
            file_age = current_time - file_path.stat().st_mtime
            if file_age < self.orphan_file_max_age:
                return False

            # Check if any tracked process is using this file
            file_str = str(file_path)
            for pid, (stdout_path, stderr_path, _) in self.temp_files.items():
                if file_str in (stdout_path, stderr_path):
                    # Check if the process still exists
                    try:
                        psutil.Process(pid)
                        return False  # Process exists, file is not orphaned
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        # Process doesn't exist, file is orphaned
                        return True

            # File is not tracked and is old enough
            return True

        except Exception as e:
            _log_with_context(
                logging.WARNING,
                "Error checking if file is orphaned",
                {"file_path": str(file_path), "error": str(e)}
            )
            return False

    async def _orphan_cleanup_worker(self) -> None:
        """Background worker for orphaned file cleanup."""
        try:
            while True:
                await asyncio.sleep(self.orphan_cleanup_interval)
                await self.cleanup_orphaned_files()
        except asyncio.CancelledError:
            _log_with_context(
                logging.INFO,
                "Orphan cleanup worker task cancelled",
                {}
            )
            raise
        except Exception as e:
            _log_with_context(
                logging.ERROR,
                "Error in orphan cleanup worker",
                {"error": str(e)}
            )

    def start_background_tasks(self) -> None:
        """Start background cleanup tasks."""
        try:
            # Start cleanup worker
            if self.cleanup_worker_task is None or self.cleanup_worker_task.done():
                self.cleanup_worker_task = asyncio.create_task(self._cleanup_worker())
                _log_with_context(
                    logging.INFO,
                    "Started cleanup worker task",
                    {}
                )

            # Start orphan cleanup worker
            if self.orphan_cleanup_task is None or self.orphan_cleanup_task.done():
                self.orphan_cleanup_task = asyncio.create_task(self._orphan_cleanup_worker())
                _log_with_context(
                    logging.INFO,
                    "Started orphan cleanup worker task",
                    {"interval": self.orphan_cleanup_interval}
                )
        except RuntimeError:
            # No event loop running, tasks will be started later
            _log_with_context(
                logging.DEBUG,
                "No event loop running, deferring background task creation",
                {}
            )

    def stop_background_tasks(self) -> None:
        """Stop background cleanup tasks."""
        if self.cleanup_worker_task and not self.cleanup_worker_task.done():
            self.cleanup_worker_task.cancel()
            self.cleanup_worker_task = None

        if self.orphan_cleanup_task and not self.orphan_cleanup_task.done():
            self.orphan_cleanup_task.cancel()
            self.orphan_cleanup_task = None

        _log_with_context(
            logging.INFO,
            "Stopped background cleanup tasks",
            {}
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get temp file operation metrics.

        Returns:
            Dictionary with metrics
        """
        # Calculate temp directory size
        temp_dir_size_mb = 0.0
        try:
            temp_dir_size_mb = sum(
                f.stat().st_size for f in self.temp_dir.rglob('*') if f.is_file()
            ) / (1024 * 1024)
        except Exception:
            pass

        return {
            **self.metrics,
            "temp_dir": str(self.temp_dir),
            "temp_dir_size_mb": round(float(temp_dir_size_mb), 2),
            "temp_dir_max_size_mb": self.temp_dir_max_size_mb,
            "tracked_files": len(self.temp_files),
            "cleanup_queue_size": self.cleanup_queue.qsize(),
            "cleanup_worker_running": self.cleanup_worker_task is not None and not self.cleanup_worker_task.done(),
            "orphan_cleanup_running": self.orphan_cleanup_task is not None and not self.orphan_cleanup_task.done(),
        }

    async def force_cleanup_all(self) -> Dict[str, Any]:
        """Force cleanup of all tracked temp files.

        Returns:
            Dictionary with cleanup results
        """
        initial_count = len(self.temp_files)
        cleaned_count = 0
        failed_count = 0

        # Copy the keys to avoid modification during iteration
        pids_to_clean = list(self.temp_files.keys())

        for pid in pids_to_clean:
            try:
                await self._safe_cleanup(pid)
                cleaned_count += 1
            except Exception as e:
                failed_count += 1
                _log_with_context(
                    logging.ERROR,
                    "Failed to force cleanup temp files",
                    {"pid": pid, "error": str(e)}
                )

        _log_with_context(
            logging.INFO,
            "Force cleanup completed",
            {
                "initial_count": initial_count,
                "cleaned_count": cleaned_count,
                "failed_count": failed_count
            }
        )

        return {
            "initial_count": initial_count,
            "cleaned_count": cleaned_count,
            "failed_count": failed_count,
            "remaining_count": len(self.temp_files)
        }

    def __del__(self):
        """Cleanup when the TempFileManager is destroyed."""
        try:
            self.stop_background_tasks()
        except Exception:
            # Ignore errors during cleanup
            pass
