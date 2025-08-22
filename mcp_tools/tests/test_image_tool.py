"""
Tests for the ImageTool implementation.

This module tests the ImageTool that handles retrieving images and files
from configured image directories.
"""

import os
import pytest
import pytest_asyncio
import base64
import mimetypes
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock
from typing import List, Union

from mcp.types import ImageContent, TextContent
from mcp_tools.image_tool import ImageTool


class TestImageTool:
    """Test the ImageTool implementation."""

    def test_tool_properties(self):
        """Test that the tool has the correct properties."""
        tool = ImageTool()

        assert tool.name == "get_session_image"
        assert "image" in tool.description.lower()
        assert isinstance(tool.input_schema, dict)
        assert tool.input_schema["type"] == "object"
        assert "session_id" in tool.input_schema["properties"]
        assert "image_name" in tool.input_schema["properties"]
        assert tool.input_schema["required"] == ["session_id", "image_name"]

    @pytest.mark.asyncio
    async def test_missing_arguments(self):
        """Test error handling when required arguments are missing."""
        tool = ImageTool()

        # Test missing session_id
        result = await tool.execute_tool({"image_name": "test.png"})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "required" in result[0].text.lower()

        # Test missing image_name
        result = await tool.execute_tool({"session_id": "test_session"})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "required" in result[0].text.lower()

        # Test empty arguments
        result = await tool.execute_tool({})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "required" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_missing_image_dir_config(self):
        """Test error handling when IMAGE_DIR is not configured."""
        tool = ImageTool()

        # Directly call _get_image_dir with None setting to trigger RuntimeError
        with patch.object(
            tool,
            "_get_image_dir",
            side_effect=RuntimeError(
                "IMAGE_DIR is not defined in your MCP configuration"
            ),
        ):
            result = await tool.execute_tool(
                {"session_id": "test_session", "image_name": "test.png"}
            )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error retrieving image" in result[0].text
        assert "IMAGE_DIR" in result[0].text

    @pytest.mark.asyncio
    @patch("config.manager.env_manager")
    async def test_image_not_found(self, mock_env_manager):
        """Test handling when the requested image file doesn't exist."""
        # Mock environment manager
        mock_env_manager.get_setting.return_value = "/fake/image/dir"

        tool = ImageTool()

        result = await tool.execute_tool(
            {"session_id": "test_session", "image_name": "nonexistent.png"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert result[0].text == "Image not found."

    @pytest.mark.asyncio
    @patch("config.manager.env_manager")
    @patch("mcp_tools.image_tool.Path")
    async def test_json_file_handling(self, mock_path, mock_env_manager):
        """Test handling of JSON files."""
        # Mock environment manager
        mock_env_manager.get_setting.return_value = "/fake/image/dir"

        # Mock file path and reading
        mock_image_path = Mock()
        mock_image_path.is_file.return_value = True
        mock_image_path.__str__ = Mock(return_value="/fake/path/test.json")

        mock_path_class = Mock()
        mock_path_class.return_value = Mock()
        mock_path_class.return_value.__truediv__ = Mock(return_value=Mock())
        mock_path_class.return_value.__truediv__.return_value.__truediv__ = Mock(
            return_value=mock_image_path
        )
        mock_path.side_effect = mock_path_class

        # Mock JSON content
        json_content = '{"key": "value", "data": [1, 2, 3]}'

        with patch("builtins.open", mock_open(read_data=json_content)):
            tool = ImageTool()
            result = await tool.execute_tool(
                {"session_id": "test_session", "image_name": "test.json"}
            )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert result[0].text == json_content

    @pytest.mark.asyncio
    @patch("config.manager.env_manager")
    @patch("mcp_tools.image_tool.Path")
    @patch("mcp_tools.image_tool.mimetypes.guess_type")
    async def test_image_file_handling(
        self, mock_guess_type, mock_path, mock_env_manager
    ):
        """Test handling of actual image files."""
        # Mock environment manager
        mock_env_manager.get_setting.return_value = "/fake/image/dir"

        # Mock MIME type detection
        mock_guess_type.return_value = ("image/png", None)

        # Mock file path
        mock_image_path = Mock()
        mock_image_path.is_file.return_value = True
        mock_image_path.__str__ = Mock(return_value="/fake/path/test.png")

        mock_path_class = Mock()
        mock_path_class.return_value = Mock()
        mock_path_class.return_value.__truediv__ = Mock(return_value=Mock())
        mock_path_class.return_value.__truediv__.return_value.__truediv__ = Mock(
            return_value=mock_image_path
        )
        mock_path.side_effect = mock_path_class

        # Mock image content (fake PNG header)
        fake_image_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        )
        expected_b64 = base64.b64encode(fake_image_bytes).decode("utf-8")

        with patch("builtins.open", mock_open(read_data=fake_image_bytes)):
            tool = ImageTool()
            result = await tool.execute_tool(
                {"session_id": "test_session", "image_name": "test.png"}
            )

        assert len(result) == 1
        assert isinstance(result[0], ImageContent)
        assert result[0].type == "image"
        assert result[0].data == expected_b64
        assert result[0].mimeType == "image/png"

    @pytest.mark.asyncio
    @patch("config.manager.env_manager")
    @patch("mcp_tools.image_tool.Path")
    @patch("mcp_tools.image_tool.mimetypes.guess_type")
    async def test_unknown_mime_type(
        self, mock_guess_type, mock_path, mock_env_manager
    ):
        """Test handling when MIME type cannot be determined."""
        # Mock environment manager
        mock_env_manager.get_setting.return_value = "/fake/image/dir"

        # Mock MIME type detection to return None
        mock_guess_type.return_value = (None, None)

        # Mock file path
        mock_image_path = Mock()
        mock_image_path.is_file.return_value = True
        mock_image_path.__str__ = Mock(return_value="/fake/path/unknown.file")

        mock_path_class = Mock()
        mock_path_class.return_value = Mock()
        mock_path_class.return_value.__truediv__ = Mock(return_value=Mock())
        mock_path_class.return_value.__truediv__.return_value.__truediv__ = Mock(
            return_value=mock_image_path
        )
        mock_path.side_effect = mock_path_class

        # Mock file content
        fake_bytes = b"unknown file content"
        expected_b64 = base64.b64encode(fake_bytes).decode("utf-8")

        with patch("builtins.open", mock_open(read_data=fake_bytes)):
            tool = ImageTool()
            result = await tool.execute_tool(
                {"session_id": "test_session", "image_name": "unknown.file"}
            )

        assert len(result) == 1
        assert isinstance(result[0], ImageContent)
        assert result[0].type == "image"
        assert result[0].data == expected_b64
        assert result[0].mimeType == "application/octet-stream"

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test general exception handling."""
        tool = ImageTool()

        # Mock _get_image_dir to raise an exception
        with patch.object(
            tool, "_get_image_dir", side_effect=Exception("Test exception")
        ):
            result = await tool.execute_tool(
                {"session_id": "test_session", "image_name": "test.png"}
            )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error retrieving image" in result[0].text
        assert "Test exception" in result[0].text

    def test_diagnostic_dir_property(self):
        """Test that the diagnostic_dir property works correctly."""
        tool = ImageTool()

        # Test default value
        assert tool.diagnostic_dir is None

        # Test setting value
        tool.diagnostic_dir = "/tmp/diagnostics"
        assert tool.diagnostic_dir == "/tmp/diagnostics"

        # Test clearing value
        tool.diagnostic_dir = None
        assert tool.diagnostic_dir is None
