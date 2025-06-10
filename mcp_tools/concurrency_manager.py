"""Concurrency management for pull request operations.

This module provides concurrency control for pull request operations to prevent
resource conflicts, API rate limiting, and performance issues.
"""

import logging
import threading
import time as time_module
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class ConcurrencyConfig:
    """Configuration for concurrency limits."""
    max_concurrent: int = 1


@dataclass
class OperationContext:
    """Context information for an operation."""
    operation_id: str
    operation_type: str = "operation"
    start_time: Optional[float] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = time_module.time()


class ConcurrencyManager:
    """Manages concurrency limits for operations."""
    
    def __init__(self):
        self._lock = threading.RLock()
        self._active_operations: Dict[str, Set[str]] = {}  # tool_name -> set of operation_ids
        self._operation_contexts: Dict[str, OperationContext] = {}  # operation_id -> context
        self._configs: Dict[str, ConcurrencyConfig] = {}  # tool_name -> config
    
    def register_config(self, tool_name: str, config: ConcurrencyConfig) -> None:
        """Register concurrency configuration for a tool.
        
        Args:
            tool_name: Name of the tool
            config: Concurrency configuration
        """
        with self._lock:
            self._configs[tool_name] = config
            logger.debug(f"Registered concurrency config for tool '{tool_name}': {config}")
    
    def can_start_operation(self, tool_name: str, context: OperationContext) -> Dict[str, Any]:
        """Check if an operation can start based on concurrency limits.
        
        Args:
            tool_name: Name of the tool requesting the operation
            context: Operation context
            
        Returns:
            Dictionary with 'allowed' boolean and optional error information
        """
        with self._lock:
            config = self._configs.get(tool_name)
            if not config:
                # No concurrency config, allow operation
                return {"allowed": True}
            
            # Get current operations for this tool
            current_operations = self._active_operations.get(tool_name, set())
            current_count = len(current_operations)
            
            if current_count >= config.max_concurrent:
                return {
                    "allowed": False,
                    "error": "concurrency_limit_exceeded",
                    "message": f"Operation rejected: maximum concurrent operations ({config.max_concurrent}) already running for tool '{tool_name}'",
                    "retry_after": "Please wait for the current operation to complete before retrying",
                    "current_operations": current_count,
                    "max_allowed": config.max_concurrent,
                    "tool_name": tool_name
                }
            
            return {"allowed": True}
    
    def start_operation(self, tool_name: str, context: OperationContext) -> Dict[str, Any]:
        """Start tracking an operation.
        
        Args:
            tool_name: Name of the tool
            context: Operation context
            
        Returns:
            Dictionary with success status and optional error information
        """
        with self._lock:
            # Check if operation can start
            check_result = self.can_start_operation(tool_name, context)
            if not check_result["allowed"]:
                return {"success": False, **check_result}
            
            config = self._configs.get(tool_name)
            if not config:
                # No concurrency config, just track the operation
                self._operation_contexts[context.operation_id] = context
                return {"success": True}
            
            # Add operation to tracking
            if tool_name not in self._active_operations:
                self._active_operations[tool_name] = set()
            
            self._active_operations[tool_name].add(context.operation_id)
            self._operation_contexts[context.operation_id] = context
            
            logger.info(f"Started tracking operation '{context.operation_id}' for tool '{tool_name}'")
            return {"success": True}
    
    def finish_operation(self, operation_id: str) -> Dict[str, Any]:
        """Stop tracking an operation.
        
        Args:
            operation_id: ID of the operation to stop tracking
            
        Returns:
            Dictionary with success status
        """
        with self._lock:
            context = self._operation_contexts.get(operation_id)
            if not context:
                logger.warning(f"Attempted to finish unknown operation: {operation_id}")
                return {"success": False, "error": "operation_not_found"}
            
            # Find and remove from all tools
            for tool_name, operations in self._active_operations.items():
                if operation_id in operations:
                    operations.remove(operation_id)
                    if not operations:  # Clean up empty sets
                        del self._active_operations[tool_name]
                    break
            
            # Remove from contexts
            del self._operation_contexts[operation_id]
            
            duration = time_module.time() - context.start_time
            logger.info(f"Finished tracking operation '{operation_id}' (duration: {duration:.2f}s)")
            return {"success": True}
    
    def get_active_operations(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get information about active operations.
        
        Args:
            tool_name: Optional tool name to filter by
            
        Returns:
            Dictionary with active operations information
        """
        with self._lock:
            if tool_name:
                operations = self._active_operations.get(tool_name, set())
                contexts = [self._operation_contexts[op_id] for op_id in operations]
                return {
                    "tool_name": tool_name,
                    "count": len(operations),
                    "operations": [
                        {
                            "operation_id": ctx.operation_id,
                            "operation_type": ctx.operation_type,
                            "duration": time_module.time() - ctx.start_time
                        }
                        for ctx in contexts
                    ]
                }
            else:
                # Return all active operations grouped by tool
                result = {}
                for tool_name, operations in self._active_operations.items():
                    contexts = [self._operation_contexts[op_id] for op_id in operations]
                    result[tool_name] = {
                        "count": len(operations),
                        "operations": [
                            {
                                "operation_id": ctx.operation_id,
                                "operation_type": ctx.operation_type,
                                "duration": time_module.time() - ctx.start_time
                            }
                            for ctx in contexts
                        ]
                    }
                return result
    
    def cleanup_stale_operations(self, max_age_seconds: float = 3600) -> Dict[str, Any]:
        """Clean up operations that have been running for too long.
        
        Args:
            max_age_seconds: Maximum age in seconds before considering an operation stale
            
        Returns:
            Dictionary with cleanup statistics
        """
        with self._lock:
            current_time = time_module.time()
            stale_operations = []
            
            for operation_id, context in self._operation_contexts.items():
                if current_time - context.start_time > max_age_seconds:
                    stale_operations.append(operation_id)
            
            # Remove stale operations
            for operation_id in stale_operations:
                self.finish_operation(operation_id)
            
            logger.info(f"Cleaned up {len(stale_operations)} stale operations")
            return {
                "cleaned_count": len(stale_operations),
                "max_age_seconds": max_age_seconds,
                "stale_operations": stale_operations
            }


# Global instance
_concurrency_manager = ConcurrencyManager()


def get_concurrency_manager() -> ConcurrencyManager:
    """Get the global concurrency manager instance."""
    return _concurrency_manager


def parse_concurrency_config(config_dict: Dict[str, Any]) -> ConcurrencyConfig:
    """Parse concurrency configuration from dictionary.
    
    Args:
        config_dict: Dictionary containing concurrency configuration
        
    Returns:
        ConcurrencyConfig instance
    """
    return ConcurrencyConfig(
        max_concurrent=config_dict.get("max_concurrent", 1)
    ) 