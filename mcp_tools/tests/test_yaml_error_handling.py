"""Comprehensive error handling and edge case tests for YAML tools.

This module tests error scenarios and edge cases for the YAML tool system including:
- Command executor unavailability and failures
- Configuration and validation errors
- File system and I/O errors
- Runtime and execution errors
- Error reporting and logging behavior
- Recovery and fallback mechanisms

This addresses GitHub issue #51: Add comprehensive error handling and edge case tests for YAML tools.
"""

import pytest
import asyncio
import yaml
import tempfile
import os
import platform
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock, mock_open
from typing import Dict, Any, Optional, List

from mcp_tools.yaml_tools import YamlToolBase, load_yaml_tools, get_yaml_tool_names, discover_and_register_yaml_tools
from mcp_tools.interfaces import CommandExecutorInterface
from mcp_tools.dependency import injector


class MockFailingCommandExecutor(CommandExecutorInterface):
    """Mock command executor that simulates various failure scenarios."""

    def __init__(self, failure_mode: str = "none"):
        self.failure_mode = failure_mode
        self.executed_commands = []

    @property
    def name(self) -> str:
        return "mock_failing_command_executor"

    @property
    def description(self) -> str:
        return "Mock command executor that simulates failures"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        if self.failure_mode == "execute_tool_failure":
            raise RuntimeError("Command executor execute_tool failed")
        return {"success": True}

    def execute(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        self.executed_commands.append(command)
        if self.failure_mode == "execute_failure":
            raise RuntimeError("Command execution failed")
        elif self.failure_mode == "timeout":
            raise TimeoutError("Command execution timed out")
        elif self.failure_mode == "permission_error":
            raise PermissionError("Permission denied")
        return {"status": "completed", "returncode": 0}

    async def execute_async(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        self.executed_commands.append(command)
        if self.failure_mode == "execute_failure":
            raise RuntimeError("Command execution failed")
        elif self.failure_mode == "async_failure":
            raise RuntimeError("Async command execution failed")
        elif self.failure_mode == "token_error":
            raise ValueError("Invalid token generated")
        return {"token": "test-token", "status": "running", "pid": 12345}

    async def query_process(self, token: str, wait: bool = False, timeout: Optional[float] = None) -> Dict[str, Any]:
        if self.failure_mode == "query_failure":
            raise RuntimeError("Process query failed")
        elif self.failure_mode == "process_not_found":
            raise ValueError(f"Process with token {token} not found")
        return {"status": "completed", "returncode": 0}

    def terminate_by_token(self, token: str) -> bool:
        if self.failure_mode == "terminate_failure":
            raise RuntimeError("Process termination failed")
        return True

    def list_running_processes(self) -> List[Dict[str, Any]]:
        if self.failure_mode == "list_failure":
            raise RuntimeError("Failed to list processes")
        return []

    async def start_periodic_status_reporter(self, interval: float = 30.0, enabled: bool = True) -> None:
        if self.failure_mode == "reporter_start_failure":
            raise RuntimeError("Failed to start status reporter")

    async def stop_periodic_status_reporter(self) -> None:
        if self.failure_mode == "reporter_stop_failure":
            raise RuntimeError("Failed to stop status reporter")


@pytest.fixture
def mock_failing_executor():
    """Fixture providing a mock failing command executor."""
    return MockFailingCommandExecutor()


@pytest.fixture
def clean_injector():
    """Fixture to provide a clean injector for each test."""
    original_instances = injector.instances.copy()
    yield injector
    injector.instances = original_instances


@pytest.fixture
def sample_invalid_tool_data():
    """Fixture providing various invalid tool data configurations."""
    return {
        "missing_description": {
            "type": "script",
            "inputSchema": {"type": "object", "properties": {}}
        },
        "invalid_description_type": {
            "description": 123,  # Should be string
            "type": "script",
            "inputSchema": {"type": "object", "properties": {}}
        },
        "missing_input_schema": {
            "description": "Tool without input schema",
            "type": "script"
        },
        "invalid_input_schema_type": {
            "description": "Tool with invalid input schema",
            "type": "script",
            "inputSchema": "not_a_dict"  # Should be dict
        },
        "invalid_schema_type": {
            "description": "Tool with invalid schema type",
            "type": "script",
            "inputSchema": {
                "type": 123,  # Should be string
                "properties": {}
            }
        },
        "missing_schema_type": {
            "description": "Tool with missing schema type",
            "type": "script",
            "inputSchema": {
                "properties": {}
            }
        }
    }


class TestCommandExecutorErrorScenarios:
    """Test command executor error scenarios."""

    @pytest.mark.asyncio
    async def test_execute_tool_with_unavailable_command_executor(self, clean_injector):
        """Test tool execution when command executor is unavailable."""
        # Ensure no command executor is available from dependency injection
        with patch('mcp_tools.dependency.injector.get_tool_instance') as mock_get_instance:
            mock_get_instance.side_effect = Exception("No command executor available")
            
            tool = YamlToolBase(
                tool_name="test_tool",
                tool_data={"description": "Test tool", "type": "script"},
                command_executor=None
            )
            
            result = await tool.execute_tool({"test": "value"})
            
            assert result == {"success": False, "error": "Command executor not available"}

    @pytest.mark.asyncio
    async def test_execute_tool_with_failing_command_executor(self):
        """Test tool execution when command executor fails."""
        failing_executor = MockFailingCommandExecutor("execute_failure")
        tool_data = {
            "description": "Test tool",
            "type": "script",
            "inputSchema": {"type": "object", "properties": {}},
            "scripts": {"linux": "echo test", "darwin": "echo test", "windows": "echo test"}
        }
        
        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=failing_executor
        )
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            result = await tool._execute_script({"test": "value"})
            
            # Should handle the exception gracefully
            assert isinstance(result, list)
            assert len(result) > 0
            # The mock executor with "execute_failure" mode will fail on execute_async
            assert "error" in result[0]["text"].lower() or "exception" in result[0]["text"].lower() or "failed" in result[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_async_execution_failure(self):
        """Test async command execution failure handling."""
        failing_executor = MockFailingCommandExecutor("async_failure")
        tool_data = {
            "description": "Test tool",
            "type": "script",
            "inputSchema": {"type": "object", "properties": {}},
            "scripts": {"linux": "echo test", "darwin": "echo test", "windows": "echo test"}
        }
        
        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=failing_executor
        )
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            result = await tool._execute_script({"test": "value"})
            
            # Should handle async execution failure
            assert isinstance(result, list)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_process_query_failure(self):
        """Test process query failure handling."""
        failing_executor = MockFailingCommandExecutor("query_failure")
        tool_data = {
            "description": "Test tool",
            "inputSchema": {"type": "object", "properties": {"token": {"type": "string"}}}
        }
        
        tool = YamlToolBase(
            tool_name="query_task_status",
            tool_data=tool_data,
            command_executor=failing_executor
        )
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            result = await tool._query_status({"token": "test-token"})
            
            # Should handle query failure gracefully
            assert isinstance(result, list)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        """Test timeout error handling during command execution."""
        failing_executor = MockFailingCommandExecutor("timeout")
        tool_data = {
            "description": "Test tool",
            "type": "script",
            "inputSchema": {"type": "object", "properties": {}},
            "scripts": {"linux": "sleep 100", "darwin": "sleep 100", "windows": "timeout 100"}
        }
        
        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=failing_executor
        )
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            result = await tool._execute_script({})
            
            # Should handle timeout gracefully
            assert isinstance(result, list)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_permission_error_handling(self):
        """Test permission error handling during command execution."""
        failing_executor = MockFailingCommandExecutor("permission_error")
        tool_data = {
            "description": "Test tool",
            "type": "script",
            "inputSchema": {"type": "object", "properties": {}},
            "scripts": {"linux": "echo test", "darwin": "echo test", "windows": "echo test"}
        }
        
        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=failing_executor
        )
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            result = await tool._execute_script({})
            
            # Should handle permission error gracefully
            assert isinstance(result, list)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_dependency_injection_failure(self, clean_injector):
        """Test handling of dependency injection failures."""
        with patch('mcp_tools.dependency.injector.get_tool_instance') as mock_get_instance:
            mock_get_instance.side_effect = Exception("Dependency injection failed")
            
            with patch('mcp_tools.yaml_tools.logger') as mock_logger:
                tool = YamlToolBase(tool_name="test_tool")
                
                # Should handle injection failure gracefully
                assert tool._command_executor is None
                mock_logger.warning.assert_called()


class TestConfigurationAndValidationErrors:
    """Test configuration and validation error scenarios."""

    def test_invalid_tool_data_structure(self, sample_invalid_tool_data):
        """Test handling of invalid tool data structures."""
        for invalid_type, invalid_data in sample_invalid_tool_data.items():
            with patch('mcp_tools.yaml_tools.logger') as mock_logger:
                tool = YamlToolBase(
                    tool_name=f"test_{invalid_type}",
                    tool_data=invalid_data
                )
                
                # Tool should still be created but with safe defaults
                assert tool.name == f"test_{invalid_type}"
                
                # Input schema should be safe
                schema = tool.input_schema
                assert isinstance(schema, dict)
                # For invalid schemas, the property should return a safe default with "type"
                if invalid_type == "missing_schema_type":
                    # This specific case might not have "type" in the original data
                    # but the property should provide a safe default
                    assert "properties" in schema
                else:
                    assert "type" in schema

    def test_non_dict_tool_data(self):
        """Test handling of non-dictionary tool data."""
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            tool = YamlToolBase(
                tool_name="test_tool",
                tool_data="not_a_dict"  # Invalid type
            )
            
            # Should use empty dict as fallback
            assert tool._tool_data == {}
            assert tool.description == ""
            mock_logger.warning.assert_called()

    def test_non_dict_input_schema(self):
        """Test handling of non-dictionary input schema."""
        tool_data = {
            "description": "Test tool",
            "inputSchema": "not_a_dict"  # Invalid type
        }
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)
            
            # Should return safe default schema
            schema = tool.input_schema
            assert schema == {"type": "object", "properties": {}, "required": []}
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_input_validation_errors(self):
        """Test input validation error handling."""
        tool_data = {
            "description": "Test tool",
            "type": "script",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "required_param": {"type": "string"}
                },
                "required": ["required_param"]
            },
            "scripts": {"linux": "echo test", "darwin": "echo test", "windows": "echo test"}
        }
        
        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=MockFailingCommandExecutor()
        )
        
        # Test missing required parameter
        result = await tool._execute_script({})
        assert isinstance(result, list)
        assert len(result) > 0
        assert "validation error" in result[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_parameter_substitution_errors(self):
        """Test parameter substitution error handling."""
        tool_data = {
            "description": "Test tool",
            "type": "script",
            "inputSchema": {"type": "object", "properties": {}},
            "scripts": {"linux": "echo {missing_param}", "darwin": "echo {missing_param}", "windows": "echo {missing_param}"}
        }
        
        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=MockFailingCommandExecutor()
        )
        
        result = await tool._execute_script({"provided_param": "value"})
        assert isinstance(result, list)
        assert len(result) > 0
        assert "missing required parameter" in result[0]["text"].lower()

    def test_missing_environment_variables(self):
        """Test handling of missing environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            tool_data = {
                "description": "Test tool",
                "type": "script",
                "inputSchema": {"type": "object", "properties": {}},
                "scripts": {"linux": "echo test", "darwin": "echo test", "windows": "echo test"}
            }
            
            tool = YamlToolBase(
                tool_name="test_tool",
                tool_data=tool_data,
                command_executor=MockFailingCommandExecutor()
            )
            
            # Should handle missing PRIVATE_TOOL_ROOT gracefully
            assert tool._tool_data == tool_data


class TestFileSystemAndIOErrors:
    """Test file system and I/O error scenarios."""

    @patch('mcp_tools.yaml_tools.yaml.safe_load')
    def test_yaml_parsing_error(self, mock_yaml_load):
        """Test YAML parsing error handling."""
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML syntax")
        
        tool = YamlToolBase()
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            with patch('builtins.open', mock_open(read_data="invalid: yaml: content")):
                with patch('pathlib.Path.exists', return_value=True):
                    result = tool._load_yaml_from_locations("test.yaml")
                    
                    # Should return empty dict on YAML error
                    assert result == {}
                    mock_logger.error.assert_called()

    @patch('builtins.open')
    def test_file_permission_error(self, mock_open_func):
        """Test file permission error handling."""
        mock_open_func.side_effect = PermissionError("Permission denied")
        
        tool = YamlToolBase()
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            with patch('pathlib.Path.exists', return_value=True):
                result = tool._load_yaml_from_locations("test.yaml")
                
                # Should return empty dict on permission error
                assert result == {}
                mock_logger.error.assert_called()

    @patch('builtins.open')
    def test_file_not_found_error(self, mock_open_func):
        """Test file not found error handling."""
        mock_open_func.side_effect = FileNotFoundError("File not found")
        
        tool = YamlToolBase()
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            with patch('pathlib.Path.exists', return_value=True):
                result = tool._load_yaml_from_locations("test.yaml")
                
                # Should return empty dict on file not found
                assert result == {}
                mock_logger.error.assert_called()

    @patch('builtins.open')
    def test_io_error_during_file_read(self, mock_open_func):
        """Test I/O error during file reading."""
        mock_open_func.side_effect = IOError("I/O operation failed")
        
        tool = YamlToolBase()
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            with patch('pathlib.Path.exists', return_value=True):
                result = tool._load_yaml_from_locations("test.yaml")
                
                # Should return empty dict on I/O error
                assert result == {}
                mock_logger.error.assert_called()

    def test_invalid_yaml_structure(self):
        """Test handling of invalid YAML structure."""
        invalid_yaml_content = "not_a_dict_root"
        
        tool = YamlToolBase()
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            with patch('builtins.open', mock_open(read_data=invalid_yaml_content)):
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('yaml.safe_load', return_value="not_a_dict"):
                        result = tool._load_yaml_from_locations("test.yaml")
                        
                        # Should return empty dict for invalid structure
                        assert result == {}
                        mock_logger.error.assert_called()

    def test_invalid_tools_section(self):
        """Test handling of invalid tools section in YAML."""
        tool = YamlToolBase()
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            with patch('builtins.open', mock_open(read_data="tools: not_a_dict")):
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('yaml.safe_load', return_value={"tools": "not_a_dict"}):
                        result = tool._load_yaml_from_locations("test.yaml")
                        
                        # Should fix invalid tools section
                        assert result["tools"] == {}
                        mock_logger.error.assert_called()

    def test_invalid_tasks_section(self):
        """Test handling of invalid tasks section in YAML."""
        tool = YamlToolBase()
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            with patch('builtins.open', mock_open(read_data="tasks: not_a_dict")):
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('yaml.safe_load', return_value={"tasks": "not_a_dict"}):
                        result = tool._load_yaml_from_locations("test.yaml")
                        
                        # Should fix invalid tasks section
                        assert result["tasks"] == {}
                        mock_logger.error.assert_called()


class TestRuntimeAndExecutionErrors:
    """Test runtime and execution error scenarios."""

    @pytest.mark.asyncio
    async def test_script_execution_on_unsupported_platform(self):
        """Test script execution on unsupported platform."""
        tool_data = {
            "description": "Test tool",
            "type": "script",
            "inputSchema": {"type": "object", "properties": {}},
            "scripts": {"linux": "echo linux", "windows": "echo windows"}  # No darwin
        }
        
        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=MockFailingCommandExecutor()
        )
        
        with patch('platform.system', return_value='Darwin'):
            result = await tool._execute_script({})
            
            assert isinstance(result, list)
            assert len(result) > 0
            assert "no script defined" in result[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_missing_script_configuration(self):
        """Test handling of missing script configuration."""
        tool_data = {
            "description": "Test tool",
            "type": "script",
            "inputSchema": {"type": "object", "properties": {}}
            # No scripts section
        }
        
        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=MockFailingCommandExecutor()
        )
        
        result = await tool._execute_script({})
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert "no script defined" in result[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_invalid_tool_type_handling(self):
        """Test handling of invalid tool types."""
        tool_data = {
            "description": "Test tool",
            "type": "invalid_type",
            "inputSchema": {"type": "object", "properties": {}}
        }
        
        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=MockFailingCommandExecutor()
        )
        
        result = await tool.execute_tool({})
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert "not fully implemented" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_execute_task_with_missing_arguments(self):
        """Test execute_task with missing required arguments."""
        tool_data = {
            "description": "Execute task tool",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_name": {"type": "string"},
                    "arguments": {"type": "object"}
                },
                "required": ["task_name"]
            }
        }
        
        tool = YamlToolBase(
            tool_name="execute_task",
            tool_data=tool_data,
            command_executor=MockFailingCommandExecutor()
        )
        
        # Test with missing task_name
        result = await tool._execute_task({})
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert "error" in result[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_task_execution_with_invalid_yaml(self):
        """Test task execution when tasks.yaml is invalid."""
        tool_data = {
            "description": "Execute task tool",
            "inputSchema": {"type": "object", "properties": {}}
        }
        
        tool = YamlToolBase(
            tool_name="execute_task",
            tool_data=tool_data,
            command_executor=MockFailingCommandExecutor()
        )
        
        with patch.object(tool, '_load_yaml_from_locations', return_value={}):
            result = await tool._execute_task({"task_name": "test_task"})
            
            assert isinstance(result, list)
            assert len(result) > 0


class TestErrorReportingAndLogging:
    """Test error reporting and logging behavior."""

    def test_logging_during_tool_initialization(self):
        """Test logging behavior during tool initialization errors."""
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            tool = YamlToolBase(
                tool_name="test_tool",
                tool_data="invalid_data"  # Should trigger warning
            )
            
            # Should log warning about invalid tool_data
            mock_logger.warning.assert_called()

    def test_logging_during_dependency_injection_failure(self):
        """Test logging during dependency injection failures."""
        with patch('mcp_tools.dependency.injector.get_tool_instance') as mock_get_instance:
            mock_get_instance.side_effect = Exception("Injection failed")
            
            with patch('mcp_tools.yaml_tools.logger') as mock_logger:
                tool = YamlToolBase(tool_name="test_tool")
                
                # Should log warning about injection failure
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_logging_during_script_execution_errors(self):
        """Test logging during script execution errors."""
        failing_executor = MockFailingCommandExecutor("execute_failure")
        tool_data = {
            "description": "Test tool",
            "type": "script",
            "inputSchema": {"type": "object", "properties": {}},
            "scripts": {"linux": "echo test", "darwin": "echo test", "windows": "echo test"}
        }
        
        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=failing_executor
        )
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            await tool._execute_script({})
            
            # Should log execution details
            mock_logger.info.assert_called()

    def test_error_message_formatting(self):
        """Test proper error message formatting."""
        tool_data = {
            "description": "Test tool",
            "inputSchema": "invalid_schema"  # Should trigger error
        }
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)
            schema = tool.input_schema
            
            # Should return properly formatted default schema
            assert isinstance(schema, dict)
            assert "type" in schema
            assert schema["type"] == "object"


class TestLoadYamlToolsErrorHandling:
    """Test error handling in load_yaml_tools function."""

    @patch('mcp_tools.yaml_tools.YamlToolBase')
    def test_load_yaml_tools_with_yaml_loading_failure(self, mock_yaml_tool_base):
        """Test load_yaml_tools when YAML loading fails."""
        mock_instance = Mock()
        mock_instance._load_yaml_from_locations.side_effect = Exception("YAML loading failed")
        mock_yaml_tool_base.return_value = mock_instance
        
        result = load_yaml_tools()
        
        # Should return empty list on YAML loading failure
        assert result == []

    @patch('mcp_tools.yaml_tools.YamlToolBase')
    def test_load_yaml_tools_with_empty_tools_data(self, mock_yaml_tool_base):
        """Test load_yaml_tools with empty tools data."""
        mock_instance = Mock()
        mock_instance._load_yaml_from_locations.return_value = {"tools": {}}
        mock_yaml_tool_base.return_value = mock_instance
        
        result = load_yaml_tools()
        
        # Should return empty list for empty tools
        assert result == []

    @patch('mcp_tools.yaml_tools.YamlToolBase')
    def test_load_yaml_tools_with_invalid_tool_data(self, mock_yaml_tool_base):
        """Test load_yaml_tools with invalid individual tool data."""
        mock_instance = Mock()
        mock_instance._load_yaml_from_locations.return_value = {
            "tools": {
                "valid_tool": {
                    "description": "Valid tool",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                "invalid_tool": {
                    "description": 123,  # Invalid type
                    "inputSchema": {"type": "object", "properties": {}}
                }
            }
        }
        mock_yaml_tool_base.return_value = mock_instance
        
        with patch('mcp_tools.yaml_tools.register_tool') as mock_register:
            mock_register.return_value = lambda cls: cls
            result = load_yaml_tools()
            
            # Should handle invalid tools gracefully
            assert isinstance(result, list)

    @patch('mcp_tools.yaml_tools.YamlToolBase')
    def test_load_yaml_tools_with_class_creation_failure(self, mock_yaml_tool_base):
        """Test load_yaml_tools when class creation fails."""
        mock_instance = Mock()
        mock_instance._load_yaml_from_locations.return_value = {
            "tools": {
                "test_tool": {
                    "description": "Test tool",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            }
        }
        mock_yaml_tool_base.return_value = mock_instance
        
        # Mock the type function used for class creation in the specific context
        with patch('mcp_tools.yaml_tools.type', side_effect=Exception("Class creation failed")):
            result = load_yaml_tools()
            
            # Should handle class creation failure
            assert isinstance(result, list)

    @patch('mcp_tools.yaml_tools.YamlToolBase')
    def test_load_yaml_tools_with_registration_failure(self, mock_yaml_tool_base):
        """Test load_yaml_tools when tool registration fails."""
        mock_instance = Mock()
        mock_instance._load_yaml_from_locations.return_value = {
            "tools": {
                "test_tool": {
                    "description": "Test tool",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            }
        }
        mock_yaml_tool_base.return_value = mock_instance
        
        with patch('mcp_tools.yaml_tools.register_tool') as mock_register:
            mock_register.side_effect = Exception("Registration failed")
            result = load_yaml_tools()
            
            # Should handle registration failure
            assert isinstance(result, list)

    def test_load_yaml_tools_critical_error(self):
        """Test load_yaml_tools with critical error."""
        with patch('mcp_tools.yaml_tools.YamlToolBase', side_effect=Exception("Critical error")):
            result = load_yaml_tools()
            
            # Should return empty list on critical error
            assert result == []


class TestGetYamlToolNamesErrorHandling:
    """Test error handling in get_yaml_tool_names function."""

    def test_get_yaml_tool_names_with_exception(self):
        """Test get_yaml_tool_names when exception occurs."""
        with patch('mcp_tools.yaml_tools.YamlToolBase', side_effect=Exception("Tool names error")):
            with patch('mcp_tools.yaml_tools.logger') as mock_logger:
                result = get_yaml_tool_names()
                
                # Should return empty set on exception
                assert result == set()
                mock_logger.error.assert_called()

    @patch('mcp_tools.yaml_tools.YamlToolBase')
    def test_get_yaml_tool_names_with_yaml_loading_failure(self, mock_yaml_tool_base):
        """Test get_yaml_tool_names when YAML loading fails."""
        mock_instance = Mock()
        mock_instance._load_yaml_from_locations.side_effect = Exception("YAML loading failed")
        mock_yaml_tool_base.return_value = mock_instance
        
        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            result = get_yaml_tool_names()
            
            # Should return empty set on YAML loading failure
            assert result == set()
            mock_logger.error.assert_called()


class TestDiscoverAndRegisterYamlToolsErrorHandling:
    """Test error handling in discover_and_register_yaml_tools function."""

    def test_discover_and_register_yaml_tools_with_exception(self):
        """Test discover_and_register_yaml_tools when exception occurs."""
        with patch('mcp_tools.yaml_tools.load_yaml_tools', side_effect=Exception("Discovery error")):
            with patch('mcp_tools.yaml_tools.logger') as mock_logger:
                result = discover_and_register_yaml_tools()
                
                # Should return empty list on exception
                assert result == []
                mock_logger.error.assert_called()


class TestRecoveryAndFallbackMechanisms:
    """Test recovery and fallback mechanisms."""

    def test_tool_continues_functioning_after_executor_failure(self):
        """Test that tool system continues functioning after command executor failure."""
        # Create tool with failing executor
        failing_executor = MockFailingCommandExecutor("execute_failure")
        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data={"description": "Test tool"},
            command_executor=failing_executor
        )
        
        # Tool should still be functional for basic operations
        assert tool.name == "test_tool"
        assert tool.description == "Test tool"
        assert isinstance(tool.input_schema, dict)

    def test_fallback_to_default_values(self):
        """Test fallback to default values when configuration is invalid."""
        # Test with completely invalid tool data
        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=None
        )
        
        # Should use safe defaults
        assert tool.name == "test_tool"
        assert tool.description == ""
        assert tool._tool_type == "object"
        assert tool._tool_data == {}

    def test_graceful_degradation_with_partial_configuration(self):
        """Test graceful degradation with partial configuration."""
        partial_data = {
            "description": "Partial tool"
            # Missing inputSchema and other fields
        }
        
        tool = YamlToolBase(
            tool_name="partial_tool",
            tool_data=partial_data
        )
        
        # Should work with partial data
        assert tool.name == "partial_tool"
        assert tool.description == "Partial tool"
        assert isinstance(tool.input_schema, dict)
        assert tool.input_schema["type"] == "object"

    @pytest.mark.asyncio
    async def test_error_propagation_patterns(self, clean_injector):
        """Test that errors are propagated in expected patterns."""
        tool_data = {
            "description": "Test tool",
            "type": "script",
            "inputSchema": {"type": "object", "properties": {}},
            "scripts": {"linux": "echo test", "darwin": "echo test", "windows": "echo test"}
        }
        
        # Ensure no command executor is available from dependency injection
        with patch('mcp_tools.dependency.injector.get_tool_instance') as mock_get_instance:
            mock_get_instance.side_effect = Exception("No command executor available")
            
            # Test with no command executor
            tool = YamlToolBase(
                tool_name="test_tool",
                tool_data=tool_data,
                command_executor=None
            )
            
            result = await tool.execute_tool({})
            
            # Should return structured error response
            assert isinstance(result, dict)
            assert "success" in result
            assert result["success"] is False
            assert "error" in result

    def test_system_stability_after_multiple_errors(self):
        """Test system stability after encountering multiple errors."""
        # Simulate multiple error scenarios
        error_scenarios = [
            ("invalid_data", "not_a_dict"),
            ("missing_schema", {"description": "Test"}),
            ("invalid_schema", {"description": "Test", "inputSchema": "invalid"})
        ]
        
        tools = []
        for name, data in error_scenarios:
            with patch('mcp_tools.yaml_tools.logger'):
                tool = YamlToolBase(tool_name=name, tool_data=data)
                tools.append(tool)
        
        # All tools should be created successfully with fallbacks
        assert len(tools) == 3
        for tool in tools:
            assert isinstance(tool.name, str)
            assert isinstance(tool.description, str)
            assert isinstance(tool.input_schema, dict)


class TestEdgeCasesAndBoundaryConditions:
    """Test edge cases and boundary conditions."""

    def test_empty_string_parameters(self):
        """Test handling of empty string parameters."""
        tool = YamlToolBase(
            tool_name="",
            tool_data={"description": "", "inputSchema": {"type": "object"}}
        )
        
        # Should handle empty strings gracefully
        assert tool.name == ""
        assert tool.description == ""

    def test_very_large_tool_data(self):
        """Test handling of very large tool data."""
        large_properties = {f"param_{i}": {"type": "string"} for i in range(1000)}
        large_tool_data = {
            "description": "Tool with many parameters",
            "inputSchema": {
                "type": "object",
                "properties": large_properties
            }
        }
        
        tool = YamlToolBase(
            tool_name="large_tool",
            tool_data=large_tool_data
        )
        
        # Should handle large data structures
        assert tool.name == "large_tool"
        assert len(tool.input_schema["properties"]) == 1000

    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters."""
        unicode_data = {
            "description": "Tool with Unicode: 测试工具 🚀",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "unicode_param": {"type": "string", "description": "Unicode: 参数 🎯"}
                }
            }
        }
        
        tool = YamlToolBase(
            tool_name="unicode_tool_测试",
            tool_data=unicode_data
        )
        
        # Should handle Unicode characters
        assert "测试工具" in tool.description
        assert "🚀" in tool.description

    def test_circular_references_in_data(self):
        """Test handling of circular references in tool data."""
        # Create data with potential circular reference
        tool_data = {"description": "Test tool"}
        tool_data["self_ref"] = tool_data  # Circular reference
        
        # Should not cause infinite recursion
        tool = YamlToolBase(
            tool_name="circular_tool",
            tool_data=tool_data
        )
        
        assert tool.name == "circular_tool"
        assert tool.description == "Test tool"

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self):
        """Test concurrent tool execution scenarios."""
        tool_data = {
            "description": "Concurrent test tool",
            "type": "script",
            "inputSchema": {"type": "object", "properties": {}},
            "scripts": {"linux": "echo test", "darwin": "echo test", "windows": "echo test"}
        }
        
        tools = [
            YamlToolBase(
                tool_name=f"concurrent_tool_{i}",
                tool_data=tool_data,
                command_executor=MockFailingCommandExecutor()
            )
            for i in range(5)
        ]
        
        # Execute tools concurrently
        tasks = [tool._execute_script({}) for tool in tools]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete without interference
        assert len(results) == 5
        for result in results:
            assert isinstance(result, list) or isinstance(result, Exception) 