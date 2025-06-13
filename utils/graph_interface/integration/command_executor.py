"""Integration between graph interface and CommandExecutor.

This module provides integration utilities for connecting the Neo4j graph interface
with the existing CommandExecutor system for task execution.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
import json

from ..graph_manager import GraphManager
from ..models import GraphNode, GraphRelationship
from ..exceptions import GraphOperationError
from ..scheduling.task_scheduler import TaskScheduler

# Import CommandExecutor if available
try:
    from mcp_tools.command_executor.executor import CommandExecutor
    COMMAND_EXECUTOR_AVAILABLE = True
except ImportError:
    COMMAND_EXECUTOR_AVAILABLE = False
    CommandExecutor = None

logger = logging.getLogger(__name__)


class TaskGraphIntegration:
    """Integration between graph-based task management and CommandExecutor."""

    def __init__(self, graph_manager: GraphManager, command_executor: Optional[CommandExecutor] = None):
        """Initialize with graph manager and optional command executor.
        
        Args:
            graph_manager: GraphManager instance for graph operations
            command_executor: CommandExecutor instance (created if None)
        """
        self.graph = graph_manager
        self.scheduler = TaskScheduler(graph_manager)
        
        if command_executor:
            self.executor = command_executor
        elif COMMAND_EXECUTOR_AVAILABLE:
            self.executor = CommandExecutor()
        else:
            self.executor = None
            logger.warning("CommandExecutor not available - some features will be disabled")
        
        # Track running tasks
        self.running_tasks: Dict[str, str] = {}  # task_id -> execution_token
        self.task_tokens: Dict[str, str] = {}    # execution_token -> task_id

    async def sync_with_command_executor(self) -> Dict[str, Any]:
        """Synchronize graph state with command executor state.
        
        Returns:
            Dictionary with synchronization results
        """
        logger.info("Synchronizing with command executor")
        
        if not self.executor:
            return {
                "success": False,
                "error": "CommandExecutor not available"
            }
        
        try:
            # Get running processes from command executor
            running_processes = self.executor.list_running_processes()
            
            # Get tasks marked as running in graph
            graph_running_tasks = await self._get_running_tasks_from_graph()
            
            # Find discrepancies
            sync_results = {
                "executor_processes": len(running_processes),
                "graph_running_tasks": len(graph_running_tasks),
                "synchronized_tasks": 0,
                "orphaned_processes": [],
                "stale_graph_tasks": [],
                "errors": []
            }
            
            # Check for orphaned processes (running in executor but not in graph)
            executor_tokens = {proc["token"] for proc in running_processes}
            known_tokens = set(self.task_tokens.keys())
            
            orphaned_tokens = executor_tokens - known_tokens
            for token in orphaned_tokens:
                proc_info = next((p for p in running_processes if p["token"] == token), None)
                if proc_info:
                    sync_results["orphaned_processes"].append({
                        "token": token,
                        "command": proc_info.get("command", "unknown"),
                        "runtime": proc_info.get("runtime", 0)
                    })
            
            # Check for stale graph tasks (marked running but not in executor)
            for task_id in graph_running_tasks:
                if task_id not in self.running_tasks:
                    sync_results["stale_graph_tasks"].append(task_id)
                    # Update task status to failed
                    try:
                        await self._update_task_status(task_id, "failed", 
                                                     error="Process not found in executor")
                    except Exception as e:
                        sync_results["errors"].append(f"Failed to update task {task_id}: {e}")
            
            # Update synchronized count
            sync_results["synchronized_tasks"] = len(self.running_tasks)
            
            logger.info(f"Synchronization complete: {sync_results}")
            return {
                "success": True,
                "results": sync_results
            }
            
        except Exception as e:
            logger.error(f"Error synchronizing with command executor: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_ready_tasks(self, max_tasks: Optional[int] = None) -> Dict[str, Any]:
        """Execute tasks that are ready for execution.
        
        Args:
            max_tasks: Maximum number of tasks to execute (None for all ready)
            
        Returns:
            Dictionary with execution results
        """
        logger.info(f"Executing ready tasks (max: {max_tasks})")
        
        if not self.executor:
            return {
                "success": False,
                "error": "CommandExecutor not available"
            }
        
        try:
            # Find ready tasks
            ready_task_ids = await self.scheduler.find_ready_tasks(max_tasks)
            
            if not ready_task_ids:
                return {
                    "success": True,
                    "executed_tasks": [],
                    "message": "No tasks ready for execution"
                }
            
            # Get task details
            executed_tasks = []
            execution_errors = []
            
            for task_id in ready_task_ids:
                try:
                    task = await self.graph.node_manager.get_node(task_id)
                    if not task:
                        execution_errors.append(f"Task {task_id} not found")
                        continue
                    
                    # Extract command from task properties
                    command = task.get_property("command")
                    if not command:
                        execution_errors.append(f"Task {task_id} has no command")
                        continue
                    
                    # Execute the task
                    execution_result = await self._execute_task(task_id, command)
                    executed_tasks.append(execution_result)
                    
                except Exception as e:
                    execution_errors.append(f"Failed to execute task {task_id}: {e}")
            
            return {
                "success": True,
                "executed_tasks": executed_tasks,
                "execution_errors": execution_errors,
                "total_executed": len(executed_tasks),
                "total_errors": len(execution_errors)
            }
            
        except Exception as e:
            logger.error(f"Error executing ready tasks: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def handle_task_completion(self, task_id: str) -> List[str]:
        """Handle task completion and return newly ready tasks.
        
        Args:
            task_id: ID of the completed task
            
        Returns:
            List of task IDs that are now ready for execution
        """
        logger.info(f"Handling completion of task {task_id}")
        
        try:
            # Update task status to completed
            await self._update_task_status(task_id, "completed")
            
            # Remove from running tasks tracking
            if task_id in self.running_tasks:
                token = self.running_tasks[task_id]
                del self.running_tasks[task_id]
                if token in self.task_tokens:
                    del self.task_tokens[token]
            
            # Find newly ready tasks
            newly_ready = await self._find_newly_ready_tasks(task_id)
            
            logger.info(f"Task {task_id} completed, {len(newly_ready)} tasks now ready")
            return newly_ready
            
        except Exception as e:
            logger.error(f"Error handling task completion: {e}")
            return []

    async def handle_task_failure(self, task_id: str, error_message: str = "") -> None:
        """Handle task failure and trigger recovery if configured.
        
        Args:
            task_id: ID of the failed task
            error_message: Error message describing the failure
        """
        logger.info(f"Handling failure of task {task_id}: {error_message}")
        
        try:
            # Update task status to failed
            await self._update_task_status(task_id, "failed", error=error_message)
            
            # Remove from running tasks tracking
            if task_id in self.running_tasks:
                token = self.running_tasks[task_id]
                del self.running_tasks[task_id]
                if token in self.task_tokens:
                    del self.task_tokens[token]
            
            # Check for fallback tasks
            await self._handle_task_fallbacks(task_id)
            
            # Trigger cleanup tasks if configured
            await self._trigger_cleanup_tasks(task_id)
            
        except Exception as e:
            logger.error(f"Error handling task failure: {e}")

    async def update_task_status(self, task_id: str, status: str, **kwargs) -> None:
        """Update task status with additional metadata.
        
        Args:
            task_id: ID of the task to update
            status: New status for the task
            **kwargs: Additional properties to set
        """
        logger.info(f"Updating task {task_id} status to {status}")
        
        try:
            await self._update_task_status(task_id, status, **kwargs)
            
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            raise GraphOperationError(f"Failed to update task status: {e}")

    async def monitor_running_tasks(self) -> Dict[str, Any]:
        """Monitor all running tasks and update their status.
        
        Returns:
            Dictionary with monitoring results
        """
        logger.info("Monitoring running tasks")
        
        if not self.executor:
            return {
                "success": False,
                "error": "CommandExecutor not available"
            }
        
        try:
            monitoring_results = {
                "total_monitored": len(self.running_tasks),
                "completed_tasks": [],
                "failed_tasks": [],
                "still_running": [],
                "errors": []
            }
            
            # Check status of each running task
            for task_id, token in list(self.running_tasks.items()):
                try:
                    # Get process status from executor
                    status = await self.executor.get_process_status(token)
                    
                    if status["status"] == "completed":
                        if status.get("success", False):
                            await self.handle_task_completion(task_id)
                            monitoring_results["completed_tasks"].append({
                                "task_id": task_id,
                                "token": token,
                                "return_code": status.get("return_code", 0),
                                "duration": status.get("duration", 0)
                            })
                        else:
                            error_msg = status.get("error", "Unknown error")
                            await self.handle_task_failure(task_id, error_msg)
                            monitoring_results["failed_tasks"].append({
                                "task_id": task_id,
                                "token": token,
                                "error": error_msg,
                                "return_code": status.get("return_code", -1)
                            })
                    
                    elif status["status"] == "terminated":
                        await self.handle_task_failure(task_id, "Task was terminated")
                        monitoring_results["failed_tasks"].append({
                            "task_id": task_id,
                            "token": token,
                            "error": "Task was terminated"
                        })
                    
                    elif status["status"] == "running":
                        monitoring_results["still_running"].append({
                            "task_id": task_id,
                            "token": token,
                            "runtime": status.get("runtime", 0)
                        })
                    
                    else:
                        # Handle other statuses (timeout, error, etc.)
                        error_msg = f"Unexpected status: {status['status']}"
                        await self.handle_task_failure(task_id, error_msg)
                        monitoring_results["failed_tasks"].append({
                            "task_id": task_id,
                            "token": token,
                            "error": error_msg
                        })
                
                except Exception as e:
                    monitoring_results["errors"].append(f"Error monitoring task {task_id}: {e}")
            
            logger.info(f"Monitoring complete: {monitoring_results}")
            return {
                "success": True,
                "results": monitoring_results
            }
            
        except Exception as e:
            logger.error(f"Error monitoring running tasks: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_execution_status(self) -> Dict[str, Any]:
        """Get comprehensive execution status.
        
        Returns:
            Dictionary with execution status information
        """
        logger.info("Getting execution status")
        
        try:
            # Get task counts by status
            status_query = """
            MATCH (t:Task)
            RETURN t.status as status, count(t) as count
            """
            
            result = await self.graph.client.execute_query(status_query)
            task_counts = {}
            for record in result.records:
                task_counts[record["status"] or "unknown"] = record["count"]
            
            # Get ready tasks
            ready_tasks = await self.scheduler.find_ready_tasks()
            
            # Get running task details
            running_task_details = []
            for task_id, token in self.running_tasks.items():
                task = await self.graph.node_manager.get_node(task_id)
                if task:
                    running_task_details.append({
                        "task_id": task_id,
                        "task_name": task.get_property("name", "Unknown"),
                        "token": token,
                        "started_at": task.get_property("started_at")
                    })
            
            return {
                "task_counts": task_counts,
                "ready_tasks_count": len(ready_tasks),
                "running_tasks_count": len(self.running_tasks),
                "ready_tasks": ready_tasks[:10],  # Limit to first 10
                "running_tasks": running_task_details,
                "executor_available": self.executor is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting execution status: {e}")
            return {
                "error": str(e)
            }

    # Helper methods

    async def _execute_task(self, task_id: str, command: str) -> Dict[str, Any]:
        """Execute a single task using the command executor."""
        try:
            # Update task status to running
            await self._update_task_status(task_id, "running", 
                                         started_at=datetime.utcnow().isoformat())
            
            # Execute command asynchronously
            execution_result = await self.executor.execute_async(command)
            
            if execution_result.get("status") == "running":
                token = execution_result["token"]
                
                # Track the running task
                self.running_tasks[task_id] = token
                self.task_tokens[token] = task_id
                
                return {
                    "task_id": task_id,
                    "token": token,
                    "status": "started",
                    "command": command
                }
            else:
                # Immediate failure
                await self._update_task_status(task_id, "failed", 
                                             error=execution_result.get("error", "Unknown error"))
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "error": execution_result.get("error", "Unknown error")
                }
                
        except Exception as e:
            await self._update_task_status(task_id, "failed", error=str(e))
            raise

    async def _update_task_status(self, task_id: str, status: str, **kwargs) -> None:
        """Update task status in the graph."""
        try:
            task = await self.graph.node_manager.get_node(task_id)
            if task:
                task.set_property("status", status)
                task.set_property("updated_at", datetime.utcnow().isoformat())
                
                # Set additional properties
                for key, value in kwargs.items():
                    task.set_property(key, value)
                
                await self.graph.node_manager.update_node(task)
            
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            raise

    async def _get_running_tasks_from_graph(self) -> List[str]:
        """Get list of tasks marked as running in the graph."""
        try:
            query = """
            MATCH (t:Task)
            WHERE t.status = 'running'
            RETURN t.id as task_id
            """
            
            result = await self.graph.client.execute_query(query)
            return [record["task_id"] for record in result.records]
            
        except Exception as e:
            logger.error(f"Error getting running tasks from graph: {e}")
            return []

    async def _find_newly_ready_tasks(self, completed_task_id: str) -> List[str]:
        """Find tasks that became ready after a task completion."""
        try:
            # Find tasks that depend on the completed task
            query = """
            MATCH (dependent:Task)-[:DEPENDS_ON]->(completed:Task {id: $completed_task_id})
            WHERE dependent.status = 'pending'
            AND NOT EXISTS {
                MATCH (dependent)-[:DEPENDS_ON]->(other:Task)
                WHERE other.status <> 'completed' AND other.id <> $completed_task_id
            }
            RETURN dependent.id as task_id
            """
            
            result = await self.graph.client.execute_query(
                query, 
                parameters={"completed_task_id": completed_task_id}
            )
            
            return [record["task_id"] for record in result.records]
            
        except Exception as e:
            logger.error(f"Error finding newly ready tasks: {e}")
            return []

    async def _handle_task_fallbacks(self, failed_task_id: str) -> None:
        """Handle fallback tasks for a failed task."""
        try:
            # Find fallback tasks
            query = """
            MATCH (fallback:Task)-[:FALLBACK_FOR]->(failed:Task {id: $failed_task_id})
            WHERE fallback.status = 'pending'
            RETURN fallback.id as fallback_id
            """
            
            result = await self.graph.client.execute_query(
                query,
                parameters={"failed_task_id": failed_task_id}
            )
            
            # Execute fallback tasks
            for record in result.records:
                fallback_id = record["fallback_id"]
                logger.info(f"Triggering fallback task {fallback_id} for failed task {failed_task_id}")
                
                # Update fallback task to ready status
                await self._update_task_status(fallback_id, "pending")
                
        except Exception as e:
            logger.error(f"Error handling task fallbacks: {e}")

    async def _trigger_cleanup_tasks(self, failed_task_id: str) -> None:
        """Trigger cleanup tasks for a failed task."""
        try:
            # Find cleanup tasks
            query = """
            MATCH (cleanup:Task)-[:CLEANUP_FOR]->(failed:Task {id: $failed_task_id})
            WHERE cleanup.status = 'pending'
            RETURN cleanup.id as cleanup_id
            """
            
            result = await self.graph.client.execute_query(
                query,
                parameters={"failed_task_id": failed_task_id}
            )
            
            # Execute cleanup tasks immediately
            for record in result.records:
                cleanup_id = record["cleanup_id"]
                logger.info(f"Triggering cleanup task {cleanup_id} for failed task {failed_task_id}")
                
                cleanup_task = await self.graph.node_manager.get_node(cleanup_id)
                if cleanup_task:
                    command = cleanup_task.get_property("command")
                    if command:
                        await self._execute_task(cleanup_id, command)
                
        except Exception as e:
            logger.error(f"Error triggering cleanup tasks: {e}")

    async def create_task_from_command(self, 
                                     task_id: str,
                                     command: str,
                                     name: str,
                                     dependencies: Optional[List[str]] = None,
                                     priority: int = 5,
                                     estimated_duration: Optional[int] = None) -> Dict[str, Any]:
        """Create a new task in the graph from a command.
        
        Args:
            task_id: Unique task identifier
            command: Command to execute
            name: Human-readable task name
            dependencies: List of task IDs this task depends on
            priority: Task priority (lower = higher priority)
            estimated_duration: Estimated duration in seconds
            
        Returns:
            Dictionary with task creation results
        """
        logger.info(f"Creating task {task_id} with command: {command}")
        
        try:
            # Create task node
            task = GraphNode(
                id=task_id,
                labels=["Task"],
                properties={
                    "name": name,
                    "command": command,
                    "status": "pending",
                    "priority": priority,
                    "estimated_duration": estimated_duration,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            await self.graph.node_manager.create_node(task)
            
            # Create dependency relationships
            dependencies_created = 0
            if dependencies:
                for dep_task_id in dependencies:
                    dependency = GraphRelationship(
                        type="DEPENDS_ON",
                        start_node_id=task_id,
                        end_node_id=dep_task_id,
                        properties={
                            "dependency_type": "prerequisite",
                            "created_at": datetime.utcnow().isoformat()
                        }
                    )
                    
                    await self.graph.relationship_manager.create_relationship(dependency)
                    dependencies_created += 1
            
            return {
                "success": True,
                "task_id": task_id,
                "dependencies_created": dependencies_created,
                "is_ready": len(dependencies or []) == 0
            }
            
        except Exception as e:
            logger.error(f"Error creating task from command: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_workflow(self, workflow_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a complete workflow of tasks.
        
        Args:
            workflow_tasks: List of task definitions with commands and dependencies
            
        Returns:
            Dictionary with workflow execution results
        """
        logger.info(f"Executing workflow with {len(workflow_tasks)} tasks")
        
        try:
            # Create all tasks first
            created_tasks = []
            for task_def in workflow_tasks:
                result = await self.create_task_from_command(
                    task_id=task_def["task_id"],
                    command=task_def["command"],
                    name=task_def.get("name", task_def["task_id"]),
                    dependencies=task_def.get("dependencies", []),
                    priority=task_def.get("priority", 5),
                    estimated_duration=task_def.get("estimated_duration")
                )
                
                if result["success"]:
                    created_tasks.append(task_def["task_id"])
            
            # Start executing ready tasks
            execution_result = await self.execute_ready_tasks()
            
            return {
                "success": True,
                "workflow_tasks": len(workflow_tasks),
                "created_tasks": len(created_tasks),
                "initial_execution": execution_result
            }
            
        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            return {
                "success": False,
                "error": str(e)
            } 