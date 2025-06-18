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

from utils.graph_interface.neo4j_client import Neo4jClient
from utils.graph_interface.config import load_neo4j_config
from utils.graph_interface.graph_manager import GraphManager
from utils.graph_interface.visualization.mermaid_generator import MermaidGenerator
from utils.graph_interface.exceptions import GraphOperationError

logger = logging.getLogger(__name__)


class VisualizationAPI:
    """API handler for visualization endpoints."""

    def __init__(self):
        """Initialize the visualization API handler."""
        self.neo4j_client: Optional[Neo4jClient] = None
        self.graph_manager: Optional[GraphManager] = None
        self.mermaid_generator: Optional[MermaidGenerator] = None
        self._initialize_graph_connection()

    def _initialize_graph_connection(self):
        """Initialize the graph manager and mermaid generator."""
        try:
            # Try to initialize Neo4j client with default configuration
            logger.info("Initializing Neo4j connection for visualizations...")
            self.neo4j_client = Neo4jClient()
            logger.info("Neo4j client created successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j client: {e}")
            self.neo4j_client = None

    async def _ensure_graph_manager(self):
        """Ensure graph manager is initialized."""
        if self.graph_manager is None:
            if self.neo4j_client is None:
                raise GraphOperationError("Neo4j client not initialized. Neo4j database is required for visualizations.")

            try:
                # Connect to Neo4j
                await self.neo4j_client.connect()

                # Initialize GraphManager with the connected client
                self.graph_manager = GraphManager(self.neo4j_client)
                self.mermaid_generator = MermaidGenerator(self.graph_manager)
                logger.info("Graph manager and mermaid generator initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize graph manager: {e}")
                raise GraphOperationError(f"Graph connection unavailable: {e}")

    async def _get_generator(self):
        """Get the Neo4j-based mermaid generator."""
        await self._ensure_graph_manager()
        logger.info("Using Neo4j database for visualizations")
        return self.mermaid_generator

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

            # Get actual task count from database
            task_count = await self._count_all_tasks()
            if task_ids:
                task_count = len(task_ids)

            response_data = {
                "diagram_type": "flowchart",
                "mermaid_code": mermaid_code,
                "metadata": {
                    "task_count": task_count,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "filters_applied": self._build_filter_list(task_ids, include_status, include_resources),
                    "data_source": "neo4j"
                }
            }

            return JSONResponse(response_data)

        except GraphOperationError as e:
            logger.error(f"Graph operation error generating task dependencies: {e}")
            return JSONResponse(
                {"error": f"Neo4j database connection required: {str(e)}"},
                status_code=503
            )
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

            # Get actual task count from database
            task_count = await self._count_all_tasks()
            if task_ids:
                task_count = len(task_ids)

            response_data = {
                "diagram_type": "gantt",
                "mermaid_code": mermaid_code,
                "metadata": {
                    "task_count": task_count,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "filters_applied": self._build_filter_list(task_ids, include_dependencies=include_dependencies),
                    "data_source": "neo4j"
                }
            }

            return JSONResponse(response_data)

        except GraphOperationError as e:
            logger.error(f"Graph operation error generating Gantt chart: {e}")
            return JSONResponse(
                {"error": f"Neo4j database connection required: {str(e)}"},
                status_code=503
            )
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

            # Get actual resource count from database
            resource_count = await self._count_all_resources()
            if resource_ids:
                resource_count = len(resource_ids)

            response_data = {
                "diagram_type": "flowchart",
                "mermaid_code": mermaid_code,
                "metadata": {
                    "resource_count": resource_count,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "filters_applied": self._build_filter_list(resource_ids=resource_ids),
                    "data_source": "neo4j"
                }
            }

            return JSONResponse(response_data)

        except GraphOperationError as e:
            logger.error(f"Graph operation error generating resource allocation: {e}")
            return JSONResponse(
                {"error": f"Neo4j database connection required: {str(e)}"},
                status_code=503
            )
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

            # Get actual task count from database
            task_count = await self._count_all_tasks()
            if task_ids:
                task_count = len(task_ids)

            response_data = {
                "diagram_type": "timeline",
                "mermaid_code": mermaid_code,
                "metadata": {
                    "task_count": task_count,
                    "time_window_hours": time_window_hours,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "filters_applied": self._build_filter_list(task_ids, time_window_hours=time_window_hours),
                    "data_source": "neo4j"
                }
            }

            return JSONResponse(response_data)

        except GraphOperationError as e:
            logger.error(f"Graph operation error generating execution timeline: {e}")
            return JSONResponse(
                {"error": f"Neo4j database connection required: {str(e)}"},
                status_code=503
            )
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
                    "data_source": "neo4j"
                }
            }

            return JSONResponse(response_data)

        except GraphOperationError as e:
            logger.error(f"Graph operation error generating critical path: {e}")
            return JSONResponse(
                {"error": f"Neo4j database connection required: {str(e)}"},
                status_code=503
            )
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

            # Get actual task count from database
            task_count = await self._count_all_tasks()

            response_data = {
                "diagram_type": "pie",
                "mermaid_code": mermaid_code,
                "metadata": {
                    "task_count": task_count,
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "filters_applied": [],
                    "data_source": "neo4j"
                }
            }

            return JSONResponse(response_data)

        except GraphOperationError as e:
            logger.error(f"Graph operation error generating status overview: {e}")
            return JSONResponse(
                {"error": f"Neo4j database connection required: {str(e)}"},
                status_code=503
            )
        except Exception as e:
            logger.error(f"Error generating status overview: {e}")
            return JSONResponse(
                {"error": f"Failed to generate status overview: {str(e)}"},
                status_code=500
            )

    async def _count_all_tasks(self) -> int:
        """Count all tasks in the graph."""
        try:
            if self.graph_manager:
                # Use graph stats to count Task nodes
                stats = await self.graph_manager.get_graph_stats()
                return stats.labels.get("Task", 0)
            return 0
        except Exception:
            return 0

    async def _count_all_resources(self) -> int:
        """Count all resources in the graph."""
        try:
            if self.graph_manager:
                # Use graph stats to count Resource nodes
                stats = await self.graph_manager.get_graph_stats()
                return stats.labels.get("Resource", 0)
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
