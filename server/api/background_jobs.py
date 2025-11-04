"""
Background job management API endpoints.

This module contains API endpoints for monitoring currently running background jobs.
For real-time progress updates, use MCP progress notifications instead of polling.
"""

import os
import sys
from pathlib import Path
import logging

# Add the project root to Python path so we can import plugins
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psutil
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


def get_command_executor():
    """Get or create the command_executor instance."""
    from mcp_tools.dependency import injector
    return injector.get_tool_instance("command_executor")


async def api_list_background_jobs(request: Request):
    """List all currently running background jobs.

    Note: This endpoint only shows currently running processes.
    Use MCP progress notifications for real-time updates during execution.
    """
    try:
        command_executor = get_command_executor()
        if not command_executor:
            return JSONResponse(
                {"error": "Command executor not available"}, status_code=500
            )

        # Get query parameters
        status_filter = request.query_params.get("status")
        try:
            limit = int(request.query_params.get("limit", 50))
        except Exception:
            limit = 50

        jobs = []

        # Get running jobs using the command executor's method
        for info in command_executor.list_running_processes():
            if not status_filter or status_filter == info.get("status"):
                jobs.append(info)

        # Calculate counts
        total_count = len(jobs)
        running_count = len([j for j in jobs if j.get("status") == "running"])

        # Apply limit
        jobs = jobs[:limit]

        response_body = {
            "jobs": jobs,
            "total_count": total_count,
            "running_count": running_count,
        }

        return JSONResponse(response_body)

    except Exception as e:
        logger.error(f"Error listing background jobs: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_background_job_stats(request: Request):
    """Get statistics about background jobs."""
    try:
        command_executor = get_command_executor()
        if not command_executor:
            return JSONResponse(
                {"error": "Command executor not available"}, status_code=500
            )

        # Get current running processes count
        current_running = 0
        longest_runtime = 0.0

        if hasattr(command_executor, "running_processes"):
            import time
            for pid, process_data in command_executor.running_processes.items():
                process = process_data.get("process")
                if process and process.poll() is None:
                    current_running += 1
                    runtime = time.time() - process_data.get("start_time", 0)
                    longest_runtime = max(longest_runtime, runtime)

        # Get system load
        system_load = {
            "cpu_usage": psutil.cpu_percent(interval=0.1),
            "memory_usage": psutil.virtual_memory().percent,
        }

        response_body = {
            "current_running": current_running,
            "longest_runtime": longest_runtime,
            "system_load": system_load,
        }

        return JSONResponse(response_body)

    except Exception as e:
        logger.error(f"Error getting background job stats: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
