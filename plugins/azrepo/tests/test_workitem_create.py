"""
Tests for work item creation operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from plugins.azrepo.workitem_tool import AzureWorkItemTool


@pytest.fixture
def mock_executor():
    """Mock command executor."""
    executor = MagicMock()
    executor.execute_async = AsyncMock()
    executor.query_process = AsyncMock()
    return executor


@pytest.fixture
def workitem_tool(mock_executor):
    """Create AzureWorkItemTool instance with mocked executor."""
    with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
        # Mock environment manager
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "https://dev.azure.com/testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)
        return tool


@pytest.fixture
def workitem_tool_no_defaults(mock_executor):
    """Create AzureWorkItemTool instance with no defaults."""
    with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
        # Mock environment manager with no defaults
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {}

        tool = AzureWorkItemTool(command_executor=mock_executor)
        return tool


@pytest.fixture
def mock_create_response():
    """Mock response for work item creation."""
    return {
        "success": True,
        "data": {
            "id": 12345,
            "title": "Test Work Item",
            "workItemType": "Task",
            "state": "New",
            "areaPath": "TestArea\\SubArea",
            "iterationPath": "Sprint 1",
            "description": "Test description",
        }
    }


@pytest.fixture
def mock_error_response():
    """Mock error response for work item creation."""
    return {
        "success": False,
        "error": "Azure CLI command failed: Access denied",
        "raw_output": "Error: Access denied to project"
    }


@pytest.fixture
def mock_json_error_response():
    """Mock JSON parsing error response."""
    return {
        "success": False,
        "error": "Failed to parse JSON output: Expecting value: line 1 column 1 (char 0)",
        "raw_output": "Invalid JSON response"
    }


class TestCreateWorkItem:
    """Test the create_work_item method."""

    @pytest.mark.asyncio
    async def test_create_work_item_basic(self, workitem_tool, mock_create_response):
        """Test basic work item creation."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        result = await workitem_tool.create_work_item(
            title="Test Work Item",
            description="Test description"
        )

        expected_command = (
            "boards work-item create --type 'Task' --title 'Test Work Item' "
            "--org https://dev.azure.com/testorg --project test-project "
            "--description 'Test description' --area 'TestArea\\SubArea' "
            "--iteration 'Sprint 1'"
        )
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_create_work_item_with_custom_type(self, workitem_tool, mock_create_response):
        """Test work item creation with custom type."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        result = await workitem_tool.create_work_item(
            title="Bug Report",
            work_item_type="Bug"
        )

        expected_command = (
            "boards work-item create --type 'Bug' --title 'Bug Report' "
            "--org https://dev.azure.com/testorg --project test-project "
            "--area 'TestArea\\SubArea' --iteration 'Sprint 1'"
        )
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_create_work_item_with_overrides(self, workitem_tool, mock_create_response):
        """Test work item creation with parameter overrides."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        result = await workitem_tool.create_work_item(
            title="Custom Work Item",
            area_path="CustomArea",
            iteration_path="Sprint 2",
            organization="https://dev.azure.com/customorg",
            project="custom-project"
        )

        expected_command = (
            "boards work-item create --type 'Task' --title 'Custom Work Item' "
            "--org https://dev.azure.com/customorg --project custom-project "
            "--area 'CustomArea' --iteration 'Sprint 2'"
        )
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_create_work_item_minimal(self, workitem_tool, mock_create_response):
        """Test work item creation with minimal parameters."""
        # Clear defaults to test minimal case
        workitem_tool.default_organization = None
        workitem_tool.default_project = None
        workitem_tool.default_area_path = None
        workitem_tool.default_iteration_path = None

        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        result = await workitem_tool.create_work_item(title="Minimal Work Item")

        expected_command = "boards work-item create --type 'Task' --title 'Minimal Work Item'"
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_create_work_item_with_special_characters(self, workitem_tool, mock_create_response):
        """Test work item creation with special characters in title and description."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        result = await workitem_tool.create_work_item(
            title="Fix issue with 'quotes' and \"double quotes\"",
            description="Description with special chars: @#$%^&*()_+-={}[]|\\:;\"'<>?,./"
        )

        expected_command = (
            "boards work-item create --type 'Task' --title 'Fix issue with 'quotes' and \"double quotes\"' "
            "--org https://dev.azure.com/testorg --project test-project "
            "--description 'Description with special chars: @#$%^&*()_+-={}[]|\\:;\"'<>?,./' "
            "--area 'TestArea\\SubArea' --iteration 'Sprint 1'"
        )
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_create_work_item_with_unicode(self, workitem_tool, mock_create_response):
        """Test work item creation with Unicode characters."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        result = await workitem_tool.create_work_item(
            title="Unicode test: 测试 🚀 émojis",
            description="Description with Unicode: café naïve résumé 中文"
        )

        expected_command = (
            "boards work-item create --type 'Task' --title 'Unicode test: 测试 🚀 émojis' "
            "--org https://dev.azure.com/testorg --project test-project "
            "--description 'Description with Unicode: café naïve résumé 中文' "
            "--area 'TestArea\\SubArea' --iteration 'Sprint 1'"
        )
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_create_work_item_all_work_item_types(self, workitem_tool, mock_create_response):
        """Test work item creation with different work item types."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        work_item_types = ["Task", "Bug", "User Story", "Epic", "Feature", "Issue", "Test Case"]

        for work_item_type in work_item_types:
            result = await workitem_tool.create_work_item(
                title=f"Test {work_item_type}",
                work_item_type=work_item_type
            )

            expected_command = (
                f"boards work-item create --type '{work_item_type}' --title 'Test {work_item_type}' "
                "--org https://dev.azure.com/testorg --project test-project "
                "--area 'TestArea\\SubArea' --iteration 'Sprint 1'"
            )
            assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_create_work_item_with_empty_description(self, workitem_tool, mock_create_response):
        """Test work item creation with empty description."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        result = await workitem_tool.create_work_item(
            title="Work Item with Empty Description",
            description=""
        )

        # Empty description should not be added to the command
        expected_command = (
            "boards work-item create --type 'Task' --title 'Work Item with Empty Description' "
            "--org https://dev.azure.com/testorg --project test-project "
            "--area 'TestArea\\SubArea' --iteration 'Sprint 1'"
        )
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_create_work_item_with_none_values(self, workitem_tool, mock_create_response):
        """Test work item creation with None values for optional parameters."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        result = await workitem_tool.create_work_item(
            title="Work Item with None Values",
            description=None,
            area_path=None,
            iteration_path=None,
            organization=None,
            project=None
        )

        expected_command = (
            "boards work-item create --type 'Task' --title 'Work Item with None Values' "
            "--org https://dev.azure.com/testorg --project test-project "
            "--area 'TestArea\\SubArea' --iteration 'Sprint 1'"
        )
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_create_work_item_command_failure(self, workitem_tool, mock_error_response):
        """Test work item creation when Azure CLI command fails."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_error_response)

        result = await workitem_tool.create_work_item(title="Failed Work Item")

        assert result == mock_error_response
        assert result["success"] is False
        assert "Access denied" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_json_parse_error(self, workitem_tool, mock_json_error_response):
        """Test work item creation when JSON parsing fails."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_json_error_response)

        result = await workitem_tool.create_work_item(title="JSON Error Work Item")

        assert result == mock_json_error_response
        assert result["success"] is False
        assert "Failed to parse JSON" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_long_title(self, workitem_tool, mock_create_response):
        """Test work item creation with very long title."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        long_title = "A" * 255  # Very long title
        result = await workitem_tool.create_work_item(title=long_title)

        expected_command = (
            f"boards work-item create --type 'Task' --title '{long_title}' "
            "--org https://dev.azure.com/testorg --project test-project "
            "--area 'TestArea\\SubArea' --iteration 'Sprint 1'"
        )
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_create_work_item_long_description(self, workitem_tool, mock_create_response):
        """Test work item creation with very long description."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        long_description = "B" * 1000  # Very long description
        result = await workitem_tool.create_work_item(
            title="Work Item with Long Description",
            description=long_description
        )

        expected_command = (
            f"boards work-item create --type 'Task' --title 'Work Item with Long Description' "
            f"--org https://dev.azure.com/testorg --project test-project "
            f"--description '{long_description}' --area 'TestArea\\SubArea' --iteration 'Sprint 1'"
        )
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response


class TestExecuteToolCreate:
    """Test the execute_tool method for create operations."""

    @pytest.mark.asyncio
    async def test_execute_tool_create_success(self, workitem_tool, mock_create_response):
        """Test successful work item creation through execute_tool."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        arguments = {
            "operation": "create",
            "title": "Test Work Item",
            "description": "Test description",
            "work_item_type": "User Story"
        }

        result = await workitem_tool.execute_tool(arguments)

        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_execute_tool_create_missing_title(self, workitem_tool):
        """Test work item creation with missing title."""
        arguments = {
            "operation": "create",
            "description": "Test description"
        }

        result = await workitem_tool.execute_tool(arguments)

        assert result["success"] is False
        assert "title is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_create_empty_title(self, workitem_tool):
        """Test work item creation with empty title."""
        arguments = {
            "operation": "create",
            "title": "",
            "description": "Test description"
        }

        result = await workitem_tool.execute_tool(arguments)

        assert result["success"] is False
        assert "title is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_create_none_title(self, workitem_tool):
        """Test work item creation with None title."""
        arguments = {
            "operation": "create",
            "title": None,
            "description": "Test description"
        }

        result = await workitem_tool.execute_tool(arguments)

        assert result["success"] is False
        assert "title is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_create_with_all_params(self, workitem_tool, mock_create_response):
        """Test work item creation with all parameters."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        arguments = {
            "operation": "create",
            "title": "Complete Work Item",
            "description": "Complete description",
            "work_item_type": "Epic",
            "area_path": "MyArea",
            "iteration_path": "MyIteration",
            "organization": "https://dev.azure.com/myorg",
            "project": "my-project"
        }

        result = await workitem_tool.execute_tool(arguments)

        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_execute_tool_create_with_defaults_fallback(self, workitem_tool_no_defaults, mock_create_response):
        """Test work item creation when no defaults are configured."""
        workitem_tool_no_defaults._run_az_command = AsyncMock(return_value=mock_create_response)

        arguments = {
            "operation": "create",
            "title": "Work Item No Defaults"
        }

        result = await workitem_tool_no_defaults.execute_tool(arguments)

        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_execute_tool_create_with_boolean_values(self, workitem_tool, mock_create_response):
        """Test work item creation with boolean values in arguments."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        arguments = {
            "operation": "create",
            "title": "Boolean Test",
            "description": True,  # Should be converted to string
            "work_item_type": False  # Should be converted to string
        }

        result = await workitem_tool.execute_tool(arguments)

        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_execute_tool_create_with_numeric_values(self, workitem_tool, mock_create_response):
        """Test work item creation with numeric values in arguments."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        arguments = {
            "operation": "create",
            "title": 12345,  # Should be converted to string
            "description": 67890,  # Should be converted to string
        }

        result = await workitem_tool.execute_tool(arguments)

        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_execute_tool_create_error_propagation(self, workitem_tool, mock_error_response):
        """Test that errors from create_work_item are properly propagated."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_error_response)

        arguments = {
            "operation": "create",
            "title": "Error Test Work Item"
        }

        result = await workitem_tool.execute_tool(arguments)

        assert result == mock_error_response
        assert result["success"] is False


class TestConfigurationLoading:
    """Test configuration loading for work items."""

    @patch("plugins.azrepo.workitem_tool.env_manager")
    def test_load_config_with_work_item_defaults(self, mock_env_manager, mock_executor):
        """Test configuration loading with work item specific defaults."""
        # Mock environment manager
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "https://dev.azure.com/testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)

        assert tool.default_organization == "https://dev.azure.com/testorg"
        assert tool.default_project == "test-project"
        assert tool.default_area_path == "TestArea\\SubArea"
        assert tool.default_iteration_path == "Sprint 1"

    @patch("plugins.azrepo.workitem_tool.env_manager")
    def test_load_config_partial_defaults(self, mock_env_manager, mock_executor):
        """Test configuration loading with partial defaults."""
        # Mock environment manager with partial configuration
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "https://dev.azure.com/testorg",
            "project": "test-project",
            # area_path and iteration not provided
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)

        assert tool.default_organization == "https://dev.azure.com/testorg"
        assert tool.default_project == "test-project"
        assert tool.default_area_path is None
        assert tool.default_iteration_path is None

    @patch("plugins.azrepo.workitem_tool.env_manager")
    def test_load_config_empty_defaults(self, mock_env_manager, mock_executor):
        """Test configuration loading with empty defaults."""
        # Mock environment manager with empty configuration
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {}

        tool = AzureWorkItemTool(command_executor=mock_executor)

        assert tool.default_organization is None
        assert tool.default_project is None
        assert tool.default_area_path is None
        assert tool.default_iteration_path is None

    @patch("plugins.azrepo.workitem_tool.env_manager")
    def test_load_config_exception_handling(self, mock_env_manager, mock_executor):
        """Test configuration loading when environment manager raises exception."""
        # Mock environment manager to raise exception
        mock_env_manager.load.side_effect = Exception("Config load failed")

        tool = AzureWorkItemTool(command_executor=mock_executor)

        # Should fall back to None values
        assert tool.default_organization is None
        assert tool.default_project is None
        assert tool.default_area_path is None
        assert tool.default_iteration_path is None

    @patch("plugins.azrepo.workitem_tool.env_manager")
    def test_load_config_with_special_characters(self, mock_env_manager, mock_executor):
        """Test configuration loading with special characters in paths."""
        # Mock environment manager with special characters
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "https://dev.azure.com/test-org",
            "project": "test_project-123",
            "area_path": "Test Area\\Sub-Area (Special)",
            "iteration": "Sprint 1.0 - Q1'2024",
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)

        assert tool.default_organization == "https://dev.azure.com/test-org"
        assert tool.default_project == "test_project-123"
        assert tool.default_area_path == "Test Area\\Sub-Area (Special)"
        assert tool.default_iteration_path == "Sprint 1.0 - Q1'2024"


class TestParameterHandling:
    """Test parameter handling with defaults."""

    def test_get_param_with_default_explicit_value(self, workitem_tool):
        """Test parameter handling when explicit value is provided."""
        result = workitem_tool._get_param_with_default("explicit", "default")
        assert result == "explicit"

    def test_get_param_with_default_none_value(self, workitem_tool):
        """Test parameter handling when None is provided."""
        result = workitem_tool._get_param_with_default(None, "default")
        assert result == "default"

    def test_get_param_with_default_both_none(self, workitem_tool):
        """Test parameter handling when both values are None."""
        result = workitem_tool._get_param_with_default(None, None)
        assert result is None

    def test_get_param_with_default_empty_string_explicit(self, workitem_tool):
        """Test parameter handling when empty string is provided explicitly."""
        result = workitem_tool._get_param_with_default("", "default")
        assert result == ""

    def test_get_param_with_default_empty_string_default(self, workitem_tool):
        """Test parameter handling when default is empty string."""
        result = workitem_tool._get_param_with_default(None, "")
        assert result == ""

    def test_get_param_with_default_zero_value(self, workitem_tool):
        """Test parameter handling when zero is provided."""
        result = workitem_tool._get_param_with_default(0, "default")
        assert result == 0

    def test_get_param_with_default_false_value(self, workitem_tool):
        """Test parameter handling when False is provided."""
        result = workitem_tool._get_param_with_default(False, "default")
        assert result is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_create_work_item_with_whitespace_title(self, workitem_tool, mock_create_response):
        """Test work item creation with whitespace-only title."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        result = await workitem_tool.create_work_item(title="   ")

        expected_command = (
            "boards work-item create --type 'Task' --title '   ' "
            "--org https://dev.azure.com/testorg --project test-project "
            "--area 'TestArea\\SubArea' --iteration 'Sprint 1'"
        )
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_create_work_item_with_newlines(self, workitem_tool, mock_create_response):
        """Test work item creation with newlines in title and description."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        result = await workitem_tool.create_work_item(
            title="Title with\nnewlines",
            description="Description with\nmultiple\nlines"
        )

        expected_command = (
            "boards work-item create --type 'Task' --title 'Title with\nnewlines' "
            "--org https://dev.azure.com/testorg --project test-project "
            "--description 'Description with\nmultiple\nlines' "
            "--area 'TestArea\\SubArea' --iteration 'Sprint 1'"
        )
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_create_work_item_with_tabs(self, workitem_tool, mock_create_response):
        """Test work item creation with tab characters."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        result = await workitem_tool.create_work_item(
            title="Title\twith\ttabs",
            description="Description\twith\ttabs"
        )

        expected_command = (
            "boards work-item create --type 'Task' --title 'Title\twith\ttabs' "
            "--org https://dev.azure.com/testorg --project test-project "
            "--description 'Description\twith\ttabs' "
            "--area 'TestArea\\SubArea' --iteration 'Sprint 1'"
        )
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response

    @pytest.mark.asyncio
    async def test_create_work_item_with_backslashes(self, workitem_tool, mock_create_response):
        """Test work item creation with backslashes in paths."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        result = await workitem_tool.create_work_item(
            title="File path: C:\\Users\\test\\file.txt",
            area_path="Project\\Team\\SubTeam",
            iteration_path="Release\\Sprint 1"
        )

        expected_command = (
            "boards work-item create --type 'Task' --title 'File path: C:\\Users\\test\\file.txt' "
            "--org https://dev.azure.com/testorg --project test-project "
            "--area 'Project\\Team\\SubTeam' --iteration 'Release\\Sprint 1'"
        )
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response


class TestIntegration:
    """Integration tests combining multiple features."""

    @pytest.mark.asyncio
    async def test_create_work_item_full_workflow(self, workitem_tool, mock_create_response):
        """Test complete work item creation workflow with all features."""
        workitem_tool._run_az_command = AsyncMock(return_value=mock_create_response)

        # Test through execute_tool with comprehensive parameters
        arguments = {
            "operation": "create",
            "title": "Complete Integration Test Work Item",
            "description": "This is a comprehensive test with Unicode: 测试 🚀 and special chars: @#$%",
            "work_item_type": "User Story",
            "area_path": "Integration\\Test Area",
            "iteration_path": "Sprint 2024.1",
            "organization": "https://dev.azure.com/integration-test",
            "project": "integration-project"
        }

        result = await workitem_tool.execute_tool(arguments)

        # Verify the command was constructed correctly
        expected_command = (
            "boards work-item create --type 'User Story' "
            "--title 'Complete Integration Test Work Item' "
            "--org https://dev.azure.com/integration-test --project integration-project "
            "--description 'This is a comprehensive test with Unicode: 测试 🚀 and special chars: @#$%' "
            "--area 'Integration\\Test Area' --iteration 'Sprint 2024.1'"
        )
        workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_create_response
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_work_item_error_recovery(self, workitem_tool):
        """Test error recovery and proper error message formatting."""
        # Mock a command failure
        error_response = {
            "success": False,
            "error": "Azure CLI command failed: TF401027: You need the Generic Contribute permission(s) for project to perform this action.",
            "raw_output": "TF401027: You need the Generic Contribute permission(s) for project to perform this action."
        }
        workitem_tool._run_az_command = AsyncMock(return_value=error_response)

        arguments = {
            "operation": "create",
            "title": "Permission Test Work Item"
        }

        result = await workitem_tool.execute_tool(arguments)

        assert result["success"] is False
        assert "Generic Contribute permission" in result["error"]
        assert "raw_output" in result
