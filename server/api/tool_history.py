"""
Tool history API endpoints.

This module contains API endpoints for tool execution history,
including listing, getting details, statistics, clearing, and exporting.
"""

import sys
import json
import datetime
import csv
import io
from pathlib import Path

# Add the project root to Python path so we can import plugins
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from server.tool_history_manager import (
    get_tool_history_entries,
    get_tool_history_stats,
    get_tool_history_detail,
    clear_tool_history
)




async def api_list_tool_history(request: Request):
    """List tool execution history with filtering and pagination."""
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
        if success_param is not None:
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

        # Get filtered entries
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

    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


async def api_get_tool_history_detail(request: Request):
    """Get detailed information about a specific tool invocation."""
    try:
        invocation_id = request.path_params.get("invocation_id")
        if not invocation_id:
            return JSONResponse(
                {"success": False, "error": "Missing invocation_id"},
                status_code=400
            )

        result = get_tool_history_detail(invocation_id)
        status_code = 200 if result.get("success") else 404
        return JSONResponse(result, status_code=status_code)

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

        result = clear_tool_history()
        status_code = 200 if result.get("success") else 404
        return JSONResponse(result, status_code=status_code)

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
