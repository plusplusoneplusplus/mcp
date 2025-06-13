"""Comprehensive task management examples using the Neo4j graph interface.

This module demonstrates practical task management scenarios including:
- Basic task creation and dependency modeling
- Complex workflows with multiple dependency types
- Resource constraint modeling
- Task priority and scheduling
- Error handling and recovery scenarios
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from ..graph_manager import GraphManager
from ..models import GraphNode, GraphRelationship
from ..exceptions import GraphOperationError

logger = logging.getLogger(__name__)


class TaskExample:
    """Comprehensive examples for task management using graph interface."""

    def __init__(self, graph_manager: GraphManager):
        """Initialize with graph manager.
        
        Args:
            graph_manager: GraphManager instance for graph operations
        """
        self.graph = graph_manager

    async def basic_task_creation_example(self) -> Dict[str, Any]:
        """Demonstrate basic task creation and dependency modeling.
        
        Returns:
            Dictionary with example results and created task IDs
        """
        logger.info("Running basic task creation example")
        
        try:
            # Create basic tasks
            setup_task = GraphNode(
                id="setup-database",
                labels=["Task"],
                properties={
                    "name": "Setup Database",
                    "description": "Initialize database schema and connections",
                    "priority": 1,
                    "estimated_duration": 300,  # 5 minutes
                    "status": "pending",
                    "created_at": datetime.utcnow().isoformat(),
                    "task_type": "setup"
                }
            )

            migrate_task = GraphNode(
                id="migrate-schema",
                labels=["Task"],
                properties={
                    "name": "Migrate Schema",
                    "description": "Apply database schema migrations",
                    "priority": 2,
                    "estimated_duration": 600,  # 10 minutes
                    "status": "pending",
                    "created_at": datetime.utcnow().isoformat(),
                    "task_type": "migration"
                }
            )

            seed_task = GraphNode(
                id="seed-data",
                labels=["Task"],
                properties={
                    "name": "Seed Initial Data",
                    "description": "Load initial application data",
                    "priority": 3,
                    "estimated_duration": 180,  # 3 minutes
                    "status": "pending",
                    "created_at": datetime.utcnow().isoformat(),
                    "task_type": "data"
                }
            )

            # Create tasks in graph
            await self.graph.node_manager.create_node(setup_task)
            await self.graph.node_manager.create_node(migrate_task)
            await self.graph.node_manager.create_node(seed_task)

            # Create dependencies: migrate depends on setup, seed depends on migrate
            setup_to_migrate = GraphRelationship(
                type="DEPENDS_ON",
                start_node_id="migrate-schema",
                end_node_id="setup-database",
                properties={
                    "dependency_type": "prerequisite",
                    "created_at": datetime.utcnow().isoformat()
                }
            )

            migrate_to_seed = GraphRelationship(
                type="DEPENDS_ON", 
                start_node_id="seed-data",
                end_node_id="migrate-schema",
                properties={
                    "dependency_type": "prerequisite",
                    "created_at": datetime.utcnow().isoformat()
                }
            )

            await self.graph.relationship_manager.create_relationship(setup_to_migrate)
            await self.graph.relationship_manager.create_relationship(migrate_to_seed)

            # Find tasks ready for execution (no blocking dependencies)
            ready_tasks = await self._find_ready_tasks()

            return {
                "success": True,
                "created_tasks": ["setup-database", "migrate-schema", "seed-data"],
                "dependencies_created": 2,
                "ready_tasks": ready_tasks,
                "execution_order": ["setup-database", "migrate-schema", "seed-data"]
            }

        except Exception as e:
            logger.error(f"Error in basic task creation example: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def complex_workflow_example(self) -> Dict[str, Any]:
        """Demonstrate complex workflow with multiple dependency types.
        
        Returns:
            Dictionary with complex workflow results
        """
        logger.info("Running complex workflow example")
        
        try:
            # Create a complex CI/CD pipeline workflow
            tasks = [
                # Source control tasks
                GraphNode(
                    id="checkout-code",
                    labels=["Task", "SourceControl"],
                    properties={
                        "name": "Checkout Code",
                        "description": "Checkout source code from repository",
                        "priority": 1,
                        "estimated_duration": 30,
                        "status": "pending",
                        "stage": "source",
                        "parallel_group": "source"
                    }
                ),
                
                # Build tasks (can run in parallel after checkout)
                GraphNode(
                    id="build-frontend",
                    labels=["Task", "Build"],
                    properties={
                        "name": "Build Frontend",
                        "description": "Build React frontend application",
                        "priority": 2,
                        "estimated_duration": 300,
                        "status": "pending",
                        "stage": "build",
                        "parallel_group": "build"
                    }
                ),
                
                GraphNode(
                    id="build-backend",
                    labels=["Task", "Build"],
                    properties={
                        "name": "Build Backend",
                        "description": "Build Python backend services",
                        "priority": 2,
                        "estimated_duration": 240,
                        "status": "pending",
                        "stage": "build",
                        "parallel_group": "build"
                    }
                ),
                
                # Test tasks (depend on respective builds)
                GraphNode(
                    id="test-frontend",
                    labels=["Task", "Test"],
                    properties={
                        "name": "Test Frontend",
                        "description": "Run frontend unit and integration tests",
                        "priority": 3,
                        "estimated_duration": 180,
                        "status": "pending",
                        "stage": "test",
                        "parallel_group": "test"
                    }
                ),
                
                GraphNode(
                    id="test-backend",
                    labels=["Task", "Test"],
                    properties={
                        "name": "Test Backend",
                        "description": "Run backend unit and integration tests",
                        "priority": 3,
                        "estimated_duration": 200,
                        "status": "pending",
                        "stage": "test",
                        "parallel_group": "test"
                    }
                ),
                
                # Security scan (can run in parallel with tests)
                GraphNode(
                    id="security-scan",
                    labels=["Task", "Security"],
                    properties={
                        "name": "Security Scan",
                        "description": "Run security vulnerability scan",
                        "priority": 3,
                        "estimated_duration": 120,
                        "status": "pending",
                        "stage": "security",
                        "parallel_group": "security"
                    }
                ),
                
                # Package task (depends on all tests and security)
                GraphNode(
                    id="package-application",
                    labels=["Task", "Package"],
                    properties={
                        "name": "Package Application",
                        "description": "Create deployment packages",
                        "priority": 4,
                        "estimated_duration": 90,
                        "status": "pending",
                        "stage": "package",
                        "parallel_group": "package"
                    }
                ),
                
                # Deploy task (final step)
                GraphNode(
                    id="deploy-staging",
                    labels=["Task", "Deploy"],
                    properties={
                        "name": "Deploy to Staging",
                        "description": "Deploy application to staging environment",
                        "priority": 5,
                        "estimated_duration": 150,
                        "status": "pending",
                        "stage": "deploy",
                        "parallel_group": "deploy"
                    }
                )
            ]

            # Create all tasks
            for task in tasks:
                await self.graph.node_manager.create_node(task)

            # Create dependency relationships
            dependencies = [
                # Build tasks depend on checkout
                ("build-frontend", "checkout-code", "prerequisite"),
                ("build-backend", "checkout-code", "prerequisite"),
                
                # Test tasks depend on respective builds
                ("test-frontend", "build-frontend", "prerequisite"),
                ("test-backend", "build-backend", "prerequisite"),
                
                # Security scan depends on both builds
                ("security-scan", "build-frontend", "prerequisite"),
                ("security-scan", "build-backend", "prerequisite"),
                
                # Package depends on all tests and security
                ("package-application", "test-frontend", "prerequisite"),
                ("package-application", "test-backend", "prerequisite"),
                ("package-application", "security-scan", "prerequisite"),
                
                # Deploy depends on package
                ("deploy-staging", "package-application", "prerequisite")
            ]

            for start_task, end_task, dep_type in dependencies:
                relationship = GraphRelationship(
                    type="DEPENDS_ON",
                    start_node_id=start_task,
                    end_node_id=end_task,
                    properties={
                        "dependency_type": dep_type,
                        "created_at": datetime.utcnow().isoformat()
                    }
                )
                await self.graph.relationship_manager.create_relationship(relationship)

            # Analyze the workflow
            ready_tasks = await self._find_ready_tasks()
            parallel_groups = await self._find_parallel_groups()
            critical_path = await self._calculate_critical_path()

            return {
                "success": True,
                "workflow_name": "CI/CD Pipeline",
                "total_tasks": len(tasks),
                "total_dependencies": len(dependencies),
                "ready_tasks": ready_tasks,
                "parallel_groups": parallel_groups,
                "critical_path": critical_path,
                "estimated_total_duration": await self._calculate_total_duration()
            }

        except Exception as e:
            logger.error(f"Error in complex workflow example: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def resource_constraint_example(self) -> Dict[str, Any]:
        """Demonstrate resource constraint modeling.
        
        Returns:
            Dictionary with resource constraint results
        """
        logger.info("Running resource constraint example")
        
        try:
            # Create resource nodes
            resources = [
                GraphNode(
                    id="server-1",
                    labels=["Resource", "ComputeServer"],
                    properties={
                        "name": "Production Server 1",
                        "type": "compute",
                        "cpu_cores": 8,
                        "memory_gb": 32,
                        "disk_gb": 500,
                        "status": "available",
                        "location": "datacenter-east"
                    }
                ),
                
                GraphNode(
                    id="server-2", 
                    labels=["Resource", "ComputeServer"],
                    properties={
                        "name": "Production Server 2",
                        "type": "compute",
                        "cpu_cores": 16,
                        "memory_gb": 64,
                        "disk_gb": 1000,
                        "status": "available",
                        "location": "datacenter-west"
                    }
                ),
                
                GraphNode(
                    id="database-cluster",
                    labels=["Resource", "Database"],
                    properties={
                        "name": "PostgreSQL Cluster",
                        "type": "database",
                        "max_connections": 100,
                        "storage_gb": 2000,
                        "status": "available",
                        "version": "14.5"
                    }
                )
            ]

            # Create resource-intensive tasks
            tasks = [
                GraphNode(
                    id="data-processing-job",
                    labels=["Task", "DataProcessing"],
                    properties={
                        "name": "Large Data Processing Job",
                        "description": "Process large dataset for analytics",
                        "cpu_required": 6,
                        "memory_required_gb": 24,
                        "disk_required_gb": 100,
                        "estimated_duration": 1800,  # 30 minutes
                        "status": "pending",
                        "priority": 1
                    }
                ),
                
                GraphNode(
                    id="ml-training-job",
                    labels=["Task", "MachineLearning"],
                    properties={
                        "name": "ML Model Training",
                        "description": "Train machine learning model",
                        "cpu_required": 12,
                        "memory_required_gb": 48,
                        "disk_required_gb": 200,
                        "estimated_duration": 3600,  # 1 hour
                        "status": "pending",
                        "priority": 2
                    }
                ),
                
                GraphNode(
                    id="backup-job",
                    labels=["Task", "Backup"],
                    properties={
                        "name": "Database Backup",
                        "description": "Create full database backup",
                        "cpu_required": 2,
                        "memory_required_gb": 8,
                        "disk_required_gb": 500,
                        "estimated_duration": 900,  # 15 minutes
                        "status": "pending",
                        "priority": 3
                    }
                )
            ]

            # Create resources and tasks
            for resource in resources:
                await self.graph.node_manager.create_node(resource)
            
            for task in tasks:
                await self.graph.node_manager.create_node(task)

            # Create resource allocation relationships
            allocations = [
                # Data processing job can use server-1
                GraphRelationship(
                    type="CAN_USE",
                    start_node_id="data-processing-job",
                    end_node_id="server-1",
                    properties={
                        "allocation_type": "compute",
                        "compatibility_score": 0.8
                    }
                ),
                
                # ML training job needs server-2 (more resources)
                GraphRelationship(
                    type="REQUIRES",
                    start_node_id="ml-training-job",
                    end_node_id="server-2",
                    properties={
                        "allocation_type": "compute",
                        "compatibility_score": 0.9
                    }
                ),
                
                # Backup job can use database cluster
                GraphRelationship(
                    type="REQUIRES",
                    start_node_id="backup-job",
                    end_node_id="database-cluster",
                    properties={
                        "allocation_type": "database",
                        "compatibility_score": 1.0
                    }
                )
            ]

            for allocation in allocations:
                await self.graph.relationship_manager.create_relationship(allocation)

            # Check resource conflicts
            conflicts = await self._check_resource_conflicts()
            
            # Find optimal resource allocation
            allocation_plan = await self._create_resource_allocation_plan()

            return {
                "success": True,
                "resources_created": len(resources),
                "tasks_created": len(tasks),
                "allocations_created": len(allocations),
                "resource_conflicts": conflicts,
                "allocation_plan": allocation_plan
            }

        except Exception as e:
            logger.error(f"Error in resource constraint example: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def priority_scheduling_example(self) -> Dict[str, Any]:
        """Demonstrate task priority and scheduling.
        
        Returns:
            Dictionary with priority scheduling results
        """
        logger.info("Running priority scheduling example")
        
        try:
            # Create tasks with different priorities and deadlines
            tasks = [
                GraphNode(
                    id="critical-security-patch",
                    labels=["Task", "Security", "Critical"],
                    properties={
                        "name": "Critical Security Patch",
                        "description": "Apply urgent security patch",
                        "priority": 1,  # Highest priority
                        "estimated_duration": 300,
                        "deadline": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
                        "status": "pending",
                        "task_type": "security"
                    }
                ),
                
                GraphNode(
                    id="feature-development",
                    labels=["Task", "Development"],
                    properties={
                        "name": "New Feature Development",
                        "description": "Implement new user feature",
                        "priority": 3,  # Lower priority
                        "estimated_duration": 7200,  # 2 hours
                        "deadline": (datetime.utcnow() + timedelta(days=3)).isoformat(),
                        "status": "pending",
                        "task_type": "development"
                    }
                ),
                
                GraphNode(
                    id="performance-optimization",
                    labels=["Task", "Performance"],
                    properties={
                        "name": "Database Performance Optimization",
                        "description": "Optimize database queries",
                        "priority": 2,  # Medium priority
                        "estimated_duration": 1800,  # 30 minutes
                        "deadline": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                        "status": "pending",
                        "task_type": "optimization"
                    }
                ),
                
                GraphNode(
                    id="documentation-update",
                    labels=["Task", "Documentation"],
                    properties={
                        "name": "Update API Documentation",
                        "description": "Update API documentation for new features",
                        "priority": 4,  # Lowest priority
                        "estimated_duration": 900,  # 15 minutes
                        "deadline": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                        "status": "pending",
                        "task_type": "documentation"
                    }
                )
            ]

            # Create tasks
            for task in tasks:
                await self.graph.node_manager.create_node(task)

            # Create some dependencies
            dependencies = [
                # Documentation depends on feature development
                GraphRelationship(
                    type="DEPENDS_ON",
                    start_node_id="documentation-update",
                    end_node_id="feature-development",
                    properties={
                        "dependency_type": "prerequisite"
                    }
                )
            ]

            for dep in dependencies:
                await self.graph.relationship_manager.create_relationship(dep)

            # Calculate priority-based scheduling
            priority_order = await self._calculate_priority_order()
            deadline_analysis = await self._analyze_deadlines()
            scheduling_conflicts = await self._detect_scheduling_conflicts()

            return {
                "success": True,
                "tasks_created": len(tasks),
                "priority_order": priority_order,
                "deadline_analysis": deadline_analysis,
                "scheduling_conflicts": scheduling_conflicts,
                "recommended_execution_order": await self._get_recommended_execution_order()
            }

        except Exception as e:
            logger.error(f"Error in priority scheduling example: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def error_handling_example(self) -> Dict[str, Any]:
        """Demonstrate error handling and recovery scenarios.
        
        Returns:
            Dictionary with error handling results
        """
        logger.info("Running error handling example")
        
        try:
            # Create tasks with potential failure scenarios
            tasks = [
                GraphNode(
                    id="unreliable-service-call",
                    labels=["Task", "ExternalService"],
                    properties={
                        "name": "Call External Service",
                        "description": "Call potentially unreliable external service",
                        "priority": 2,
                        "estimated_duration": 120,
                        "max_retries": 3,
                        "retry_delay": 30,
                        "status": "pending",
                        "failure_probability": 0.3
                    }
                ),
                
                GraphNode(
                    id="fallback-service-call",
                    labels=["Task", "Fallback"],
                    properties={
                        "name": "Fallback Service Call",
                        "description": "Alternative service call if primary fails",
                        "priority": 2,
                        "estimated_duration": 90,
                        "status": "pending",
                        "is_fallback": True
                    }
                ),
                
                GraphNode(
                    id="data-validation",
                    labels=["Task", "Validation"],
                    properties={
                        "name": "Validate Data",
                        "description": "Validate processed data",
                        "priority": 1,
                        "estimated_duration": 60,
                        "status": "pending",
                        "validation_rules": ["not_null", "format_check", "range_check"]
                    }
                ),
                
                GraphNode(
                    id="cleanup-on-failure",
                    labels=["Task", "Cleanup"],
                    properties={
                        "name": "Cleanup Resources",
                        "description": "Clean up resources on failure",
                        "priority": 1,
                        "estimated_duration": 30,
                        "status": "pending",
                        "is_cleanup": True
                    }
                )
            ]

            # Create tasks
            for task in tasks:
                await self.graph.node_manager.create_node(task)

            # Create error handling relationships
            error_relationships = [
                # Fallback relationship
                GraphRelationship(
                    type="FALLBACK_FOR",
                    start_node_id="fallback-service-call",
                    end_node_id="unreliable-service-call",
                    properties={
                        "trigger_condition": "failure",
                        "fallback_type": "alternative_service"
                    }
                ),
                
                # Cleanup relationship
                GraphRelationship(
                    type="CLEANUP_FOR",
                    start_node_id="cleanup-on-failure",
                    end_node_id="unreliable-service-call",
                    properties={
                        "trigger_condition": "failure",
                        "cleanup_type": "resource_cleanup"
                    }
                ),
                
                # Validation depends on service call (either primary or fallback)
                GraphRelationship(
                    type="DEPENDS_ON",
                    start_node_id="data-validation",
                    end_node_id="unreliable-service-call",
                    properties={
                        "dependency_type": "data_dependency",
                        "allow_fallback": True
                    }
                )
            ]

            for rel in error_relationships:
                await self.graph.relationship_manager.create_relationship(rel)

            # Simulate error scenarios
            error_scenarios = await self._simulate_error_scenarios()
            recovery_plans = await self._create_recovery_plans()

            return {
                "success": True,
                "tasks_created": len(tasks),
                "error_relationships_created": len(error_relationships),
                "error_scenarios": error_scenarios,
                "recovery_plans": recovery_plans
            }

        except Exception as e:
            logger.error(f"Error in error handling example: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # Helper methods for task analysis

    async def _find_ready_tasks(self) -> List[str]:
        """Find tasks that are ready for execution (no blocking dependencies)."""
        try:
            query = """
            MATCH (t:Task)
            WHERE t.status = 'pending'
            AND NOT EXISTS {
                MATCH (t)-[:DEPENDS_ON]->(dep:Task)
                WHERE dep.status <> 'completed'
            }
            RETURN t.id as task_id
            ORDER BY t.priority ASC
            """
            
            result = await self.graph.client.execute_query(query)
            return [record["task_id"] for record in result.records]
            
        except Exception as e:
            logger.error(f"Error finding ready tasks: {e}")
            return []

    async def _find_parallel_groups(self) -> Dict[str, List[str]]:
        """Find groups of tasks that can run in parallel."""
        try:
            query = """
            MATCH (t:Task)
            WHERE t.status = 'pending'
            RETURN t.parallel_group as group_name, collect(t.id) as task_ids
            """
            
            result = await self.graph.client.execute_query(query)
            groups = {}
            for record in result.records:
                group_name = record.get("group_name")
                if group_name:
                    groups[group_name] = record["task_ids"]
            
            return groups
            
        except Exception as e:
            logger.error(f"Error finding parallel groups: {e}")
            return {}

    async def _calculate_critical_path(self) -> List[str]:
        """Calculate the critical path through the task graph."""
        try:
            # This is a simplified critical path calculation
            # In a real implementation, you'd use more sophisticated algorithms
            query = """
            MATCH path = (start:Task)-[:DEPENDS_ON*]->(end:Task)
            WHERE NOT EXISTS((start)-[:DEPENDS_ON]->(:Task))
            AND NOT EXISTS((:Task)-[:DEPENDS_ON]->(end))
            WITH path, reduce(duration = 0, n in nodes(path) | duration + n.estimated_duration) as total_duration
            ORDER BY total_duration DESC
            LIMIT 1
            RETURN [n in nodes(path) | n.id] as critical_path
            """
            
            result = await self.graph.client.execute_query(query)
            if result.records:
                return result.records[0]["critical_path"]
            return []
            
        except Exception as e:
            logger.error(f"Error calculating critical path: {e}")
            return []

    async def _calculate_total_duration(self) -> int:
        """Calculate estimated total duration considering parallelism."""
        try:
            # Simplified calculation - in reality, you'd need to consider parallel execution
            query = """
            MATCH (t:Task)
            RETURN sum(t.estimated_duration) as total_duration
            """
            
            result = await self.graph.client.execute_query(query)
            if result.records:
                return result.records[0]["total_duration"]
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating total duration: {e}")
            return 0

    async def _check_resource_conflicts(self) -> List[Dict[str, Any]]:
        """Check for resource allocation conflicts."""
        try:
            query = """
            MATCH (t1:Task)-[r1:REQUIRES|CAN_USE]->(res:Resource)<-[r2:REQUIRES|CAN_USE]-(t2:Task)
            WHERE t1.id <> t2.id
            AND t1.status = 'pending' AND t2.status = 'pending'
            WITH res, collect({task: t1.id, cpu: t1.cpu_required, memory: t1.memory_required_gb}) as task1_reqs,
                 collect({task: t2.id, cpu: t2.cpu_required, memory: t2.memory_required_gb}) as task2_reqs
            WHERE any(t1 in task1_reqs, t2 in task2_reqs | 
                t1.cpu + t2.cpu > res.cpu_cores OR 
                t1.memory + t2.memory > res.memory_gb)
            RETURN res.id as resource_id, task1_reqs, task2_reqs
            """
            
            result = await self.graph.client.execute_query(query)
            conflicts = []
            for record in result.records:
                conflicts.append({
                    "resource_id": record["resource_id"],
                    "conflicting_tasks": record["task1_reqs"] + record["task2_reqs"],
                    "conflict_type": "resource_overallocation"
                })
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Error checking resource conflicts: {e}")
            return []

    async def _create_resource_allocation_plan(self) -> Dict[str, Any]:
        """Create an optimal resource allocation plan."""
        try:
            # Simplified allocation plan
            query = """
            MATCH (t:Task)-[r:REQUIRES|CAN_USE]->(res:Resource)
            WHERE t.status = 'pending'
            RETURN t.id as task_id, res.id as resource_id, type(r) as relationship_type,
                   t.cpu_required as cpu_needed, t.memory_required_gb as memory_needed,
                   res.cpu_cores as cpu_available, res.memory_gb as memory_available
            """
            
            result = await self.graph.client.execute_query(query)
            allocations = []
            
            for record in result.records:
                if (record["cpu_needed"] <= record["cpu_available"] and 
                    record["memory_needed"] <= record["memory_available"]):
                    allocations.append({
                        "task_id": record["task_id"],
                        "resource_id": record["resource_id"],
                        "allocation_feasible": True,
                        "cpu_utilization": record["cpu_needed"] / record["cpu_available"],
                        "memory_utilization": record["memory_needed"] / record["memory_available"]
                    })
                else:
                    allocations.append({
                        "task_id": record["task_id"],
                        "resource_id": record["resource_id"],
                        "allocation_feasible": False,
                        "reason": "insufficient_resources"
                    })
            
            return {
                "allocations": allocations,
                "total_allocations": len(allocations),
                "feasible_allocations": len([a for a in allocations if a.get("allocation_feasible", False)])
            }
            
        except Exception as e:
            logger.error(f"Error creating resource allocation plan: {e}")
            return {"allocations": [], "error": str(e)}

    async def _calculate_priority_order(self) -> List[Dict[str, Any]]:
        """Calculate task execution order based on priority."""
        try:
            query = """
            MATCH (t:Task)
            WHERE t.status = 'pending'
            RETURN t.id as task_id, t.name as task_name, t.priority as priority,
                   t.estimated_duration as duration, t.deadline as deadline
            ORDER BY t.priority ASC, t.deadline ASC
            """
            
            result = await self.graph.client.execute_query(query)
            return [dict(record) for record in result.records]
            
        except Exception as e:
            logger.error(f"Error calculating priority order: {e}")
            return []

    async def _analyze_deadlines(self) -> Dict[str, Any]:
        """Analyze task deadlines and identify potential issues."""
        try:
            current_time = datetime.utcnow()
            
            query = """
            MATCH (t:Task)
            WHERE t.status = 'pending' AND t.deadline IS NOT NULL
            RETURN t.id as task_id, t.name as task_name, t.deadline as deadline,
                   t.estimated_duration as duration
            """
            
            result = await self.graph.client.execute_query(query)
            
            at_risk_tasks = []
            overdue_tasks = []
            
            for record in result.records:
                deadline = datetime.fromisoformat(record["deadline"].replace('Z', '+00:00'))
                duration_minutes = record["duration"] / 60
                
                if deadline < current_time:
                    overdue_tasks.append({
                        "task_id": record["task_id"],
                        "task_name": record["task_name"],
                        "deadline": record["deadline"],
                        "overdue_by_minutes": (current_time - deadline).total_seconds() / 60
                    })
                elif deadline < current_time + timedelta(minutes=duration_minutes):
                    at_risk_tasks.append({
                        "task_id": record["task_id"],
                        "task_name": record["task_name"],
                        "deadline": record["deadline"],
                        "time_remaining_minutes": (deadline - current_time).total_seconds() / 60,
                        "estimated_duration_minutes": duration_minutes
                    })
            
            return {
                "overdue_tasks": overdue_tasks,
                "at_risk_tasks": at_risk_tasks,
                "total_overdue": len(overdue_tasks),
                "total_at_risk": len(at_risk_tasks)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing deadlines: {e}")
            return {"error": str(e)}

    async def _detect_scheduling_conflicts(self) -> List[Dict[str, Any]]:
        """Detect potential scheduling conflicts."""
        try:
            # Look for tasks that might conflict due to resource or timing constraints
            query = """
            MATCH (t1:Task), (t2:Task)
            WHERE t1.id <> t2.id 
            AND t1.status = 'pending' AND t2.status = 'pending'
            AND t1.priority = t2.priority
            OPTIONAL MATCH (t1)-[:REQUIRES|CAN_USE]->(res:Resource)<-[:REQUIRES|CAN_USE]-(t2)
            RETURN t1.id as task1_id, t2.id as task2_id, t1.priority as priority,
                   count(res) as shared_resources
            """
            
            result = await self.graph.client.execute_query(query)
            conflicts = []
            
            for record in result.records:
                if record["shared_resources"] > 0:
                    conflicts.append({
                        "task1_id": record["task1_id"],
                        "task2_id": record["task2_id"],
                        "conflict_type": "resource_contention",
                        "priority": record["priority"],
                        "shared_resources": record["shared_resources"]
                    })
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Error detecting scheduling conflicts: {e}")
            return []

    async def _get_recommended_execution_order(self) -> List[str]:
        """Get recommended task execution order considering all factors."""
        try:
            # Complex query considering priority, dependencies, and deadlines
            query = """
            MATCH (t:Task)
            WHERE t.status = 'pending'
            AND NOT EXISTS {
                MATCH (t)-[:DEPENDS_ON]->(dep:Task)
                WHERE dep.status <> 'completed'
            }
            RETURN t.id as task_id
            ORDER BY t.priority ASC, 
                     CASE WHEN t.deadline IS NOT NULL THEN datetime(t.deadline) ELSE datetime('9999-12-31T23:59:59Z') END ASC,
                     t.estimated_duration ASC
            """
            
            result = await self.graph.client.execute_query(query)
            return [record["task_id"] for record in result.records]
            
        except Exception as e:
            logger.error(f"Error getting recommended execution order: {e}")
            return []

    async def _simulate_error_scenarios(self) -> List[Dict[str, Any]]:
        """Simulate various error scenarios."""
        scenarios = [
            {
                "scenario_name": "External Service Failure",
                "affected_task": "unreliable-service-call",
                "failure_type": "timeout",
                "probability": 0.3,
                "impact": "medium",
                "recovery_actions": ["retry", "fallback"]
            },
            {
                "scenario_name": "Resource Exhaustion",
                "affected_task": "data-processing-job",
                "failure_type": "resource_limit",
                "probability": 0.1,
                "impact": "high",
                "recovery_actions": ["cleanup", "reschedule"]
            },
            {
                "scenario_name": "Data Validation Failure",
                "affected_task": "data-validation",
                "failure_type": "validation_error",
                "probability": 0.2,
                "impact": "medium",
                "recovery_actions": ["data_correction", "manual_review"]
            }
        ]
        
        return scenarios

    async def _create_recovery_plans(self) -> List[Dict[str, Any]]:
        """Create recovery plans for different failure scenarios."""
        recovery_plans = [
            {
                "plan_name": "Service Failure Recovery",
                "trigger_conditions": ["service_timeout", "service_error"],
                "recovery_steps": [
                    {"step": 1, "action": "retry_with_backoff", "max_attempts": 3},
                    {"step": 2, "action": "switch_to_fallback_service", "condition": "max_retries_exceeded"},
                    {"step": 3, "action": "notify_administrators", "condition": "fallback_also_failed"}
                ],
                "estimated_recovery_time": 180
            },
            {
                "plan_name": "Resource Cleanup Recovery",
                "trigger_conditions": ["resource_exhaustion", "memory_leak"],
                "recovery_steps": [
                    {"step": 1, "action": "cleanup_temporary_resources", "immediate": True},
                    {"step": 2, "action": "restart_affected_services", "condition": "cleanup_insufficient"},
                    {"step": 3, "action": "scale_up_resources", "condition": "persistent_issues"}
                ],
                "estimated_recovery_time": 300
            }
        ]
        
        return recovery_plans

    async def cleanup_example_data(self) -> Dict[str, Any]:
        """Clean up all example data from the graph.
        
        Returns:
            Dictionary with cleanup results
        """
        logger.info("Cleaning up example data")
        
        try:
            # Delete all example tasks and relationships
            cleanup_query = """
            MATCH (n)
            WHERE n:Task OR n:Resource
            DETACH DELETE n
            """
            
            result = await self.graph.client.execute_query(cleanup_query)
            
            return {
                "success": True,
                "message": "All example data cleaned up successfully"
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up example data: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def run_all_examples(self) -> Dict[str, Any]:
        """Run all task management examples in sequence.
        
        Returns:
            Dictionary with results from all examples
        """
        logger.info("Running all task management examples")
        
        results = {}
        
        try:
            # Run each example
            results["basic_task_creation"] = await self.basic_task_creation_example()
            results["complex_workflow"] = await self.complex_workflow_example()
            results["resource_constraints"] = await self.resource_constraint_example()
            results["priority_scheduling"] = await self.priority_scheduling_example()
            results["error_handling"] = await self.error_handling_example()
            
            # Summary
            successful_examples = sum(1 for result in results.values() if result.get("success", False))
            
            results["summary"] = {
                "total_examples": len(results) - 1,  # Exclude summary itself
                "successful_examples": successful_examples,
                "failed_examples": len(results) - 1 - successful_examples,
                "overall_success": successful_examples == len(results) - 1
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error running all examples: {e}")
            results["summary"] = {
                "error": str(e),
                "overall_success": False
            }
            return results


# Example usage
async def main():
    """Example usage of TaskExample class."""
    # This would typically be called with a real GraphManager instance
    # graph_manager = await GraphManager.create("bolt://localhost:7687", "neo4j", "password")
    # task_example = TaskExample(graph_manager)
    # results = await task_example.run_all_examples()
    # print(results)
    # await task_example.cleanup_example_data()
    # await graph_manager.close()
    pass


if __name__ == "__main__":
    asyncio.run(main()) 