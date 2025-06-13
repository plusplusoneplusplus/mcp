"""Mermaid diagram generator for task dependency graphs.

This module provides utilities for generating Mermaid diagrams from task
dependency graphs, including flowcharts, Gantt charts, and timeline visualizations.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict

from ..graph_manager import GraphManager
from ..models import GraphNode, GraphRelationship
from ..exceptions import GraphOperationError

logger = logging.getLogger(__name__)


class MermaidGenerator:
    """Generator for Mermaid diagrams from task dependency graphs."""

    def __init__(self, graph_manager: GraphManager):
        """Initialize with graph manager.
        
        Args:
            graph_manager: GraphManager instance for graph operations
        """
        self.graph = graph_manager

    async def generate_task_dependency_flowchart(self, 
                                               task_ids: Optional[List[str]] = None,
                                               include_status: bool = True,
                                               include_resources: bool = False) -> str:
        """Generate a Mermaid flowchart showing task dependencies.
        
        Args:
            task_ids: Specific task IDs to include (None for all tasks)
            include_status: Whether to include task status in the diagram
            include_resources: Whether to include resource nodes
            
        Returns:
            Mermaid flowchart diagram as string
        """
        logger.info("Generating task dependency flowchart")
        
        try:
            # Get tasks and their relationships
            tasks_data = await self._get_tasks_data(task_ids)
            relationships_data = await self._get_relationships_data(task_ids)
            
            if include_resources:
                resources_data = await self._get_resources_data(task_ids)
            else:
                resources_data = []
            
            # Start building the Mermaid diagram
            mermaid_lines = ["flowchart TD"]
            
            # Add task nodes
            for task in tasks_data:
                node_def = self._create_task_node_definition(task, include_status)
                mermaid_lines.append(f"    {node_def}")
            
            # Add resource nodes if requested
            if include_resources:
                for resource in resources_data:
                    node_def = self._create_resource_node_definition(resource)
                    mermaid_lines.append(f"    {node_def}")
            
            # Add dependency relationships
            for rel in relationships_data:
                if rel["type"] == "DEPENDS_ON":
                    edge_def = self._create_dependency_edge_definition(rel)
                    mermaid_lines.append(f"    {edge_def}")
            
            # Add resource relationships if requested
            if include_resources:
                resource_relationships = await self._get_resource_relationships_data(task_ids)
                for rel in resource_relationships:
                    edge_def = self._create_resource_edge_definition(rel)
                    mermaid_lines.append(f"    {edge_def}")
            
            # Add styling
            styling_lines = self._generate_task_styling(tasks_data, include_status)
            mermaid_lines.extend(styling_lines)
            
            return "\n".join(mermaid_lines)
            
        except Exception as e:
            logger.error(f"Error generating task dependency flowchart: {e}")
            raise GraphOperationError(f"Failed to generate flowchart: {e}")

    async def generate_gantt_chart(self, 
                                 task_ids: Optional[List[str]] = None,
                                 start_date: Optional[datetime] = None,
                                 include_dependencies: bool = True) -> str:
        """Generate a Mermaid Gantt chart for task scheduling.
        
        Args:
            task_ids: Specific task IDs to include (None for all tasks)
            start_date: Start date for the chart (default: now)
            include_dependencies: Whether to show dependencies in the chart
            
        Returns:
            Mermaid Gantt chart as string
        """
        logger.info("Generating Gantt chart")
        
        try:
            if start_date is None:
                start_date = datetime.utcnow()
            
            # Get tasks with timing information
            tasks_data = await self._get_tasks_with_timing(task_ids)
            
            # Calculate task scheduling
            scheduled_tasks = await self._calculate_task_schedule(tasks_data, start_date)
            
            # Start building the Gantt chart
            mermaid_lines = ["gantt"]
            mermaid_lines.append("    title Task Execution Schedule")
            mermaid_lines.append(f"    dateFormat YYYY-MM-DD")
            mermaid_lines.append(f"    axisFormat %m/%d")
            
            # Group tasks by section (e.g., by task type or priority)
            task_sections = self._group_tasks_for_gantt(scheduled_tasks)
            
            for section_name, section_tasks in task_sections.items():
                mermaid_lines.append(f"    section {section_name}")
                
                for task in section_tasks:
                    gantt_line = self._create_gantt_task_line(task, start_date)
                    mermaid_lines.append(f"    {gantt_line}")
            
            return "\n".join(mermaid_lines)
            
        except Exception as e:
            logger.error(f"Error generating Gantt chart: {e}")
            raise GraphOperationError(f"Failed to generate Gantt chart: {e}")

    async def generate_resource_allocation_diagram(self, 
                                                 resource_ids: Optional[List[str]] = None) -> str:
        """Generate a diagram showing resource allocation to tasks.
        
        Args:
            resource_ids: Specific resource IDs to include (None for all)
            
        Returns:
            Mermaid diagram showing resource allocation
        """
        logger.info("Generating resource allocation diagram")
        
        try:
            # Get resources and their allocated tasks
            resources_data = await self._get_resources_with_allocations(resource_ids)
            
            # Start building the diagram
            mermaid_lines = ["flowchart LR"]
            
            # Add resource nodes
            for resource in resources_data:
                node_def = self._create_resource_allocation_node(resource)
                mermaid_lines.append(f"    {node_def}")
            
            # Add task nodes and allocations
            for resource in resources_data:
                for task in resource.get("allocated_tasks", []):
                    task_node_def = self._create_allocated_task_node(task)
                    mermaid_lines.append(f"    {task_node_def}")
                    
                    # Add allocation edge
                    allocation_edge = f"{self._sanitize_id(resource['id'])} -->|allocated| {self._sanitize_id(task['id'])}"
                    mermaid_lines.append(f"    {allocation_edge}")
            
            # Add styling for resources and tasks
            resource_styling = self._generate_resource_allocation_styling(resources_data)
            mermaid_lines.extend(resource_styling)
            
            return "\n".join(mermaid_lines)
            
        except Exception as e:
            logger.error(f"Error generating resource allocation diagram: {e}")
            raise GraphOperationError(f"Failed to generate resource allocation diagram: {e}")

    async def generate_execution_timeline(self, 
                                        task_ids: Optional[List[str]] = None,
                                        time_window_hours: int = 24) -> str:
        """Generate a timeline diagram showing task execution over time.
        
        Args:
            task_ids: Specific task IDs to include (None for all)
            time_window_hours: Time window to display in hours
            
        Returns:
            Mermaid timeline diagram as string
        """
        logger.info("Generating execution timeline")
        
        try:
            # Get tasks with execution history
            tasks_with_history = await self._get_tasks_execution_history(task_ids, time_window_hours)
            
            # Start building the timeline
            mermaid_lines = ["timeline"]
            mermaid_lines.append("    title Task Execution Timeline")
            
            # Group tasks by time periods
            time_periods = self._group_tasks_by_time_periods(tasks_with_history, time_window_hours)
            
            for period, period_tasks in time_periods.items():
                mermaid_lines.append(f"    {period}")
                
                for task in period_tasks:
                    timeline_entry = self._create_timeline_entry(task)
                    mermaid_lines.append(f"        : {timeline_entry}")
            
            return "\n".join(mermaid_lines)
            
        except Exception as e:
            logger.error(f"Error generating execution timeline: {e}")
            raise GraphOperationError(f"Failed to generate execution timeline: {e}")

    async def generate_critical_path_diagram(self, 
                                           start_task: str, 
                                           end_task: str) -> str:
        """Generate a diagram highlighting the critical path between tasks.
        
        Args:
            start_task: Starting task ID
            end_task: Ending task ID
            
        Returns:
            Mermaid diagram with critical path highlighted
        """
        logger.info(f"Generating critical path diagram from {start_task} to {end_task}")
        
        try:
            # Get all tasks and relationships
            all_tasks = await self._get_tasks_data()
            all_relationships = await self._get_relationships_data()
            
            # Calculate critical path
            critical_path = await self.graph.calculate_critical_path(start_task, end_task)
            
            # Start building the diagram
            mermaid_lines = ["flowchart TD"]
            
            # Add all task nodes
            for task in all_tasks:
                is_critical = task["id"] in critical_path
                node_def = self._create_critical_path_node_definition(task, is_critical)
                mermaid_lines.append(f"    {node_def}")
            
            # Add relationships with critical path highlighting
            for rel in all_relationships:
                if rel["type"] == "DEPENDS_ON":
                    is_critical_edge = (rel["start_node_id"] in critical_path and 
                                      rel["end_node_id"] in critical_path)
                    edge_def = self._create_critical_path_edge_definition(rel, is_critical_edge)
                    mermaid_lines.append(f"    {edge_def}")
            
            # Add styling for critical path
            critical_path_styling = self._generate_critical_path_styling(critical_path)
            mermaid_lines.extend(critical_path_styling)
            
            return "\n".join(mermaid_lines)
            
        except Exception as e:
            logger.error(f"Error generating critical path diagram: {e}")
            raise GraphOperationError(f"Failed to generate critical path diagram: {e}")

    async def generate_task_status_overview(self) -> str:
        """Generate a pie chart showing task status distribution.
        
        Returns:
            Mermaid pie chart showing task status distribution
        """
        logger.info("Generating task status overview")
        
        try:
            # Get task status counts
            status_query = """
            MATCH (t:Task)
            RETURN t.status as status, count(t) as count
            ORDER BY count DESC
            """
            
            result = await self.graph.client.execute_query(status_query)
            
            # Start building the pie chart
            mermaid_lines = ["pie title Task Status Distribution"]
            
            for record in result.records:
                status = record["status"] or "unknown"
                count = record["count"]
                mermaid_lines.append(f'    "{status.title()}" : {count}')
            
            return "\n".join(mermaid_lines)
            
        except Exception as e:
            logger.error(f"Error generating task status overview: {e}")
            raise GraphOperationError(f"Failed to generate task status overview: {e}")

    # Helper methods for data retrieval

    async def _get_tasks_data(self, task_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get task data for diagram generation."""
        try:
            if task_ids:
                query = """
                MATCH (t:Task)
                WHERE t.id IN $task_ids
                RETURN t.id as id, t.name as name, t.status as status, 
                       t.priority as priority, t.estimated_duration as duration,
                       labels(t) as labels
                """
                result = await self.graph.client.execute_query(query, parameters={"task_ids": task_ids})
            else:
                query = """
                MATCH (t:Task)
                RETURN t.id as id, t.name as name, t.status as status,
                       t.priority as priority, t.estimated_duration as duration,
                       labels(t) as labels
                """
                result = await self.graph.client.execute_query(query)
            
            return [dict(record) for record in result.records]
            
        except Exception as e:
            logger.error(f"Error getting tasks data: {e}")
            return []

    async def _get_relationships_data(self, task_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get relationship data for diagram generation."""
        try:
            if task_ids:
                query = """
                MATCH (start:Task)-[r]->(end:Task)
                WHERE start.id IN $task_ids AND end.id IN $task_ids
                RETURN start.id as start_node_id, end.id as end_node_id, 
                       type(r) as type, properties(r) as properties
                """
                result = await self.graph.client.execute_query(query, parameters={"task_ids": task_ids})
            else:
                query = """
                MATCH (start:Task)-[r]->(end:Task)
                RETURN start.id as start_node_id, end.id as end_node_id,
                       type(r) as type, properties(r) as properties
                """
                result = await self.graph.client.execute_query(query)
            
            return [dict(record) for record in result.records]
            
        except Exception as e:
            logger.error(f"Error getting relationships data: {e}")
            return []

    async def _get_resources_data(self, task_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get resource data for diagram generation."""
        try:
            if task_ids:
                query = """
                MATCH (t:Task)-[:REQUIRES|CAN_USE]->(r:Resource)
                WHERE t.id IN $task_ids
                RETURN DISTINCT r.id as id, r.name as name, r.type as type,
                       r.status as status, labels(r) as labels
                """
                result = await self.graph.client.execute_query(query, parameters={"task_ids": task_ids})
            else:
                query = """
                MATCH (r:Resource)
                RETURN r.id as id, r.name as name, r.type as type,
                       r.status as status, labels(r) as labels
                """
                result = await self.graph.client.execute_query(query)
            
            return [dict(record) for record in result.records]
            
        except Exception as e:
            logger.error(f"Error getting resources data: {e}")
            return []

    async def _get_resource_relationships_data(self, task_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get task-resource relationship data."""
        try:
            if task_ids:
                query = """
                MATCH (t:Task)-[r:REQUIRES|CAN_USE]->(res:Resource)
                WHERE t.id IN $task_ids
                RETURN t.id as start_node_id, res.id as end_node_id,
                       type(r) as type, properties(r) as properties
                """
                result = await self.graph.client.execute_query(query, parameters={"task_ids": task_ids})
            else:
                query = """
                MATCH (t:Task)-[r:REQUIRES|CAN_USE]->(res:Resource)
                RETURN t.id as start_node_id, res.id as end_node_id,
                       type(r) as type, properties(r) as properties
                """
                result = await self.graph.client.execute_query(query)
            
            return [dict(record) for record in result.records]
            
        except Exception as e:
            logger.error(f"Error getting resource relationships data: {e}")
            return []

    # Helper methods for node and edge creation

    def _sanitize_id(self, node_id: str) -> str:
        """Sanitize node ID for Mermaid diagram."""
        # Replace special characters that might cause issues in Mermaid
        return node_id.replace("-", "_").replace(".", "_").replace(" ", "_")

    def _create_task_node_definition(self, task: Dict[str, Any], include_status: bool) -> str:
        """Create a Mermaid node definition for a task."""
        sanitized_id = self._sanitize_id(task["id"])
        name = task.get("name", task["id"])
        
        if include_status:
            status = task.get("status", "unknown")
            label = f"{name}<br/>({status})"
        else:
            label = name
        
        # Choose node shape based on task status or type
        status = task.get("status", "unknown")
        if status == "completed":
            return f'{sanitized_id}["{label}"]'
        elif status == "running":
            return f'{sanitized_id}("{label}")'
        elif status == "failed":
            return f'{sanitized_id}{{"{label}"}}'
        else:  # pending or unknown
            return f'{sanitized_id}["{label}"]'

    def _create_resource_node_definition(self, resource: Dict[str, Any]) -> str:
        """Create a Mermaid node definition for a resource."""
        sanitized_id = self._sanitize_id(resource["id"])
        name = resource.get("name", resource["id"])
        resource_type = resource.get("type", "unknown")
        
        label = f"{name}<br/>({resource_type})"
        return f'{sanitized_id}[/{label}/]'

    def _create_dependency_edge_definition(self, relationship: Dict[str, Any]) -> str:
        """Create a Mermaid edge definition for a dependency."""
        start_id = self._sanitize_id(relationship["start_node_id"])
        end_id = self._sanitize_id(relationship["end_node_id"])
        
        # Use different arrow styles for different dependency types
        dep_type = relationship.get("properties", {}).get("dependency_type", "prerequisite")
        
        if dep_type == "prerequisite":
            return f"{end_id} --> {start_id}"
        elif dep_type == "soft":
            return f"{end_id} -.-> {start_id}"
        else:
            return f"{end_id} --> {start_id}"

    def _create_resource_edge_definition(self, relationship: Dict[str, Any]) -> str:
        """Create a Mermaid edge definition for a resource relationship."""
        start_id = self._sanitize_id(relationship["start_node_id"])
        end_id = self._sanitize_id(relationship["end_node_id"])
        rel_type = relationship["type"]
        
        if rel_type == "REQUIRES":
            return f"{start_id} -.->|requires| {end_id}"
        elif rel_type == "CAN_USE":
            return f"{start_id} -.->|can use| {end_id}"
        else:
            return f"{start_id} -.-> {end_id}"

    def _create_critical_path_node_definition(self, task: Dict[str, Any], is_critical: bool) -> str:
        """Create a node definition with critical path highlighting."""
        sanitized_id = self._sanitize_id(task["id"])
        name = task.get("name", task["id"])
        
        if is_critical:
            return f'{sanitized_id}["{name}"]'
        else:
            return f'{sanitized_id}["{name}"]'

    def _create_critical_path_edge_definition(self, relationship: Dict[str, Any], is_critical: bool) -> str:
        """Create an edge definition with critical path highlighting."""
        start_id = self._sanitize_id(relationship["start_node_id"])
        end_id = self._sanitize_id(relationship["end_node_id"])
        
        if is_critical:
            return f"{end_id} ==> {start_id}"
        else:
            return f"{end_id} --> {start_id}"

    # Helper methods for styling

    def _generate_task_styling(self, tasks_data: List[Dict[str, Any]], include_status: bool) -> List[str]:
        """Generate styling for task nodes based on status."""
        styling_lines = []
        
        if include_status:
            # Group tasks by status for styling
            status_groups = defaultdict(list)
            for task in tasks_data:
                status = task.get("status", "unknown")
                status_groups[status].append(self._sanitize_id(task["id"]))
            
            # Add class definitions
            styling_lines.append("    classDef completed fill:#90EE90,stroke:#006400,stroke-width:2px")
            styling_lines.append("    classDef running fill:#FFD700,stroke:#FF8C00,stroke-width:2px")
            styling_lines.append("    classDef failed fill:#FFB6C1,stroke:#DC143C,stroke-width:2px")
            styling_lines.append("    classDef pending fill:#E6E6FA,stroke:#4B0082,stroke-width:2px")
            
            # Apply classes to nodes
            for status, node_ids in status_groups.items():
                if node_ids:
                    nodes_str = ",".join(node_ids)
                    styling_lines.append(f"    class {nodes_str} {status}")
        
        return styling_lines

    def _generate_critical_path_styling(self, critical_path: List[str]) -> List[str]:
        """Generate styling for critical path highlighting."""
        styling_lines = []
        
        if critical_path:
            # Define critical path styling
            styling_lines.append("    classDef critical fill:#FF6B6B,stroke:#C92A2A,stroke-width:3px")
            
            # Apply to critical path nodes
            critical_nodes = [self._sanitize_id(task_id) for task_id in critical_path]
            if critical_nodes:
                nodes_str = ",".join(critical_nodes)
                styling_lines.append(f"    class {nodes_str} critical")
        
        return styling_lines

    def _generate_resource_allocation_styling(self, resources_data: List[Dict[str, Any]]) -> List[str]:
        """Generate styling for resource allocation diagram."""
        styling_lines = []
        
        # Define resource and task styling
        styling_lines.append("    classDef resource fill:#87CEEB,stroke:#4682B4,stroke-width:2px")
        styling_lines.append("    classDef task fill:#98FB98,stroke:#32CD32,stroke-width:2px")
        
        # Apply styling to resource nodes
        resource_nodes = [self._sanitize_id(res["id"]) for res in resources_data]
        if resource_nodes:
            nodes_str = ",".join(resource_nodes)
            styling_lines.append(f"    class {nodes_str} resource")
        
        return styling_lines

    # Helper methods for Gantt chart generation

    async def _get_tasks_with_timing(self, task_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get tasks with timing information for Gantt chart."""
        try:
            if task_ids:
                query = """
                MATCH (t:Task)
                WHERE t.id IN $task_ids
                RETURN t.id as id, t.name as name, t.status as status,
                       t.priority as priority, t.estimated_duration as duration,
                       t.deadline as deadline, t.started_at as started_at,
                       t.completed_at as completed_at
                ORDER BY t.priority ASC, t.deadline ASC
                """
                result = await self.graph.client.execute_query(query, parameters={"task_ids": task_ids})
            else:
                query = """
                MATCH (t:Task)
                RETURN t.id as id, t.name as name, t.status as status,
                       t.priority as priority, t.estimated_duration as duration,
                       t.deadline as deadline, t.started_at as started_at,
                       t.completed_at as completed_at
                ORDER BY t.priority ASC, t.deadline ASC
                """
                result = await self.graph.client.execute_query(query)
            
            return [dict(record) for record in result.records]
            
        except Exception as e:
            logger.error(f"Error getting tasks with timing: {e}")
            return []

    async def _calculate_task_schedule(self, tasks_data: List[Dict[str, Any]], start_date: datetime) -> List[Dict[str, Any]]:
        """Calculate task schedule for Gantt chart."""
        # This is a simplified scheduling algorithm
        # In a real implementation, you'd consider dependencies and resource constraints
        
        scheduled_tasks = []
        current_date = start_date
        
        for task in tasks_data:
            duration = task.get("duration", 3600)  # Default 1 hour
            duration_days = max(1, duration // (24 * 3600))  # Convert to days, minimum 1
            
            end_date = current_date + timedelta(days=duration_days)
            
            scheduled_tasks.append({
                **task,
                "start_date": current_date,
                "end_date": end_date,
                "duration_days": duration_days
            })
            
            # Move to next start date (simple sequential scheduling)
            current_date = end_date
        
        return scheduled_tasks

    def _group_tasks_for_gantt(self, scheduled_tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group tasks by section for Gantt chart."""
        sections = defaultdict(list)
        
        for task in scheduled_tasks:
            # Group by priority or status
            priority = task.get("priority", 5)
            if priority <= 2:
                section = "High Priority"
            elif priority <= 4:
                section = "Medium Priority"
            else:
                section = "Low Priority"
            
            sections[section].append(task)
        
        return dict(sections)

    def _create_gantt_task_line(self, task: Dict[str, Any], start_date: datetime) -> str:
        """Create a Gantt chart task line."""
        name = task.get("name", task["id"])
        task_start = task["start_date"]
        task_end = task["end_date"]
        
        # Format dates for Gantt chart
        start_str = task_start.strftime("%Y-%m-%d")
        end_str = task_end.strftime("%Y-%m-%d")
        
        # Determine task status for Gantt
        status = task.get("status", "pending")
        if status == "completed":
            status_marker = "done"
        elif status == "running":
            status_marker = "active"
        elif status == "failed":
            status_marker = "crit"
        else:
            status_marker = ""
        
        if status_marker:
            return f"{name} :{status_marker}, {start_str}, {end_str}"
        else:
            return f"{name} : {start_str}, {end_str}"

    # Helper methods for timeline generation

    async def _get_tasks_execution_history(self, task_ids: Optional[List[str]] = None, 
                                         time_window_hours: int = 24) -> List[Dict[str, Any]]:
        """Get tasks execution history for timeline."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            
            if task_ids:
                query = """
                MATCH (t:Task)
                WHERE t.id IN $task_ids
                AND (t.started_at IS NOT NULL OR t.completed_at IS NOT NULL)
                RETURN t.id as id, t.name as name, t.status as status,
                       t.started_at as started_at, t.completed_at as completed_at,
                       t.estimated_duration as duration
                ORDER BY t.started_at DESC
                """
                result = await self.graph.client.execute_query(query, parameters={"task_ids": task_ids})
            else:
                query = """
                MATCH (t:Task)
                WHERE (t.started_at IS NOT NULL OR t.completed_at IS NOT NULL)
                RETURN t.id as id, t.name as name, t.status as status,
                       t.started_at as started_at, t.completed_at as completed_at,
                       t.estimated_duration as duration
                ORDER BY t.started_at DESC
                """
                result = await self.graph.client.execute_query(query)
            
            return [dict(record) for record in result.records]
            
        except Exception as e:
            logger.error(f"Error getting tasks execution history: {e}")
            return []

    def _group_tasks_by_time_periods(self, tasks_with_history: List[Dict[str, Any]], 
                                   time_window_hours: int) -> Dict[str, List[Dict[str, Any]]]:
        """Group tasks by time periods for timeline."""
        periods = defaultdict(list)
        now = datetime.utcnow()
        
        for task in tasks_with_history:
            # Determine the most relevant timestamp
            timestamp = None
            if task.get("completed_at"):
                try:
                    timestamp = datetime.fromisoformat(task["completed_at"].replace('Z', '+00:00'))
                except:
                    pass
            elif task.get("started_at"):
                try:
                    timestamp = datetime.fromisoformat(task["started_at"].replace('Z', '+00:00'))
                except:
                    pass
            
            if timestamp:
                # Calculate time period
                hours_ago = (now - timestamp).total_seconds() / 3600
                
                if hours_ago < 1:
                    period = "Last Hour"
                elif hours_ago < 6:
                    period = "Last 6 Hours"
                elif hours_ago < 12:
                    period = "Last 12 Hours"
                elif hours_ago < 24:
                    period = "Last 24 Hours"
                else:
                    period = "Earlier"
                
                periods[period].append(task)
        
        return dict(periods)

    def _create_timeline_entry(self, task: Dict[str, Any]) -> str:
        """Create a timeline entry for a task."""
        name = task.get("name", task["id"])
        status = task.get("status", "unknown")
        
        return f"{name} ({status})"

    async def _get_resources_with_allocations(self, resource_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get resources with their allocated tasks."""
        try:
            if resource_ids:
                query = """
                MATCH (r:Resource)
                WHERE r.id IN $resource_ids
                OPTIONAL MATCH (t:Task)-[:REQUIRES|CAN_USE]->(r)
                WHERE t.status IN ['pending', 'running']
                RETURN r.id as id, r.name as name, r.type as type, r.status as status,
                       collect({id: t.id, name: t.name, status: t.status}) as allocated_tasks
                """
                result = await self.graph.client.execute_query(query, parameters={"resource_ids": resource_ids})
            else:
                query = """
                MATCH (r:Resource)
                OPTIONAL MATCH (t:Task)-[:REQUIRES|CAN_USE]->(r)
                WHERE t.status IN ['pending', 'running']
                RETURN r.id as id, r.name as name, r.type as type, r.status as status,
                       collect({id: t.id, name: t.name, status: t.status}) as allocated_tasks
                """
                result = await self.graph.client.execute_query(query)
            
            resources = []
            for record in result.records:
                resource_data = dict(record)
                # Filter out null tasks
                resource_data["allocated_tasks"] = [
                    task for task in resource_data["allocated_tasks"] 
                    if task["id"] is not None
                ]
                resources.append(resource_data)
            
            return resources
            
        except Exception as e:
            logger.error(f"Error getting resources with allocations: {e}")
            return []

    def _create_resource_allocation_node(self, resource: Dict[str, Any]) -> str:
        """Create a resource node for allocation diagram."""
        sanitized_id = self._sanitize_id(resource["id"])
        name = resource.get("name", resource["id"])
        resource_type = resource.get("type", "unknown")
        allocated_count = len(resource.get("allocated_tasks", []))
        
        label = f"{name}<br/>({resource_type})<br/>{allocated_count} tasks"
        return f'{sanitized_id}["{label}"]'

    def _create_allocated_task_node(self, task: Dict[str, Any]) -> str:
        """Create a task node for allocation diagram."""
        sanitized_id = self._sanitize_id(task["id"])
        name = task.get("name", task["id"])
        status = task.get("status", "unknown")
        
        label = f"{name}<br/>({status})"
        return f'{sanitized_id}("{label}")' 