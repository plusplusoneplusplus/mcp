"""Unit tests for tool_history_manager module."""

import os
import json
import tempfile
import shutil
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, Mock

from server.tool_history_manager import (
    get_tool_history_directory,
    parse_invocation_id,
    read_tool_history_record,
    get_tool_history_entries,
    get_tool_history_stats,
    get_tool_history_detail,
    clear_tool_history
)


class TestToolHistoryManager(unittest.TestCase):
    """Test cases for the tool_history_manager module."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_history_dir = Path(self.temp_dir) / "tool_history"
        self.test_history_dir.mkdir(exist_ok=True)

        # Mock configuration
        self.config_patcher = patch('server.tool_history_manager.env')
        self.mock_env = self.config_patcher.start()
        self.mock_env.is_tool_history_enabled.return_value = True
        self.mock_env.get_tool_history_path.return_value = str(self.test_history_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        self.config_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_sample_invocation(self, tool_name: str, success: bool = True, timestamp: datetime = None) -> str:
        """Create a sample invocation directory with record."""
        if timestamp is None:
            timestamp = datetime.now()

        # Create directory name in expected format
        dir_name = f"{timestamp.strftime('%Y-%m-%d_%H-%M-%S_%f')}_{tool_name}"
        invocation_dir = self.test_history_dir / dir_name
        invocation_dir.mkdir(exist_ok=True)

        # Create sample record
        record = {
            "tool": tool_name,
            "arguments": {"param1": "value1", "param2": "value2"},
            "result": {"output": "test result"},
            "success": success,
            "duration_ms": 150
        }

        if not success:
            record["error"] = "Test error message"

        record_file = invocation_dir / "record.jsonl"
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(record, f)

        return dir_name

    def test_get_tool_history_directory_enabled(self):
        """Test getting tool history directory when enabled."""
        result = get_tool_history_directory()
        self.assertEqual(result, self.test_history_dir)

    def test_get_tool_history_directory_disabled(self):
        """Test getting tool history directory when disabled."""
        self.mock_env.is_tool_history_enabled.return_value = False
        result = get_tool_history_directory()
        self.assertIsNone(result)

    def test_get_tool_history_directory_nonexistent(self):
        """Test getting tool history directory when path doesn't exist."""
        self.mock_env.get_tool_history_path.return_value = "/nonexistent/path"
        result = get_tool_history_directory()
        self.assertIsNone(result)

    def test_parse_invocation_id_valid(self):
        """Test parsing valid invocation ID."""
        dir_name = "2024-01-15_14-30-45_123456_test_tool"
        result = parse_invocation_id(dir_name)

        self.assertIsNotNone(result)
        self.assertEqual(result["invocation_id"], dir_name)
        self.assertEqual(result["tool_name"], "test_tool")
        self.assertIsInstance(result["timestamp"], datetime)
        self.assertEqual(result["timestamp"].year, 2024)
        self.assertEqual(result["timestamp"].month, 1)
        self.assertEqual(result["timestamp"].day, 15)

    def test_parse_invocation_id_with_underscore_in_toolname(self):
        """Test parsing invocation ID with underscores in tool name."""
        dir_name = "2024-01-15_14-30-45_123456_complex_tool_name"
        result = parse_invocation_id(dir_name)

        self.assertIsNotNone(result)
        self.assertEqual(result["tool_name"], "complex_tool_name")

    def test_parse_invocation_id_invalid(self):
        """Test parsing invalid invocation ID."""
        result = parse_invocation_id("invalid_format")
        self.assertIsNone(result)

        result = parse_invocation_id("2024-01-15_invalid_time")
        self.assertIsNone(result)

    def test_read_tool_history_record_success(self):
        """Test reading valid tool history record."""
        dir_name = self.create_sample_invocation("test_tool")
        invocation_dir = self.test_history_dir / dir_name

        result = read_tool_history_record(invocation_dir)

        self.assertIsNotNone(result)
        self.assertEqual(result["tool"], "test_tool")
        self.assertTrue(result["success"])
        self.assertEqual(result["duration_ms"], 150)

    def test_read_tool_history_record_nonexistent(self):
        """Test reading from nonexistent directory."""
        nonexistent_dir = self.test_history_dir / "nonexistent"
        result = read_tool_history_record(nonexistent_dir)
        self.assertIsNone(result)

    def test_read_tool_history_record_invalid_json(self):
        """Test reading invalid JSON record."""
        # Create directory with invalid JSON
        invocation_dir = self.test_history_dir / "test_invalid"
        invocation_dir.mkdir(exist_ok=True)

        record_file = invocation_dir / "record.jsonl"
        with open(record_file, 'w', encoding='utf-8') as f:
            f.write("invalid json content")

        result = read_tool_history_record(invocation_dir)
        self.assertIsNone(result)

    def test_get_tool_history_entries_basic(self):
        """Test getting tool history entries with basic functionality."""
        # Create sample invocations
        self.create_sample_invocation("tool1", success=True)
        self.create_sample_invocation("tool2", success=False)

        result = get_tool_history_entries()

        self.assertTrue(result["success"])
        self.assertEqual(len(result["history"]), 2)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["per_page"], 50)
        self.assertEqual(result["total_pages"], 1)

    def test_get_tool_history_entries_pagination(self):
        """Test pagination in tool history entries."""
        # Create multiple invocations
        for i in range(5):
            self.create_sample_invocation(f"tool{i}")

        result = get_tool_history_entries(page=1, per_page=2)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["history"]), 2)
        self.assertEqual(result["total"], 5)
        self.assertEqual(result["total_pages"], 3)

        # Test second page
        result = get_tool_history_entries(page=2, per_page=2)
        self.assertEqual(len(result["history"]), 2)

        # Test last page
        result = get_tool_history_entries(page=3, per_page=2)
        self.assertEqual(len(result["history"]), 1)

    def test_get_tool_history_entries_tool_filter(self):
        """Test filtering by tool name."""
        self.create_sample_invocation("tool1")
        self.create_sample_invocation("tool2")
        self.create_sample_invocation("tool1")

        result = get_tool_history_entries(tool_filter="tool1")

        self.assertTrue(result["success"])
        self.assertEqual(len(result["history"]), 2)
        self.assertEqual(result["total"], 2)

        for entry in result["history"]:
            self.assertEqual(entry["tool"], "tool1")

    def test_get_tool_history_entries_success_filter(self):
        """Test filtering by success status."""
        self.create_sample_invocation("tool1", success=True)
        self.create_sample_invocation("tool2", success=False)
        self.create_sample_invocation("tool3", success=True)

        result = get_tool_history_entries(success_filter=True)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["history"]), 2)
        self.assertEqual(result["total"], 2)

        for entry in result["history"]:
            self.assertTrue(entry["success"])

    def test_get_tool_history_entries_date_filter(self):
        """Test filtering by date range."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        self.create_sample_invocation("tool1", timestamp=yesterday)
        self.create_sample_invocation("tool2", timestamp=now)
        self.create_sample_invocation("tool3", timestamp=tomorrow)

        # Filter for entries from today onwards
        result = get_tool_history_entries(start_date=now)

        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 2)  # now and tomorrow

        # Filter for entries until today
        result = get_tool_history_entries(end_date=now)

        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 2)  # yesterday and now

    def test_get_tool_history_entries_search(self):
        """Test search functionality."""
        # Create invocations with different arguments
        dir_name = self.create_sample_invocation("tool1")
        invocation_dir = self.test_history_dir / dir_name

        # Modify record to have searchable content
        record = {
            "tool": "tool1",
            "arguments": {"search_param": "findme", "other": "value"},
            "result": {"output": "result"},
            "success": True,
            "duration_ms": 100
        }

        record_file = invocation_dir / "record.jsonl"
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(record, f)

        self.create_sample_invocation("tool2")  # This won't match

        result = get_tool_history_entries(search="findme")

        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["history"][0]["tool"], "tool1")

    def test_get_tool_history_entries_disabled(self):
        """Test getting entries when tool history is disabled."""
        self.mock_env.is_tool_history_enabled.return_value = False

        result = get_tool_history_entries()

        self.assertFalse(result["success"])
        self.assertIn("disabled", result["error"])
        self.assertEqual(result["total"], 0)

    def test_get_tool_history_stats_basic(self):
        """Test getting basic statistics."""
        self.create_sample_invocation("tool1", success=True)
        self.create_sample_invocation("tool2", success=False)
        self.create_sample_invocation("tool1", success=True)

        result = get_tool_history_stats()

        self.assertTrue(result["success"])
        self.assertEqual(result["total_invocations"], 3)
        self.assertEqual(result["successful_invocations"], 2)
        self.assertEqual(result["failed_invocations"], 1)
        self.assertEqual(result["average_duration_ms"], 150)
        self.assertEqual(result["total_duration_ms"], 450)

        # Check tool-specific stats
        self.assertIn("tool1", result["tools"])
        self.assertIn("tool2", result["tools"])

        tool1_stats = result["tools"]["tool1"]
        self.assertEqual(tool1_stats["count"], 2)
        self.assertEqual(tool1_stats["successful"], 2)
        self.assertEqual(tool1_stats["failed"], 0)

        tool2_stats = result["tools"]["tool2"]
        self.assertEqual(tool2_stats["count"], 1)
        self.assertEqual(tool2_stats["successful"], 0)
        self.assertEqual(tool2_stats["failed"], 1)

    def test_get_tool_history_stats_date_range(self):
        """Test date range in statistics."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        self.create_sample_invocation("tool1", timestamp=yesterday)
        self.create_sample_invocation("tool2", timestamp=now)

        result = get_tool_history_stats()

        self.assertTrue(result["success"])
        self.assertIsNotNone(result["date_range"]["earliest"])
        self.assertIsNotNone(result["date_range"]["latest"])

        # Parse dates to verify order
        earliest = datetime.fromisoformat(result["date_range"]["earliest"])
        latest = datetime.fromisoformat(result["date_range"]["latest"])
        self.assertLess(earliest, latest)

    def test_get_tool_history_stats_disabled(self):
        """Test getting stats when tool history is disabled."""
        self.mock_env.is_tool_history_enabled.return_value = False

        result = get_tool_history_stats()

        self.assertFalse(result["success"])
        self.assertIn("disabled", result["error"])

    def test_get_tool_history_detail_success(self):
        """Test getting detail for specific invocation."""
        dir_name = self.create_sample_invocation("test_tool")

        result = get_tool_history_detail(dir_name)

        self.assertTrue(result["success"])
        self.assertIn("invocation", result)

        invocation = result["invocation"]
        self.assertEqual(invocation["invocation_id"], dir_name)
        self.assertEqual(invocation["tool"], "test_tool")
        self.assertTrue(invocation["success"])
        self.assertEqual(invocation["duration_ms"], 150)
        self.assertIn("arguments", invocation)
        self.assertIn("result", invocation)

    def test_get_tool_history_detail_with_error(self):
        """Test getting detail for failed invocation."""
        dir_name = self.create_sample_invocation("test_tool", success=False)

        result = get_tool_history_detail(dir_name)

        self.assertTrue(result["success"])
        invocation = result["invocation"]
        self.assertFalse(invocation["success"])
        self.assertIn("error", invocation)
        self.assertEqual(invocation["error"], "Test error message")

    def test_get_tool_history_detail_nonexistent(self):
        """Test getting detail for nonexistent invocation."""
        result = get_tool_history_detail("nonexistent_invocation")

        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])

    def test_get_tool_history_detail_invalid_format(self):
        """Test getting detail with invalid invocation ID format."""
        # Create directory with invalid format
        invalid_dir = self.test_history_dir / "invalid_format"
        invalid_dir.mkdir(exist_ok=True)

        result = get_tool_history_detail("invalid_format")

        self.assertFalse(result["success"])
        self.assertIn("Invalid invocation ID", result["error"])

    def test_get_tool_history_detail_disabled(self):
        """Test getting detail when tool history is disabled."""
        self.mock_env.is_tool_history_enabled.return_value = False

        result = get_tool_history_detail("some_id")

        self.assertFalse(result["success"])
        self.assertIn("disabled", result["error"])

    def test_clear_tool_history_success(self):
        """Test clearing tool history successfully."""
        # Create some invocations
        self.create_sample_invocation("tool1")
        self.create_sample_invocation("tool2")
        self.create_sample_invocation("tool3")

        # Verify they exist
        self.assertEqual(len(list(self.test_history_dir.iterdir())), 3)

        result = clear_tool_history()

        self.assertTrue(result["success"])
        self.assertIn("Cleared 3 tool history entries", result["message"])

        # Verify they're gone
        self.assertEqual(len(list(self.test_history_dir.iterdir())), 0)

    def test_clear_tool_history_empty(self):
        """Test clearing empty tool history."""
        result = clear_tool_history()

        self.assertTrue(result["success"])
        self.assertIn("Cleared 0 tool history entries", result["message"])

    def test_clear_tool_history_disabled(self):
        """Test clearing when tool history is disabled."""
        self.mock_env.is_tool_history_enabled.return_value = False

        result = clear_tool_history()

        self.assertFalse(result["success"])
        self.assertIn("disabled", result["error"])

    def test_error_handling_in_get_entries(self):
        """Test error handling in get_tool_history_entries."""
        # Create an entry with a corrupted record file
        dir_name = self.create_sample_invocation("tool1")
        invocation_dir = self.test_history_dir / dir_name

        # Corrupt the record file
        record_file = invocation_dir / "record.jsonl"
        with open(record_file, 'w', encoding='utf-8') as f:
            f.write("corrupted json {")

        # Should still return success but skip the corrupted entry
        result = get_tool_history_entries()

        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 0)  # Corrupted entry should be skipped

    def test_error_handling_in_get_stats(self):
        """Test error handling in get_tool_history_stats."""
        # Create an entry with a corrupted record file
        dir_name = self.create_sample_invocation("tool1")
        invocation_dir = self.test_history_dir / dir_name

        # Corrupt the record file
        record_file = invocation_dir / "record.jsonl"
        with open(record_file, 'w', encoding='utf-8') as f:
            f.write("corrupted json {")

        # Should still return success but skip the corrupted entry
        result = get_tool_history_stats()

        self.assertTrue(result["success"])
        self.assertEqual(result["total_invocations"], 0)  # Corrupted entry should be skipped

    def test_sorting_by_timestamp(self):
        """Test that entries are sorted by timestamp (newest first)."""
        now = datetime.now()
        timestamps = [
            now - timedelta(hours=2),
            now - timedelta(hours=1),
            now
        ]

        # Create invocations in random order
        self.create_sample_invocation("tool2", timestamp=timestamps[1])
        self.create_sample_invocation("tool1", timestamp=timestamps[0])
        self.create_sample_invocation("tool3", timestamp=timestamps[2])

        result = get_tool_history_entries()

        self.assertTrue(result["success"])
        self.assertEqual(len(result["history"]), 3)

        # Verify ordering (newest first)
        self.assertEqual(result["history"][0]["tool"], "tool3")
        self.assertEqual(result["history"][1]["tool"], "tool2")
        self.assertEqual(result["history"][2]["tool"], "tool1")

    def test_relative_path_handling(self):
        """Test handling of relative paths in get_tool_history_directory."""
        # Mock a relative path
        self.mock_env.get_tool_history_path.return_value = "relative/path"

        # Mock the current file path
        with patch('server.tool_history_manager.Path') as mock_path:
            mock_path.return_value.resolve.return_value.parent = Path("/absolute/base")
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.is_dir.return_value = True

            result = get_tool_history_directory()

            # Should convert relative path to absolute
            self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
