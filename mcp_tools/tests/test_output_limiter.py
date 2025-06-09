"""Tests for output length management functionality."""

import pytest
from mcp_tools.output_limiter import OutputLimiter


class TestOutputLimiter:
    """Test cases for OutputLimiter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.limiter = OutputLimiter()

    def test_no_limits_applied_when_empty_config(self):
        """Test that no limits are applied when config is empty."""
        result = {"output": "test output", "error": "test error"}
        processed = self.limiter.apply_output_limits(result, {})

        assert processed == result

    def test_no_limits_applied_when_none_config(self):
        """Test that no limits are applied when config is None."""
        result = {"output": "test output", "error": "test error"}
        processed = self.limiter.apply_output_limits(result, None)

        assert processed == result

    def test_preserve_raw_output(self):
        """Test that raw output is preserved when requested."""
        result = {"output": "original stdout", "error": "original stderr"}
        limits = {"preserve_raw": True}

        processed = self.limiter.apply_output_limits(result, limits)

        assert processed["raw_output"] == "original stdout"
        assert processed["raw_error"] == "original stderr"

    def test_max_stdout_length_truncation(self):
        """Test stdout length limiting."""
        long_output = "x" * 1000
        result = {"output": long_output, "error": ""}
        limits = {"max_stdout_length": 100}

        processed = self.limiter.apply_output_limits(result, limits)

        assert len(processed["output"]) <= 100
        assert "... (truncated)" in processed["output"]

    def test_max_stderr_length_truncation(self):
        """Test stderr length limiting."""
        long_error = "e" * 1000
        result = {"output": "", "error": long_error}
        limits = {"max_stderr_length": 100}

        processed = self.limiter.apply_output_limits(result, limits)

        assert len(processed["error"]) <= 100
        assert "... (truncated)" in processed["error"]

    def test_max_total_length_truncation(self):
        """Test total length limiting."""
        result = {"output": "o" * 300, "error": "e" * 300}
        limits = {"max_total_length": 400}

        processed = self.limiter.apply_output_limits(result, limits)

        total_length = len(processed["output"]) + len(processed["error"])
        assert total_length <= 400

    def test_truncate_end_strategy(self):
        """Test end truncation strategy."""
        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        limits = {"truncate_strategy": "end", "truncate_message": "...TRUNCATED"}

        result = self.limiter._truncate_text(text, 20, limits)

        assert result.startswith("Line 1")
        assert result.endswith("...TRUNCATED")
        assert len(result) <= 20

    def test_truncate_start_strategy(self):
        """Test start truncation strategy."""
        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        limits = {"truncate_strategy": "start", "truncate_message": "TRUNCATED..."}

        result = self.limiter._truncate_text(text, 20, limits)

        assert result.startswith("TRUNCATED...")
        assert result.endswith("Line 5")
        assert len(result) <= 20

    def test_truncate_middle_strategy(self):
        """Test middle truncation strategy."""
        text = "Start content here and end content here"
        limits = {"truncate_strategy": "middle", "truncate_message": "...MID..."}

        result = self.limiter._truncate_text(text, 25, limits)

        assert result.startswith("Start")
        assert result.endswith("here")
        assert "...MID..." in result
        assert len(result) <= 25

    def test_truncate_smart_strategy_preserves_errors(self):
        """Test smart truncation preserves error messages."""
        text = "Normal line 1\nERROR: Critical failure\nNormal line 2\nWARNING: Issue detected\nNormal line 3"
        limits = {"truncate_strategy": "smart", "truncate_message": "...SMART..."}

        result = self.limiter._truncate_text(text, 50, limits)

        assert "ERROR: Critical failure" in result
        assert "WARNING:" in result  # Should at least preserve the start of warning lines

    def test_preserve_first_lines_with_end_strategy(self):
        """Test preserving first lines with end truncation."""
        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7"
        limits = {
            "truncate_strategy": "end",
            "preserve_first_lines": 2,
            "truncate_message": "...TRUNCATED"
        }

        result = self.limiter._truncate_text(text, 30, limits)

        assert "Line 1" in result
        assert "Line 2" in result
        assert "...TRUNCATED" in result

    def test_preserve_last_lines_with_start_strategy(self):
        """Test preserving last lines with start truncation."""
        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7"
        limits = {
            "truncate_strategy": "start",
            "preserve_last_lines": 2,
            "truncate_message": "TRUNCATED..."
        }

        result = self.limiter._truncate_text(text, 30, limits)

        assert "Line 6" in result
        assert "Line 7" in result
        assert "TRUNCATED..." in result

    def test_preserve_both_lines_with_middle_strategy(self):
        """Test preserving both first and last lines with middle truncation."""
        text = "First 1\nFirst 2\nMiddle 1\nMiddle 2\nMiddle 3\nLast 1\nLast 2"
        limits = {
            "truncate_strategy": "middle",
            "preserve_first_lines": 2,
            "preserve_last_lines": 2,
            "truncate_message": "...MIDDLE..."
        }

        result = self.limiter._truncate_text(text, 40, limits)

        assert "First 1" in result
        assert "First 2" in result
        assert "Last 1" in result
        assert "Last 2" in result
        assert "...MIDDLE..." in result

    def test_custom_truncate_message(self):
        """Test custom truncation message."""
        text = "x" * 100
        limits = {"truncate_message": "*** CUSTOM MESSAGE ***"}

        result = self.limiter._truncate_text(text, 50, limits)

        assert "*** CUSTOM MESSAGE ***" in result

    def test_no_truncation_when_under_limit(self):
        """Test that no truncation occurs when text is under limit."""
        text = "Short text"
        limits = {"max_stdout_length": 100}

        result = self.limiter._truncate_text(text, 100, limits)

        assert result == text

    def test_combined_stdout_stderr_limits(self):
        """Test applying both stdout and stderr limits."""
        result = {"output": "o" * 200, "error": "e" * 200}
        limits = {
            "max_stdout_length": 50,
            "max_stderr_length": 50,
            "truncate_message": "...CUT"
        }

        processed = self.limiter.apply_output_limits(result, limits)

        assert len(processed["output"]) <= 50
        assert len(processed["error"]) <= 50
        assert "...CUT" in processed["output"]
        assert "...CUT" in processed["error"]

    def test_total_limit_with_stderr_priority(self):
        """Test total limit prioritizes stderr when both exist."""
        result = {"output": "o" * 100, "error": "e" * 100}
        limits = {"max_total_length": 120}

        processed = self.limiter.apply_output_limits(result, limits)

        total_length = len(processed["output"]) + len(processed["error"])
        assert total_length <= 120
        # stderr should get more space (60% of 120 = 72)
        assert len(processed["error"]) >= len(processed["output"])

    def test_total_limit_stdout_only(self):
        """Test total limit with only stdout."""
        result = {"output": "o" * 200, "error": ""}
        limits = {"max_total_length": 100}

        processed = self.limiter.apply_output_limits(result, limits)

        assert len(processed["output"]) <= 100

    def test_smart_truncation_with_timestamped_errors(self):
        """Test smart truncation preserves timestamped errors."""
        text = "2024-01-01 10:00:00 INFO: Starting process\n2024-01-01 10:01:00 ERROR: Database connection failed\n2024-01-01 10:02:00 INFO: Retrying connection"
        limits = {"truncate_strategy": "smart"}

        result = self.limiter._truncate_text(text, 80, limits)

        assert "ERROR: Database connection failed" in result

    def test_fallback_to_simple_truncation(self):
        """Test fallback to simple truncation for unknown strategy."""
        text = "x" * 100
        limits = {"truncate_strategy": "unknown", "truncate_message": "...FALLBACK"}

        result = self.limiter._truncate_text(text, 50, limits)

        assert len(result) <= 50
        assert result.endswith("...FALLBACK")

    def test_empty_output_handling(self):
        """Test handling of empty output."""
        result = {"output": "", "error": ""}
        limits = {"max_stdout_length": 100, "max_stderr_length": 100}

        processed = self.limiter.apply_output_limits(result, limits)

        assert processed["output"] == ""
        assert processed["error"] == ""

    def test_missing_output_fields(self):
        """Test handling when output fields are missing."""
        result = {}
        limits = {"max_stdout_length": 100}

        processed = self.limiter.apply_output_limits(result, limits)

        # Should handle gracefully without errors
        assert "output" not in processed or processed["output"] == ""

    def test_preserve_raw_with_truncation(self):
        """Test that raw output is preserved even when truncation occurs."""
        original_output = "x" * 200
        original_error = "e" * 200
        result = {"output": original_output, "error": original_error}
        limits = {
            "max_stdout_length": 50,
            "max_stderr_length": 50,
            "preserve_raw": True
        }

        processed = self.limiter.apply_output_limits(result, limits)

        assert processed["raw_output"] == original_output
        assert processed["raw_error"] == original_error
        assert len(processed["output"]) <= 50
        assert len(processed["error"]) <= 50
