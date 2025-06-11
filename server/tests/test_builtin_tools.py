"""
Comprehensive test coverage for built-in tools.

This module tests all built-in tools that are directly integrated into the MCP server,
focusing on the get_session_image tool and server integration.

Test Categories:
- Tool definition validation
- Argument validation
- Successful operations
- Error handling
- File system interactions (mocked)
- Image handling and base64 encoding
- MIME type detection
- Server integration
"""

import os
import pytest
import pytest_asyncio
import base64
import mimetypes
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock
from typing import List, Union

# Import the modules under test
from server import image_tool
from mcp.types import Tool, ImageContent, TextContent


class TestGetSessionImageToolDefinition:
    """Test the get_session_image tool definition."""

    def test_get_tool_def_returns_valid_tool(self):
        """Test that get_tool_def() returns a valid Tool instance."""
        tool_def = image_tool.get_tool_def()
        
        assert isinstance(tool_def, Tool)
        assert tool_def.name == "get_session_image"
        assert tool_def.description
        assert isinstance(tool_def.description, str)
        assert len(tool_def.description) > 0

    def test_tool_input_schema_structure(self):
        """Test that the tool input schema has the correct structure."""
        tool_def = image_tool.get_tool_def()
        schema = tool_def.inputSchema
        
        assert isinstance(schema, dict)
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema

    def test_tool_required_parameters(self):
        """Test that the tool has the correct required parameters."""
        tool_def = image_tool.get_tool_def()
        schema = tool_def.inputSchema
        
        required_fields = schema["required"]
        assert "session_id" in required_fields
        assert "image_name" in required_fields
        assert len(required_fields) == 2

    def test_tool_parameter_types(self):
        """Test that the tool parameters have correct types."""
        tool_def = image_tool.get_tool_def()
        properties = tool_def.inputSchema["properties"]
        
        assert properties["session_id"]["type"] == "string"
        assert properties["image_name"]["type"] == "string"


class TestImageToolArgumentValidation:
    """Test argument validation in the image tool."""

    def test_handle_tool_missing_session_id(self):
        """Test error handling when session_id is missing."""
        arguments = {"image_name": "test.png"}
        result = image_tool.handle_tool(arguments)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert result[0].type == "text"
        assert "session_id and image_name are required" in result[0].text

    def test_handle_tool_missing_image_name(self):
        """Test error handling when image_name is missing."""
        arguments = {"session_id": "test_session"}
        result = image_tool.handle_tool(arguments)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert result[0].type == "text"
        assert "session_id and image_name are required" in result[0].text

    def test_handle_tool_missing_both_arguments(self):
        """Test error handling when both arguments are missing."""
        arguments = {}
        result = image_tool.handle_tool(arguments)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert result[0].type == "text"
        assert "session_id and image_name are required" in result[0].text

    @patch('server.image_tool.get_session_image')
    def test_handle_tool_valid_arguments(self, mock_get_session_image):
        """Test that handle_tool calls get_session_image with valid arguments."""
        mock_result = [ImageContent(type="image", data="fake_data", mimeType="image/png")]
        mock_get_session_image.return_value = mock_result
        
        arguments = {"session_id": "test_session", "image_name": "test.png"}
        result = image_tool.handle_tool(arguments)
        
        mock_get_session_image.assert_called_once_with("test_session", "test.png")
        assert result == mock_result


class TestGetImageDir:
    """Test the get_image_dir function."""

    @patch('config.env.get_setting')
    def test_get_image_dir_with_valid_setting(self, mock_get_setting):
        """Test get_image_dir when IMAGE_DIR is properly configured."""
        mock_get_setting.return_value = "/path/to/images"
        
        result = image_tool.get_image_dir()
        
        mock_get_setting.assert_called_once_with("image_dir", None)
        assert isinstance(result, Path)
        assert result == Path("/path/to/images")

    @patch('config.env.get_setting')
    def test_get_image_dir_missing_setting(self, mock_get_setting):
        """Test get_image_dir when IMAGE_DIR is not configured."""
        mock_get_setting.return_value = None
        
        with pytest.raises(RuntimeError) as exc_info:
            image_tool.get_image_dir()
        
        assert "IMAGE_DIR is not defined" in str(exc_info.value)
        assert "Set IMAGE_DIR in your .env file" in str(exc_info.value)


class TestGetSessionImageFunction:
    """Test the get_session_image function with various scenarios."""

    @patch('server.image_tool.get_image_dir')
    @patch('pathlib.Path.is_file')
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake_image_data')
    @patch('mimetypes.guess_type')
    def test_get_session_image_success_png(self, mock_guess_type, mock_file, mock_is_file, mock_get_dir):
        """Test successful image retrieval for PNG file."""
        # Setup mocks
        mock_image_dir = Path("/test/images")
        mock_get_dir.return_value = mock_image_dir
        mock_is_file.return_value = True
        mock_guess_type.return_value = ("image/png", None)
        
        # Call the function
        result = image_tool.get_session_image("test_session", "test.png")
        
        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], ImageContent)
        assert result[0].type == "image"
        assert result[0].mimeType == "image/png"
        
        # Verify base64 encoding
        expected_b64 = base64.b64encode(b'fake_image_data').decode('utf-8')
        assert result[0].data == expected_b64
        
        # Verify file path construction
        mock_is_file.assert_called_once()
        mock_guess_type.assert_called_once()

    @patch('server.image_tool.get_image_dir')
    @patch('pathlib.Path.is_file')
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake_jpeg_data')
    @patch('mimetypes.guess_type')
    def test_get_session_image_success_jpeg(self, mock_guess_type, mock_file, mock_is_file, mock_get_dir):
        """Test successful image retrieval for JPEG file."""
        # Setup mocks
        mock_image_dir = Path("/test/images")
        mock_get_dir.return_value = mock_image_dir
        mock_is_file.return_value = True
        mock_guess_type.return_value = ("image/jpeg", None)
        
        # Call the function
        result = image_tool.get_session_image("test_session", "photo.jpg")
        
        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], ImageContent)
        assert result[0].type == "image"
        assert result[0].mimeType == "image/jpeg"
        
        # Verify base64 encoding
        expected_b64 = base64.b64encode(b'fake_jpeg_data').decode('utf-8')
        assert result[0].data == expected_b64

    @patch('server.image_tool.get_image_dir')
    @patch('pathlib.Path.is_file')
    @patch('builtins.open', new_callable=mock_open, read_data=b'unknown_format_data')
    @patch('mimetypes.guess_type')
    def test_get_session_image_unknown_mime_type(self, mock_guess_type, mock_file, mock_is_file, mock_get_dir):
        """Test image retrieval when MIME type cannot be determined."""
        # Setup mocks
        mock_image_dir = Path("/test/images")
        mock_get_dir.return_value = mock_image_dir
        mock_is_file.return_value = True
        mock_guess_type.return_value = (None, None)  # Unknown MIME type
        
        # Call the function
        result = image_tool.get_session_image("test_session", "unknown.xyz")
        
        # Verify the result uses fallback MIME type
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], ImageContent)
        assert result[0].type == "image"
        assert result[0].mimeType == "application/octet-stream"

    @patch('server.image_tool.get_image_dir')
    @patch('pathlib.Path.is_file')
    def test_get_session_image_file_not_found(self, mock_is_file, mock_get_dir):
        """Test error handling when image file is not found."""
        # Setup mocks
        mock_image_dir = Path("/test/images")
        mock_get_dir.return_value = mock_image_dir
        mock_is_file.return_value = False
        
        # Call the function
        result = image_tool.get_session_image("test_session", "nonexistent.png")
        
        # Verify error response
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert result[0].type == "text"
        assert result[0].text == "Image not found."

    @patch('server.image_tool.get_image_dir')
    @patch('pathlib.Path.is_file')
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_get_session_image_permission_error(self, mock_file, mock_is_file, mock_get_dir):
        """Test error handling when file cannot be read due to permissions."""
        # Setup mocks
        mock_image_dir = Path("/test/images")
        mock_get_dir.return_value = mock_image_dir
        mock_is_file.return_value = True
        
        # Call the function and expect exception to propagate
        with pytest.raises(PermissionError):
            image_tool.get_session_image("test_session", "restricted.png")

    @patch('server.image_tool.get_image_dir')
    @patch('pathlib.Path.is_file')
    @patch('builtins.open', new_callable=mock_open, read_data=b'')
    @patch('mimetypes.guess_type')
    def test_get_session_image_empty_file(self, mock_guess_type, mock_file, mock_is_file, mock_get_dir):
        """Test handling of empty image files."""
        # Setup mocks
        mock_image_dir = Path("/test/images")
        mock_get_dir.return_value = mock_image_dir
        mock_is_file.return_value = True
        mock_guess_type.return_value = ("image/png", None)
        
        # Call the function
        result = image_tool.get_session_image("test_session", "empty.png")
        
        # Verify the result handles empty file
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], ImageContent)
        assert result[0].type == "image"
        assert result[0].data == ""  # Empty base64 string
        assert result[0].mimeType == "image/png"

    def test_get_session_image_path_construction(self):
        """Test that image paths are constructed correctly."""
        with patch('server.image_tool.get_image_dir') as mock_get_dir, \
             patch('pathlib.Path.is_file') as mock_is_file:
            
            mock_image_dir = Path("/test/images")
            mock_get_dir.return_value = mock_image_dir
            mock_is_file.return_value = False
            
            # Call the function
            image_tool.get_session_image("my_session", "my_image.png")
            
            # Verify the path construction by checking what path was tested
            # The is_file method should be called on the constructed path
            mock_is_file.assert_called_once()


class TestMimeTypeDetection:
    """Test MIME type detection for various file formats."""

    @patch('server.image_tool.get_image_dir')
    @patch('pathlib.Path.is_file')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test_data')
    def test_mime_type_detection_various_formats(self, mock_file, mock_is_file, mock_get_dir):
        """Test MIME type detection for various image formats."""
        mock_image_dir = Path("/test/images")
        mock_get_dir.return_value = mock_image_dir
        mock_is_file.return_value = True
        
        test_cases = [
            ("test.png", "image/png"),
            ("test.jpg", "image/jpeg"),
            ("test.jpeg", "image/jpeg"),
            ("test.gif", "image/gif"),
            ("test.bmp", "image/bmp"),
            ("test.webp", "image/webp"),
            ("test.svg", "image/svg+xml"),
        ]
        
        for filename, expected_mime in test_cases:
            with patch('mimetypes.guess_type') as mock_guess_type:
                mock_guess_type.return_value = (expected_mime, None)
                
                result = image_tool.get_session_image("test_session", filename)
                
                assert len(result) == 1
                assert isinstance(result[0], ImageContent)
                assert result[0].mimeType == expected_mime


class TestBase64Encoding:
    """Test base64 encoding of image data."""

    @patch('server.image_tool.get_image_dir')
    @patch('pathlib.Path.is_file')
    @patch('mimetypes.guess_type')
    def test_base64_encoding_various_data(self, mock_guess_type, mock_is_file, mock_get_dir):
        """Test base64 encoding with various binary data."""
        mock_image_dir = Path("/test/images")
        mock_get_dir.return_value = mock_image_dir
        mock_is_file.return_value = True
        mock_guess_type.return_value = ("image/png", None)
        
        test_data_sets = [
            b'simple_text_data',
            b'\x89PNG\r\n\x1a\n',  # PNG header
            b'\xff\xd8\xff\xe0',   # JPEG header
            b'\x00\x01\x02\x03\x04\x05',  # Binary data
            b'',  # Empty data
        ]
        
        for test_data in test_data_sets:
            with patch('builtins.open', mock_open(read_data=test_data)):
                result = image_tool.get_session_image("test_session", "test.png")
                
                expected_b64 = base64.b64encode(test_data).decode('utf-8')
                assert len(result) == 1
                assert isinstance(result[0], ImageContent)
                assert result[0].data == expected_b64


class TestServerIntegration:
    """Test integration of built-in tools with the MCP server."""

    @pytest.mark.asyncio
    async def test_builtin_tool_in_server_tool_list(self, mcp_client_info):
        """Test that built-in tools appear in the server's tool list."""
        from .conftest import create_mcp_client

        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            tools_response = await session.list_tools()
            
            # Find the get_session_image tool
            tool_names = [tool.name for tool in tools_response.tools]
            assert "get_session_image" in tool_names
            
            # Get the specific tool
            get_session_image_tool = next(
                tool for tool in tools_response.tools 
                if tool.name == "get_session_image"
            )
            
            # Verify tool properties
            assert get_session_image_tool.description
            assert get_session_image_tool.inputSchema
            assert get_session_image_tool.inputSchema["type"] == "object"
            assert "session_id" in get_session_image_tool.inputSchema["required"]
            assert "image_name" in get_session_image_tool.inputSchema["required"]

    @pytest.mark.asyncio
    @pytest.mark.skipif(os.name == 'nt', reason="Skipping on Windows due to timeout issues with MCP client session cleanup (Issue #205)")
    async def test_builtin_tool_execution_via_server(self, mcp_client_info, tmp_path):
        """Test executing built-in tool through the MCP server."""
        from .conftest import create_mcp_client

        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        # Create a test image file
        test_session_dir = tmp_path / "test_session"
        test_session_dir.mkdir()
        test_image_path = test_session_dir / "test.png"
        test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        test_image_path.write_bytes(test_image_data)

        # Mock the image directory configuration
        with patch('config.env.get_setting') as mock_get_setting:
            mock_get_setting.return_value = str(tmp_path)
            
            async with create_mcp_client(server_url, worker_id) as session:
                # Execute the tool
                result = await session.call_tool(
                    "get_session_image",
                    {"session_id": "test_session", "image_name": "test.png"}
                )
                
                # Verify the result
                assert result is not None
                assert len(result.content) == 1
                
                content = result.content[0]
                # The result should be an image content with base64 data
                assert hasattr(content, 'type')
                # Note: The actual type checking depends on the MCP client implementation

    @pytest.mark.asyncio
    @pytest.mark.skipif(os.name == 'nt', reason="Skipping on Windows due to timeout issues with MCP client session cleanup (Issue #205)")
    async def test_builtin_tool_error_handling_via_server(self, mcp_client_info):
        """Test error handling of built-in tool through the MCP server."""
        from .conftest import create_mcp_client

        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            # Test missing arguments
            result = await session.call_tool(
                "get_session_image",
                {"session_id": "test_session"}  # Missing image_name
            )
            
            # Verify error response
            assert result is not None
            assert len(result.content) == 1
            
            content = result.content[0]
            # Should be a text content with error message
            assert hasattr(content, 'text')
            assert "required" in content.text.lower()


class TestErrorScenarios:
    """Test various error scenarios and edge cases."""

    @patch('server.image_tool.get_image_dir')
    def test_get_image_dir_exception_propagation(self, mock_get_dir):
        """Test that exceptions from get_image_dir are properly propagated."""
        mock_get_dir.side_effect = RuntimeError("Configuration error")
        
        with pytest.raises(RuntimeError, match="Configuration error"):
            image_tool.get_session_image("test_session", "test.png")

    @patch('server.image_tool.get_image_dir')
    @patch('pathlib.Path.is_file')
    @patch('builtins.open', side_effect=IOError("Disk error"))
    def test_file_io_error_propagation(self, mock_file, mock_is_file, mock_get_dir):
        """Test that file I/O errors are properly propagated."""
        mock_image_dir = Path("/test/images")
        mock_get_dir.return_value = mock_image_dir
        mock_is_file.return_value = True
        
        with pytest.raises(IOError, match="Disk error"):
            image_tool.get_session_image("test_session", "test.png")

    def test_handle_tool_with_extra_arguments(self):
        """Test that handle_tool works correctly with extra arguments."""
        with patch('server.image_tool.get_session_image') as mock_get_session_image:
            mock_result = [ImageContent(type="image", data="fake_data", mimeType="image/png")]
            mock_get_session_image.return_value = mock_result
            
            arguments = {
                "session_id": "test_session",
                "image_name": "test.png",
                "extra_arg": "ignored"
            }
            result = image_tool.handle_tool(arguments)
            
            # Should still work and ignore extra arguments
            mock_get_session_image.assert_called_once_with("test_session", "test.png")
            assert result == mock_result

    def test_handle_tool_with_none_values(self):
        """Test handle_tool behavior with None values."""
        arguments = {"session_id": None, "image_name": "test.png"}
        result = image_tool.handle_tool(arguments)
        
        # Should treat None as missing
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "required" in result[0].text


class TestPathSecurity:
    """Test path security and validation."""

    @patch('server.image_tool.get_image_dir')
    @patch('pathlib.Path.is_file')
    def test_path_traversal_attempts(self, mock_is_file, mock_get_dir):
        """Test that path traversal attempts are handled safely."""
        mock_image_dir = Path("/test/images")
        mock_get_dir.return_value = mock_image_dir
        mock_is_file.return_value = False
        
        # Test various path traversal attempts
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "session/../../../etc/passwd",
        ]
        
        for dangerous_path in dangerous_paths:
            result = image_tool.get_session_image("test_session", dangerous_path)
            
            # Should return "Image not found" for any path that doesn't exist
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert result[0].text == "Image not found."

    @patch('server.image_tool.get_image_dir')
    @patch('pathlib.Path.is_file')
    def test_special_characters_in_paths(self, mock_is_file, mock_get_dir):
        """Test handling of special characters in file paths."""
        mock_image_dir = Path("/test/images")
        mock_get_dir.return_value = mock_image_dir
        mock_is_file.return_value = False
        
        special_names = [
            "file with spaces.png",
            "file-with-dashes.png",
            "file_with_underscores.png",
            "file.with.dots.png",
            "file@symbol.png",
            "file#hash.png",
            "file%percent.png",
        ]
        
        for special_name in special_names:
            result = image_tool.get_session_image("test_session", special_name)
            
            # Should handle special characters gracefully
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert result[0].text == "Image not found."


class TestResponseFormat:
    """Test that responses conform to expected MCP format."""

    @patch('server.image_tool.get_image_dir')
    @patch('pathlib.Path.is_file')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test_data')
    @patch('mimetypes.guess_type')
    def test_successful_response_format(self, mock_guess_type, mock_file, mock_is_file, mock_get_dir):
        """Test that successful responses have the correct format."""
        mock_image_dir = Path("/test/images")
        mock_get_dir.return_value = mock_image_dir
        mock_is_file.return_value = True
        mock_guess_type.return_value = ("image/png", None)
        
        result = image_tool.get_session_image("test_session", "test.png")
        
        # Verify response format
        assert isinstance(result, list)
        assert len(result) == 1
        
        content = result[0]
        assert isinstance(content, ImageContent)
        assert content.type == "image"
        assert isinstance(content.data, str)  # Base64 string
        assert isinstance(content.mimeType, str)
        assert content.mimeType.startswith("image/") or content.mimeType == "application/octet-stream"

    def test_error_response_format(self):
        """Test that error responses have the correct format."""
        with patch('server.image_tool.get_image_dir') as mock_get_dir, \
             patch('pathlib.Path.is_file') as mock_is_file:
            
            mock_image_dir = Path("/test/images")
            mock_get_dir.return_value = mock_image_dir
            mock_is_file.return_value = False
            
            result = image_tool.get_session_image("test_session", "nonexistent.png")
            
            # Verify error response format
            assert isinstance(result, list)
            assert len(result) == 1
            
            content = result[0]
            assert isinstance(content, TextContent)
            assert content.type == "text"
            assert isinstance(content.text, str)
            assert len(content.text) > 0 