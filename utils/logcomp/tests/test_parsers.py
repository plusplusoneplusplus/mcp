"""Tests for the parsers module."""

import pytest
from utils.logcomp.parsers import (
    parse_timestamp,
    read_log_entries,
    get_available_algorithms,
    is_logparser_available
)
from utils.logcomp.types import LogEntry


def test_parse_timestamp():
    """Test timestamp parsing functionality."""
    # Test with valid timestamp
    line_with_ts = "2023-01-01 12:00:00,123 This is a log message"
    timestamp, content = parse_timestamp(line_with_ts)
    assert content == "This is a log message"
    assert isinstance(timestamp, float)

    # Test without timestamp
    line_without_ts = "This is a log message without timestamp"
    timestamp, content = parse_timestamp(line_without_ts)
    assert content == line_without_ts
    assert isinstance(timestamp, float)


def test_get_available_algorithms():
    """Test getting available algorithms."""
    algorithms = get_available_algorithms()
    assert isinstance(algorithms, list)
    # If logparser is available, we should have some algorithms
    if is_logparser_available():
        assert len(algorithms) > 0
        assert "drain" in algorithms
    else:
        assert len(algorithms) == 0


def test_is_logparser_available():
    """Test logparser availability check."""
    result = is_logparser_available()
    assert isinstance(result, bool)


def test_read_log_entries(tmp_path):
    """Test reading log entries from file."""
    # Create a temporary log file
    log_file = tmp_path / "test.log"
    log_content = """2023-01-01 12:00:00,123 First log message
2023-01-01 12:00:01,456 Second log message
Log without timestamp"""

    log_file.write_text(log_content)

    # Read log entries
    entries = read_log_entries(str(log_file))

    assert len(entries) == 3
    assert all(isinstance(entry, LogEntry) for entry in entries)
    assert entries[0].content == "First log message"
    assert entries[1].content == "Second log message"
    assert entries[2].content == "Log without timestamp"
