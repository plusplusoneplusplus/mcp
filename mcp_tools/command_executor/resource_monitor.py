import asyncio
import time
import psutil
from typing import Dict, Optional, Any, List
import logging
import signal
import os

from .types import ResourceLimitConfig

logger = logging.getLogger(__name__)


class ProcessResourceInfo:
    """Information about a process's resource usage"""
    
    def __init__(self, pid: int):
        self.pid = pid
        self.start_time = time.time()
        self.cpu_time_start = 0.0
        self.memory_peak_mb = 0.0
        self.terminated = False
        
        # Get initial CPU time if process exists
        try:
            process = psutil.Process(pid)
            cpu_times = process.cpu_times()
            self.cpu_time_start = cpu_times.user + cpu_times.system
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    def update_from_psutil(self, process: psutil.Process) -> Dict[str, Any]:
        """Update resource info from psutil process"""
        try:
            # Memory info
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            self.memory_peak_mb = max(self.memory_peak_mb, memory_mb)
            
            # CPU time
            cpu_times = process.cpu_times()
            current_cpu_time = cpu_times.user + cpu_times.system
            cpu_time_used = current_cpu_time - self.cpu_time_start
            
            # Execution time
            execution_time = time.time() - self.start_time
            
            return {
                "memory_mb": memory_mb,
                "memory_peak_mb": self.memory_peak_mb,
                "cpu_time_used": cpu_time_used,
                "execution_time": execution_time,
                "status": process.status()
            }
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return {
                "memory_mb": 0.0,
                "memory_peak_mb": self.memory_peak_mb,
                "cpu_time_used": 0.0,
                "execution_time": time.time() - self.start_time,
                "status": "not_found"
            }


class ResourceMonitor:
    """Monitors and enforces resource limits for processes"""
    
    def __init__(self, config: ResourceLimitConfig):
        """
        Initialize resource monitor
        
        Args:
            config: Resource limit configuration
        """
        self.config = config
        self.enabled = config.enabled
        
        # Track monitored processes
        self.monitored_processes: Dict[int, ProcessResourceInfo] = {}
        self.monitor_lock = asyncio.Lock()
        
        # Monitoring task
        self.monitor_task: Optional[asyncio.Task] = None
        self.monitor_running = False
        
        logger.info(f"ResourceMonitor initialized: enabled={self.enabled}, "
                   f"memory_limit={config.max_memory_per_process_mb}MB, "
                   f"cpu_limit={config.max_cpu_time_seconds}s, "
                   f"execution_limit={config.max_execution_time_seconds}s")
    
    async def start_monitoring(self):
        """Start the resource monitoring task"""
        if not self.enabled:
            return
            
        if self.monitor_task is None or self.monitor_task.done():
            self.monitor_running = True
            self.monitor_task = asyncio.create_task(self._monitor_processes())
            logger.info("Resource monitoring started")
    
    async def stop_monitoring(self):
        """Stop the resource monitoring task"""
        self.monitor_running = False
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Resource monitoring stopped")
    
    async def add_process(self, pid: int) -> None:
        """
        Add a process to monitoring
        
        Args:
            pid: Process ID to monitor
        """
        if not self.enabled:
            return
            
        async with self.monitor_lock:
            if pid not in self.monitored_processes:
                self.monitored_processes[pid] = ProcessResourceInfo(pid)
                logger.debug(f"Added process {pid} to resource monitoring")
    
    async def remove_process(self, pid: int) -> Optional[Dict[str, Any]]:
        """
        Remove a process from monitoring and return final stats
        
        Args:
            pid: Process ID to remove
            
        Returns:
            Final resource usage statistics
        """
        async with self.monitor_lock:
            if pid in self.monitored_processes:
                process_info = self.monitored_processes[pid]
                
                # Get final stats
                try:
                    process = psutil.Process(pid)
                    final_stats = process_info.update_from_psutil(process)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    final_stats = {
                        "memory_mb": 0.0,
                        "memory_peak_mb": process_info.memory_peak_mb,
                        "cpu_time_used": 0.0,
                        "execution_time": time.time() - process_info.start_time,
                        "status": "completed"
                    }
                
                del self.monitored_processes[pid]
                logger.debug(f"Removed process {pid} from monitoring")
                return final_stats
        
        return None
    
    async def get_process_stats(self, pid: int) -> Optional[Dict[str, Any]]:
        """
        Get current resource statistics for a process
        
        Args:
            pid: Process ID
            
        Returns:
            Current resource usage statistics
        """
        async with self.monitor_lock:
            if pid not in self.monitored_processes:
                return None
            
            process_info = self.monitored_processes[pid]
            
            try:
                process = psutil.Process(pid)
                return process_info.update_from_psutil(process)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return {
                    "memory_mb": 0.0,
                    "memory_peak_mb": process_info.memory_peak_mb,
                    "cpu_time_used": 0.0,
                    "execution_time": time.time() - process_info.start_time,
                    "status": "not_found"
                }
    
    async def check_limits(self, pid: int) -> Dict[str, Any]:
        """
        Check if process exceeds any limits
        
        Args:
            pid: Process ID to check
            
        Returns:
            Dictionary with limit check results
        """
        stats = await self.get_process_stats(pid)
        if not stats:
            return {"exceeded": False, "reason": None}
        
        # Check memory limit
        if stats["memory_mb"] > self.config.max_memory_per_process_mb:
            return {
                "exceeded": True,
                "reason": "memory_limit",
                "limit": self.config.max_memory_per_process_mb,
                "current": stats["memory_mb"],
                "message": f"Memory usage {stats['memory_mb']:.1f}MB exceeds limit {self.config.max_memory_per_process_mb}MB"
            }
        
        # Check CPU time limit
        if stats["cpu_time_used"] > self.config.max_cpu_time_seconds:
            return {
                "exceeded": True,
                "reason": "cpu_time_limit",
                "limit": self.config.max_cpu_time_seconds,
                "current": stats["cpu_time_used"],
                "message": f"CPU time {stats['cpu_time_used']:.1f}s exceeds limit {self.config.max_cpu_time_seconds}s"
            }
        
        # Check execution time limit
        if stats["execution_time"] > self.config.max_execution_time_seconds:
            return {
                "exceeded": True,
                "reason": "execution_time_limit",
                "limit": self.config.max_execution_time_seconds,
                "current": stats["execution_time"],
                "message": f"Execution time {stats['execution_time']:.1f}s exceeds limit {self.config.max_execution_time_seconds}s"
            }
        
        return {"exceeded": False, "reason": None}
    
    async def terminate_process(self, pid: int, reason: str) -> bool:
        """
        Terminate a process that exceeded limits
        
        Args:
            pid: Process ID to terminate
            reason: Reason for termination
            
        Returns:
            True if termination was successful
        """
        try:
            process = psutil.Process(pid)
            
            logger.warning(f"Terminating process {pid} due to {reason}")
            
            # Try graceful termination first
            process.terminate()
            
            # Wait a bit for graceful termination
            try:
                process.wait(timeout=5)
                logger.info(f"Process {pid} terminated gracefully")
                return True
            except psutil.TimeoutExpired:
                # Force kill if graceful termination failed
                logger.warning(f"Force killing process {pid}")
                process.kill()
                process.wait(timeout=5)
                logger.info(f"Process {pid} force killed")
                return True
                
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"Could not terminate process {pid}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error terminating process {pid}: {e}")
            return False
    
    async def _monitor_processes(self):
        """Background task to monitor process resource usage"""
        logger.info("Resource monitoring task started")
        
        while self.monitor_running:
            try:
                # Get list of processes to check (copy to avoid modification during iteration)
                async with self.monitor_lock:
                    pids_to_check = list(self.monitored_processes.keys())
                
                # Check each process
                for pid in pids_to_check:
                    try:
                        limit_check = await self.check_limits(pid)
                        
                        if limit_check["exceeded"]:
                            # Process exceeded limits, terminate it
                            reason = limit_check["reason"]
                            message = limit_check["message"]
                            
                            logger.warning(f"Process {pid} exceeded {reason}: {message}")
                            
                            # Mark as terminated in our tracking
                            async with self.monitor_lock:
                                if pid in self.monitored_processes:
                                    self.monitored_processes[pid].terminated = True
                            
                            # Terminate the process
                            await self.terminate_process(pid, reason)
                            
                    except Exception as e:
                        logger.error(f"Error checking limits for process {pid}: {e}")
                
                # Sleep before next check
                await asyncio.sleep(1.0)  # Check every second
                
            except asyncio.CancelledError:
                logger.info("Resource monitoring task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in resource monitoring task: {e}")
                await asyncio.sleep(5.0)  # Wait before retrying
        
        logger.info("Resource monitoring task stopped")
    
    async def get_all_stats(self) -> List[Dict[str, Any]]:
        """Get resource statistics for all monitored processes"""
        async with self.monitor_lock:
            stats = []
            for pid in self.monitored_processes.keys():
                process_stats = await self.get_process_stats(pid)
                if process_stats:
                    process_stats["pid"] = pid
                    stats.append(process_stats)
            return stats
    
    def update_config(self, config: ResourceLimitConfig) -> None:
        """Update resource monitoring configuration"""
        self.config = config
        self.enabled = config.enabled
        logger.info(f"ResourceMonitor config updated: enabled={self.enabled}")
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.stop_monitoring()
        
        # Clear monitored processes
        async with self.monitor_lock:
            self.monitored_processes.clear() 