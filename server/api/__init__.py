"""
API routes aggregation module.

This module imports all API endpoints from the individual modules and
aggregates them into a single api_routes list for use by the main server.
"""

from starlette.routing import Route

# Import all API endpoints from individual modules
from .knowledge import (
    api_import_knowledge,
    api_list_collections,
    api_list_documents,
    api_query_segments,
    api_delete_collection,
)

from .background_jobs import (
    api_list_background_jobs,
    api_get_background_job,
    api_terminate_background_job,
    api_background_job_stats,
)

from .configuration import (
    api_get_configuration,
    api_update_configuration,
    api_reset_setting,
    api_get_env_file,
    api_save_env_file,
    api_validate_env_content,
    api_reload_configuration,
    api_backup_env_file,
)

from .tool_history import (
    api_list_tool_history,
    api_get_tool_history_detail,
    api_get_tool_history_stats,
    api_clear_tool_history,
    api_export_tool_history,
)

from .tools import (
    api_list_tools,
    api_get_tool_detail,
    api_execute_tool,
    api_tool_stats,
    api_tool_categories,
)

from .visualizations import visualization_api

# Aggregate all routes into a single list
api_routes = [
    # Knowledge management endpoints
    Route("/api/import-knowledge", endpoint=api_import_knowledge, methods=["POST"]),
    Route("/api/collections", endpoint=api_list_collections, methods=["GET"]),
    Route("/api/collection-documents", endpoint=api_list_documents, methods=["GET"]),
    Route("/api/query-segments", endpoint=api_query_segments, methods=["GET"]),
    Route("/api/delete-collection", endpoint=api_delete_collection, methods=["POST"]),

    # Background job management endpoints
    Route("/api/background-jobs", endpoint=api_list_background_jobs, methods=["GET"]),
    Route("/api/background-jobs/stats", endpoint=api_background_job_stats, methods=["GET"]),
    Route("/api/background-jobs/{token}", endpoint=api_get_background_job, methods=["GET"]),
    Route("/api/background-jobs/{token}/terminate", endpoint=api_terminate_background_job, methods=["POST"]),

    # Configuration management endpoints
    Route("/api/configuration", endpoint=api_get_configuration, methods=["GET"]),
    Route("/api/configuration", endpoint=api_update_configuration, methods=["POST"]),
    Route("/api/configuration/reset/{setting_name}", endpoint=api_reset_setting, methods=["POST"]),
    Route("/api/configuration/env-file", endpoint=api_get_env_file, methods=["GET"]),
    Route("/api/configuration/env-file", endpoint=api_save_env_file, methods=["POST"]),
    Route("/api/configuration/validate-env", endpoint=api_validate_env_content, methods=["POST"]),
    Route("/api/configuration/reload", endpoint=api_reload_configuration, methods=["POST"]),
    Route("/api/configuration/backup-env", endpoint=api_backup_env_file, methods=["POST"]),

    # Tool history endpoints - specific routes first, then generic ones
    Route("/api/tool-history", endpoint=api_list_tool_history, methods=["GET"]),
    Route("/api/tool-history/stats", endpoint=api_get_tool_history_stats, methods=["GET"]),
    Route("/api/tool-history/clear", endpoint=api_clear_tool_history, methods=["POST"]),
    Route("/api/tool-history/export", endpoint=api_export_tool_history, methods=["GET"]),
    Route("/api/tool-history/{invocation_id}", endpoint=api_get_tool_history_detail, methods=["GET"]),

    # Tools endpoints
    Route("/api/tools", endpoint=api_list_tools, methods=["GET"]),
    Route("/api/tools/stats", endpoint=api_tool_stats, methods=["GET"]),
    Route("/api/tools/categories", endpoint=api_tool_categories, methods=["GET"]),
    Route("/api/tools/{tool_name}", endpoint=api_get_tool_detail, methods=["GET"]),
    Route("/api/tools/{tool_name}/execute", endpoint=api_execute_tool, methods=["POST"]),

    # Visualization endpoints
    Route("/api/visualizations/task-dependencies", endpoint=visualization_api.get_task_dependencies, methods=["GET"]),
    Route("/api/visualizations/gantt-chart", endpoint=visualization_api.get_gantt_chart, methods=["GET"]),
    Route("/api/visualizations/resource-allocation", endpoint=visualization_api.get_resource_allocation, methods=["GET"]),
    Route("/api/visualizations/execution-timeline", endpoint=visualization_api.get_execution_timeline, methods=["GET"]),
    Route("/api/visualizations/critical-path", endpoint=visualization_api.get_critical_path, methods=["GET"]),
    Route("/api/visualizations/status-overview", endpoint=visualization_api.get_status_overview, methods=["GET"]),
]
