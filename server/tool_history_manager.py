"""
Tool history management core business logic.

This module contains the core functionality for managing tool execution history,
including reading, filtering, and statistics calculation.
"""

import os
import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from config import env


def get_tool_history_directory() -> Optional[Path]:
    """Get the tool history directory path if tool history is enabled."""
    if not env.is_tool_history_enabled():
        return None

    base_path = env.get_tool_history_path()
    if not os.path.isabs(base_path):
        current_dir = Path(__file__).resolve().parent
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


def get_tool_history_detail(invocation_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific tool invocation."""
    try:
        history_dir = get_tool_history_directory()
        if not history_dir:
            return {
                "success": False,
                "error": "Tool history is disabled or directory not found"
            }

        invocation_dir = history_dir / invocation_id
        if not invocation_dir.exists() or not invocation_dir.is_dir():
            return {
                "success": False,
                "error": "Invocation not found"
            }

        # Parse invocation ID
        parsed = parse_invocation_id(invocation_id)
        if not parsed:
            return {
                "success": False,
                "error": "Invalid invocation ID format"
            }

        # Read the record
        record = read_tool_history_record(invocation_dir)
        if not record:
            return {
                "success": False,
                "error": "No record found for this invocation"
            }

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

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def clear_tool_history() -> Dict[str, Any]:
    """Clear all tool execution history."""
    try:
        history_dir = get_tool_history_directory()
        if not history_dir:
            return {
                "success": False,
                "error": "Tool history is disabled or directory not found"
            }

        # Count entries before deletion
        entry_count = 0
        for dir_path in history_dir.iterdir():
            if dir_path.is_dir():
                entry_count += 1

        # Remove all invocation directories
        import shutil
        for dir_path in history_dir.iterdir():
            if dir_path.is_dir():
                shutil.rmtree(dir_path)

        return {
            "success": True,
            "message": f"Cleared {entry_count} tool history entries"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
