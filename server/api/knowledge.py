"""
Knowledge management API endpoints.

This module contains all API endpoints related to knowledge indexing, querying,
and collection management.
"""

import base64
from starlette.requests import Request
from starlette.responses import JSONResponse

# Import the knowledge tools directly
from plugins.knowledge_indexer.tool import (
    KnowledgeIndexerTool,
    KnowledgeQueryTool,
    KnowledgeCollectionManagerTool,
)

# Global tool instances (lazy initialized)
_knowledge_indexer = None
_knowledge_query = None
_knowledge_collections = None


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
                {"success": False, "error": "Missing collection parameter."},
                status_code=400,
            )

        # Execute the knowledge collections tool
        result = await get_knowledge_collections().execute_tool(
            {"action": "delete", "collection": collection}
        )

        # Return the result with appropriate status code
        status_code = 200 if result.get("success") else 500
        return JSONResponse(result, status_code=status_code)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500) 