"""Basic usage examples for the Neo4j graph interface.

This module provides simple, easy-to-understand examples for getting started
with the graph interface for task management.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any

from ..graph_manager import GraphManager
from ..models import GraphNode, GraphRelationship
from ..exceptions import GraphOperationError

logger = logging.getLogger(__name__)


class BasicUsageExample:
    """Simple examples for getting started with graph-based task management."""

    def __init__(self, graph_manager: GraphManager):
        """Initialize with graph manager.
        
        Args:
            graph_manager: GraphManager instance for graph operations
        """
        self.graph = graph_manager

    async def create_simple_task(self) -> Dict[str, Any]:
        """Create a simple task node.
        
        Returns:
            Dictionary with task creation results
        """
        logger.info("Creating simple task")
        
        try:
            # Create a basic task
            task = GraphNode(
                id="my-first-task",
                labels=["Task"],
                properties={
                    "name": "My First Task",
                    "description": "A simple example task",
                    "status": "pending",
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            # Add task to graph
            await self.graph.node_manager.create_node(task)
            
            # Verify task was created
            retrieved_task = await self.graph.node_manager.get_node("my-first-task")
            
            return {
                "success": True,
                "task_id": task.id,
                "task_created": retrieved_task is not None,
                "task_properties": retrieved_task.properties if retrieved_task else None
            }
            
        except Exception as e:
            logger.error(f"Error creating simple task: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def create_task_with_dependency(self) -> Dict[str, Any]:
        """Create two tasks with a dependency relationship.
        
        Returns:
            Dictionary with dependency creation results
        """
        logger.info("Creating tasks with dependency")
        
        try:
            # Create first task
            task_a = GraphNode(
                id="task-a",
                labels=["Task"],
                properties={
                    "name": "Task A",
                    "description": "First task that must complete before Task B",
                    "status": "pending",
                    "estimated_duration": 300
                }
            )
            
            # Create second task
            task_b = GraphNode(
                id="task-b", 
                labels=["Task"],
                properties={
                    "name": "Task B",
                    "description": "Second task that depends on Task A",
                    "status": "pending",
                    "estimated_duration": 180
                }
            )
            
            # Add tasks to graph
            await self.graph.node_manager.create_node(task_a)
            await self.graph.node_manager.create_node(task_b)
            
            # Create dependency: Task B depends on Task A
            dependency = GraphRelationship(
                type="DEPENDS_ON",
                start_node_id="task-b",
                end_node_id="task-a",
                properties={
                    "dependency_type": "prerequisite",
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            await self.graph.relationship_manager.create_relationship(dependency)
            
            # Find which task can run first (no dependencies)
            ready_tasks = await self._find_tasks_without_dependencies()
            
            return {
                "success": True,
                "tasks_created": ["task-a", "task-b"],
                "dependency_created": True,
                "ready_to_run": ready_tasks
            }
            
        except Exception as e:
            logger.error(f"Error creating tasks with dependency: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def update_task_status(self) -> Dict[str, Any]:
        """Update a task's status and see the effect on dependent tasks.
        
        Returns:
            Dictionary with status update results
        """
        logger.info("Updating task status")
        
        try:
            # First, ensure we have tasks to work with
            await self.create_task_with_dependency()
            
            # Update Task A to completed
            task_a = await self.graph.node_manager.get_node("task-a")
            if task_a:
                task_a.set_property("status", "completed")
                task_a.set_property("completed_at", datetime.utcnow().isoformat())
                await self.graph.node_manager.update_node(task_a)
            
            # Check which tasks are now ready to run
            ready_tasks_before = await self._find_tasks_without_dependencies()
            
            # Find tasks that are now ready (dependencies completed)
            ready_tasks_after = await self._find_tasks_with_completed_dependencies()
            
            return {
                "success": True,
                "task_updated": "task-a",
                "new_status": "completed",
                "ready_tasks_before": ready_tasks_before,
                "ready_tasks_after": ready_tasks_after,
                "newly_available": list(set(ready_tasks_after) - set(ready_tasks_before))
            }
            
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def query_task_dependencies(self) -> Dict[str, Any]:
        """Query and display task dependencies.
        
        Returns:
            Dictionary with dependency query results
        """
        logger.info("Querying task dependencies")
        
        try:
            # Query to find all tasks and their dependencies
            query = """
            MATCH (t:Task)
            OPTIONAL MATCH (t)-[:DEPENDS_ON]->(dep:Task)
            RETURN t.id as task_id, t.name as task_name, t.status as status,
                   collect(dep.id) as dependencies
            ORDER BY t.id
            """
            
            result = await self.graph.client.execute_query(query)
            
            tasks_info = []
            for record in result.records:
                tasks_info.append({
                    "task_id": record["task_id"],
                    "task_name": record["task_name"],
                    "status": record["status"],
                    "dependencies": record["dependencies"] if record["dependencies"][0] else []
                })
            
            return {
                "success": True,
                "total_tasks": len(tasks_info),
                "tasks": tasks_info
            }
            
        except Exception as e:
            logger.error(f"Error querying task dependencies: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def find_execution_path(self) -> Dict[str, Any]:
        """Find the execution path through a set of tasks.
        
        Returns:
            Dictionary with execution path results
        """
        logger.info("Finding execution path")
        
        try:
            # Create a simple chain of tasks for demonstration
            tasks = [
                GraphNode(id="start-task", labels=["Task"], 
                         properties={"name": "Start Task", "status": "pending"}),
                GraphNode(id="middle-task", labels=["Task"], 
                         properties={"name": "Middle Task", "status": "pending"}),
                GraphNode(id="end-task", labels=["Task"], 
                         properties={"name": "End Task", "status": "pending"})
            ]
            
            # Create tasks
            for task in tasks:
                await self.graph.node_manager.create_node(task)
            
            # Create dependencies: start -> middle -> end
            dependencies = [
                GraphRelationship(type="DEPENDS_ON", start_node_id="middle-task", 
                                end_node_id="start-task"),
                GraphRelationship(type="DEPENDS_ON", start_node_id="end-task", 
                                end_node_id="middle-task")
            ]
            
            for dep in dependencies:
                await self.graph.relationship_manager.create_relationship(dep)
            
            # Find the execution path
            execution_path = await self._calculate_execution_order()
            
            return {
                "success": True,
                "tasks_created": [task.id for task in tasks],
                "execution_path": execution_path,
                "path_length": len(execution_path)
            }
            
        except Exception as e:
            logger.error(f"Error finding execution path: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def demonstrate_parallel_tasks(self) -> Dict[str, Any]:
        """Demonstrate tasks that can run in parallel.
        
        Returns:
            Dictionary with parallel task results
        """
        logger.info("Demonstrating parallel tasks")
        
        try:
            # Create a setup task
            setup_task = GraphNode(
                id="setup-parallel",
                labels=["Task"],
                properties={
                    "name": "Setup for Parallel Tasks",
                    "status": "pending"
                }
            )
            
            # Create parallel tasks that both depend on setup
            parallel_tasks = [
                GraphNode(
                    id="parallel-task-1",
                    labels=["Task"],
                    properties={
                        "name": "Parallel Task 1",
                        "status": "pending",
                        "can_run_parallel": True
                    }
                ),
                GraphNode(
                    id="parallel-task-2", 
                    labels=["Task"],
                    properties={
                        "name": "Parallel Task 2",
                        "status": "pending",
                        "can_run_parallel": True
                    }
                )
            ]
            
            # Create all tasks
            await self.graph.node_manager.create_node(setup_task)
            for task in parallel_tasks:
                await self.graph.node_manager.create_node(task)
            
            # Create dependencies: both parallel tasks depend on setup
            dependencies = [
                GraphRelationship(type="DEPENDS_ON", start_node_id="parallel-task-1", 
                                end_node_id="setup-parallel"),
                GraphRelationship(type="DEPENDS_ON", start_node_id="parallel-task-2", 
                                end_node_id="setup-parallel")
            ]
            
            for dep in dependencies:
                await self.graph.relationship_manager.create_relationship(dep)
            
            # Mark setup as completed to make parallel tasks available
            setup_task.set_property("status", "completed")
            await self.graph.node_manager.update_node(setup_task)
            
            # Find tasks that can run in parallel
            parallel_ready = await self._find_parallel_ready_tasks()
            
            return {
                "success": True,
                "setup_task": "setup-parallel",
                "parallel_tasks": ["parallel-task-1", "parallel-task-2"],
                "parallel_ready": parallel_ready,
                "can_run_simultaneously": len(parallel_ready) > 1
            }
            
        except Exception as e:
            logger.error(f"Error demonstrating parallel tasks: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def cleanup_basic_examples(self) -> Dict[str, Any]:
        """Clean up all basic example data.
        
        Returns:
            Dictionary with cleanup results
        """
        logger.info("Cleaning up basic examples")
        
        try:
            # Delete all example tasks
            example_task_ids = [
                "my-first-task", "task-a", "task-b", 
                "start-task", "middle-task", "end-task",
                "setup-parallel", "parallel-task-1", "parallel-task-2"
            ]
            
            deleted_count = 0
            for task_id in example_task_ids:
                try:
                    await self.graph.node_manager.delete_node(task_id)
                    deleted_count += 1
                except:
                    # Task might not exist, continue
                    pass
            
            return {
                "success": True,
                "deleted_tasks": deleted_count,
                "message": "Basic examples cleaned up"
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up basic examples: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # Helper methods

    async def _find_tasks_without_dependencies(self) -> List[str]:
        """Find tasks that have no dependencies."""
        try:
            query = """
            MATCH (t:Task)
            WHERE NOT EXISTS((t)-[:DEPENDS_ON]->(:Task))
            AND t.status = 'pending'
            RETURN t.id as task_id
            """
            
            result = await self.graph.client.execute_query(query)
            return [record["task_id"] for record in result.records]
            
        except Exception as e:
            logger.error(f"Error finding tasks without dependencies: {e}")
            return []

    async def _find_tasks_with_completed_dependencies(self) -> List[str]:
        """Find tasks whose dependencies are all completed."""
        try:
            query = """
            MATCH (t:Task)
            WHERE t.status = 'pending'
            AND NOT EXISTS {
                MATCH (t)-[:DEPENDS_ON]->(dep:Task)
                WHERE dep.status <> 'completed'
            }
            RETURN t.id as task_id
            """
            
            result = await self.graph.client.execute_query(query)
            return [record["task_id"] for record in result.records]
            
        except Exception as e:
            logger.error(f"Error finding tasks with completed dependencies: {e}")
            return []

    async def _calculate_execution_order(self) -> List[str]:
        """Calculate the order in which tasks should be executed."""
        try:
            # Simple topological sort using Cypher
            query = """
            MATCH (t:Task)
            WHERE NOT EXISTS((t)-[:DEPENDS_ON]->(:Task))
            WITH collect(t.id) as level0
            
            MATCH (t:Task)-[:DEPENDS_ON]->(dep:Task)
            WHERE dep.id IN level0
            WITH level0, collect(DISTINCT t.id) as level1
            
            MATCH (t:Task)-[:DEPENDS_ON*2]->(dep:Task)
            WHERE dep.id IN level0
            AND NOT t.id IN level1
            WITH level0, level1, collect(DISTINCT t.id) as level2
            
            RETURN level0 + level1 + level2 as execution_order
            """
            
            result = await self.graph.client.execute_query(query)
            if result.records:
                return result.records[0]["execution_order"]
            return []
            
        except Exception as e:
            logger.error(f"Error calculating execution order: {e}")
            return []

    async def _find_parallel_ready_tasks(self) -> List[str]:
        """Find tasks that are ready and can run in parallel."""
        try:
            query = """
            MATCH (t:Task)
            WHERE t.status = 'pending'
            AND NOT EXISTS {
                MATCH (t)-[:DEPENDS_ON]->(dep:Task)
                WHERE dep.status <> 'completed'
            }
            RETURN t.id as task_id
            """
            
            result = await self.graph.client.execute_query(query)
            return [record["task_id"] for record in result.records]
            
        except Exception as e:
            logger.error(f"Error finding parallel ready tasks: {e}")
            return []

    async def run_all_basic_examples(self) -> Dict[str, Any]:
        """Run all basic usage examples.
        
        Returns:
            Dictionary with results from all basic examples
        """
        logger.info("Running all basic usage examples")
        
        results = {}
        
        try:
            # Run examples in sequence
            results["simple_task"] = await self.create_simple_task()
            results["task_dependency"] = await self.create_task_with_dependency()
            results["status_update"] = await self.update_task_status()
            results["dependency_query"] = await self.query_task_dependencies()
            results["execution_path"] = await self.find_execution_path()
            results["parallel_tasks"] = await self.demonstrate_parallel_tasks()
            
            # Summary
            successful = sum(1 for result in results.values() if result.get("success", False))
            
            results["summary"] = {
                "total_examples": len(results) - 1,
                "successful": successful,
                "failed": len(results) - 1 - successful,
                "success_rate": successful / (len(results) - 1) if len(results) > 1 else 0
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error running basic examples: {e}")
            results["summary"] = {
                "error": str(e),
                "overall_success": False
            }
            return results


# Example usage
async def main():
    """Example usage of BasicUsageExample class."""
    # This would typically be called with a real GraphManager instance
    # graph_manager = await GraphManager.create("bolt://localhost:7687", "neo4j", "password")
    # basic_example = BasicUsageExample(graph_manager)
    # results = await basic_example.run_all_basic_examples()
    # print(results)
    # await basic_example.cleanup_basic_examples()
    # await graph_manager.close()
    pass


if __name__ == "__main__":
    asyncio.run(main()) 