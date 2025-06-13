"""API endpoints for task management visualizations.

This module provides REST API endpoints for generating various types of
task visualization diagrams using the MermaidGenerator class.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from starlette.responses import JSONResponse
from starlette.requests import Request

from utils.graph_interface.graph_manager import GraphManager
from utils.graph_interface.visualization.mermaid_generator import MermaidGenerator
from utils.graph_interface.exceptions import GraphOperationError

logger = logging.getLogger(__name__)


class MockMermaidGenerator:
    """Mock generator for demo purposes when graph connection is unavailable."""

    async def generate_task_dependency_flowchart(self, task_ids=None, include_status=True, include_resources=False):
        """Generate a sample task dependency flowchart."""
        status_style = ""
        if include_status:
            status_style = """
    classDef pending fill:#fff2cc,stroke:#d6b656,stroke-width:2px;
    classDef running fill:#d5e8d4,stroke:#82b366,stroke-width:2px;
    classDef completed fill:#f8cecc,stroke:#b85450,stroke-width:2px;

    class TASK001,TASK004 pending;
    class TASK002 running;
    class TASK003,TASK005 completed;"""

        resource_nodes = ""
        resource_edges = ""
        if include_resources:
            resource_nodes = """
    RES001["🖥️ Server A"]
    RES002["💾 Database"]
    RES003["👤 Developer"]"""
            resource_edges = """
    RES001 -.-> TASK002
    RES002 -.-> TASK003
    RES003 -.-> TASK001"""

        return f"""flowchart TD
    TASK001["📋 Setup Environment"]
    TASK002["⚙️ Configure Database"]
    TASK003["🔧 Install Dependencies"]
    TASK004["🧪 Run Tests"]
    TASK005["🚀 Deploy Application"]{resource_nodes}

    TASK001 --> TASK002
    TASK001 --> TASK003
    TASK002 --> TASK004
    TASK003 --> TASK004
    TASK004 --> TASK005{resource_edges}{status_style}"""

    async def generate_gantt_chart(self, task_ids=None, start_date=None, include_dependencies=True):
        """Generate a sample Gantt chart."""
        start_date_str = start_date.strftime("%Y-%m-%d") if start_date else "2024-01-01"
        return f"""gantt
    title Task Execution Schedule
    dateFormat YYYY-MM-DD
    axisFormat %m/%d

    section Setup Phase
    Setup Environment      :active, setup, {start_date_str}, 3d
    Configure Database      :config, after setup, 2d

    section Development
    Install Dependencies    :deps, after setup, 1d
    Implement Features      :feat, after deps, 5d
    Code Review            :review, after feat, 1d

    section Testing
    Unit Tests             :unit, after review, 2d
    Integration Tests      :integration, after unit, 2d
    Performance Tests      :perf, after integration, 1d

    section Deployment
    Deploy to Staging      :staging, after perf, 1d
    Deploy to Production   :prod, after staging, 1d"""

    async def generate_resource_allocation_diagram(self, resource_ids=None):
        """Generate a sample resource allocation diagram."""
        return """flowchart LR
    subgraph "Compute Resources"
        SERVER1["🖥️ Server-01<br/>CPU: 80%<br/>Memory: 60%"]
        SERVER2["🖥️ Server-02<br/>CPU: 45%<br/>Memory: 40%"]
        SERVER3["🖥️ Server-03<br/>CPU: 90%<br/>Memory: 85%"]
    end

    subgraph "Storage Resources"
        DB1["💾 Database-Primary<br/>Storage: 70%"]
        DB2["💾 Database-Replica<br/>Storage: 65%"]
        CACHE["⚡ Redis Cache<br/>Memory: 55%"]
    end

    subgraph "Human Resources"
        DEV1["👤 Developer-A<br/>Availability: 100%"]
        DEV2["👤 Developer-B<br/>Availability: 80%"]
        ADMIN["👤 Admin<br/>Availability: 60%"]
    end

    subgraph "Active Tasks"
        TASK1["📋 API Development"]
        TASK2["🔧 Database Migration"]
        TASK3["🧪 Performance Testing"]
        TASK4["🔒 Security Audit"]
    end

    SERVER1 --> TASK1
    SERVER2 --> TASK2
    SERVER3 --> TASK3
    DB1 --> TASK2
    DB2 --> TASK3
    CACHE --> TASK1
    DEV1 --> TASK1
    DEV2 --> TASK2
    ADMIN --> TASK4

    classDef highUsage fill:#ffcccb,stroke:#ff6b6b,stroke-width:2px;
    classDef mediumUsage fill:#fff2cc,stroke:#ffa726,stroke-width:2px;
    classDef lowUsage fill:#d4edda,stroke:#28a745,stroke-width:2px;

    class SERVER3 highUsage;
    class SERVER1,DB1,DB2 mediumUsage;
    class SERVER2,CACHE,DEV1,DEV2,ADMIN lowUsage;"""

    async def generate_execution_timeline(self, task_ids=None, time_window_hours=24):
        """Generate a sample execution timeline."""
        return """timeline
    title Task Execution Timeline (Last 24 Hours)

    section Morning
        08:00 : Task Setup Started
              : Environment Configuration
        09:30 : Database Migration Begin
              : Schema Updates Applied
        10:15 : Unit Tests Execution
              : 145 tests passed

    section Afternoon
        13:00 : Code Review Session
              : PR #123 reviewed
        14:30 : Integration Testing
              : API endpoints tested
        15:45 : Performance Optimization
              : Query performance improved

    section Evening
        18:00 : Deployment Preparation
              : Build artifacts created
        19:30 : Staging Deployment
              : Release candidate deployed
        20:15 : Production Deployment
              : Version 2.1.0 released"""

    async def generate_critical_path_diagram(self, start_task, end_task):
        """Generate a sample critical path diagram."""
        return f"""flowchart TD
    START["{start_task}<br/>📋 Project Start"]
    DESIGN["🎨 System Design<br/>Duration: 3 days<br/>🔥 CRITICAL"]
    DEV1["💻 Frontend Dev<br/>Duration: 5 days"]
    DEV2["⚙️ Backend Dev<br/>Duration: 7 days<br/>🔥 CRITICAL"]
    DB["💾 Database Setup<br/>Duration: 2 days<br/>🔥 CRITICAL"]
    TEST["🧪 Testing<br/>Duration: 3 days<br/>🔥 CRITICAL"]
    DEPLOY["🚀 Deployment<br/>Duration: 1 day<br/>🔥 CRITICAL"]
    END["{end_task}<br/>✅ Project Complete"]

    START --> DESIGN
    DESIGN --> DEV1
    DESIGN --> DEV2
    DESIGN --> DB
    DEV1 --> TEST
    DEV2 --> TEST
    DB --> TEST
    TEST --> DEPLOY
    DEPLOY --> END

    classDef critical fill:#ffcccb,stroke:#ff0000,stroke-width:3px;
    classDef normal fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef milestone fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;

    class DESIGN,DEV2,DB,TEST,DEPLOY critical;
    class DEV1 normal;
    class START,END milestone;"""

    async def generate_task_status_overview(self):
        """Generate a sample task status overview."""
        return """pie title Task Status Distribution
    "Completed" : 42
    "In Progress" : 18
    "Pending" : 25
    "Blocked" : 8
    "On Hold" : 7"""


class VisualizationAPI:
    """API handler for visualization endpoints."""

    def __init__(self):
        """Initialize the visualization API handler."""
        self.graph_manager = None
        self.mermaid_generator = None
        self.mock_generator = MockMermaidGenerator()
        self._initialize_graph_connection()

    def _initialize_graph_connection(self):
        """Initialize the graph manager and mermaid generator."""
        try:
            # Initialize graph manager (this will need to be configured with proper Neo4j connection)
            # For now, we'll set it up to be initialized lazily when needed
            pass
        except Exception as e:
            logger.error(f"Failed to initialize graph connection: {e}")

    async def _ensure_graph_manager(self):
        """Ensure graph manager is initialized."""
        if self.graph_manager is None:
            try:
                # Initialize GraphManager with default configuration
                # This should be configured based on your Neo4j setup
                self.graph_manager = GraphManager()
                self.mermaid_generator = MermaidGenerator(self.graph_manager)
                logger.info("Graph manager and mermaid generator initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize graph manager: {e}")
                # Fall back to demo mode
                raise GraphOperationError(f"Graph connection unavailable: {e}")

    async def _get_generator(self):
        """Get the appropriate generator (real or mock)."""
        try:
            await self._ensure_graph_manager()
            return self.mermaid_generator
        except GraphOperationError:
            # Use mock generator for demo purposes
            logger.info("Using mock generator for demonstration")
            return self.mock_generator

    async def get_task_dependencies(self, request: Request) -> JSONResponse:
        """Generate task dependency flowchart.

        Query Parameters:
        - task_ids: Comma-separated list of task IDs (optional)
        - include_status: Whether to include task status (default: true)
        - include_resources: Whether to include resource nodes (default: false)
        """
        try:
            generator = await self._get_generator()

            # Parse query parameters
            task_ids_param = request.query_params.get("task_ids")
            task_ids = task_ids_param.split(",") if task_ids_param else None
            include_status = request.query_params.get("include_status", "true").lower() == "true"
            include_resources = request.query_params.get("include_resources", "false").lower() == "true"

            # Generate the diagram
            mermaid_code = await generator.generate_task_dependency_flowchart(
                task_ids=task_ids,
                include_status=include_status,
                include_resources=include_resources
            )

            # Mock task count for demo
            task_count = len(task_ids) if task_ids else 5

            response_data = {
                "diagram_type": "flowchart",
                "mermaid_code": mermaid_code,
                "metadata": {
                    "task_count": task_count,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "filters_applied": self._build_filter_list(task_ids, include_status, include_resources),
                    "demo_mode": isinstance(generator, MockMermaidGenerator)
                }
            }

            return JSONResponse(response_data)

        except Exception as e:
            logger.error(f"Error generating task dependencies: {e}")
            return JSONResponse(
                {"error": f"Failed to generate task dependencies: {str(e)}"},
                status_code=500
            )

    async def get_gantt_chart(self, request: Request) -> JSONResponse:
        """Generate Gantt chart for task scheduling.

        Query Parameters:
        - task_ids: Comma-separated list of task IDs (optional)
        - start_date: Start date for the chart (ISO format, optional)
        - include_dependencies: Whether to show dependencies (default: true)
        """
        try:
            generator = await self._get_generator()

            # Parse query parameters
            task_ids_param = request.query_params.get("task_ids")
            task_ids = task_ids_param.split(",") if task_ids_param else None

            start_date_param = request.query_params.get("start_date")
            start_date = datetime.fromisoformat(start_date_param.replace("Z", "+00:00")) if start_date_param else None

            include_dependencies = request.query_params.get("include_dependencies", "true").lower() == "true"

            # Generate the diagram
            mermaid_code = await generator.generate_gantt_chart(
                task_ids=task_ids,
                start_date=start_date,
                include_dependencies=include_dependencies
            )

            # Mock task count for demo
            task_count = len(task_ids) if task_ids else 10

            response_data = {
                "diagram_type": "gantt",
                "mermaid_code": mermaid_code,
                "metadata": {
                    "task_count": task_count,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "filters_applied": self._build_filter_list(task_ids, include_dependencies=include_dependencies),
                    "demo_mode": isinstance(generator, MockMermaidGenerator)
                }
            }

            return JSONResponse(response_data)

        except Exception as e:
            logger.error(f"Error generating Gantt chart: {e}")
            return JSONResponse(
                {"error": f"Failed to generate Gantt chart: {str(e)}"},
                status_code=500
            )

    async def get_resource_allocation(self, request: Request) -> JSONResponse:
        """Generate resource allocation diagram.

        Query Parameters:
        - resource_ids: Comma-separated list of resource IDs (optional)
        """
        try:
            generator = await self._get_generator()

            # Parse query parameters
            resource_ids_param = request.query_params.get("resource_ids")
            resource_ids = resource_ids_param.split(",") if resource_ids_param else None

            # Generate the diagram
            mermaid_code = await generator.generate_resource_allocation_diagram(
                resource_ids=resource_ids
            )

            # Mock resource count for demo
            resource_count = len(resource_ids) if resource_ids else 8

            response_data = {
                "diagram_type": "flowchart",
                "mermaid_code": mermaid_code,
                "metadata": {
                    "resource_count": resource_count,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "filters_applied": self._build_filter_list(resource_ids=resource_ids),
                    "demo_mode": isinstance(generator, MockMermaidGenerator)
                }
            }

            return JSONResponse(response_data)

        except Exception as e:
            logger.error(f"Error generating resource allocation: {e}")
            return JSONResponse(
                {"error": f"Failed to generate resource allocation: {str(e)}"},
                status_code=500
            )

    async def get_execution_timeline(self, request: Request) -> JSONResponse:
        """Generate execution timeline diagram.

        Query Parameters:
        - task_ids: Comma-separated list of task IDs (optional)
        - time_window_hours: Time window in hours (default: 24)
        """
        try:
            generator = await self._get_generator()

            # Parse query parameters
            task_ids_param = request.query_params.get("task_ids")
            task_ids = task_ids_param.split(",") if task_ids_param else None

            time_window_hours = int(request.query_params.get("time_window_hours", "24"))

            # Generate the diagram
            mermaid_code = await generator.generate_execution_timeline(
                task_ids=task_ids,
                time_window_hours=time_window_hours
            )

            # Mock task count for demo
            task_count = len(task_ids) if task_ids else 12

            response_data = {
                "diagram_type": "timeline",
                "mermaid_code": mermaid_code,
                "metadata": {
                    "task_count": task_count,
                    "time_window_hours": time_window_hours,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "filters_applied": self._build_filter_list(task_ids, time_window_hours=time_window_hours),
                    "demo_mode": isinstance(generator, MockMermaidGenerator)
                }
            }

            return JSONResponse(response_data)

        except Exception as e:
            logger.error(f"Error generating execution timeline: {e}")
            return JSONResponse(
                {"error": f"Failed to generate execution timeline: {str(e)}"},
                status_code=500
            )

    async def get_critical_path(self, request: Request) -> JSONResponse:
        """Generate critical path diagram.

        Query Parameters:
        - start_task: Start task ID (required)
        - end_task: End task ID (required)
        """
        try:
            generator = await self._get_generator()

            # Parse query parameters
            start_task = request.query_params.get("start_task", "Project Start")
            end_task = request.query_params.get("end_task", "Project Complete")

            # Generate the diagram
            mermaid_code = await generator.generate_critical_path_diagram(
                start_task=start_task,
                end_task=end_task
            )

            response_data = {
                "diagram_type": "flowchart",
                "mermaid_code": mermaid_code,
                "metadata": {
                    "start_task": start_task,
                    "end_task": end_task,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "filters_applied": [f"start_task:{start_task}", f"end_task:{end_task}"],
                    "demo_mode": isinstance(generator, MockMermaidGenerator)
                }
            }

            return JSONResponse(response_data)

        except Exception as e:
            logger.error(f"Error generating critical path: {e}")
            return JSONResponse(
                {"error": f"Failed to generate critical path: {str(e)}"},
                status_code=500
            )

    async def get_status_overview(self, request: Request) -> JSONResponse:
        """Generate task status overview diagram."""
        try:
            generator = await self._get_generator()

            # Generate the diagram
            mermaid_code = await generator.generate_task_status_overview()

            # Mock task count for demo
            task_count = 100

            response_data = {
                "diagram_type": "pie",
                "mermaid_code": mermaid_code,
                "metadata": {
                    "task_count": task_count,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "filters_applied": [],
                    "demo_mode": isinstance(generator, MockMermaidGenerator)
                }
            }

            return JSONResponse(response_data)

        except Exception as e:
            logger.error(f"Error generating status overview: {e}")
            return JSONResponse(
                {"error": f"Failed to generate status overview: {str(e)}"},
                status_code=500
            )

    async def _count_all_tasks(self) -> int:
        """Count all tasks in the graph."""
        try:
            # This is a placeholder - implement based on your graph manager's API
            if self.graph_manager:
                # Assuming graph manager has a method to count nodes by type
                return await self.graph_manager.count_nodes_by_type("Task")
            return 0
        except Exception:
            return 0

    async def _count_all_resources(self) -> int:
        """Count all resources in the graph."""
        try:
            # This is a placeholder - implement based on your graph manager's API
            if self.graph_manager:
                # Assuming graph manager has a method to count nodes by type
                return await self.graph_manager.count_nodes_by_type("Resource")
            return 0
        except Exception:
            return 0

    def _build_filter_list(self, task_ids=None, include_status=None, include_resources=None,
                          include_dependencies=None, resource_ids=None, time_window_hours=None) -> List[str]:
        """Build a list of applied filters for metadata."""
        filters = []

        if task_ids:
            filters.append(f"task_ids:{','.join(task_ids)}")
        if include_status is not None:
            filters.append(f"include_status:{include_status}")
        if include_resources is not None:
            filters.append(f"include_resources:{include_resources}")
        if include_dependencies is not None:
            filters.append(f"include_dependencies:{include_dependencies}")
        if resource_ids:
            filters.append(f"resource_ids:{','.join(resource_ids)}")
        if time_window_hours is not None:
            filters.append(f"time_window_hours:{time_window_hours}")

        return filters


# Global instance for use in route definitions
visualization_api = VisualizationAPI()
