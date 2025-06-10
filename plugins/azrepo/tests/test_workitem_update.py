"""Tests for work item update REST API operations."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from plugins.azrepo.workitem_tool import AzureWorkItemTool


def mock_aiohttp_for_update_success(work_item_data=None):
    """Helper function to mock successful aiohttp PATCH calls for update operations."""
    if work_item_data is None:
        work_item_data = {
            "id": 12345,
            "rev": 2,
            "fields": {
                "System.Title": "Updated Work Item Title",
                "System.WorkItemType": "Task",
                "System.State": "Active",
                "System.AreaPath": "TestArea\\SubArea",
                "System.IterationPath": "Sprint 1",
                "System.Description": "<p>Updated test description</p>",
                "System.ChangedDate": "2024-01-16T14:20:00.000Z",
                "System.ChangedBy": {
                    "displayName": "Test User",
                    "id": "test-user-id",
                    "uniqueName": "test@example.com"
                }
            },
            "_links": {
                "self": {
                    "href": "https://dev.azure.com/testorg/_apis/wit/workItems/12345"
                }
            },
            "url": "https://dev.azure.com/testorg/_apis/wit/workItems/12345"
        }

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=json.dumps(work_item_data))

    mock_session = MagicMock()
    mock_session.patch.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.patch.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    return patch("aiohttp.ClientSession", return_value=mock_session)


def mock_aiohttp_for_update_error(status_code=404, error_message="Work item not found"):
    """Helper function to mock error aiohttp PATCH calls for update operations."""
    mock_response = MagicMock()
    mock_response.status = status_code
    mock_response.text = AsyncMock(return_value=json.dumps({
        "message": error_message,
        "typeKey": "WorkItemNotFoundException" if status_code == 404 else "UnauthorizedRequestException"
    }))

    mock_session = MagicMock()
    mock_session.patch.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.patch.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    return patch("aiohttp.ClientSession", return_value=mock_session)


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
    # Use a persistent patch that lasts for the entire test
    patcher = patch("plugins.azrepo.workitem_tool.env_manager")
    mock_env_manager = patcher.start()

    # Mock environment manager
    mock_env_manager.load.return_value = None
    mock_env_manager.get_azrepo_parameters.return_value = {
        "org": "testorg",
        "project": "test-project",
        "area_path": "TestArea\\SubArea",
        "iteration": "Sprint 1",
        "bearer_token": "test-bearer-token-123"
    }

    tool = AzureWorkItemTool(command_executor=mock_executor)

    yield tool

    # Clean up the patch
    patcher.stop()


@pytest.fixture
def workitem_tool_no_defaults(mock_executor):
    """Create AzureWorkItemTool instance with no defaults."""
    # Use a persistent patch that lasts for the entire test
    patcher = patch("plugins.azrepo.workitem_tool.env_manager")
    mock_env_manager = patcher.start()

    # Mock environment manager with no defaults
    mock_env_manager.load.return_value = None
    mock_env_manager.get_azrepo_parameters.return_value = {
        "bearer_token": "test-bearer-token-123"  # Still need bearer token
    }

    tool = AzureWorkItemTool(command_executor=mock_executor)

    yield tool

    # Clean up the patch
    patcher.stop()


class TestUpdateWorkItem:
    """Test the update_work_item method."""

    @pytest.mark.asyncio
    async def test_update_work_item_title_only(self, workitem_tool):
        """Test updating work item title only."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Work Item Title"
            )

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["id"] == 12345
            assert result["data"]["fields"]["System.Title"] == "Updated Work Item Title"

    @pytest.mark.asyncio
    async def test_update_work_item_description_only(self, workitem_tool):
        """Test updating work item description only."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.update_work_item(
                work_item_id=12345,
                description="Updated test description"
            )

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["id"] == 12345

    @pytest.mark.asyncio
    async def test_update_work_item_both_fields(self, workitem_tool):
        """Test updating both title and description."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title",
                description="Updated description"
            )

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["id"] == 12345

    @pytest.mark.asyncio
    async def test_update_work_item_with_markdown(self, workitem_tool):
        """Test updating work item description with markdown content."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.update_work_item(
                work_item_id=12345,
                description="## Updated Description\n\nNew details with **markdown** support"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_update_work_item_string_id(self, workitem_tool):
        """Test updating work item with string ID."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.update_work_item(
                work_item_id="12345",
                title="Updated Title"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_update_work_item_with_overrides(self, workitem_tool):
        """Test updating work item with parameter overrides."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title",
                organization="customorg",
                project="custom-project"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_update_work_item_no_fields_provided(self, workitem_tool):
        """Test updating work item with no fields provided."""
        result = await workitem_tool.update_work_item(work_item_id=12345)

        assert result["success"] is False
        assert "At least one of title or description must be provided" in result["error"]

    @pytest.mark.asyncio
    async def test_update_work_item_missing_org(self, workitem_tool):
        """Test updating work item with missing organization."""
        # Clear the organization
        workitem_tool.default_organization = None

        result = await workitem_tool.update_work_item(
            work_item_id=12345,
            title="Updated Title"
        )

        assert result["success"] is False
        assert "Organization is required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_work_item_missing_project(self, workitem_tool):
        """Test updating work item with missing project."""
        # Clear the project
        workitem_tool.default_project = None

        result = await workitem_tool.update_work_item(
            work_item_id=12345,
            title="Updated Title"
        )

        assert result["success"] is False
        assert "Project is required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_work_item_not_found(self, workitem_tool):
        """Test updating work item that doesn't exist."""
        with mock_aiohttp_for_update_error(404, "Work item not found"):
            result = await workitem_tool.update_work_item(
                work_item_id=99999,
                title="Updated Title"
            )

            assert result["success"] is False
            assert "Work item 99999 not found" in result["error"]
            assert "raw_output" in result

    @pytest.mark.asyncio
    async def test_update_work_item_http_error(self, workitem_tool):
        """Test updating work item with HTTP error."""
        with mock_aiohttp_for_update_error(401, "Access denied"):
            result = await workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title"
            )

            assert result["success"] is False
            assert "HTTP 401" in result["error"]
            assert "raw_output" in result

    @pytest.mark.asyncio
    async def test_update_work_item_json_parse_error(self, workitem_tool):
        """Test updating work item with JSON parsing error."""
        # Mock invalid JSON response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="Invalid JSON response")

        mock_session = MagicMock()
        mock_session.patch.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.patch.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title"
            )

            assert result["success"] is False
            assert "Failed to parse response" in result["error"]
            assert "raw_output" in result

    @pytest.mark.asyncio
    async def test_update_work_item_network_error(self, workitem_tool):
        """Test updating work item with network error."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.side_effect = Exception("Network error")

            result = await workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title"
            )

            assert result["success"] is False
            assert "Network error" in result["error"]

    @pytest.mark.asyncio
    async def test_update_work_item_with_special_characters(self, workitem_tool):
        """Test updating work item with special characters."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title with Special Characters: @#$%^&*()",
                description="Description with special chars: <>&\"'"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_update_work_item_with_unicode(self, workitem_tool):
        """Test updating work item with Unicode characters."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title with Unicode: 测试 🚀 ñáéíóú",
                description="Unicode description: 日本語 العربية русский"
            )

            assert result["success"] is True
            assert "data" in result


class TestExecuteToolUpdate:
    """Test the execute_tool method for update operations."""

    @pytest.mark.asyncio
    async def test_execute_tool_update_success(self, workitem_tool):
        """Test successful update via execute_tool."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.execute_tool({
                "operation": "update",
                "work_item_id": 12345,
                "title": "Updated Title",
                "description": "Updated description"
            })

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_update_title_only(self, workitem_tool):
        """Test updating title only via execute_tool."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.execute_tool({
                "operation": "update",
                "work_item_id": 12345,
                "title": "Updated Title Only"
            })

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_update_description_only(self, workitem_tool):
        """Test updating description only via execute_tool."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.execute_tool({
                "operation": "update",
                "work_item_id": 12345,
                "description": "Updated description only"
            })

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_update_missing_work_item_id(self, workitem_tool):
        """Test update operation with missing work_item_id."""
        result = await workitem_tool.execute_tool({
            "operation": "update",
            "title": "Updated Title"
        })

        assert result["success"] is False
        assert "work_item_id is required for update operation" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_update_missing_fields(self, workitem_tool):
        """Test update operation with missing title and description."""
        result = await workitem_tool.execute_tool({
            "operation": "update",
            "work_item_id": 12345
        })

        assert result["success"] is False
        assert "At least one of title or description must be provided" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_update_with_overrides(self, workitem_tool):
        """Test update operation with parameter overrides."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.execute_tool({
                "operation": "update",
                "work_item_id": 12345,
                "title": "Updated Title",
                "organization": "customorg",
                "project": "custom-project"
            })

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_update_error_propagation(self, workitem_tool):
        """Test that update errors are properly propagated through execute_tool."""
        with mock_aiohttp_for_update_error(404, "Work item not found"):
            result = await workitem_tool.execute_tool({
                "operation": "update",
                "work_item_id": 99999,
                "title": "Updated Title"
            })

            assert result["success"] is False
            assert "Work item 99999 not found" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_update_with_markdown(self, workitem_tool):
        """Test update operation with markdown description."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.execute_tool({
                "operation": "update",
                "work_item_id": 12345,
                "description": "## Updated Description\n\nWith **markdown** formatting"
            })

            assert result["success"] is True
            assert "data" in result


class TestUpdateValidation:
    """Test validation logic for update operations."""

    @pytest.mark.asyncio
    async def test_update_validation_both_none(self, workitem_tool):
        """Test validation when both title and description are None."""
        result = await workitem_tool.update_work_item(
            work_item_id=12345,
            title=None,
            description=None
        )

        assert result["success"] is False
        assert "At least one of title or description must be provided" in result["error"]

    @pytest.mark.asyncio
    async def test_update_validation_empty_string_title(self, workitem_tool):
        """Test validation with empty string title (should be allowed)."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.update_work_item(
                work_item_id=12345,
                title=""
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_validation_empty_string_description(self, workitem_tool):
        """Test validation with empty string description (should be allowed)."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.update_work_item(
                work_item_id=12345,
                description=""
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_validation_whitespace_only_title(self, workitem_tool):
        """Test validation with whitespace-only title (should be allowed)."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.update_work_item(
                work_item_id=12345,
                title="   "
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_validation_whitespace_only_description(self, workitem_tool):
        """Test validation with whitespace-only description (should be allowed)."""
        with mock_aiohttp_for_update_success():
            result = await workitem_tool.update_work_item(
                work_item_id=12345,
                description="   "
            )

            assert result["success"] is True


class TestUpdateConfiguration:
    """Test configuration handling for update operations."""

    @pytest.mark.asyncio
    async def test_update_with_defaults_fallback(self, workitem_tool_no_defaults):
        """Test update operation with defaults fallback."""
        # Set bearer token but no org/project defaults
        workitem_tool_no_defaults.bearer_token = "test-token"

        # Test with missing organization (should fail with org required)
        result = await workitem_tool_no_defaults.update_work_item(
            work_item_id=12345,
            title="Updated Title",
            project="fallback-project"
        )

        assert result["success"] is False
        assert "Organization is required" in result["error"]

    def test_update_parameter_handling(self, workitem_tool):
        """Test parameter handling for update operations."""
        # Test _get_param_with_default method behavior
        result = workitem_tool._get_param_with_default("explicit_value", "default_value")
        assert result == "explicit_value"

        result = workitem_tool._get_param_with_default(None, "default_value")
        assert result == "default_value"

        result = workitem_tool._get_param_with_default(None, None)
        assert result is None


class TestUpdatePatchDocument:
    """Test JSON Patch document construction for update operations."""

    @pytest.mark.asyncio
    async def test_patch_document_title_only(self, workitem_tool):
        """Test that PATCH request is made with correct JSON patch document for title only."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"id": 12345}')

            mock_session = MagicMock()
            mock_session.patch = MagicMock()
            mock_session.patch.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.patch.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            await workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title"
            )

            # Verify PATCH was called with correct patch document
            mock_session.patch.assert_called_once()
            call_args = mock_session.patch.call_args

            # Check the JSON patch document
            patch_document = call_args[1]['json']
            assert len(patch_document) == 1
            assert patch_document[0]['op'] == 'replace'
            assert patch_document[0]['path'] == '/fields/System.Title'
            assert patch_document[0]['value'] == 'Updated Title'

    @pytest.mark.asyncio
    async def test_patch_document_description_only(self, workitem_tool):
        """Test that PATCH request is made with correct JSON patch document for description only."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"id": 12345}')

            mock_session = MagicMock()
            mock_session.patch = MagicMock()
            mock_session.patch.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.patch.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            await workitem_tool.update_work_item(
                work_item_id=12345,
                description="Updated description"
            )

            # Verify PATCH was called with correct patch document
            mock_session.patch.assert_called_once()
            call_args = mock_session.patch.call_args

            # Check the JSON patch document
            patch_document = call_args[1]['json']
            assert len(patch_document) == 1
            assert patch_document[0]['op'] == 'replace'
            assert patch_document[0]['path'] == '/fields/System.Description'
            # Description should be processed through markdown conversion

    @pytest.mark.asyncio
    async def test_patch_document_both_fields(self, workitem_tool):
        """Test that PATCH request is made with correct JSON patch document for both fields."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"id": 12345}')

            mock_session = MagicMock()
            mock_session.patch = MagicMock()
            mock_session.patch.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.patch.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            await workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title",
                description="Updated description"
            )

            # Verify PATCH was called with correct patch document
            mock_session.patch.assert_called_once()
            call_args = mock_session.patch.call_args

            # Check the JSON patch document
            patch_document = call_args[1]['json']
            assert len(patch_document) == 2

            # Check title patch
            title_patch = next(p for p in patch_document if p['path'] == '/fields/System.Title')
            assert title_patch['op'] == 'replace'
            assert title_patch['value'] == 'Updated Title'

            # Check description patch
            desc_patch = next(p for p in patch_document if p['path'] == '/fields/System.Description')
            assert desc_patch['op'] == 'replace'


class TestUpdateUrlConstruction:
    """Test URL construction for update operations."""

    def test_update_url_construction(self, workitem_tool):
        """Test that update operations use correct URL format."""
        # Test URL building for update operation
        url = workitem_tool._build_api_url(
            "testorg",
            "test-project",
            "wit/workitems/12345?api-version=7.1"
        )

        expected_url = "https://dev.azure.com/testorg/test-project/_apis/wit/workitems/12345?api-version=7.1"
        assert url == expected_url

    def test_update_url_with_string_id(self, workitem_tool):
        """Test URL construction with string work item ID."""
        url = workitem_tool._build_api_url(
            "testorg",
            "test-project",
            "wit/workitems/abc123?api-version=7.1"
        )

        expected_url = "https://dev.azure.com/testorg/test-project/_apis/wit/workitems/abc123?api-version=7.1"
        assert url == expected_url


class TestUpdateAuthHeaders:
    """Test authentication headers for update operations."""

    def test_update_auth_headers(self, workitem_tool):
        """Test that update operations use correct authentication headers."""
        headers = workitem_tool._get_auth_headers()

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        assert headers["Content-Type"] == "application/json-patch+json"
        assert headers["Accept"] == "application/json"

    def test_update_auth_headers_without_token(self, workitem_tool):
        """Test authentication headers when bearer token is missing."""
        # Clear the bearer token from instance
        workitem_tool.bearer_token = None

        # Mock environment manager to return no bearer token
        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.get_azrepo_parameters.return_value = {}

            with pytest.raises(ValueError, match="Bearer token not configured"):
                workitem_tool._get_auth_headers()
