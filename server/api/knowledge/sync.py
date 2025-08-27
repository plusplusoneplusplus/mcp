"""
Knowledge sync API endpoints.

This module contains endpoints for managing knowledge synchronization
with local folders and directories.
"""

from starlette.requests import Request
from starlette.responses import JSONResponse

# Import knowledge sync service
from utils.knowledge_sync import knowledge_sync_service


async def api_knowledge_sync_status(request: Request):
    """Get status of knowledge sync service."""
    try:
        folder_collections = knowledge_sync_service.get_folder_collections()

        status = {
            "enabled": knowledge_sync_service.is_enabled(),
            "configured_folders": len(folder_collections),
            "folders": [
                {
                    "path": folder,
                    "collection": collection,
                    "resolved_path": str(knowledge_sync_service.resolve_folder_path(folder)) if knowledge_sync_service.resolve_folder_path(folder) else None
                }
                for folder, collection in folder_collections
            ],
            "settings": {
                "knowledge_sync_enabled": knowledge_sync_service.is_enabled(),
            }
        }

        return JSONResponse(status)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_knowledge_sync_trigger(request: Request):
    """Manually trigger knowledge sync."""
    try:
        if not knowledge_sync_service.is_enabled():
            return JSONResponse(
                {"success": False, "error": "Knowledge sync is not enabled"},
                status_code=400
            )

        # Check if reindex parameter is provided
        data = {}
        try:
            data = await request.json()
        except:
            pass  # No JSON body, use default values

        resync = data.get("resync", False)
        result = await knowledge_sync_service.run_manual_sync(resync=resync)
        status_code = 200 if result.get("success") else 500
        return JSONResponse(result, status_code=status_code)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_knowledge_sync_folder(request: Request):
    """Sync a specific folder manually."""
    try:
        data = await request.json()
        folder_path = data.get("folder_path")
        collection_name = data.get("collection_name")
        overwrite = data.get("overwrite", False)

        if not folder_path or not collection_name:
            return JSONResponse(
                {"success": False, "error": "Both folder_path and collection_name are required"},
                status_code=400
            )

        result = await knowledge_sync_service.index_folder(folder_path, collection_name, overwrite=overwrite)
        status_code = 200 if result.get("success") else 500
        return JSONResponse(result, status_code=status_code)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
