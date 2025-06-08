"""Startup performance tracing utilities for MCP server.

This module provides comprehensive timing instrumentation to identify
startup bottlenecks and performance issues.
"""

import time
import logging
import functools
from typing import Dict, List, Optional, Any, Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class TimingEntry:
    """Represents a single timing measurement."""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    parent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self) -> float:
        """Mark the timing entry as finished and calculate duration."""
        if self.end_time is None:
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time
        return self.duration or 0.0


class StartupTracer:
    """Comprehensive startup performance tracer.
    
    Tracks timing information for various startup phases and provides
    detailed analysis of performance bottlenecks.
    """
    
    def __init__(self):
        self.timings: Dict[str, TimingEntry] = {}
        self.active_timings: Dict[str, TimingEntry] = {}
        self.startup_start: float = time.time()
        self.phase_stack: List[str] = []
        
    def start_timing(self, name: str, parent: Optional[str] = None, **metadata) -> TimingEntry:
        """Start timing a named operation.
        
        Args:
            name: Name of the operation being timed
            parent: Optional parent operation name
            **metadata: Additional metadata to store with the timing
            
        Returns:
            TimingEntry object for the started timing
        """
        if parent is None and self.phase_stack:
            parent = self.phase_stack[-1]
            
        entry = TimingEntry(
            name=name,
            start_time=time.time(),
            parent=parent,
            metadata=metadata
        )
        
        self.timings[name] = entry
        self.active_timings[name] = entry
        self.phase_stack.append(name)
        
        elapsed = entry.start_time - self.startup_start
        logger.info(f">> [{elapsed:.2f}s] Starting {name}...")
        
        return entry
    
    def finish_timing(self, name: str) -> Optional[float]:
        """Finish timing a named operation.
        
        Args:
            name: Name of the operation to finish
            
        Returns:
            Duration in seconds, or None if timing not found
        """
        if name not in self.active_timings:
            logger.warning(f"Attempted to finish unknown timing: {name}")
            return None
            
        entry = self.active_timings.pop(name)
        duration = entry.finish()
        
        if name in self.phase_stack:
            self.phase_stack.remove(name)
        
        elapsed = time.time() - self.startup_start
        logger.info(f"OK [{elapsed:.2f}s] {name} completed in {duration:.2f}s")
        
        return duration
    
    @contextmanager
    def time_operation(self, name: str, parent: Optional[str] = None, **metadata):
        """Context manager for timing operations.
        
        Args:
            name: Name of the operation being timed
            parent: Optional parent operation name
            **metadata: Additional metadata to store with the timing
        """
        entry = self.start_timing(name, parent, **metadata)
        try:
            yield entry
        finally:
            self.finish_timing(name)
    
    def get_timing_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of all timings.
        
        Returns:
            Dictionary containing timing analysis and statistics
        """
        total_startup_time = time.time() - self.startup_start
        
        # Calculate statistics
        completed_timings = {
            name: entry for name, entry in self.timings.items() 
            if entry.duration is not None
        }
        
        if not completed_timings:
            return {
                "total_startup_time": total_startup_time,
                "completed_operations": 0,
                "timings": {}
            }
        
        durations = [entry.duration for entry in completed_timings.values() if entry.duration is not None]
        
        # Find top-level operations (no parent)
        top_level = [
            entry for entry in completed_timings.values() 
            if entry.parent is None
        ]
        
        # Find slowest operations
        slowest = sorted(
            completed_timings.values(), 
            key=lambda x: x.duration, 
            reverse=True
        )[:10]
        
        return {
            "total_startup_time": total_startup_time,
            "completed_operations": len(completed_timings),
            "total_measured_time": sum(durations),
            "average_operation_time": sum(durations) / len(durations) if durations else 0.0,
            "slowest_operations": [
                {
                    "name": entry.name,
                    "duration": entry.duration or 0.0,
                    "percentage": ((entry.duration or 0.0) / total_startup_time) * 100,
                    "metadata": entry.metadata
                }
                for entry in slowest
            ],
            "top_level_operations": [
                {
                    "name": entry.name,
                    "duration": entry.duration or 0.0,
                    "percentage": ((entry.duration or 0.0) / total_startup_time) * 100
                }
                for entry in top_level
            ],
            "timings": {
                name: {
                    "duration": entry.duration,
                    "parent": entry.parent,
                    "metadata": entry.metadata
                }
                for name, entry in completed_timings.items()
            }
        }
    
    def log_summary(self):
        """Log a comprehensive summary of startup performance."""
        summary = self.get_timing_summary()
        
        logger.info("=" * 60)
        logger.info("STARTUP PERFORMANCE ANALYSIS")
        logger.info("=" * 60)
        logger.info(f"Total startup time: {summary['total_startup_time']:.2f}s")
        logger.info(f"Completed operations: {summary['completed_operations']}")
        
        if summary['completed_operations'] > 0:
            logger.info(f"Total measured time: {summary['total_measured_time']:.2f}s")
            logger.info(f"Average operation time: {summary['average_operation_time']:.2f}s")
            
            logger.info("\nSLOWEST OPERATIONS:")
            for i, op in enumerate(summary['slowest_operations'][:5], 1):
                logger.info(f"  {i}. {op['name']}: {op['duration']:.2f}s ({op['percentage']:.1f}%)")
            
            logger.info("\nTOP-LEVEL OPERATIONS:")
            for op in summary['top_level_operations']:
                logger.info(f"  • {op['name']}: {op['duration']:.2f}s ({op['percentage']:.1f}%)")
        
        # Check for performance issues
        if summary['total_startup_time'] > 10:
            logger.warning(f"WARNING: Startup time ({summary['total_startup_time']:.2f}s) exceeds target of 10s")
        
        logger.info("=" * 60)
    
    def save_detailed_report(self, filepath: Optional[Path] = None):
        """Save a detailed timing report to a JSON file.
        
        Args:
            filepath: Optional path to save the report. If None, saves to server/.logs/startup_timing_report.json
        """
        if filepath is None:
            # Create logs directory if it doesn't exist
            logs_dir = Path(__file__).parent / ".logs"
            logs_dir.mkdir(exist_ok=True)
            filepath = logs_dir / "startup_timing_report.json"
        
        summary = self.get_timing_summary()
        
        # Add additional details
        report = {
            "timestamp": time.time(),
            "startup_analysis": summary,
            "detailed_timings": [
                {
                    "name": entry.name,
                    "start_time": entry.start_time,
                    "end_time": entry.end_time,
                    "duration": entry.duration,
                    "parent": entry.parent,
                    "metadata": entry.metadata
                }
                for entry in self.timings.values()
            ]
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Detailed timing report saved to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save timing report: {e}")


def trace_startup_time(name: Optional[str] = None, tracer: Optional[StartupTracer] = None):
    """Decorator to trace startup time for functions.
    
    Args:
        name: Optional custom name for the operation. If None, uses function name.
        tracer: Optional tracer instance. If None, uses the global tracer.
    """
    def decorator(func: Callable) -> Callable:
        operation_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_tracer = tracer or get_global_tracer()
            with current_tracer.time_operation(operation_name):
                return func(*args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_tracer = tracer or get_global_tracer()
            with current_tracer.time_operation(operation_name):
                return await func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return wrapper
    
    return decorator


# Global tracer instance
_global_tracer: Optional[StartupTracer] = None


def get_global_tracer() -> StartupTracer:
    """Get or create the global startup tracer instance."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = StartupTracer()
    return _global_tracer


def reset_global_tracer():
    """Reset the global tracer instance."""
    global _global_tracer
    _global_tracer = None


# Convenience functions for global tracer
def start_timing(name: str, parent: Optional[str] = None, **metadata) -> TimingEntry:
    """Start timing using the global tracer."""
    return get_global_tracer().start_timing(name, parent, **metadata)


def finish_timing(name: str) -> Optional[float]:
    """Finish timing using the global tracer."""
    return get_global_tracer().finish_timing(name)


def time_operation(name: str, parent: Optional[str] = None, **metadata):
    """Context manager for timing operations using the global tracer."""
    return get_global_tracer().time_operation(name, parent, **metadata)


def log_startup_summary():
    """Log startup summary using the global tracer."""
    get_global_tracer().log_summary()


def save_startup_report(filepath: Optional[Path] = None):
    """Save startup report using the global tracer."""
    get_global_tracer().save_detailed_report(filepath) 