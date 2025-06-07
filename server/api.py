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
from starlette.requests import Request
from starlette.responses import JSONResponse
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
            info["token"] = executor.running_processes[info["pid"]]["token"]
            jobs.append(info)

    if include_completed:
        for token, result in executor.completed_processes.items():
            status = result.get("status", "completed")
            if not status_filter or status_filter == status:
                job = result.copy()
                job["token"] = token
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
]
