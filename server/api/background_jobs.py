"""
Background job management API endpoints.

This module contains all API endpoints related to background job management,
including listing, getting details, terminating jobs, and getting statistics.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path so we can import plugins
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psutil
from starlette.requests import Request
from starlette.responses import JSONResponse


def get_command_executor():
    """Get or create the command executor instance."""
    from mcp_tools.dependency import injector
    return injector.get_tool_instance("command_executor")


async def api_list_background_jobs(request: Request):
    """List all background jobs."""
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
        include_completed = request.query_params.get("include_completed", "true").lower() != "false"

        jobs = []

        # Get running jobs from running_processes
        if hasattr(command_executor, "running_processes"):
            for pid, process_data in command_executor.running_processes.items():
                process = process_data.get("process")
                if process and process.poll() is None:  # Still running
                    job_data = {
                        "token": process_data.get("token", "unknown"),
                        "command": process_data.get("command", ""),
                        "start_time": process_data.get("start_time", ""),
                        "status": "running",
                        "pid": pid,
                    }

                    # Add process info if available
                    try:
                        process_info = psutil.Process(pid)
                        job_data.update({
                            "cpu_percent": process_info.cpu_percent(),
                            "memory_info": process_info.memory_info()._asdict(),
                            "create_time": process_info.create_time(),
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        job_data["status"] = "completed"

                    if not status_filter or status_filter == job_data["status"]:
                        jobs.append(job_data)

        # Get completed jobs from completed_processes if requested
        if include_completed and hasattr(command_executor, "completed_processes"):
            for token, result in command_executor.completed_processes.items():
                status = result.get("status", "completed")
                if not status_filter or status_filter == status:
                    job = result.copy()
                    job["token"] = token
                    # Ensure start_time is present
                    if "start_time" not in job:
                        job["start_time"] = None
                    jobs.append(job)

        # Calculate counts
        total_count = len(jobs)
        running_count = len([j for j in jobs if j.get("status") == "running"])
        completed_count = len([j for j in jobs if j.get("status") != "running"])

        # Apply limit
        jobs = jobs[:limit]

        return JSONResponse({
            "jobs": jobs,
            "total_count": total_count,
            "running_count": running_count,
            "completed_count": completed_count,
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_get_background_job(request: Request):
    """Get details of a specific background job."""
    try:
        token = request.path_params.get("token")
        if not token:
            return JSONResponse({"error": "Missing job token"}, status_code=400)

        command_executor = get_command_executor()
        if not command_executor:
            return JSONResponse({"error": "Command executor not available"}, status_code=500)

        # First check completed processes
        if hasattr(command_executor, "completed_processes") and token in command_executor.completed_processes:
            job_data = command_executor.completed_processes[token].copy()
            job_data["token"] = token
            return JSONResponse(job_data)

        # Then check running processes by token
        if hasattr(command_executor, "process_tokens") and token in command_executor.process_tokens:
            pid = command_executor.process_tokens[token]
            if pid in command_executor.running_processes:
                process_data = command_executor.running_processes[pid]
                process = process_data.get("process")

                job_data = {
                    "token": token,
                    "command": process_data.get("command", ""),
                    "start_time": process_data.get("start_time", ""),
                    "status": "running" if process and process.poll() is None else "completed",
                    "pid": pid,
                }

                # Add detailed process info if available
                if process and process.poll() is None:
                    try:
                        process_info = psutil.Process(pid)
                        job_data.update({
                            "cpu_percent": process_info.cpu_percent(),
                            "memory_info": process_info.memory_info()._asdict(),
                            "create_time": process_info.create_time(),
                            "status": "running",
                        })
                        # Add runtime
                        import time
                        job_data["runtime"] = time.time() - process_data.get("start_time", time.time())
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        job_data["status"] = "completed"
                else:
                    job_data["status"] = "completed"

                # Add duration for completed jobs
                if job_data["status"] == "completed":
                    import time
                    start_time = process_data.get("start_time", time.time())
                    job_data["duration"] = time.time() - start_time

                return JSONResponse(job_data)

        return JSONResponse({"error": "Job not found"}, status_code=404)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_terminate_background_job(request: Request):
    """Terminate a specific background job."""
    try:
        token = request.path_params.get("token")
        if not token:
            return JSONResponse({"error": "Missing job token"}, status_code=400)

        command_executor = get_command_executor()
        if not command_executor or not hasattr(command_executor, "background_jobs"):
            return JSONResponse({"error": "Command executor not available"}, status_code=500)

        job_info = command_executor.background_jobs.get(token)
        if not job_info:
            return JSONResponse({"error": "Job not found"}, status_code=404)

        # Terminate the process
        if job_info.get("process"):
            try:
                process = job_info["process"]
                process.terminate()
                return JSONResponse({"success": True, "message": f"Job {token} terminated"})
            except Exception as e:
                return JSONResponse({"error": f"Failed to terminate job: {str(e)}"}, status_code=500)
        else:
            return JSONResponse({"error": "Job process not found"}, status_code=404)

    except Exception as e:
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
        if hasattr(command_executor, "running_processes"):
            current_running = len([
                pid for pid, process_data in command_executor.running_processes.items()
                if process_data.get("process") and process_data["process"].poll() is None
            ])

        # Get completed processes count and statistics
        total_completed = 0
        total_failed = 0
        durations = []

        if hasattr(command_executor, "completed_processes"):
            total_completed = len(command_executor.completed_processes)
            total_failed = sum(1 for r in command_executor.completed_processes.values() if not r.get("success"))
            durations = [r.get("duration", 0.0) for r in command_executor.completed_processes.values()]

        average_runtime = sum(durations) / len(durations) if durations else 0.0

        # Determine longest running token
        longest_running_token = None
        longest_runtime = 0.0
        if hasattr(command_executor, "running_processes"):
            import time
            for pid, data in command_executor.running_processes.items():
                if data.get("process") and data["process"].poll() is None:
                    runtime = time.time() - data.get("start_time", 0)
                    if runtime > longest_runtime:
                        longest_runtime = runtime
                        longest_running_token = data.get("token")

        # Get system load
        system_load = {
            "cpu_usage": psutil.cpu_percent(interval=0.1),
            "memory_usage": psutil.virtual_memory().percent,
        }

        return JSONResponse({
            "current_running": current_running,
            "total_completed": total_completed,
            "total_failed": total_failed,
            "average_runtime": average_runtime,
            "longest_running_token": longest_running_token,
            "system_load": system_load,
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
