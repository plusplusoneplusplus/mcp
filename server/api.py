import os
import sys
from pathlib import Path

# Add the project root to Python path so we can import plugins
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tempfile
import shutil
import base64
import time
import psutil
import json
import datetime
import csv
import io
from typing import Dict, List, Any, Optional, Union
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route
from utils.vector_store.markdown_segmenter import MarkdownSegmenter
from utils.vector_store.vector_store import ChromaVectorStore

# Import the knowledge tools directly
from plugins.knowledge_indexer.tool import (
    KnowledgeIndexerTool,
    KnowledgeQueryTool,
    KnowledgeCollectionManagerTool,
)
from config import env

# Vector store path constant for backward compatibility
PERSIST_DIR = env.get_vector_store_path()

# Global tool instances (lazy initialized)
_knowledge_indexer = None
_knowledge_query = None
_knowledge_collections = None
_command_executor = None


def get_knowledge_indexer():
    """Get or create the knowledge indexer tool instance."""
    global _knowledge_indexer
    if _knowledge_indexer is None:
        _knowledge_indexer = KnowledgeIndexerTool()
    return _knowledge_indexer


def get_knowledge_query():
    """Get or create the knowledge query tool instance."""
    global _knowledge_query
    if _knowledge_query is None:
        _knowledge_query = KnowledgeQueryTool()
    return _knowledge_query


def get_knowledge_collections():
    """Get or create the knowledge collections tool instance."""
    global _knowledge_collections
    if _knowledge_collections is None:
        _knowledge_collections = KnowledgeCollectionManagerTool()
    return _knowledge_collections


def get_command_executor():
    """Get or create the command executor instance."""
    global _command_executor
    if _command_executor is None:
        from mcp_tools.dependency import injector
        _command_executor = injector.get_tool_instance("command_executor")
    return _command_executor


async def api_import_knowledge(request: Request):
    """API endpoint that delegates to the knowledge_indexer tool."""
    try:
        form = await request.form()
        files = form.getlist("files")
        collection = form.get("collection") or "default"
        overwrite = form.get("overwrite") == "true"

        if not files:
            return JSONResponse(
                {"success": False, "error": "No files uploaded."}, status_code=400
            )

        # Convert uploaded files to the format expected by the tool
        file_data = []
        for upload in files:
            filename = getattr(upload, "filename", None) or getattr(
                upload, "name", None
            )
            if not filename:
                continue

            content = await upload.read()
            # Convert binary content to base64 for the tool
            content_b64 = base64.b64encode(content).decode("utf-8")

            file_data.append(
                {"filename": filename, "content": content_b64, "encoding": "base64"}
            )

        # Execute the knowledge indexer tool
        result = await get_knowledge_indexer().execute_tool(
            {"files": file_data, "collection": collection, "overwrite": overwrite}
        )

        # Return the result with appropriate status code
        status_code = 200 if result.get("success") else 500
        return JSONResponse(result, status_code=status_code)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


from starlette.responses import JSONResponse


async def api_list_collections(request: Request):
    """API endpoint that delegates to the knowledge_collections tool."""
    try:
        # Execute the knowledge collections tool
        result = await get_knowledge_collections().execute_tool({"action": "list"})

        if result.get("success"):
            return JSONResponse({"collections": result.get("collections", [])})
        else:
            return JSONResponse(
                {"error": result.get("error", "Unknown error")}, status_code=500
            )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_list_documents(request: Request):
    """API endpoint that delegates to the knowledge_collections tool."""
    try:
        collection = request.query_params.get("collection")
        if not collection:
            return JSONResponse(
                {"error": "Missing collection parameter."}, status_code=400
            )

        # Execute the knowledge collections tool
        result = await get_knowledge_collections().execute_tool(
            {"action": "info", "collection": collection}
        )

        if result.get("success"):
            # Convert the tool result to match the original API format
            return JSONResponse(
                {
                    "ids": [],  # Tool doesn't return IDs in the same format
                    "documents": result.get("sample_documents", []),
                    "metadatas": [],  # Tool doesn't return metadata in the same format
                    "document_count": result.get("document_count", 0),
                }
            )
        else:
            return JSONResponse(
                {"error": result.get("error", "Unknown error")}, status_code=500
            )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_query_segments(request: Request):
    """API endpoint that delegates to the knowledge_query tool."""
    try:
        collection = request.query_params.get("collection")
        query_text = request.query_params.get("query")
        try:
            limit = int(request.query_params.get("limit", 3))
        except Exception:
            limit = 3

        if not collection or not query_text:
            return JSONResponse(
                {"error": "Missing collection or query parameter."}, status_code=400
            )

        # Execute the knowledge query tool
        result = await get_knowledge_query().execute_tool(
            {"query": query_text, "collection": collection, "limit": limit}
        )

        if result.get("success"):
            # Return the results in the expected format
            results_data = result.get("results", {})
            return JSONResponse(
                {
                    "ids": results_data.get("ids", []),
                    "documents": results_data.get("documents", []),
                    "metadatas": results_data.get("metadatas", []),
                    "distances": results_data.get("distances", []),
                }
            )
        else:
            return JSONResponse(
                {"error": result.get("error", "Unknown error")}, status_code=500
            )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_delete_collection(request: Request):
    """API endpoint that delegates to the knowledge_collections tool."""
    try:
        data = await request.json()
        collection = data.get("collection")
        if not collection:
            return JSONResponse(
                {"success": False, "error": "Missing collection name."}, status_code=400
            )

        # Execute the knowledge collections tool
        result = await get_knowledge_collections().execute_tool(
            {"action": "delete", "collection": collection}
        )

        # Return the result as-is since it already has the expected format
        status_code = 200 if result.get("success") else 500
        return JSONResponse(result, status_code=status_code)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_list_background_jobs(request: Request):
    """List running and completed background jobs."""
    executor = get_command_executor()

    status_filter = request.query_params.get("status")
    try:
        limit = int(request.query_params.get("limit", 50))
    except Exception:
        limit = 50
    include_completed = request.query_params.get("include_completed", "true").lower() != "false"

    jobs = []

    # Running jobs
    for info in executor.list_running_processes():
        if not status_filter or status_filter == info.get("status"):
            pid = info["pid"]
            # Get the full token and start_time from running_processes
            if pid in executor.running_processes:
                process_data = executor.running_processes[pid]
                info["token"] = process_data["token"]
                info["start_time"] = process_data["start_time"]
            else:
                # Fallback if process data not found
                info["token"] = executor.running_processes.get(pid, {}).get("token", "unknown")
                info["start_time"] = None
            jobs.append(info)

    if include_completed:
        for token, result in executor.completed_processes.items():
            status = result.get("status", "completed")
            if not status_filter or status_filter == status:
                job = result.copy()
                job["token"] = token
                # For completed jobs, calculate start_time from duration if available
                if "duration" in job and "start_time" not in job:
                    # If we have duration but no start_time, we can't calculate it accurately
                    # since we don't know when it completed. Leave start_time as None.
                    job["start_time"] = None
                jobs.append(job)

    total_count = len(jobs)
    running_count = len([j for j in jobs if j.get("status") == "running"])
    completed_count = len([j for j in jobs if j.get("status") != "running"])

    jobs = jobs[:limit]
    return JSONResponse({
        "jobs": jobs,
        "total_count": total_count,
        "running_count": running_count,
        "completed_count": completed_count,
    })


async def api_get_background_job(request: Request):
    """Get detailed information about a specific background job."""
    token = request.path_params.get("token")
    executor = get_command_executor()
    result = await executor.get_process_status(token)
    return JSONResponse(result)


async def api_terminate_background_job(request: Request):
    """Terminate a specific background job."""
    token = request.path_params.get("token")
    if not token:
        return JSONResponse(
            {"success": False, "error": "Missing job token."}, status_code=400
        )

    executor = get_command_executor()
    try:
        success = executor.terminate_by_token(token)
        if success:
            return JSONResponse({"success": True, "message": f"Job {token} terminated successfully."})
        else:
            return JSONResponse(
                {"success": False, "error": f"Failed to terminate job {token}. Job may not exist or already completed."},
                status_code=404
            )
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": f"Error terminating job: {str(e)}"},
            status_code=500
        )


async def api_background_job_stats(request: Request):
    """Get aggregate statistics about background job execution."""
    executor = get_command_executor()
    current_running = len(executor.running_processes)
    total_completed = len(executor.completed_processes)
    total_failed = sum(1 for r in executor.completed_processes.values() if not r.get("success"))
    durations = [r.get("duration", 0.0) for r in executor.completed_processes.values()]
    average_runtime = sum(durations) / len(durations) if durations else 0.0

    # Determine longest running token
    longest_running_token = None
    longest_runtime = 0.0
    for pid, data in executor.running_processes.items():
        runtime = time.time() - data.get("start_time", 0)
        if runtime > longest_runtime:
            longest_runtime = runtime
            longest_running_token = data.get("token")

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


# Configuration Management API Endpoints
async def api_get_configuration(request: Request):
    """Get all configuration settings."""
    try:
        config = env.get_all_configuration()
        return JSONResponse(config)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_update_configuration(request: Request):
    """Update configuration settings."""
    try:
        data = await request.json()
        result = env.update_configuration(data)
        status_code = 200 if result.get("success") else 500
        return JSONResponse(result, status_code=status_code)
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "message": f"Failed to update configuration: {str(e)}"
        }, status_code=500)


async def api_reset_setting(request: Request):
    """Reset a specific setting to its default value."""
    try:
        setting_name = request.path_params.get("setting_name")
        if not setting_name:
            return JSONResponse({
                "success": False,
                "error": "Missing setting name"
            }, status_code=400)

        result = env.reset_setting(setting_name)
        status_code = 200 if result.get("success") else 400
        return JSONResponse(result, status_code=status_code)
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


async def api_get_env_file(request: Request):
    """Get the content of the .env file."""
    try:
        result = env.get_env_file_content()
        status_code = 200 if result.get("success") else 404
        return JSONResponse(result, status_code=status_code)
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "content": "",
            "file_path": None,
            "message": f"Error reading .env file: {str(e)}"
        }, status_code=500)


async def api_save_env_file(request: Request):
    """Save content to the .env file."""
    try:
        data = await request.json()
        content = data.get("content", "")
        result = env.save_env_file_content(content)
        status_code = 200 if result.get("success") else 500
        return JSONResponse(result, status_code=status_code)
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "message": f"Error saving .env file: {str(e)}"
        }, status_code=500)


async def api_validate_env_content(request: Request):
    """Validate .env file content syntax."""
    try:
        data = await request.json()
        content = data.get("content", "")
        result = env.validate_env_content(content)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({
            "success": False,
            "errors": [f"Validation failed: {str(e)}"],
            "warnings": [],
            "message": f"Error validating .env content: {str(e)}"
        }, status_code=500)


async def api_reload_configuration(request: Request):
    """Reload configuration from .env file and environment variables."""
    try:
        env.load()
        return JSONResponse({
            "success": True,
            "message": "Configuration reloaded successfully"
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "message": f"Error reloading configuration: {str(e)}"
        }, status_code=500)


async def api_backup_env_file(request: Request):
    """Create a backup of the .env file with timestamp."""
    try:
        result = env.backup_env_file()
        status_code = 200 if result.get("success") else 404
        return JSONResponse(result, status_code=status_code)
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "message": f"Error creating backup: {str(e)}"
        }, status_code=500)


# Tool History API Helper Functions
def get_tool_history_directory() -> Optional[Path]:
    """Get the tool history directory path if history is enabled."""
    if not env.is_tool_history_enabled():
        return None

    base_path = env.get_tool_history_path()
    if not os.path.isabs(base_path):
        current_dir = Path(__file__).resolve().parent
        base_path = current_dir / base_path

    history_dir = Path(base_path)
    return history_dir if history_dir.exists() else None


def parse_invocation_id(dir_name: str) -> Optional[Dict[str, Any]]:
    """Parse invocation directory name to extract metadata."""
    try:
        # Format: YYYY-MM-DD_HH-MM-SS_microseconds_tool_name
        parts = dir_name.split('_')
        if len(parts) < 4:
            return None

        date_part = parts[0]
        time_part = parts[1]
        microseconds = parts[2]
        tool_name = '_'.join(parts[3:])

        timestamp_str = f"{date_part}_{time_part}_{microseconds}"
        timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S_%f")

        return {
            "invocation_id": dir_name,
            "timestamp": timestamp,
            "tool": tool_name
        }
    except Exception:
        return None


def read_tool_history_record(invocation_dir: Path) -> Optional[Dict[str, Any]]:
    """Read the record.jsonl file from an invocation directory."""
    record_file = invocation_dir / "record.jsonl"
    if not record_file.exists():
        return None

    try:
        with open(record_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    except Exception:
        pass

    return None


def get_tool_history_entries(
    page: int = 1,
    per_page: int = 50,
    tool_filter: Optional[str] = None,
    success_filter: Optional[bool] = None,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """Get tool history entries with filtering and pagination."""
    history_dir = get_tool_history_directory()
    if not history_dir:
        return {
            "success": False,
            "error": "Tool history is disabled or directory not found",
            "history": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 0
        }

    entries = []

    # Get all invocation directories
    for dir_path in history_dir.iterdir():
        if not dir_path.is_dir():
            continue

        # Parse directory name
        metadata = parse_invocation_id(dir_path.name)
        if not metadata:
            continue

        # Read record file
        record = read_tool_history_record(dir_path)
        if not record:
            continue

        # Apply filters
        if tool_filter and metadata["tool"] != tool_filter:
            continue

        if success_filter is not None and record.get("success") != success_filter:
            continue

        if start_date and metadata["timestamp"] < start_date:
            continue

        if end_date and metadata["timestamp"] > end_date:
            continue

        if search:
            search_text = json.dumps({
                "arguments": record.get("arguments", {}),
                "result": record.get("result", {})
            }).lower()
            if search.lower() not in search_text:
                continue

        # Create entry
        entry = {
            "invocation_id": metadata["invocation_id"],
            "timestamp": record.get("timestamp", metadata["timestamp"].isoformat()),
            "tool": metadata["tool"],
            "arguments": record.get("arguments", {}),
            "result": record.get("result", {}),
            "duration_ms": record.get("duration_ms", 0),
            "success": record.get("success", True)
        }

        if "error" in record:
            entry["error"] = record["error"]

        entries.append(entry)

    # Sort by timestamp (newest first)
    entries.sort(key=lambda x: x["timestamp"], reverse=True)

    # Pagination
    total = len(entries)
    total_pages = (total + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_entries = entries[start_idx:end_idx]

    return {
        "success": True,
        "history": paginated_entries,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }


def get_tool_history_stats() -> Dict[str, Any]:
    """Get aggregated statistics about tool usage."""
    history_dir = get_tool_history_directory()
    if not history_dir:
        return {
            "success": False,
            "error": "Tool history is disabled or directory not found"
        }

    total_invocations = 0
    successful_invocations = 0
    durations = []
    tool_stats = {}

    # Process all invocation directories
    for dir_path in history_dir.iterdir():
        if not dir_path.is_dir():
            continue

        metadata = parse_invocation_id(dir_path.name)
        if not metadata:
            continue

        record = read_tool_history_record(dir_path)
        if not record:
            continue

        total_invocations += 1
        tool_name = metadata["tool"]
        success = record.get("success", True)
        duration = record.get("duration_ms", 0)

        if success:
            successful_invocations += 1

        durations.append(duration)

        # Per-tool statistics
        if tool_name not in tool_stats:
            tool_stats[tool_name] = {
                "count": 0,
                "success_count": 0,
                "durations": []
            }

        tool_stats[tool_name]["count"] += 1
        if success:
            tool_stats[tool_name]["success_count"] += 1
        tool_stats[tool_name]["durations"].append(duration)

    # Calculate aggregated statistics
    success_rate = successful_invocations / total_invocations if total_invocations > 0 else 0.0
    avg_duration = sum(durations) / len(durations) if len(durations) > 0 else 0.0

    # Calculate per-tool statistics
    tools = {}
    for tool_name, stats in tool_stats.items():
        tool_durations = stats["durations"]
        tools[tool_name] = {
            "count": stats["count"],
            "success_count": stats["success_count"],
            "success_rate": stats["success_count"] / stats["count"] if stats["count"] > 0 else 0.0,
            "avg_duration": sum(tool_durations) / len(tool_durations) if len(tool_durations) > 0 else 0.0
        }

    return {
        "success": True,
        "stats": {
            "total_invocations": total_invocations,
            "successful_invocations": successful_invocations,
            "success_rate": success_rate,
            "avg_duration": avg_duration,
            "tools": tools
        }
    }


# Tool History API Endpoints
async def api_list_tool_history(request: Request):
    """List tool execution history with pagination and filtering."""
    try:
        # Parse query parameters
        page = int(request.query_params.get("page", 1))
        per_page = min(int(request.query_params.get("per_page", 50)), 100)
        tool_filter = request.query_params.get("tool")
        success_param = request.query_params.get("success")
        start_date_param = request.query_params.get("start_date")
        end_date_param = request.query_params.get("end_date")
        search = request.query_params.get("search")

        # Parse success filter
        success_filter = None
        if success_param:
            success_filter = success_param.lower() == "true"

        # Parse date filters
        start_date = None
        end_date = None
        if start_date_param:
            try:
                start_date = datetime.datetime.fromisoformat(start_date_param.replace('Z', '+00:00'))
            except ValueError:
                return JSONResponse(
                    {"success": False, "error": "Invalid start_date format. Use ISO format."},
                    status_code=400
                )

        if end_date_param:
            try:
                end_date = datetime.datetime.fromisoformat(end_date_param.replace('Z', '+00:00'))
            except ValueError:
                return JSONResponse(
                    {"success": False, "error": "Invalid end_date format. Use ISO format."},
                    status_code=400
                )

        # Get history entries
        result = get_tool_history_entries(
            page=page,
            per_page=per_page,
            tool_filter=tool_filter,
            success_filter=success_filter,
            start_date=start_date,
            end_date=end_date,
            search=search
        )

        status_code = 200 if result.get("success") else 404
        return JSONResponse(result, status_code=status_code)

    except ValueError as e:
        return JSONResponse(
            {"success": False, "error": f"Invalid parameter: {str(e)}"},
            status_code=400
        )
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


async def api_get_tool_history_detail(request: Request):
    """Get detailed information for a specific tool invocation."""
    try:
        invocation_id = request.path_params.get("invocation_id")
        if not invocation_id:
            return JSONResponse(
                {"success": False, "error": "Missing invocation_id"},
                status_code=400
            )

        history_dir = get_tool_history_directory()
        if not history_dir:
            return JSONResponse(
                {"success": False, "error": "Tool history is disabled or directory not found"},
                status_code=404
            )

        invocation_dir = history_dir / invocation_id
        if not invocation_dir.exists():
            return JSONResponse(
                {"success": False, "error": f"Invocation {invocation_id} not found"},
                status_code=404
            )

        # Read the main record
        record = read_tool_history_record(invocation_dir)
        if not record:
            return JSONResponse(
                {"success": False, "error": f"No record found for invocation {invocation_id}"},
                status_code=404
            )

        # Parse metadata from directory name
        metadata = parse_invocation_id(invocation_id)

        # Get additional files in the directory
        additional_files = []
        for file_path in invocation_dir.iterdir():
            if file_path.name != "record.jsonl" and file_path.is_file():
                try:
                    # Try to read as text first
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    additional_files.append({
                        "filename": file_path.name,
                        "content": content,
                        "type": "text"
                    })
                except UnicodeDecodeError:
                    # If not text, provide file info only
                    additional_files.append({
                        "filename": file_path.name,
                        "size": file_path.stat().st_size,
                        "type": "binary"
                    })

        result = {
            "success": True,
            "invocation": {
                "invocation_id": invocation_id,
                "timestamp": record.get("timestamp"),
                "tool": metadata["tool"] if metadata else "unknown",
                "arguments": record.get("arguments", {}),
                "result": record.get("result", {}),
                "duration_ms": record.get("duration_ms", 0),
                "success": record.get("success", True),
                "additional_files": additional_files
            }
        }

        if "error" in record:
            result["invocation"]["error"] = record["error"]

        return JSONResponse(result)

    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


async def api_get_tool_history_stats(request: Request):
    """Get aggregated statistics about tool usage."""
    try:
        result = get_tool_history_stats()
        status_code = 200 if result.get("success") else 404
        return JSONResponse(result, status_code=status_code)
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


async def api_clear_tool_history(request: Request):
    """Clear tool execution history with confirmation."""
    try:
        data = await request.json()
        confirm = data.get("confirm", False)

        if not confirm:
            return JSONResponse(
                {"success": False, "error": "Confirmation required. Set 'confirm': true"},
                status_code=400
            )

        history_dir = get_tool_history_directory()
        if not history_dir:
            return JSONResponse(
                {"success": False, "error": "Tool history is disabled or directory not found"},
                status_code=404
            )

        # Count entries before deletion
        entry_count = 0
        for dir_path in history_dir.iterdir():
            if dir_path.is_dir():
                entry_count += 1

        # Remove all invocation directories
        for dir_path in history_dir.iterdir():
            if dir_path.is_dir():
                shutil.rmtree(dir_path)

        return JSONResponse({
            "success": True,
            "message": f"Cleared {entry_count} tool history entries"
        })

    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


async def api_export_tool_history(request: Request):
    """Export tool history data in multiple formats."""
    try:
        # Parse query parameters
        format_param = request.query_params.get("format", "json").lower()
        tool_filter = request.query_params.get("tool")
        start_date_param = request.query_params.get("start_date")
        end_date_param = request.query_params.get("end_date")

        if format_param not in ["json", "csv"]:
            return JSONResponse(
                {"success": False, "error": "Invalid format. Supported: json, csv"},
                status_code=400
            )

        # Parse date filters
        start_date = None
        end_date = None
        if start_date_param:
            try:
                start_date = datetime.datetime.fromisoformat(start_date_param.replace('Z', '+00:00'))
            except ValueError:
                return JSONResponse(
                    {"success": False, "error": "Invalid start_date format. Use ISO format."},
                    status_code=400
                )

        if end_date_param:
            try:
                end_date = datetime.datetime.fromisoformat(end_date_param.replace('Z', '+00:00'))
            except ValueError:
                return JSONResponse(
                    {"success": False, "error": "Invalid end_date format. Use ISO format."},
                    status_code=400
                )

        # Get all entries (no pagination for export)
        result = get_tool_history_entries(
            page=1,
            per_page=10000,  # Large number to get all entries
            tool_filter=tool_filter,
            start_date=start_date,
            end_date=end_date
        )

        if not result.get("success"):
            return JSONResponse(result, status_code=404)

        entries = result["history"]

        if format_param == "json":
            # JSON export
            export_data = {
                "export_timestamp": datetime.datetime.now().isoformat(),
                "total_entries": len(entries),
                "filters": {
                    "tool": tool_filter,
                    "start_date": start_date_param,
                    "end_date": end_date_param
                },
                "entries": entries
            }

            return JSONResponse(export_data)

        elif format_param == "csv":
            # CSV export
            output = io.StringIO()
            if entries:
                fieldnames = ["invocation_id", "timestamp", "tool", "duration_ms", "success", "arguments", "result", "error"]
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()

                for entry in entries:
                    csv_row = {
                        "invocation_id": entry.get("invocation_id", ""),
                        "timestamp": entry.get("timestamp", ""),
                        "tool": entry.get("tool", ""),
                        "duration_ms": entry.get("duration_ms", 0),
                        "success": entry.get("success", True),
                        "arguments": json.dumps(entry.get("arguments", {})),
                        "result": json.dumps(entry.get("result", {})),
                        "error": entry.get("error", "")
                    }
                    writer.writerow(csv_row)

            csv_content = output.getvalue()
            output.close()

            # Return CSV as streaming response
            def generate():
                yield csv_content

            return StreamingResponse(
                generate(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=tool_history.csv"}
            )

    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


api_routes = [
    Route("/api/import-knowledge", endpoint=api_import_knowledge, methods=["POST"]),
    Route("/api/collections", endpoint=api_list_collections, methods=["GET"]),
    Route("/api/collection-documents", endpoint=api_list_documents, methods=["GET"]),
    Route("/api/query-segments", endpoint=api_query_segments, methods=["GET"]),
    Route("/api/delete-collection", endpoint=api_delete_collection, methods=["POST"]),
    Route("/api/background-jobs", endpoint=api_list_background_jobs, methods=["GET"]),
    Route("/api/background-jobs/stats", endpoint=api_background_job_stats, methods=["GET"]),
    Route("/api/background-jobs/{token}", endpoint=api_get_background_job, methods=["GET"]),
    Route("/api/background-jobs/{token}/terminate", endpoint=api_terminate_background_job, methods=["POST"]),
    # Configuration Management API endpoints
    Route("/api/configuration", endpoint=api_get_configuration, methods=["GET"]),
    Route("/api/configuration", endpoint=api_update_configuration, methods=["POST"]),
    Route("/api/configuration/reset/{setting_name}", endpoint=api_reset_setting, methods=["POST"]),
    Route("/api/configuration/env-file", endpoint=api_get_env_file, methods=["GET"]),
    Route("/api/configuration/env-file", endpoint=api_save_env_file, methods=["POST"]),
    Route("/api/configuration/validate-env", endpoint=api_validate_env_content, methods=["POST"]),
    Route("/api/configuration/reload", endpoint=api_reload_configuration, methods=["POST"]),
    Route("/api/configuration/backup-env", endpoint=api_backup_env_file, methods=["POST"]),
    # Tool History API endpoints - specific routes first, then generic ones
    Route("/api/tool-history", endpoint=api_list_tool_history, methods=["GET"]),
    Route("/api/tool-history/stats", endpoint=api_get_tool_history_stats, methods=["GET"]),
    Route("/api/tool-history/clear", endpoint=api_clear_tool_history, methods=["POST"]),
    Route("/api/tool-history/export", endpoint=api_export_tool_history, methods=["GET"]),
    Route("/api/tool-history/{invocation_id}", endpoint=api_get_tool_history_detail, methods=["GET"]),
]
