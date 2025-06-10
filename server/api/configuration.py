"""
Configuration management API endpoints.

This module contains all API endpoints related to configuration management,
including getting/updating configuration, managing env files, and validation.
"""

import os
import sys
import shutil
import datetime
from pathlib import Path

# Add the project root to Python path so we can import plugins
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.requests import Request
from starlette.responses import JSONResponse
from config import env


async def api_get_configuration(request: Request):
    """Get current configuration settings."""
    try:
        # Get configuration from env module
        config_data = env.get_all_configuration()
        return JSONResponse(config_data)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_update_configuration(request: Request):
    """Update configuration settings."""
    try:
        data = await request.json()
        # Update configuration through env module
        result = env.update_configuration(data)
        if result.get("success"):
            return JSONResponse(result)
        else:
            return JSONResponse(result, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_reset_setting(request: Request):
    """Reset a specific setting to its default value."""
    try:
        setting_name = request.path_params.get("setting_name")
        if not setting_name:
            return JSONResponse(
                {"success": False, "error": "Missing setting name"}, status_code=400
            )

        # Reset setting through env module
        result = env.reset_setting(setting_name)
        if result.get("success"):
            return JSONResponse(result)
        else:
            return JSONResponse(result, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_get_env_file(request: Request):
    """Get the contents of the .env file."""
    try:
        result = env.get_env_file_content()
        if result.get("success"):
            return JSONResponse(result)
        else:
            return JSONResponse(result, status_code=404)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_save_env_file(request: Request):
    """Save contents to the .env file."""
    try:
        data = await request.json()
        content = data.get("content", "")

        result = env.save_env_file_content(content)
        if result.get("success"):
            return JSONResponse(result)
        else:
            return JSONResponse(result, status_code=500)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_validate_env_content(request: Request):
    """Validate environment file content."""
    try:
        data = await request.json()
        content = data.get("content", "")

        # Validate the content through env module
        result = env.validate_env_content(content)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_reload_configuration(request: Request):
    """Reload configuration from the environment file."""
    try:
        # For now, return a simple success message as the env manager doesn't have a reload method
        return JSONResponse({
            "success": True, 
            "message": "Configuration reload requested. Restart server to apply changes."
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_backup_env_file(request: Request):
    """Create a backup of the current .env file."""
    try:
        result = env.backup_env_file()
        if result.get("success"):
            return JSONResponse(result)
        else:
            return JSONResponse(result, status_code=404)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500) 