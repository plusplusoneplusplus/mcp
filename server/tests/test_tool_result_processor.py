"""Tests for tool result processing utilities."""

import pytest
from typing import Any, List, Union
from mcp.types import TextContent, ImageContent

from server.tool_result_processor import process_tool_result, format_result_as_text


class TestProcessToolResult:
    """Test the process_tool_result function."""

    def test_list_of_content_objects_returned_as_is(self):
        """Test that a list of ImageContent/TextContent objects is returned as-is."""
        text_content = TextContent(type="text", text="Hello world")
        image_content = ImageContent(
            type="image", data="base64data", mimeType="image/png"
        )

        result = [text_content, image_content]
        processed = process_tool_result(result)

        assert processed == result
        assert len(processed) == 2
        assert isinstance(processed[0], TextContent)
        assert isinstance(processed[1], ImageContent)

    def test_list_of_dicts_converted_to_text_content(self):
        """Test that a list of dicts is converted to TextContent objects."""
        result = [
            {"type": "text", "text": "First message"},
            {"type": "text", "text": "Second message"},
        ]

        processed = process_tool_result(result)

        assert len(processed) == 2
        assert all(isinstance(item, TextContent) for item in processed)
        assert processed[0].text == "First message"
        assert processed[1].text == "Second message"

    def test_list_of_objects_with_type_text_attributes(self):
        """Test objects with type and text attributes are converted properly."""

        class MockObject:
            def __init__(self, type_val: str, text_val: str, annotations=None):
                self.type = type_val
                self.text = text_val
                self.annotations = annotations

        result = [
            MockObject("text", "Object 1"),
            MockObject("text", "Object 2", {"highlight": True}),
        ]

        processed = process_tool_result(result)

        assert len(processed) == 2
        assert all(isinstance(item, TextContent) for item in processed)
        assert processed[0].text == "Object 1"
        assert processed[1].text == "Object 2"
        assert processed[1].annotations.highlight == True

    def test_mixed_list_converted_to_string(self):
        """Test that mixed/unknown list contents are converted to string."""
        result = [1, "text", {"key": "value"}, None]

        processed = process_tool_result(result)

        assert len(processed) == 1
        assert isinstance(processed[0], TextContent)
        assert processed[0].type == "text"
        assert str(result) in processed[0].text

    def test_single_text_content_wrapped_in_list(self):
        """Test that a single TextContent object is wrapped in a list."""
        text_content = TextContent(type="text", text="Single content")

        processed = process_tool_result(text_content)

        assert len(processed) == 1
        assert processed[0] is text_content

    def test_single_image_content_wrapped_in_list(self):
        """Test that a single ImageContent object is wrapped in a list."""
        image_content = ImageContent(
            type="image", data="base64data", mimeType="image/jpeg"
        )

        processed = process_tool_result(image_content)

        assert len(processed) == 1
        assert processed[0] is image_content

    def test_dict_result_formatted_as_text(self):
        """Test that a dictionary result is formatted and wrapped in TextContent."""
        result = {"output": "Command executed successfully", "success": True}

        processed = process_tool_result(result)

        assert len(processed) == 1
        assert isinstance(processed[0], TextContent)
        assert processed[0].text == "Command executed successfully"

    def test_other_types_converted_to_string(self):
        """Test that other types are converted to string and wrapped."""
        test_cases = [
            (42, "42"),
            (3.14, "3.14"),
            (True, "True"),
            (None, "None"),
        ]

        for case, expected in test_cases:
            processed = process_tool_result(case)

            assert len(processed) == 1
            assert isinstance(processed[0], TextContent)
            assert processed[0].text == expected

    def test_dict_without_special_keys_formatted(self):
        """Test that dicts without special keys are formatted properly."""
        case = {"complex": "object", "another": "value"}
        processed = process_tool_result(case)

        assert len(processed) == 1
        assert isinstance(processed[0], TextContent)
        # Should be formatted by format_result_as_text
        assert "complex: object" in processed[0].text
        assert "another: value" in processed[0].text

    def test_empty_list_returns_empty_list(self):
        """Test that an empty list returns an empty list."""
        processed = process_tool_result([])

        assert processed == []

    def test_list_with_none_values(self):
        """Test handling of list with None values."""
        result = [None, None]

        processed = process_tool_result(result)

        assert len(processed) == 1
        assert isinstance(processed[0], TextContent)
        assert str(result) in processed[0].text


class TestFormatResultAsText:
    """Test the format_result_as_text function."""

    def test_error_result_formatted_correctly(self):
        """Test that error results are formatted with error prefix."""
        result = {"success": False, "error": "Command failed"}

        formatted = format_result_as_text(result)

        assert formatted == "Error: Command failed"

    def test_error_result_with_unknown_error(self):
        """Test error result without specific error message."""
        result = {"success": False}

        formatted = format_result_as_text(result)

        assert formatted == "Error: Unknown error"

    def test_output_result_returns_output_value(self):
        """Test that results with 'output' key return the output value."""
        result = {"output": "Hello world", "success": True}

        formatted = format_result_as_text(result)

        assert formatted == "Hello world"

    def test_empty_output_returns_empty_string(self):
        """Test that empty output returns empty string."""
        result = {"output": "", "success": True}

        formatted = format_result_as_text(result)

        assert formatted == ""

    def test_html_result_formatted_with_length(self):
        """Test that HTML results are formatted with length information."""
        html_content = "<html><body>Test</body></html>"
        result = {
            "html": html_content,
            "html_length": len(html_content),
            "success": True,
        }

        formatted = format_result_as_text(result)

        expected = f"HTML content (length: {len(html_content)}):\n{html_content}"
        assert formatted == expected

    def test_html_result_without_length(self):
        """Test HTML result without html_length field."""
        html_content = "<p>Simple HTML</p>"
        result = {"html": html_content, "success": True}

        formatted = format_result_as_text(result)

        expected = f"HTML content (length: 0):\n{html_content}"
        assert formatted == expected

    def test_generic_result_formatting(self):
        """Test generic result formatting for other dictionary types."""
        result = {
            "status": "completed",
            "count": 42,
            "message": "Processing finished",
            "success": True,
        }

        formatted = format_result_as_text(result)

        # Should exclude 'success' key
        expected_parts = [
            "status: completed",
            "count: 42",
            "message: Processing finished",
        ]
        for part in expected_parts:
            assert part in formatted
        assert "success:" not in formatted

    def test_result_without_success_field_treated_as_successful(self):
        """Test that results without 'success' field are treated as successful."""
        result = {"data": "some value", "info": "additional info"}

        formatted = format_result_as_text(result)

        expected_parts = ["data: some value", "info: additional info"]
        for part in expected_parts:
            assert part in formatted

    def test_empty_dict_returns_empty_string(self):
        """Test that empty dictionary returns empty string."""
        result = {}

        formatted = format_result_as_text(result)

        assert formatted == ""

    def test_dict_with_only_success_returns_empty_string(self):
        """Test that dict with only 'success' key returns empty string."""
        result = {"success": True}

        formatted = format_result_as_text(result)

        assert formatted == ""


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_command_executor_success_result(self):
        """Test typical command executor success result."""
        result = {
            "success": True,
            "output": "File copied successfully",
            "return_code": 0,
        }

        processed = process_tool_result(result)

        assert len(processed) == 1
        assert isinstance(processed[0], TextContent)
        assert processed[0].text == "File copied successfully"

    def test_command_executor_error_result(self):
        """Test typical command executor error result."""
        result = {"success": False, "error": "Permission denied", "return_code": 1}

        processed = process_tool_result(result)

        assert len(processed) == 1
        assert isinstance(processed[0], TextContent)
        assert "Error: Permission denied" in processed[0].text

    def test_browser_screenshot_result(self):
        """Test browser tool returning image content."""
        image_content = ImageContent(
            type="image",
            data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
            mimeType="image/png",
        )

        processed = process_tool_result([image_content])

        assert len(processed) == 1
        assert isinstance(processed[0], ImageContent)
        assert processed[0].mimeType == "image/png"

    def test_mixed_content_result(self):
        """Test result with both text and image content."""
        text_content = TextContent(type="text", text="Screenshot taken")
        image_content = ImageContent(
            type="image", data="base64imagedata", mimeType="image/png"
        )

        result = [text_content, image_content]
        processed = process_tool_result(result)

        assert len(processed) == 2
        assert isinstance(processed[0], TextContent)
        assert isinstance(processed[1], ImageContent)
        assert processed[0].text == "Screenshot taken"

    def test_yaml_tool_dict_list_result(self):
        """Test YAML tool returning list of text content dicts."""
        result = [
            {"type": "text", "text": "Step 1: Initialization"},
            {"type": "text", "text": "Step 2: Processing"},
            {"type": "text", "text": "Step 3: Completion"},
        ]

        processed = process_tool_result(result)

        assert len(processed) == 3
        assert all(isinstance(item, TextContent) for item in processed)
        assert processed[0].text == "Step 1: Initialization"
        assert processed[1].text == "Step 2: Processing"
        assert processed[2].text == "Step 3: Completion"
