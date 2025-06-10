import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque
import logging
import uuid

from .types import ConcurrencyConfig, QueueStatus, ConcurrencyLimitError

logger = logging.getLogger(__name__)


class QueuedRequest:
    """Represents a queued command request"""
    
    def __init__(self, command: str, user_id: str, timeout: Optional[float] = None):
        self.id = str(uuid.uuid4())
        self.command = command
        self.user_id = user_id
        self.timeout = timeout
        self.queued_at = time.time()
        self.future: Optional[asyncio.Future] = None
    
    def __repr__(self):
        return f"QueuedRequest(id={self.id[:8]}, user={self.user_id}, command={self.command[:50]}...)"


class ConcurrencyManager:
    """Manages process concurrency and queuing"""
    
    def __init__(self, config: ConcurrencyConfig):
        """
        Initialize concurrency manager
        
        Args:
            config: Concurrency configuration
        """
        self.config = config
        self.enabled = config.enabled
        
        # Track running processes
        self.running_processes: Dict[str, Dict[str, Any]] = {}  # token -> process_info
        self.user_processes: Dict[str, List[str]] = defaultdict(list)  # user_id -> [tokens]
        
        # Process queue
        self.process_queue: deque[QueuedRequest] = deque()
        self.queue_lock = asyncio.Lock()
        
        # Queue processing task
        self.queue_processor_task: Optional[asyncio.Task] = None
        self.queue_processor_running = False
        
        logger.info(f"ConcurrencyManager initialized: enabled={self.enabled}, "
                   f"max_concurrent={config.max_concurrent_processes}, "
                   f"max_per_user={config.max_processes_per_user}")
    
    async def start_queue_processor(self):
        """Start the queue processor task"""
        if self.queue_processor_task is None or self.queue_processor_task.done():
            self.queue_processor_running = True
            self.queue_processor_task = asyncio.create_task(self._process_queue())
            logger.info("Queue processor started")
    
    async def stop_queue_processor(self):
        """Stop the queue processor task"""
        self.queue_processor_running = False
        if self.queue_processor_task and not self.queue_processor_task.done():
            self.queue_processor_task.cancel()
            try:
                await self.queue_processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Queue processor stopped")
    
    async def check_concurrency_limit(self, user_id: str) -> Tuple[bool, Optional[Dict]]:
        """
        Check if user can start a new process
        
        Args:
            user_id: User identifier
            
        Returns:
            Tuple of (can_start, error_info)
        """
        if not self.enabled:
            return True, None
        
        async with self.queue_lock:
            # Check global concurrency limit
            total_running = len(self.running_processes)
            if total_running >= self.config.max_concurrent_processes:
                # Check if queue has space
                if len(self.process_queue) >= self.config.process_queue_size:
                    error_info = {
                        "error": "concurrency_limited",
                        "message": "Too many concurrent processes and queue is full",
                        "queue_position": None,
                        "estimated_wait_seconds": None
                    }
                    return False, error_info
                
                # Can be queued
                queue_position = len(self.process_queue) + 1
                estimated_wait = self._estimate_wait_time()
                
                error_info = {
                    "error": "concurrency_limited",
                    "message": "Too many concurrent processes",
                    "queue_position": queue_position,
                    "estimated_wait_seconds": estimated_wait
                }
                return False, error_info
            
            # Check per-user limit
            user_running = len(self.user_processes.get(user_id, []))
            if user_running >= self.config.max_processes_per_user:
                error_info = {
                    "error": "concurrency_limited",
                    "message": f"Too many concurrent processes for user (max: {self.config.max_processes_per_user})",
                    "queue_position": None,
                    "estimated_wait_seconds": None
                }
                return False, error_info
        
        return True, None
    
    async def register_process(self, token: str, user_id: str, command: str, pid: int) -> None:
        """
        Register a running process
        
        Args:
            token: Process token
            user_id: User identifier
            command: Command being executed
            pid: Process ID
        """
        async with self.queue_lock:
            self.running_processes[token] = {
                "user_id": user_id,
                "command": command,
                "pid": pid,
                "start_time": time.time()
            }
            self.user_processes[user_id].append(token)
            
            logger.debug(f"Registered process: token={token[:8]}, user={user_id}, pid={pid}")
    
    async def unregister_process(self, token: str) -> None:
        """
        Unregister a completed process
        
        Args:
            token: Process token
        """
        async with self.queue_lock:
            if token in self.running_processes:
                process_info = self.running_processes[token]
                user_id = process_info["user_id"]
                
                # Remove from running processes
                del self.running_processes[token]
                
                # Remove from user processes
                if user_id in self.user_processes:
                    try:
                        self.user_processes[user_id].remove(token)
                        if not self.user_processes[user_id]:
                            del self.user_processes[user_id]
                    except ValueError:
                        pass  # Token not in list
                
                logger.debug(f"Unregistered process: token={token[:8]}, user={user_id}")
                
                # Trigger queue processing
                if self.process_queue and self.queue_processor_running:
                    # Wake up the queue processor
                    pass
    
    async def queue_request(self, command: str, user_id: str, timeout: Optional[float] = None) -> QueuedRequest:
        """
        Queue a request for later processing
        
        Args:
            command: Command to execute
            user_id: User identifier
            timeout: Optional timeout
            
        Returns:
            QueuedRequest object
        """
        async with self.queue_lock:
            if len(self.process_queue) >= self.config.process_queue_size:
                raise ValueError("Queue is full")
            
            request = QueuedRequest(command, user_id, timeout)
            request.future = asyncio.Future()
            self.process_queue.append(request)
            
            logger.info(f"Queued request: id={request.id[:8]}, user={user_id}, "
                       f"queue_size={len(self.process_queue)}")
            
            return request
    
    async def _process_queue(self):
        """Background task to process queued requests"""
        logger.info("Queue processor started")
        
        while self.queue_processor_running:
            try:
                # Check if we can process any queued requests
                async with self.queue_lock:
                    if not self.process_queue:
                        # No requests to process
                        pass
                    elif len(self.running_processes) < self.config.max_concurrent_processes:
                        # Can process next request
                        request = self.process_queue.popleft()
                        
                        # Check per-user limit
                        user_running = len(self.user_processes.get(request.user_id, []))
                        if user_running < self.config.max_processes_per_user:
                            # Can start this request
                            if request.future and not request.future.done():
                                request.future.set_result(request)
                                logger.info(f"Dequeued request for processing: id={request.id[:8]}")
                        else:
                            # Put back at front of queue
                            self.process_queue.appendleft(request)
                
                # Sleep briefly before checking again
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                logger.info("Queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(1)  # Wait before retrying
        
        logger.info("Queue processor stopped")
    
    def _estimate_wait_time(self) -> int:
        """Estimate wait time for queued requests"""
        if not self.running_processes:
            return 0
        
        # Simple estimation: assume average process takes 30 seconds
        # and we can process (max_concurrent - current_running) at a time
        avg_process_time = 30
        current_running = len(self.running_processes)
        available_slots = max(0, self.config.max_concurrent_processes - current_running)
        
        if available_slots == 0:
            return avg_process_time
        
        queue_ahead = len(self.process_queue)
        batches = (queue_ahead + available_slots - 1) // available_slots  # Ceiling division
        
        return batches * avg_process_time
    
    async def get_queue_status(self) -> QueueStatus:
        """Get current queue status"""
        async with self.queue_lock:
            return QueueStatus(
                queue_size=len(self.process_queue),
                max_queue_size=self.config.process_queue_size,
                processing=len(self.running_processes),
                max_concurrent=self.config.max_concurrent_processes
            )
    
    async def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """Get status for specific user"""
        async with self.queue_lock:
            user_processes = self.user_processes.get(user_id, [])
            
            return {
                "user_id": user_id,
                "concurrent_processes": len(user_processes),
                "max_concurrent_processes": self.config.max_processes_per_user,
                "running_tokens": [token[:8] for token in user_processes]
            }
    
    async def list_running_processes(self) -> List[Dict[str, Any]]:
        """List all running processes"""
        async with self.queue_lock:
            processes = []
            for token, info in self.running_processes.items():
                processes.append({
                    "token": token[:8],
                    "user_id": info["user_id"],
                    "command": info["command"],
                    "pid": info["pid"],
                    "runtime": time.time() - info["start_time"]
                })
            return processes
    
    def update_config(self, config: ConcurrencyConfig) -> None:
        """Update concurrency configuration"""
        self.config = config
        self.enabled = config.enabled
        logger.info(f"ConcurrencyManager config updated: enabled={self.enabled}")
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.stop_queue_processor()
        
        # Cancel any pending futures
        async with self.queue_lock:
            for request in self.process_queue:
                if request.future and not request.future.done():
                    request.future.cancel()
            self.process_queue.clear() 