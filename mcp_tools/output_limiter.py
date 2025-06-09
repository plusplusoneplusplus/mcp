"""Output length management for script-based tools.

This module provides functionality to limit and truncate command outputs
to prevent memory issues, improve readability, and manage large outputs.
"""

import re
import logging
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)


class OutputLimiter:
    """Handles output length management with various truncation strategies."""

    def __init__(self):
        """Initialize the output limiter."""
        pass

    def apply_output_limits(self, result: Dict, limits: Dict) -> Dict:
        """Apply output length limits to command result.

        Args:
            result: The command execution result
            limits: The output_limits configuration

        Returns:
            Modified result with output limits applied
        """
        if not limits:
            return result

        # Create a copy to avoid modifying the original
        processed_result = result.copy()

        stdout = result.get("output", "")
        stderr = result.get("error", "")

        # Preserve raw outputs if requested
        if limits.get("preserve_raw", False):
            processed_result["raw_output"] = stdout
            processed_result["raw_error"] = stderr

        # Apply individual limits
        max_stdout = limits.get("max_stdout_length")
        max_stderr = limits.get("max_stderr_length")

        if max_stdout and len(stdout) > max_stdout:
            processed_result["output"] = self._truncate_text(stdout, max_stdout, limits)

        if max_stderr and len(stderr) > max_stderr:
            processed_result["error"] = self._truncate_text(stderr, max_stderr, limits)

        # Apply total limit
        max_total = limits.get("max_total_length")
        if max_total:
            current_total = len(processed_result.get("output", "")) + len(processed_result.get("error", ""))
            if current_total > max_total:
                processed_result["output"], processed_result["error"] = self._truncate_combined(
                    processed_result.get("output", ""), processed_result.get("error", ""), max_total, limits
                )

        return processed_result

    def _truncate_text(self, text: str, max_length: int, limits: Dict) -> str:
        """Truncate text using specified strategy.

        Args:
            text: Text to truncate
            max_length: Maximum allowed length
            limits: Configuration with truncation strategy and options

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text

        strategy = limits.get("truncate_strategy", "end")
        message = limits.get("truncate_message", "\n... (truncated)")

        if strategy == "end":
            return self._truncate_end(text, max_length, message, limits)
        elif strategy == "start":
            return self._truncate_start(text, max_length, message, limits)
        elif strategy == "middle":
            return self._truncate_middle(text, max_length, message, limits)
        elif strategy == "smart":
            return self._truncate_smart(text, max_length, message, limits)

        # Fallback to simple truncation
        return text[:max_length - len(message)] + message

    def _truncate_end(self, text: str, max_length: int, message: str, limits: Dict) -> str:
        """Keep beginning, truncate end.

        Args:
            text: Text to truncate
            max_length: Maximum allowed length
            message: Truncation message
            limits: Configuration with line preservation options

        Returns:
            Truncated text
        """
        preserve_first_lines = limits.get("preserve_first_lines", 0)

        if preserve_first_lines > 0:
            lines = text.split('\n')
            if len(lines) > preserve_first_lines:
                preserved_lines = lines[:preserve_first_lines]
                preserved_text = '\n'.join(preserved_lines)

                # If preserved text plus message fits, use it
                if len(preserved_text) + len(message) <= max_length:
                    return preserved_text + message

        # Standard end truncation
        return text[:max_length - len(message)] + message

    def _truncate_start(self, text: str, max_length: int, message: str, limits: Dict) -> str:
        """Keep end, truncate beginning.

        Args:
            text: Text to truncate
            max_length: Maximum allowed length
            message: Truncation message
            limits: Configuration with line preservation options

        Returns:
            Truncated text
        """
        preserve_last_lines = limits.get("preserve_last_lines", 0)

        if preserve_last_lines > 0:
            lines = text.split('\n')
            if len(lines) > preserve_last_lines:
                preserved_lines = lines[-preserve_last_lines:]
                preserved_text = '\n'.join(preserved_lines)

                # If preserved text plus message fits, use it
                if len(preserved_text) + len(message) <= max_length:
                    return message + preserved_text

        # Standard start truncation
        return message + text[-(max_length - len(message)):]

    def _truncate_middle(self, text: str, max_length: int, message: str, limits: Dict) -> str:
        """Keep beginning and end, truncate middle.

        Args:
            text: Text to truncate
            max_length: Maximum allowed length
            message: Truncation message
            limits: Configuration with line preservation options

        Returns:
            Truncated text
        """
        preserve_first_lines = limits.get("preserve_first_lines", 0)
        preserve_last_lines = limits.get("preserve_last_lines", 0)

        if preserve_first_lines > 0 or preserve_last_lines > 0:
            lines = text.split('\n')

            first_lines = lines[:preserve_first_lines] if preserve_first_lines > 0 else []
            last_lines = lines[-preserve_last_lines:] if preserve_last_lines > 0 else []

            first_text = '\n'.join(first_lines) if first_lines else ""
            last_text = '\n'.join(last_lines) if last_lines else ""

            combined_length = len(first_text) + len(last_text) + len(message)
            if combined_length <= max_length:
                if first_text and last_text:
                    return first_text + message + last_text
                elif first_text:
                    return first_text + message
                elif last_text:
                    return message + last_text

        # Standard middle truncation
        available_length = max_length - len(message)
        half_length = available_length // 2

        start_part = text[:half_length]
        end_part = text[-(available_length - half_length):]

        return start_part + message + end_part

    def _truncate_smart(self, text: str, max_length: int, message: str, limits: Dict) -> str:
        """Apply intelligent truncation preserving important content.

        Args:
            text: Text to truncate
            max_length: Maximum allowed length
            message: Truncation message
            limits: Configuration with line preservation options

        Returns:
            Truncated text with smart preservation
        """
        lines = text.split('\n')

        # Identify important lines (errors, warnings, etc.)
        important_patterns = [
            r'\b(error|exception|failed|failure)\b',
            r'\b(warning|warn)\b',
            r'\b(stack trace|traceback)\b',
            r'^\d{4}-\d{2}-\d{2}.*\b(error|exception|failed)\b'  # timestamped errors
        ]

        important_lines = []
        normal_lines = []

        for i, line in enumerate(lines):
            is_important = False
            for pattern in important_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    is_important = True
                    break

            if is_important:
                important_lines.append((i, line))
            else:
                normal_lines.append((i, line))

        # Preserve important lines and recent output
        preserve_last_lines = limits.get("preserve_last_lines", 10)
        preserve_first_lines = limits.get("preserve_first_lines", 5)

        # Build list of lines to preserve with their original order
        lines_to_preserve = []

        # Add important lines first (they have highest priority)
        for i, line in important_lines:
            lines_to_preserve.append((i, line))

        # Add first lines if specified
        if preserve_first_lines > 0:
            for i in range(min(preserve_first_lines, len(lines))):
                if not any(idx == i for idx, _ in lines_to_preserve):
                    lines_to_preserve.append((i, lines[i]))

        # Add last lines if specified
        if preserve_last_lines > 0:
            start_idx = max(0, len(lines) - preserve_last_lines)
            for i in range(start_idx, len(lines)):
                if not any(idx == i for idx, _ in lines_to_preserve):
                    lines_to_preserve.append((i, lines[i]))

        # Sort by original line order
        lines_to_preserve.sort(key=lambda x: x[0])

        # Build preserved text
        preserved_lines = [line for _, line in lines_to_preserve]
        preserved_text = '\n'.join(preserved_lines)

        # If it fits within the limit, return it
        if len(preserved_text) + len(message) <= max_length:
            return preserved_text + message

        # If still too long, try to fit just the important lines
        if important_lines:
            important_text = '\n'.join([line for _, line in important_lines])
            if len(important_text) + len(message) <= max_length:
                return important_text + message

        # If important lines still don't fit, try to preserve them with truncation
        if important_lines:
            # Calculate available space for important content
            available_space = max_length - len(message)

            # Try to fit as many important lines as possible
            result_lines = []
            current_length = 0

            for _, line in important_lines:
                line_length = len(line) + 1  # +1 for newline
                if current_length + line_length <= available_space:
                    result_lines.append(line)
                    current_length += line_length
                else:
                    # Truncate this line to fit
                    remaining_space = available_space - current_length
                    if remaining_space > 10:  # Only if we have reasonable space
                        truncated_line = line[:remaining_space-3] + "..."
                        result_lines.append(truncated_line)
                    break

            if result_lines:
                return '\n'.join(result_lines) + message

        # If still too long, fall back to middle truncation
        return self._truncate_middle(text, max_length, message, limits)

    def _truncate_combined(self, stdout: str, stderr: str, max_total: int, limits: Dict) -> Tuple[str, str]:
        """Truncate combined stdout and stderr to fit within total limit.

        Args:
            stdout: Standard output text
            stderr: Standard error text
            max_total: Maximum combined length
            limits: Configuration options

        Returns:
            Tuple of (truncated_stdout, truncated_stderr)
        """
        current_total = len(stdout) + len(stderr)
        if current_total <= max_total:
            return stdout, stderr

        message = limits.get("truncate_message", "\n... (truncated)")
        strategy = limits.get("truncate_strategy", "end")

        # Prioritize stderr for errors, stdout for normal output
        if stderr and len(stderr.strip()) > 0:
            # Prioritize stderr - give it 60% of available space
            stderr_limit = int(max_total * 0.6)
            stdout_limit = max_total - stderr_limit
        else:
            # No stderr, give all space to stdout
            stdout_limit = max_total
            stderr_limit = 0

        # Truncate each part
        truncated_stdout = self._truncate_text(stdout, stdout_limit, limits) if stdout_limit > 0 else ""
        truncated_stderr = self._truncate_text(stderr, stderr_limit, limits) if stderr_limit > 0 else ""

        # Adjust if still over limit
        actual_total = len(truncated_stdout) + len(truncated_stderr)
        if actual_total > max_total:
            # Reduce stdout further
            reduction_needed = actual_total - max_total
            new_stdout_limit = max(0, len(truncated_stdout) - reduction_needed)
            truncated_stdout = self._truncate_text(stdout, new_stdout_limit, limits) if new_stdout_limit > 0 else ""

        return truncated_stdout, truncated_stderr
