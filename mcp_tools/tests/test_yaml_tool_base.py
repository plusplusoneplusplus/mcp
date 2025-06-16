"""Comprehensive unit tests for YamlToolBase class.

This module tests the core functionality of the YamlToolBase class including:
- Tool initialization with different parameter combinations
- Property getters (name, description, input_schema)
- Tool data validation and defaults
- Command executor dependency injection
- Initialization edge cases
- Tool type handling
- Error handling for invalid inputs
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import Dict, Any, Optional

from mcp_tools.yaml_tools import YamlToolBase
from mcp_tools.interfaces import CommandExecutorInterface
from mcp_tools.dependency import injector


class MockCommandExecutor(CommandExecutorInterface):
    """Mock command executor for testing."""

    def __init__(self):
        self.executed_commands = []
        self.mock_results = {}

    @property
    def name(self) -> str:
        return "mock_command_executor"

    @property
    def description(self) -> str:
        return "Mock command executor for testing"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        return {"success": True}

    def execute(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        self.executed_commands.append(command)
        return self.mock_results.get(command, {"status": "completed", "returncode": 0})

    async def execute_async(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        self.executed_commands.append(command)
        return self.mock_results.get(command, {"token": "test-token", "status": "running", "pid": 12345})

    async def query_process(self, token: str, wait: bool = False, timeout: Optional[float] = None) -> Dict[str, Any]:
        return {"status": "completed", "returncode": 0}

    def terminate_by_token(self, token: str) -> bool:
        return True

    def list_running_processes(self) -> list:
        return []

    async def start_periodic_status_reporter(self, interval: float = 30.0, enabled: bool = True) -> None:
        pass

    async def stop_periodic_status_reporter(self) -> None:
        pass


@pytest.fixture
def mock_command_executor():
    """Fixture providing a mock command executor."""
    return MockCommandExecutor()


@pytest.fixture
def clean_injector():
    """Fixture to provide a clean injector for each test."""
    # Save the original injector state
    original_instances = injector.instances.copy()

    yield injector

    # Restore the original injector state
    injector.instances = original_instances


@pytest.fixture
def sample_tool_data():
    """Fixture providing sample tool data for testing."""
    return {
        "description": "A sample YAML tool for testing",
        "type": "script",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to process"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of iterations",
                    "default": 1
                }
            },
            "required": ["message"]
        },
        "scripts": {
            "linux": "echo '{message}' | head -n {count}",
            "darwin": "echo '{message}' | head -n {count}",
            "windows": "echo {message}"
        },
        "parameters": {
            "default_param": "default_value"
        }
    }


class TestYamlToolBaseInitialization:
    """Test cases for YamlToolBase initialization."""

    def test_init_with_all_parameters(self, sample_tool_data, mock_command_executor):
        """Test initialization with all parameters provided."""
        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=sample_tool_data,
            command_executor=mock_command_executor
        )

        assert tool.name == "test_tool"
        assert tool.description == "A sample YAML tool for testing"
        assert tool._tool_type == "script"
        assert tool._command_executor == mock_command_executor
        assert tool._tool_data == sample_tool_data

    def test_init_with_minimal_parameters(self):
        """Test initialization with minimal parameters."""
        tool = YamlToolBase(tool_name="minimal_tool")

        assert tool.name == "minimal_tool"
        assert tool.description == ""
        assert tool._tool_type == "object"
        assert tool._tool_data == {}

    def test_init_with_missing_tool_name(self, sample_tool_data):
        """Test initialization with missing tool_name parameter."""
        tool = YamlToolBase(tool_data=sample_tool_data)

        assert tool.name == "unknown_yaml_tool"
        assert tool.description == "A sample YAML tool for testing"

    def test_init_with_missing_tool_data(self):
        """Test initialization with missing tool_data parameter."""
        tool = YamlToolBase(tool_name="test_tool")

        assert tool.name == "test_tool"
        assert tool.description == ""
        assert tool._tool_data == {}
        assert tool._tool_type == "object"

    def test_init_with_class_attributes(self):
        """Test initialization using class attributes as defaults."""
        class TestYamlTool(YamlToolBase):
            _tool_name = "class_tool"
            _tool_data = {
                "description": "Tool from class attributes",
                "type": "custom"
            }

        tool = TestYamlTool()

        assert tool.name == "class_tool"
        assert tool.description == "Tool from class attributes"
        assert tool._tool_type == "custom"

    def test_init_parameters_override_class_attributes(self, sample_tool_data):
        """Test that parameters override class attributes."""
        class TestYamlTool(YamlToolBase):
            _tool_name = "class_tool"
            _tool_data = {"description": "Class description"}

        tool = TestYamlTool(
            tool_name="param_tool",
            tool_data=sample_tool_data
        )

        assert tool.name == "param_tool"
        assert tool.description == "A sample YAML tool for testing"

    @patch('mcp_tools.dependency.injector.get_tool_instance')
    def test_init_with_injector_dependency(self, mock_get_tool_instance, sample_tool_data):
        """Test initialization with command executor from dependency injector."""
        mock_executor = MockCommandExecutor()
        mock_get_tool_instance.return_value = mock_executor

        tool = YamlToolBase(tool_name="test_tool", tool_data=sample_tool_data)

        assert tool._command_executor == mock_executor
        mock_get_tool_instance.assert_called_once_with("command_executor")

    @patch('mcp_tools.dependency.injector.get_tool_instance')
    def test_init_with_injector_returning_none(self, mock_get_tool_instance, sample_tool_data):
        """Test initialization when injector returns None."""
        mock_get_tool_instance.return_value = None

        tool = YamlToolBase(tool_name="test_tool", tool_data=sample_tool_data)

        assert tool._command_executor is None
        mock_get_tool_instance.assert_called_once_with("command_executor")


class TestYamlToolBaseProperties:
    """Test cases for YamlToolBase properties."""

    def test_name_property(self, sample_tool_data):
        """Test the name property getter."""
        tool = YamlToolBase(tool_name="property_test", tool_data=sample_tool_data)
        assert tool.name == "property_test"

    def test_description_property(self, sample_tool_data):
        """Test the description property getter."""
        tool = YamlToolBase(tool_name="test_tool", tool_data=sample_tool_data)
        assert tool.description == "A sample YAML tool for testing"

    def test_description_property_empty(self):
        """Test the description property with empty tool data."""
        tool = YamlToolBase(tool_name="test_tool", tool_data={})
        assert tool.description == ""

    def test_input_schema_property(self, sample_tool_data):
        """Test the input_schema property getter."""
        tool = YamlToolBase(tool_name="test_tool", tool_data=sample_tool_data)
        expected_schema = sample_tool_data["inputSchema"]
        assert tool.input_schema == expected_schema

    def test_input_schema_property_default(self):
        """Test the input_schema property with default value."""
        tool = YamlToolBase(tool_name="test_tool", tool_data={})
        expected_default = {"type": "object", "properties": {}, "required": []}
        assert tool.input_schema == expected_default

    def test_input_schema_property_partial(self):
        """Test the input_schema property with partial schema."""
        tool_data = {
            "inputSchema": {
                "type": "object",
                "properties": {"param": {"type": "string"}}
                # Missing "required" field
            }
        }
        tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)
        assert tool.input_schema["type"] == "object"
        assert "param" in tool.input_schema["properties"]

    def test_category_property(self, sample_tool_data):
        """Test the category property getter."""
        tool_data = dict(sample_tool_data)
        tool_data["category"] = "testing"
        tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)
        assert tool.category == "testing"

    def test_category_property_default(self):
        """Test default category when not provided."""
        tool = YamlToolBase(tool_name="test_tool", tool_data={})
        assert tool.category == "uncategorized"


class TestYamlToolBaseToolTypeHandling:
    """Test cases for tool type handling."""

    def test_default_tool_type(self):
        """Test default tool type assignment."""
        tool = YamlToolBase(tool_name="test_tool", tool_data={})
        assert tool._tool_type == "object"

    def test_custom_tool_type(self):
        """Test custom tool type assignment."""
        tool_data = {"type": "script"}
        tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)
        assert tool._tool_type == "script"

    def test_tool_type_validation(self):
        """Test that tool type is stored correctly."""
        test_types = ["script", "task", "custom", "object"]
        
        for tool_type in test_types:
            tool_data = {"type": tool_type}
            tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)
            assert tool._tool_type == tool_type


class TestYamlToolBaseExecuteToolRouting:
    """Test cases for execute_tool routing logic."""

    @pytest.mark.asyncio
    async def test_execute_tool_no_command_executor(self):
        """Test execute_tool when command executor is not available."""
        tool = YamlToolBase(tool_name="test_tool", tool_data={"type": "script"})
        tool._command_executor = None

        result = await tool.execute_tool({})

        assert result["success"] is False
        assert "Command executor not available" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_script_type(self, mock_command_executor):
        """Test execute_tool routing for script type."""
        tool_data = {
            "type": "script",
            "scripts": {"linux": "echo 'test'"},
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }
        tool = YamlToolBase(
            tool_name="script_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        with patch.object(tool, '_execute_script', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = [{"type": "text", "text": "Script executed"}]
            
            result = await tool.execute_tool({"param": "value"})
            
            mock_execute.assert_called_once_with({"param": "value"})
            assert result == [{"type": "text", "text": "Script executed"}]

    @pytest.mark.asyncio
    async def test_execute_tool_execute_task(self, mock_command_executor):
        """Test execute_tool routing for execute_task."""
        tool = YamlToolBase(
            tool_name="execute_task",
            tool_data={"type": "task"},
            command_executor=mock_command_executor
        )

        with patch.object(tool, '_execute_task', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = [{"type": "text", "text": "Task executed"}]
            
            result = await tool.execute_tool({"task": "test"})
            
            mock_execute.assert_called_once_with({"task": "test"})
            assert result == [{"type": "text", "text": "Task executed"}]

    @pytest.mark.asyncio
    async def test_execute_tool_query_task_status(self, mock_command_executor):
        """Test execute_tool routing for query_task_status."""
        tool = YamlToolBase(
            tool_name="query_task_status",
            tool_data={},
            command_executor=mock_command_executor
        )

        with patch.object(tool, '_query_status', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [{"type": "text", "text": "Status queried"}]
            
            result = await tool.execute_tool({"token": "test-token"})
            
            mock_query.assert_called_once_with({"token": "test-token"})
            assert result == [{"type": "text", "text": "Status queried"}]

    @pytest.mark.asyncio
    async def test_execute_tool_query_script_status(self, mock_command_executor):
        """Test execute_tool routing for query_script_status."""
        tool = YamlToolBase(
            tool_name="query_script_status",
            tool_data={},
            command_executor=mock_command_executor
        )

        with patch.object(tool, '_query_status', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [{"type": "text", "text": "Status queried"}]
            
            result = await tool.execute_tool({"token": "test-token"})
            
            mock_query.assert_called_once_with({"token": "test-token"})

    @pytest.mark.asyncio
    async def test_execute_tool_list_tasks(self, mock_command_executor):
        """Test execute_tool routing for list_tasks."""
        tool = YamlToolBase(
            tool_name="list_tasks",
            tool_data={},
            command_executor=mock_command_executor
        )

        with patch.object(tool, '_list_tasks', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [{"type": "text", "text": "Tasks listed"}]
            
            result = await tool.execute_tool({})
            
            mock_list.assert_called_once()
            assert result == [{"type": "text", "text": "Tasks listed"}]

    @pytest.mark.asyncio
    async def test_execute_tool_list_instructions(self, mock_command_executor):
        """Test execute_tool routing for list_instructions."""
        tool = YamlToolBase(
            tool_name="list_instructions",
            tool_data={},
            command_executor=mock_command_executor
        )

        with patch.object(tool, '_list_instructions', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [{"type": "text", "text": "Instructions listed"}]
            
            result = await tool.execute_tool({})
            
            mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tool_get_instruction(self, mock_command_executor):
        """Test execute_tool routing for get_instruction."""
        tool = YamlToolBase(
            tool_name="get_instruction",
            tool_data={},
            command_executor=mock_command_executor
        )

        with patch.object(tool, '_get_instruction', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [{"type": "text", "text": "Instruction retrieved"}]
            
            result = await tool.execute_tool({"name": "test_instruction"})
            
            mock_get.assert_called_once_with({"name": "test_instruction"})

    @pytest.mark.asyncio
    async def test_execute_tool_unimplemented(self, mock_command_executor):
        """Test execute_tool for unimplemented tool types."""
        tool = YamlToolBase(
            tool_name="unknown_tool",
            tool_data={"type": "unknown"},
            command_executor=mock_command_executor
        )

        result = await tool.execute_tool({})

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "not fully implemented" in result[0]["text"]
        assert "unknown_tool" in result[0]["text"]


class TestYamlToolBaseInputValidation:
    """Test cases for input validation functionality."""

    def test_validate_input_schema_success(self):
        """Test successful input validation."""
        tool = YamlToolBase(tool_name="test_tool")
        
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"]
        }
        
        arguments = {"name": "John", "age": 30}
        
        result = tool._validate_input_schema(arguments, schema)
        assert result is None

    def test_validate_input_schema_missing_required(self):
        """Test validation failure for missing required field."""
        tool = YamlToolBase(tool_name="test_tool")
        
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"]
        }
        
        arguments = {}
        
        result = tool._validate_input_schema(arguments, schema)
        assert result == "Missing required field: name"

    def test_validate_input_schema_wrong_type_string(self):
        """Test validation failure for wrong string type."""
        tool = YamlToolBase(tool_name="test_tool")
        
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"]
        }
        
        arguments = {"name": 123}
        
        result = tool._validate_input_schema(arguments, schema)
        assert result == "Field 'name' must be a string"

    def test_validate_input_schema_wrong_type_number(self):
        """Test validation failure for wrong number type."""
        tool = YamlToolBase(tool_name="test_tool")
        
        schema = {
            "type": "object",
            "properties": {"age": {"type": "number"}},
            "required": ["age"]
        }
        
        arguments = {"age": "not_a_number"}
        
        result = tool._validate_input_schema(arguments, schema)
        assert result == "Field 'age' must be a number"

    def test_validate_input_schema_wrong_type_integer(self):
        """Test validation failure for wrong integer type."""
        tool = YamlToolBase(tool_name="test_tool")
        
        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer"}},
            "required": ["count"]
        }
        
        arguments = {"count": 3.14}
        
        result = tool._validate_input_schema(arguments, schema)
        assert result == "Field 'count' must be an integer"

    def test_validate_input_schema_wrong_type_boolean(self):
        """Test validation failure for wrong boolean type."""
        tool = YamlToolBase(tool_name="test_tool")
        
        schema = {
            "type": "object",
            "properties": {"enabled": {"type": "boolean"}},
            "required": ["enabled"]
        }
        
        arguments = {"enabled": "true"}
        
        result = tool._validate_input_schema(arguments, schema)
        assert result == "Field 'enabled' must be a boolean"

    def test_validate_input_schema_wrong_type_array(self):
        """Test validation failure for wrong array type."""
        tool = YamlToolBase(tool_name="test_tool")
        
        schema = {
            "type": "object",
            "properties": {"items": {"type": "array"}},
            "required": ["items"]
        }
        
        arguments = {"items": "not_an_array"}
        
        result = tool._validate_input_schema(arguments, schema)
        assert result == "Field 'items' must be an array"

    def test_validate_input_schema_wrong_type_object(self):
        """Test validation failure for wrong object type."""
        tool = YamlToolBase(tool_name="test_tool")
        
        schema = {
            "type": "object",
            "properties": {"config": {"type": "object"}},
            "required": ["config"]
        }
        
        arguments = {"config": "not_an_object"}
        
        result = tool._validate_input_schema(arguments, schema)
        assert result == "Field 'config' must be an object"

    def test_validate_input_schema_enum_success(self):
        """Test successful enum validation."""
        tool = YamlToolBase(tool_name="test_tool")
        
        schema = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "inactive", "pending"]
                }
            },
            "required": ["status"]
        }
        
        arguments = {"status": "active"}
        
        result = tool._validate_input_schema(arguments, schema)
        assert result is None

    def test_validate_input_schema_enum_failure(self):
        """Test enum validation failure."""
        tool = YamlToolBase(tool_name="test_tool")
        
        schema = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "inactive", "pending"]
                }
            },
            "required": ["status"]
        }
        
        arguments = {"status": "unknown"}
        
        result = tool._validate_input_schema(arguments, schema)
        assert result == "Field 'status' must be one of: active, inactive, pending"

    def test_validate_input_schema_empty_schema(self):
        """Test validation with empty schema."""
        tool = YamlToolBase(tool_name="test_tool")
        
        result = tool._validate_input_schema({"any": "value"}, {})
        assert result is None

    def test_validate_input_schema_none_schema(self):
        """Test validation with None schema."""
        tool = YamlToolBase(tool_name="test_tool")
        
        result = tool._validate_input_schema({"any": "value"}, None)
        assert result is None


class TestYamlToolBaseScriptExecution:
    """Test cases for script execution functionality."""

    @pytest.mark.asyncio
    async def test_execute_script_success(self, mock_command_executor):
        """Test successful script execution."""
        tool_data = {
            "type": "script",
            "scripts": {"linux": "echo 'Hello {name}'"},
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"]
            }
        }
        
        tool = YamlToolBase(
            tool_name="test_script",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        # Mock the execute_async method
        mock_command_executor.mock_results["echo 'Hello World'"] = {
            "token": "test-token-123",
            "status": "running",
            "pid": 12345
        }

        with patch('platform.system', return_value='Linux'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/test/dir')):
                result = await tool._execute_script({"name": "World"})

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "test-token-123" in result[0]["text"]
        assert "running" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_execute_script_validation_error(self, mock_command_executor):
        """Test script execution with validation error."""
        tool_data = {
            "type": "script",
            "scripts": {"linux": "echo 'Hello {name}'"},
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"]
            }
        }
        
        tool = YamlToolBase(
            tool_name="test_script",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        result = await tool._execute_script({})  # Missing required 'name'

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "Input validation error" in result[0]["text"]
        assert "Missing required field: name" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_execute_script_no_script_for_os(self, mock_command_executor):
        """Test script execution when no script is defined for current OS."""
        tool_data = {
            "type": "script",
            "scripts": {"windows": "echo 'Windows only'"},
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }
        
        tool = YamlToolBase(
            tool_name="test_script",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        with patch('platform.system', return_value='Linux'):
            result = await tool._execute_script({})

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "No script defined" in result[0]["text"]
        assert "linux" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_execute_script_fallback_to_script_key(self, mock_command_executor):
        """Test script execution fallback to 'script' key."""
        tool_data = {
            "type": "script",
            "script": "echo 'Fallback script'",
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }
        
        tool = YamlToolBase(
            tool_name="test_script",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        mock_command_executor.mock_results["echo 'Fallback script'"] = {
            "token": "fallback-token",
            "status": "running",
            "pid": 54321
        }

        with patch('platform.system', return_value='Linux'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/test/dir')):
                result = await tool._execute_script({})

        assert len(result) == 1
        assert "fallback-token" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_execute_script_missing_parameter(self, mock_command_executor):
        """Test script execution with missing parameter in script template."""
        tool_data = {
            "type": "script",
            "scripts": {"linux": "echo 'Hello {missing_param}'"},
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }
        
        tool = YamlToolBase(
            tool_name="test_script",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        with patch('platform.system', return_value='Linux'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/test/dir')):
                result = await tool._execute_script({})

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "Missing required parameter" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_execute_script_with_additional_parameters(self, mock_command_executor):
        """Test script execution with additional parameters from tool data."""
        tool_data = {
            "type": "script",
            "scripts": {"linux": "echo '{message}' with {extra_param}"},
            "parameters": {"extra_param": "extra_value"},
            "inputSchema": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"]
            }
        }
        
        tool = YamlToolBase(
            tool_name="test_script",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        expected_command = "echo 'Hello' with extra_value"
        mock_command_executor.mock_results[expected_command] = {
            "token": "param-token",
            "status": "running",
            "pid": 99999
        }

        with patch('platform.system', return_value='Linux'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/test/dir')):
                result = await tool._execute_script({"message": "Hello"})

        assert len(result) == 1
        assert "param-token" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_execute_script_exception_handling(self, mock_command_executor):
        """Test script execution exception handling."""
        tool_data = {
            "type": "script",
            "scripts": {"linux": "echo 'test'"},
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }
        
        tool = YamlToolBase(
            tool_name="test_script",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        # Mock execute_async to raise an exception
        mock_command_executor.execute_async = AsyncMock(side_effect=Exception("Test exception"))

        with patch('platform.system', return_value='Linux'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/test/dir')):
                result = await tool._execute_script({})

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "Error executing script" in result[0]["text"]
        assert "Test exception" in result[0]["text"]


class TestYamlToolBaseEdgeCases:
    """Test cases for edge cases and error conditions."""

    def test_init_with_invalid_tool_data_structure(self):
        """Test initialization with invalid tool data structure."""
        # Test with non-dict tool_data
        tool = YamlToolBase(tool_name="test_tool", tool_data="invalid")
        
        # Should handle gracefully and use defaults
        assert tool.name == "test_tool"
        assert tool.description == ""
        assert tool._tool_type == "object"
        assert tool._tool_data == {}  # Should be converted to empty dict

    def test_init_with_none_values(self):
        """Test initialization with None values."""
        tool = YamlToolBase(tool_name=None, tool_data=None)
        
        assert tool.name == "unknown_yaml_tool"
        assert tool.description == ""
        assert tool._tool_data == {}

    def test_class_attribute_fallback_partial(self):
        """Test class attribute fallback when only some attributes are set."""
        class PartialYamlTool(YamlToolBase):
            _tool_name = "partial_tool"
            # No _tool_data attribute

        tool = PartialYamlTool()
        
        assert tool.name == "partial_tool"
        assert tool._tool_data == {}

    def test_input_schema_with_malformed_data(self):
        """Test input schema property with malformed tool data."""
        tool_data = {
            "inputSchema": "not_a_dict"  # Should be a dict
        }
        
        tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)
        
        # Should fall back to default schema when input_schema is not a dict
        expected_default = {"type": "object", "properties": {}, "required": []}
        assert tool.input_schema == expected_default

    @pytest.mark.asyncio
    async def test_execute_tool_with_malformed_tool_data(self, mock_command_executor):
        """Test execute_tool with malformed tool data."""
        tool = YamlToolBase(
            tool_name="malformed_tool",
            tool_data="not_a_dict",
            command_executor=mock_command_executor
        )

        result = await tool.execute_tool({})

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "not fully implemented" in result[0]["text"]


class TestYamlToolBaseDependencyInjection:
    """Test cases for dependency injection behavior."""

    @patch('mcp_tools.dependency.injector.get_tool_instance')
    def test_dependency_injection_success(self, mock_get_tool_instance):
        """Test successful dependency injection."""
        mock_executor = MockCommandExecutor()
        mock_get_tool_instance.return_value = mock_executor

        tool = YamlToolBase(tool_name="test_tool")

        assert tool._command_executor == mock_executor
        mock_get_tool_instance.assert_called_once_with("command_executor")

    @patch('mcp_tools.dependency.injector.get_tool_instance')
    def test_dependency_injection_failure(self, mock_get_tool_instance):
        """Test dependency injection when injector fails."""
        mock_get_tool_instance.return_value = None

        tool = YamlToolBase(tool_name="test_tool")

        assert tool._command_executor is None
        mock_get_tool_instance.assert_called_once_with("command_executor")

    @patch('mcp_tools.dependency.injector.get_tool_instance')
    def test_dependency_injection_exception(self, mock_get_tool_instance):
        """Test dependency injection when injector raises exception."""
        mock_get_tool_instance.side_effect = Exception("Injector error")

        # Should not raise exception, should handle gracefully
        tool = YamlToolBase(tool_name="test_tool")

        # The exception should be caught and command_executor should be None
        assert tool._command_executor is None

    def test_explicit_command_executor_overrides_injection(self, mock_command_executor):
        """Test that explicit command executor overrides dependency injection."""
        with patch('mcp_tools.dependency.injector.get_tool_instance') as mock_get_tool_instance:
            mock_get_tool_instance.return_value = MockCommandExecutor()

            tool = YamlToolBase(
                tool_name="test_tool",
                command_executor=mock_command_executor
            )

            assert tool._command_executor == mock_command_executor
            # Should not call injector when explicit executor is provided
            mock_get_tool_instance.assert_not_called()


class TestYamlToolBaseIntegration:
    """Integration test cases for YamlToolBase."""

    @pytest.mark.asyncio
    async def test_full_workflow_script_execution(self, mock_command_executor):
        """Test complete workflow from initialization to script execution."""
        tool_data = {
            "description": "Integration test tool",
            "type": "script",
            "scripts": {
                "linux": "echo 'Processing {item}' && sleep {delay}",
                "darwin": "echo 'Processing {item}' && sleep {delay}",
                "windows": "echo Processing {item} && timeout {delay}"
            },
            "parameters": {
                "delay": "1"
            },
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item": {
                        "type": "string",
                        "description": "Item to process"
                    }
                },
                "required": ["item"]
            }
        }

        tool = YamlToolBase(
            tool_name="integration_test_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        # Verify initialization
        assert tool.name == "integration_test_tool"
        assert tool.description == "Integration test tool"
        assert tool._tool_type == "script"

        # Mock command execution
        expected_command = "echo 'Processing test_item' && sleep 1"
        mock_command_executor.mock_results[expected_command] = {
            "token": "integration-token",
            "status": "running",
            "pid": 88888
        }

        # Execute the tool
        with patch('platform.system', return_value='Linux'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/integration/test')):
                result = await tool.execute_tool({"item": "test_item"})

        # Verify result
        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "integration-token" in result[0]["text"]
        assert "running" in result[0]["text"]
        assert "88888" in result[0]["text"]

        # Verify command was executed
        assert expected_command in mock_command_executor.executed_commands

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, mock_command_executor):
        """Test error handling in complete workflow."""
        tool_data = {
            "type": "script",
            "scripts": {"linux": "echo 'test'"},
            "inputSchema": {
                "type": "object",
                "properties": {"required_param": {"type": "string"}},
                "required": ["required_param"]
            }
        }

        tool = YamlToolBase(
            tool_name="error_test_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        # Test validation error
        result = await tool.execute_tool({})  # Missing required parameter

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "Input validation error" in result[0]["text"]
        assert "Missing required field: required_param" in result[0]["text"]

        # Verify no command was executed due to validation error
        assert len(mock_command_executor.executed_commands) == 0 