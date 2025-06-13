"""Task scheduler for graph-based task management.

This module provides utilities for finding schedulable tasks, resolving dependencies,
detecting conflicts, and managing task execution order based on graph relationships.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict, deque

from ..graph_manager import GraphManager
from ..models import GraphNode, GraphRelationship
from ..exceptions import GraphOperationError

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Advanced task scheduler for graph-based task management."""

    def __init__(self, graph_manager: GraphManager):
        """Initialize with graph manager.
        
        Args:
            graph_manager: GraphManager instance for graph operations
        """
        self.graph = graph_manager

    async def find_ready_tasks(self, max_tasks: Optional[int] = None) -> List[str]:
        """Find tasks that can be executed (no blocking dependencies).
        
        Args:
            max_tasks: Maximum number of tasks to return (None for all)
            
        Returns:
            List of task IDs ready for execution
        """
        logger.info(f"Finding ready tasks (max: {max_tasks})")
        
        try:
            query = """
            MATCH (t:Task)
            WHERE t.status = 'pending'
            AND NOT EXISTS {
                MATCH (t)-[:DEPENDS_ON]->(dep:Task)
                WHERE dep.status <> 'completed'
            }
            RETURN t.id as task_id, t.priority as priority, t.deadline as deadline
            ORDER BY 
                CASE WHEN t.priority IS NOT NULL THEN t.priority ELSE 999 END ASC,
                CASE WHEN t.deadline IS NOT NULL THEN datetime(t.deadline) ELSE datetime('9999-12-31T23:59:59Z') END ASC
            """
            
            if max_tasks:
                query += f" LIMIT {max_tasks}"
            
            result = await self.graph.client.execute_query(query)
            ready_tasks = [record["task_id"] for record in result.records]
            
            logger.info(f"Found {len(ready_tasks)} ready tasks")
            return ready_tasks
            
        except Exception as e:
            logger.error(f"Error finding ready tasks: {e}")
            raise GraphOperationError(f"Failed to find ready tasks: {e}")

    async def detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies in task graph.
        
        Returns:
            List of cycles, where each cycle is a list of task IDs
        """
        logger.info("Detecting circular dependencies")
        
        try:
            # Use Neo4j's path finding to detect cycles
            query = """
            MATCH (start:Task)
            MATCH path = (start)-[:DEPENDS_ON*1..10]->(start)
            RETURN [n in nodes(path) | n.id] as cycle
            """
            
            result = await self.graph.client.execute_query(query)
            cycles = []
            
            for record in result.records:
                cycle = record["cycle"]
                if cycle and len(cycle) > 1:
                    # Remove duplicate start node at the end
                    if cycle[0] == cycle[-1]:
                        cycle = cycle[:-1]
                    cycles.append(cycle)
            
            logger.info(f"Found {len(cycles)} circular dependencies")
            return cycles
            
        except Exception as e:
            logger.error(f"Error detecting circular dependencies: {e}")
            raise GraphOperationError(f"Failed to detect circular dependencies: {e}")

    async def calculate_critical_path(self, start_task: str, end_task: str) -> List[str]:
        """Calculate the critical path between tasks.
        
        Args:
            start_task: Starting task ID
            end_task: Ending task ID
            
        Returns:
            List of task IDs representing the critical path
        """
        logger.info(f"Calculating critical path from {start_task} to {end_task}")
        
        try:
            # Find the longest path (by duration) between start and end tasks
            query = """
            MATCH (start:Task {id: $start_task}), (end:Task {id: $end_task})
            MATCH path = (start)-[:DEPENDS_ON*]->(end)
            WITH path, reduce(duration = 0, n in nodes(path) | 
                duration + CASE WHEN n.estimated_duration IS NOT NULL 
                          THEN n.estimated_duration ELSE 0 END) as total_duration
            ORDER BY total_duration DESC
            LIMIT 1
            RETURN [n in nodes(path) | n.id] as critical_path, total_duration
            """
            
            result = await self.graph.client.execute_query(
                query, 
                parameters={"start_task": start_task, "end_task": end_task}
            )
            
            if result.records:
                critical_path = result.records[0]["critical_path"]
                total_duration = result.records[0]["total_duration"]
                logger.info(f"Critical path found with duration {total_duration}: {critical_path}")
                return critical_path
            else:
                logger.warning(f"No path found between {start_task} and {end_task}")
                return []
                
        except Exception as e:
            logger.error(f"Error calculating critical path: {e}")
            raise GraphOperationError(f"Failed to calculate critical path: {e}")

    async def check_resource_conflicts(self) -> List[Dict[str, Any]]:
        """Check for resource allocation conflicts.
        
        Returns:
            List of resource conflicts with details
        """
        logger.info("Checking resource conflicts")
        
        try:
            # Find tasks that require the same resources and might conflict
            query = """
            MATCH (t1:Task)-[r1:REQUIRES|CAN_USE]->(res:Resource)<-[r2:REQUIRES|CAN_USE]-(t2:Task)
            WHERE t1.id <> t2.id 
            AND t1.status = 'pending' AND t2.status = 'pending'
            WITH res, t1, t2, type(r1) as rel1_type, type(r2) as rel2_type
            WHERE rel1_type = 'REQUIRES' OR rel2_type = 'REQUIRES'
            RETURN res.id as resource_id, 
                   res.name as resource_name,
                   t1.id as task1_id, 
                   t1.name as task1_name,
                   t1.cpu_required as task1_cpu,
                   t1.memory_required_gb as task1_memory,
                   t2.id as task2_id,
                   t2.name as task2_name, 
                   t2.cpu_required as task2_cpu,
                   t2.memory_required_gb as task2_memory,
                   res.cpu_cores as resource_cpu,
                   res.memory_gb as resource_memory
            """
            
            result = await self.graph.client.execute_query(query)
            conflicts = []
            
            for record in result.records:
                # Check if resource requirements exceed capacity
                task1_cpu = record.get("task1_cpu", 0) or 0
                task1_memory = record.get("task1_memory", 0) or 0
                task2_cpu = record.get("task2_cpu", 0) or 0
                task2_memory = record.get("task2_memory", 0) or 0
                resource_cpu = record.get("resource_cpu", 0) or 0
                resource_memory = record.get("resource_memory", 0) or 0
                
                cpu_conflict = (task1_cpu + task2_cpu) > resource_cpu
                memory_conflict = (task1_memory + task2_memory) > resource_memory
                
                if cpu_conflict or memory_conflict:
                    conflicts.append({
                        "resource_id": record["resource_id"],
                        "resource_name": record["resource_name"],
                        "conflicting_tasks": [
                            {
                                "task_id": record["task1_id"],
                                "task_name": record["task1_name"],
                                "cpu_required": task1_cpu,
                                "memory_required": task1_memory
                            },
                            {
                                "task_id": record["task2_id"],
                                "task_name": record["task2_name"],
                                "cpu_required": task2_cpu,
                                "memory_required": task2_memory
                            }
                        ],
                        "resource_capacity": {
                            "cpu_cores": resource_cpu,
                            "memory_gb": resource_memory
                        },
                        "conflict_types": {
                            "cpu_conflict": cpu_conflict,
                            "memory_conflict": memory_conflict
                        }
                    })
            
            logger.info(f"Found {len(conflicts)} resource conflicts")
            return conflicts
            
        except Exception as e:
            logger.error(f"Error checking resource conflicts: {e}")
            raise GraphOperationError(f"Failed to check resource conflicts: {e}")

    async def get_task_execution_order(self, 
                                     consider_priority: bool = True,
                                     consider_deadlines: bool = True,
                                     consider_resources: bool = True) -> List[Dict[str, Any]]:
        """Get recommended task execution order.
        
        Args:
            consider_priority: Whether to consider task priorities
            consider_deadlines: Whether to consider task deadlines
            consider_resources: Whether to consider resource constraints
            
        Returns:
            List of task execution recommendations with metadata
        """
        logger.info("Calculating task execution order")
        
        try:
            # Build comprehensive query considering all factors
            query_parts = [
                "MATCH (t:Task)",
                "WHERE t.status = 'pending'",
                "AND NOT EXISTS {",
                "  MATCH (t)-[:DEPENDS_ON]->(dep:Task)",
                "  WHERE dep.status <> 'completed'",
                "}"
            ]
            
            # Add resource information if needed
            if consider_resources:
                query_parts.extend([
                    "OPTIONAL MATCH (t)-[:REQUIRES|CAN_USE]->(res:Resource)",
                    "WITH t, collect(res) as resources"
                ])
            
            # Build return clause with ordering
            return_parts = [
                "RETURN t.id as task_id,",
                "       t.name as task_name,",
                "       t.priority as priority,",
                "       t.deadline as deadline,",
                "       t.estimated_duration as estimated_duration"
            ]
            
            if consider_resources:
                return_parts.append("       , resources")
            
            # Build ordering clause
            order_parts = ["ORDER BY"]
            order_conditions = []
            
            if consider_priority:
                order_conditions.append("CASE WHEN t.priority IS NOT NULL THEN t.priority ELSE 999 END ASC")
            
            if consider_deadlines:
                order_conditions.append("CASE WHEN t.deadline IS NOT NULL THEN datetime(t.deadline) ELSE datetime('9999-12-31T23:59:59Z') END ASC")
            
            # Add duration as tiebreaker
            order_conditions.append("CASE WHEN t.estimated_duration IS NOT NULL THEN t.estimated_duration ELSE 0 END ASC")
            
            order_parts.append(", ".join(order_conditions))
            
            # Combine query parts
            query = " ".join(query_parts + return_parts + order_parts)
            
            result = await self.graph.client.execute_query(query)
            
            execution_order = []
            for record in result.records:
                task_info = {
                    "task_id": record["task_id"],
                    "task_name": record["task_name"],
                    "priority": record.get("priority"),
                    "deadline": record.get("deadline"),
                    "estimated_duration": record.get("estimated_duration"),
                    "scheduling_score": self._calculate_scheduling_score(record, consider_priority, consider_deadlines)
                }
                
                if consider_resources and "resources" in record:
                    task_info["required_resources"] = [
                        {"id": res.get("id"), "type": res.get("type")} 
                        for res in record["resources"] if res
                    ]
                
                execution_order.append(task_info)
            
            logger.info(f"Generated execution order for {len(execution_order)} tasks")
            return execution_order
            
        except Exception as e:
            logger.error(f"Error calculating task execution order: {e}")
            raise GraphOperationError(f"Failed to calculate task execution order: {e}")

    async def find_parallel_execution_groups(self) -> List[List[str]]:
        """Find groups of tasks that can be executed in parallel.
        
        Returns:
            List of parallel execution groups (each group is a list of task IDs)
        """
        logger.info("Finding parallel execution groups")
        
        try:
            # Find tasks at the same dependency level that don't conflict
            ready_tasks = await self.find_ready_tasks()
            
            if not ready_tasks:
                return []
            
            # Check for resource conflicts among ready tasks
            conflicts = await self.check_resource_conflicts()
            
            # Build conflict graph
            conflict_graph = defaultdict(set)
            for conflict in conflicts:
                tasks = [task["task_id"] for task in conflict["conflicting_tasks"]]
                if len(tasks) >= 2:
                    for i, task1 in enumerate(tasks):
                        for task2 in tasks[i+1:]:
                            if task1 in ready_tasks and task2 in ready_tasks:
                                conflict_graph[task1].add(task2)
                                conflict_graph[task2].add(task1)
            
            # Find parallel groups using graph coloring approach
            parallel_groups = []
            remaining_tasks = set(ready_tasks)
            
            while remaining_tasks:
                current_group = []
                used_in_group = set()
                
                for task in list(remaining_tasks):
                    # Check if task conflicts with any task already in current group
                    if not any(conflicting_task in used_in_group 
                             for conflicting_task in conflict_graph[task]):
                        current_group.append(task)
                        used_in_group.add(task)
                        remaining_tasks.remove(task)
                
                if current_group:
                    parallel_groups.append(current_group)
                else:
                    # Fallback: add remaining tasks one by one
                    task = remaining_tasks.pop()
                    parallel_groups.append([task])
            
            logger.info(f"Found {len(parallel_groups)} parallel execution groups")
            return parallel_groups
            
        except Exception as e:
            logger.error(f"Error finding parallel execution groups: {e}")
            raise GraphOperationError(f"Failed to find parallel execution groups: {e}")

    async def estimate_completion_time(self, task_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Estimate completion time for tasks considering dependencies and parallelism.
        
        Args:
            task_ids: Specific task IDs to estimate (None for all pending tasks)
            
        Returns:
            Dictionary with completion time estimates
        """
        logger.info("Estimating completion time")
        
        try:
            # Get all pending tasks if none specified
            if task_ids is None:
                query = """
                MATCH (t:Task)
                WHERE t.status = 'pending'
                RETURN t.id as task_id
                """
                result = await self.graph.client.execute_query(query)
                task_ids = [record["task_id"] for record in result.records]
            
            if not task_ids:
                return {
                    "total_tasks": 0,
                    "estimated_completion_time": 0,
                    "critical_path_duration": 0,
                    "parallel_efficiency": 1.0
                }
            
            # Calculate critical path duration
            critical_path_duration = await self._calculate_critical_path_duration(task_ids)
            
            # Calculate total duration if executed sequentially
            sequential_duration = await self._calculate_sequential_duration(task_ids)
            
            # Find parallel execution groups
            parallel_groups = await self.find_parallel_execution_groups()
            
            # Calculate parallel execution duration
            parallel_duration = 0
            for group in parallel_groups:
                group_tasks = [tid for tid in group if tid in task_ids]
                if group_tasks:
                    group_duration = await self._calculate_group_duration(group_tasks)
                    parallel_duration += group_duration
            
            # Calculate efficiency metrics
            parallel_efficiency = sequential_duration / parallel_duration if parallel_duration > 0 else 1.0
            
            return {
                "total_tasks": len(task_ids),
                "estimated_completion_time": max(critical_path_duration, parallel_duration),
                "critical_path_duration": critical_path_duration,
                "sequential_duration": sequential_duration,
                "parallel_duration": parallel_duration,
                "parallel_efficiency": parallel_efficiency,
                "parallel_groups_count": len(parallel_groups),
                "average_group_size": sum(len(group) for group in parallel_groups) / len(parallel_groups) if parallel_groups else 0
            }
            
        except Exception as e:
            logger.error(f"Error estimating completion time: {e}")
            raise GraphOperationError(f"Failed to estimate completion time: {e}")

    async def schedule_tasks_with_resources(self, 
                                          available_resources: List[str],
                                          time_window: Optional[int] = None) -> Dict[str, Any]:
        """Schedule tasks considering available resources and time constraints.
        
        Args:
            available_resources: List of available resource IDs
            time_window: Time window in seconds (None for no limit)
            
        Returns:
            Dictionary with scheduling plan
        """
        logger.info(f"Scheduling tasks with {len(available_resources)} resources")
        
        try:
            # Get ready tasks
            ready_tasks = await self.find_ready_tasks()
            
            if not ready_tasks:
                return {
                    "scheduled_tasks": [],
                    "resource_allocation": {},
                    "estimated_duration": 0,
                    "resource_utilization": {}
                }
            
            # Get task resource requirements
            task_requirements = await self._get_task_resource_requirements(ready_tasks)
            
            # Get resource capacities
            resource_capacities = await self._get_resource_capacities(available_resources)
            
            # Schedule tasks using resource-aware algorithm
            schedule = await self._create_resource_aware_schedule(
                ready_tasks, task_requirements, resource_capacities, time_window
            )
            
            return schedule
            
        except Exception as e:
            logger.error(f"Error scheduling tasks with resources: {e}")
            raise GraphOperationError(f"Failed to schedule tasks with resources: {e}")

    async def get_scheduling_metrics(self) -> Dict[str, Any]:
        """Get comprehensive scheduling metrics.
        
        Returns:
            Dictionary with various scheduling metrics
        """
        logger.info("Calculating scheduling metrics")
        
        try:
            # Get basic task counts
            task_counts = await self._get_task_status_counts()
            
            # Get dependency metrics
            dependency_metrics = await self._get_dependency_metrics()
            
            # Get resource metrics
            resource_metrics = await self._get_resource_metrics()
            
            # Get timing metrics
            timing_metrics = await self._get_timing_metrics()
            
            return {
                "task_counts": task_counts,
                "dependency_metrics": dependency_metrics,
                "resource_metrics": resource_metrics,
                "timing_metrics": timing_metrics,
                "overall_health": self._calculate_overall_health(
                    task_counts, dependency_metrics, resource_metrics, timing_metrics
                )
            }
            
        except Exception as e:
            logger.error(f"Error calculating scheduling metrics: {e}")
            raise GraphOperationError(f"Failed to calculate scheduling metrics: {e}")

    # Helper methods

    def _calculate_scheduling_score(self, record: Dict[str, Any], 
                                  consider_priority: bool, 
                                  consider_deadlines: bool) -> float:
        """Calculate a scheduling score for a task."""
        score = 0.0
        
        if consider_priority and record.get("priority"):
            # Lower priority number = higher score
            score += (10 - record["priority"]) * 10
        
        if consider_deadlines and record.get("deadline"):
            try:
                deadline = datetime.fromisoformat(record["deadline"].replace('Z', '+00:00'))
                time_to_deadline = (deadline - datetime.utcnow()).total_seconds()
                # Closer deadline = higher score
                if time_to_deadline > 0:
                    score += 1000 / (time_to_deadline / 3600)  # Hours to deadline
            except:
                pass
        
        return score

    async def _calculate_critical_path_duration(self, task_ids: List[str]) -> int:
        """Calculate the duration of the critical path."""
        try:
            query = """
            MATCH (t:Task)
            WHERE t.id IN $task_ids AND t.status = 'pending'
            WITH collect(t) as tasks
            UNWIND tasks as start_task
            UNWIND tasks as end_task
            WHERE start_task <> end_task
            MATCH path = (start_task)-[:DEPENDS_ON*]->(end_task)
            WITH path, reduce(duration = 0, n in nodes(path) | 
                duration + CASE WHEN n.estimated_duration IS NOT NULL 
                          THEN n.estimated_duration ELSE 0 END) as total_duration
            RETURN max(total_duration) as max_duration
            """
            
            result = await self.graph.client.execute_query(query, parameters={"task_ids": task_ids})
            if result.records and result.records[0]["max_duration"]:
                return result.records[0]["max_duration"]
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating critical path duration: {e}")
            return 0

    async def _calculate_sequential_duration(self, task_ids: List[str]) -> int:
        """Calculate total duration if tasks are executed sequentially."""
        try:
            query = """
            MATCH (t:Task)
            WHERE t.id IN $task_ids AND t.status = 'pending'
            RETURN sum(CASE WHEN t.estimated_duration IS NOT NULL 
                           THEN t.estimated_duration ELSE 0 END) as total_duration
            """
            
            result = await self.graph.client.execute_query(query, parameters={"task_ids": task_ids})
            if result.records:
                return result.records[0]["total_duration"] or 0
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating sequential duration: {e}")
            return 0

    async def _calculate_group_duration(self, group_task_ids: List[str]) -> int:
        """Calculate duration for a group of parallel tasks (max duration in group)."""
        try:
            query = """
            MATCH (t:Task)
            WHERE t.id IN $task_ids
            RETURN max(CASE WHEN t.estimated_duration IS NOT NULL 
                           THEN t.estimated_duration ELSE 0 END) as max_duration
            """
            
            result = await self.graph.client.execute_query(query, parameters={"task_ids": group_task_ids})
            if result.records:
                return result.records[0]["max_duration"] or 0
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating group duration: {e}")
            return 0

    async def _get_task_resource_requirements(self, task_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get resource requirements for tasks."""
        try:
            query = """
            MATCH (t:Task)-[r:REQUIRES|CAN_USE]->(res:Resource)
            WHERE t.id IN $task_ids
            RETURN t.id as task_id, 
                   res.id as resource_id,
                   type(r) as relationship_type,
                   t.cpu_required as cpu_required,
                   t.memory_required_gb as memory_required
            """
            
            result = await self.graph.client.execute_query(query, parameters={"task_ids": task_ids})
            
            requirements = defaultdict(lambda: {"resources": [], "cpu": 0, "memory": 0})
            for record in result.records:
                task_id = record["task_id"]
                requirements[task_id]["resources"].append({
                    "resource_id": record["resource_id"],
                    "relationship_type": record["relationship_type"]
                })
                requirements[task_id]["cpu"] = record.get("cpu_required", 0) or 0
                requirements[task_id]["memory"] = record.get("memory_required", 0) or 0
            
            return dict(requirements)
            
        except Exception as e:
            logger.error(f"Error getting task resource requirements: {e}")
            return {}

    async def _get_resource_capacities(self, resource_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get resource capacities."""
        try:
            query = """
            MATCH (res:Resource)
            WHERE res.id IN $resource_ids
            RETURN res.id as resource_id,
                   res.cpu_cores as cpu_cores,
                   res.memory_gb as memory_gb,
                   res.status as status
            """
            
            result = await self.graph.client.execute_query(query, parameters={"resource_ids": resource_ids})
            
            capacities = {}
            for record in result.records:
                capacities[record["resource_id"]] = {
                    "cpu_cores": record.get("cpu_cores", 0) or 0,
                    "memory_gb": record.get("memory_gb", 0) or 0,
                    "status": record.get("status", "unknown")
                }
            
            return capacities
            
        except Exception as e:
            logger.error(f"Error getting resource capacities: {e}")
            return {}

    async def _create_resource_aware_schedule(self, 
                                            task_ids: List[str],
                                            task_requirements: Dict[str, Dict[str, Any]],
                                            resource_capacities: Dict[str, Dict[str, Any]],
                                            time_window: Optional[int]) -> Dict[str, Any]:
        """Create a resource-aware schedule."""
        # Simplified scheduling algorithm
        scheduled_tasks = []
        resource_allocation = {}
        current_time = 0
        
        # Sort tasks by priority and resource requirements
        sorted_tasks = sorted(task_ids, key=lambda t: (
            task_requirements.get(t, {}).get("cpu", 0),
            task_requirements.get(t, {}).get("memory", 0)
        ))
        
        for task_id in sorted_tasks:
            task_req = task_requirements.get(task_id, {})
            
            # Find suitable resource
            suitable_resource = None
            for res_id, capacity in resource_capacities.items():
                if (capacity["cpu_cores"] >= task_req.get("cpu", 0) and
                    capacity["memory_gb"] >= task_req.get("memory", 0) and
                    capacity["status"] == "available"):
                    suitable_resource = res_id
                    break
            
            if suitable_resource:
                scheduled_tasks.append({
                    "task_id": task_id,
                    "resource_id": suitable_resource,
                    "start_time": current_time,
                    "estimated_duration": task_req.get("duration", 0)
                })
                resource_allocation[task_id] = suitable_resource
                
                # Update resource availability (simplified)
                resource_capacities[suitable_resource]["status"] = "allocated"
        
        return {
            "scheduled_tasks": scheduled_tasks,
            "resource_allocation": resource_allocation,
            "estimated_duration": current_time,
            "resource_utilization": len(resource_allocation) / len(resource_capacities) if resource_capacities else 0
        }

    async def _get_task_status_counts(self) -> Dict[str, int]:
        """Get counts of tasks by status."""
        try:
            query = """
            MATCH (t:Task)
            RETURN t.status as status, count(t) as count
            """
            
            result = await self.graph.client.execute_query(query)
            counts = {}
            for record in result.records:
                counts[record["status"] or "unknown"] = record["count"]
            
            return counts
            
        except Exception as e:
            logger.error(f"Error getting task status counts: {e}")
            return {}

    async def _get_dependency_metrics(self) -> Dict[str, Any]:
        """Get dependency-related metrics."""
        try:
            query = """
            MATCH (t:Task)
            OPTIONAL MATCH (t)-[:DEPENDS_ON]->(dep:Task)
            WITH t, count(dep) as dep_count
            RETURN avg(dep_count) as avg_dependencies,
                   max(dep_count) as max_dependencies,
                   count(CASE WHEN dep_count = 0 THEN 1 END) as tasks_without_deps
            """
            
            result = await self.graph.client.execute_query(query)
            if result.records:
                record = result.records[0]
                return {
                    "average_dependencies": record.get("avg_dependencies", 0) or 0,
                    "max_dependencies": record.get("max_dependencies", 0) or 0,
                    "tasks_without_dependencies": record.get("tasks_without_deps", 0) or 0
                }
            return {}
            
        except Exception as e:
            logger.error(f"Error getting dependency metrics: {e}")
            return {}

    async def _get_resource_metrics(self) -> Dict[str, Any]:
        """Get resource-related metrics."""
        try:
            query = """
            MATCH (res:Resource)
            OPTIONAL MATCH (t:Task)-[:REQUIRES|CAN_USE]->(res)
            WHERE t.status = 'pending'
            WITH res, count(t) as pending_tasks
            RETURN count(res) as total_resources,
                   avg(pending_tasks) as avg_pending_per_resource,
                   max(pending_tasks) as max_pending_per_resource
            """
            
            result = await self.graph.client.execute_query(query)
            if result.records:
                record = result.records[0]
                return {
                    "total_resources": record.get("total_resources", 0) or 0,
                    "average_pending_per_resource": record.get("avg_pending_per_resource", 0) or 0,
                    "max_pending_per_resource": record.get("max_pending_per_resource", 0) or 0
                }
            return {}
            
        except Exception as e:
            logger.error(f"Error getting resource metrics: {e}")
            return {}

    async def _get_timing_metrics(self) -> Dict[str, Any]:
        """Get timing-related metrics."""
        try:
            current_time = datetime.utcnow()
            
            query = """
            MATCH (t:Task)
            WHERE t.status = 'pending'
            RETURN count(CASE WHEN t.deadline IS NOT NULL AND datetime(t.deadline) < datetime() THEN 1 END) as overdue_tasks,
                   count(CASE WHEN t.deadline IS NOT NULL THEN 1 END) as tasks_with_deadlines,
                   avg(CASE WHEN t.estimated_duration IS NOT NULL THEN t.estimated_duration END) as avg_duration
            """
            
            result = await self.graph.client.execute_query(query)
            if result.records:
                record = result.records[0]
                return {
                    "overdue_tasks": record.get("overdue_tasks", 0) or 0,
                    "tasks_with_deadlines": record.get("tasks_with_deadlines", 0) or 0,
                    "average_duration": record.get("avg_duration", 0) or 0
                }
            return {}
            
        except Exception as e:
            logger.error(f"Error getting timing metrics: {e}")
            return {}

    def _calculate_overall_health(self, task_counts: Dict[str, int],
                                dependency_metrics: Dict[str, Any],
                                resource_metrics: Dict[str, Any],
                                timing_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall scheduling health score."""
        health_score = 100.0
        issues = []
        
        # Check for overdue tasks
        overdue_tasks = timing_metrics.get("overdue_tasks", 0)
        if overdue_tasks > 0:
            health_score -= min(overdue_tasks * 10, 30)
            issues.append(f"{overdue_tasks} overdue tasks")
        
        # Check for blocked tasks
        pending_tasks = task_counts.get("pending", 0)
        if pending_tasks > 50:
            health_score -= 20
            issues.append(f"High number of pending tasks ({pending_tasks})")
        
        # Check for resource contention
        max_pending_per_resource = resource_metrics.get("max_pending_per_resource", 0)
        if max_pending_per_resource > 10:
            health_score -= 15
            issues.append(f"Resource contention detected")
        
        # Check for complex dependencies
        max_dependencies = dependency_metrics.get("max_dependencies", 0)
        if max_dependencies > 5:
            health_score -= 10
            issues.append(f"Complex dependency chains detected")
        
        health_score = max(0, health_score)
        
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 70:
            status = "good"
        elif health_score >= 50:
            status = "fair"
        else:
            status = "poor"
        
        return {
            "health_score": health_score,
            "status": status,
            "issues": issues
        } 