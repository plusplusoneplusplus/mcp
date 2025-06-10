"""
Tool history management API endpoints.

This module contains all API endpoints related to tool execution history,
including listing, getting details, statistics, clearing, and exporting.
"""

import os
import sys
import shutil
import json
import datetime
import csv
import io
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the project root to Python path so we can import plugins
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from config import env


def get_tool_history_directory() -> Optional[Path]:
    """Get the tool history directory path if tool history is enabled."""
    if not env.is_tool_history_enabled():
        return None
    
    base_path = env.get_tool_history_path()
    if not os.path.isabs(base_path):
        current_dir = Path(__file__).resolve().parent.parent
        base_path = current_dir / base_path
    
    history_dir = Path(base_path)
    if history_dir.exists() and history_dir.is_dir():
        return history_dir
    return None


def parse_invocation_id(dir_name: str) -> Optional[Dict[str, Any]]:
    """Parse invocation ID from directory name format: YYYY-MM-DD_HH-MM-SS_microseconds_toolname"""
    try:
        parts = dir_name.split('_')
        if len(parts) >= 4:
            date_part = parts[0]
            time_part = parts[1] + '_' + parts[2]
            microseconds = parts[3]
            tool_name = '_'.join(parts[4:]) if len(parts) > 4 else 'unknown'
            
            # Parse the timestamp
            timestamp_str = f"{date_part}_{time_part}"
            timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S_%f")
            
            return {
                "invocation_id": dir_name,
                "timestamp": timestamp,
                "tool_name": tool_name
            }
    except Exception:
        pass
    return None


def read_tool_history_record(invocation_dir: Path) -> Optional[Dict[str, Any]]:
    """Read tool history record from an invocation directory."""
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
    try:
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

        # Get all invocation directories
        invocation_dirs = []
        for dir_path in history_dir.iterdir():
            if dir_path.is_dir():
                parsed = parse_invocation_id(dir_path.name)
                if parsed:
                    invocation_dirs.append((dir_path, parsed))

        # Sort by timestamp (newest first)
        invocation_dirs.sort(key=lambda x: x[1]["timestamp"], reverse=True)

        # Apply filters
        filtered_entries = []
        for dir_path, parsed in invocation_dirs:
            # Read the record
            record = read_tool_history_record(dir_path)
            if not record:
                continue

            # Apply filters
            if tool_filter and record.get("tool") != tool_filter:
                continue
            
            if success_filter is not None and record.get("success") != success_filter:
                continue
            
            if start_date and parsed["timestamp"] < start_date:
                continue
            
            if end_date and parsed["timestamp"] > end_date:
                continue
            
            if search:
                search_lower = search.lower()
                searchable_text = f"{record.get('tool', '')} {json.dumps(record.get('arguments', {}))}"
                if search_lower not in searchable_text.lower():
                    continue

            # Add to filtered results
            entry = {
                "invocation_id": parsed["invocation_id"],
                "timestamp": parsed["timestamp"].isoformat(),
                "tool": record.get("tool", "unknown"),
                "duration_ms": record.get("duration_ms", 0),
                "success": record.get("success", True),
                "arguments": record.get("arguments", {}),
                "result": record.get("result", {}),
            }
            
            if "error" in record:
                entry["error"] = record["error"]
            
            filtered_entries.append(entry)

        # Pagination
        total = len(filtered_entries)
        total_pages = (total + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_entries = filtered_entries[start_idx:end_idx]

        return {
            "success": True,
            "history": page_entries,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "history": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 0
        }


def get_tool_history_stats() -> Dict[str, Any]:
    """Get aggregated statistics about tool usage."""
    try:
        history_dir = get_tool_history_directory()
        if not history_dir:
            return {
                "success": False,
                "error": "Tool history is disabled or directory not found"
            }

        stats = {
            "total_invocations": 0,
            "successful_invocations": 0,
            "failed_invocations": 0,
            "tools": {},
            "average_duration_ms": 0,
            "total_duration_ms": 0,
            "date_range": {
                "earliest": None,
                "latest": None
            }
        }

        total_duration = 0
        earliest_date = None
        latest_date = None

        # Process all invocation directories
        for dir_path in history_dir.iterdir():
            if not dir_path.is_dir():
                continue

            parsed = parse_invocation_id(dir_path.name)
            if not parsed:
                continue

            record = read_tool_history_record(dir_path)
            if not record:
                continue

            stats["total_invocations"] += 1
            
            # Track success/failure
            if record.get("success", True):
                stats["successful_invocations"] += 1
            else:
                stats["failed_invocations"] += 1

            # Track tool usage
            tool_name = record.get("tool", "unknown")
            if tool_name not in stats["tools"]:
                stats["tools"][tool_name] = {
                    "count": 0,
                    "successful": 0,
                    "failed": 0,
                    "total_duration_ms": 0,
                    "average_duration_ms": 0
                }
            
            tool_stats = stats["tools"][tool_name]
            tool_stats["count"] += 1
            
            if record.get("success", True):
                tool_stats["successful"] += 1
            else:
                tool_stats["failed"] += 1

            # Track duration
            duration = record.get("duration_ms", 0)
            total_duration += duration
            tool_stats["total_duration_ms"] += duration
            tool_stats["average_duration_ms"] = tool_stats["total_duration_ms"] / tool_stats["count"]

            # Track date range
            timestamp = parsed["timestamp"]
            if earliest_date is None or timestamp < earliest_date:
                earliest_date = timestamp
            if latest_date is None or timestamp > latest_date:
                latest_date = timestamp

        # Calculate overall average duration
        if stats["total_invocations"] > 0:
            stats["average_duration_ms"] = total_duration / stats["total_invocations"]
        
        stats["total_duration_ms"] = total_duration
        
        if earliest_date:
            stats["date_range"]["earliest"] = earliest_date.isoformat()
        if latest_date:
            stats["date_range"]["latest"] = latest_date.isoformat()

        return {
            "success": True,
            **stats
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


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

        history_dir = get_tool_history_directory()
        if not history_dir:
            return JSONResponse(
                {"success": False, "error": "Tool history is disabled or directory not found"},
                status_code=404
            )

        invocation_dir = history_dir / invocation_id
        if not invocation_dir.exists() or not invocation_dir.is_dir():
            return JSONResponse(
                {"success": False, "error": "Invocation not found"},
                status_code=404
            )

        # Parse invocation ID
        parsed = parse_invocation_id(invocation_id)
        if not parsed:
            return JSONResponse(
                {"success": False, "error": "Invalid invocation ID format"},
                status_code=400
            )

        # Read the record
        record = read_tool_history_record(invocation_dir)
        if not record:
            return JSONResponse(
                {"success": False, "error": "No record found for this invocation"},
                status_code=404
            )

        # Build detailed response
        result = {
            "success": True,
            "invocation": {
                "invocation_id": invocation_id,
                "timestamp": parsed["timestamp"].isoformat(),
                "tool": record.get("tool", "unknown"),
                "duration_ms": record.get("duration_ms", 0),
                "success": record.get("success", True),
                "arguments": record.get("arguments", {}),
                "result": record.get("result", {}),
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