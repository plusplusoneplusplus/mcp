"""
Background job management API endpoints.

This module contains all API endpoints related to background job management,
including listing, getting details, terminating jobs, and getting statistics.
"""

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

        # Get background jobs from the command executor
        jobs = []
        if hasattr(command_executor, "background_jobs"):
            for token, job_info in command_executor.background_jobs.items():
                job_data = {
                    "token": token,
                    "command": job_info.get("command", ""),
                    "start_time": job_info.get("start_time", ""),
                    "status": "running" if job_info.get("process") and job_info["process"].poll() is None else "completed",
                    "pid": job_info.get("process").pid if job_info.get("process") else None,
                }
                
                # Add process info if available
                if job_info.get("process"):
                    try:
                        process = psutil.Process(job_info["process"].pid)
                        job_data.update({
                            "cpu_percent": process.cpu_percent(),
                            "memory_info": process.memory_info()._asdict(),
                            "create_time": process.create_time(),
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        job_data["status"] = "completed"
                
                jobs.append(job_data)

        return JSONResponse({"jobs": jobs})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_get_background_job(request: Request):
    """Get details of a specific background job."""
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

        job_data = {
            "token": token,
            "command": job_info.get("command", ""),
            "start_time": job_info.get("start_time", ""),
            "status": "running" if job_info.get("process") and job_info["process"].poll() is None else "completed",
            "pid": job_info.get("process").pid if job_info.get("process") else None,
        }

        # Add detailed process info if available
        if job_info.get("process"):
            try:
                process = psutil.Process(job_info["process"].pid)
                job_data.update({
                    "cpu_percent": process.cpu_percent(),
                    "memory_info": process.memory_info()._asdict(),
                    "create_time": process.create_time(),
                    "status": "running",
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                job_data["status"] = "completed"

        return JSONResponse(job_data)

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

        stats = {
            "total_jobs": 0,
            "running_jobs": 0,
            "completed_jobs": 0,
            "total_cpu_percent": 0.0,
            "total_memory_mb": 0.0,
        }

        if hasattr(command_executor, "background_jobs"):
            stats["total_jobs"] = len(command_executor.background_jobs)
            
            for job_info in command_executor.background_jobs.values():
                if job_info.get("process"):
                    try:
                        process = psutil.Process(job_info["process"].pid)
                        if process.is_running():
                            stats["running_jobs"] += 1
                            stats["total_cpu_percent"] += process.cpu_percent()
                            stats["total_memory_mb"] += process.memory_info().rss / 1024 / 1024
                        else:
                            stats["completed_jobs"] += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        stats["completed_jobs"] += 1
                else:
                    stats["completed_jobs"] += 1

        return JSONResponse(stats)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500) 