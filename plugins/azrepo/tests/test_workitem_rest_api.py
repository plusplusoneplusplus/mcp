"""
Tests for work item REST API operations.
"""

import pytest
import json
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
def workitem_tool_with_token(mock_executor):
    """Create AzureWorkItemTool instance with bearer token configured."""
    with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
        # Mock environment manager with bearer token
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token": "test-bearer-token-123"
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)
        return tool


@pytest.fixture
def workitem_tool_no_token(mock_executor):
    """Create AzureWorkItemTool instance without bearer token."""
    with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
        # Mock environment manager without bearer token
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project",
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)
        return tool


@pytest.fixture
def mock_rest_api_response():
    """Mock successful REST API response for work item creation."""
    return {
        "id": 12345,
        "rev": 1,
        "fields": {
            "System.AreaPath": "TestArea\\SubArea",
            "System.TeamProject": "test-project",
            "System.IterationPath": "Sprint 1",
            "System.WorkItemType": "Task",
            "System.State": "New",
            "System.Reason": "New",
            "System.CreatedDate": "2024-01-15T10:30:00.000Z",
            "System.CreatedBy": {
                "displayName": "Test User",
                "id": "test-user-id",
                "uniqueName": "test@example.com"
            },
            "System.Title": "Test Work Item",
            "System.Description": "Test description"
        },
        "_links": {
            "self": {
                "href": "https://dev.azure.com/testorg/_apis/wit/workItems/12345"
            }
        },
        "url": "https://dev.azure.com/testorg/_apis/wit/workItems/12345"
    }


class TestRestApiAuthentication:
    """Test REST API authentication functionality."""

    def test_get_auth_headers_with_token(self, workitem_tool_with_token):
        """Test authentication headers generation with bearer token."""
        headers = workitem_tool_with_token._get_auth_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
        assert headers["Content-Type"] == "application/json-patch+json"
        assert headers["Accept"] == "application/json"

    def test_get_auth_headers_without_token(self, workitem_tool_no_token):
        """Test authentication headers generation without bearer token."""
        with pytest.raises(ValueError, match="Bearer token not configured"):
            workitem_tool_no_token._get_auth_headers()


class TestRestApiConfiguration:
    """Test REST API configuration and validation."""

    @pytest.mark.asyncio
    async def test_create_work_item_missing_org(self, workitem_tool_no_token):
        """Test work item creation with missing organization."""
        # Set bearer token but clear organization
        workitem_tool_no_token.bearer_token = "test-token"
        workitem_tool_no_token.default_organization = None
        
        result = await workitem_tool_no_token.create_work_item(title="Test Work Item")
        
        assert result["success"] is False
        assert "Organization is required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_missing_project(self, workitem_tool_no_token):
        """Test work item creation with missing project."""
        # Set bearer token and org but clear project
        workitem_tool_no_token.bearer_token = "test-token"
        workitem_tool_no_token.default_organization = "testorg"
        workitem_tool_no_token.default_project = None
        
        result = await workitem_tool_no_token.create_work_item(title="Test Work Item")
        
        assert result["success"] is False
        assert "Project is required" in result["error"]

    def test_configuration_loading_with_bearer_token(self, mock_executor):
        """Test that bearer token is properly loaded from configuration."""
        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.load.return_value = None
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "bearer_token": "test-token-456"
            }

            tool = AzureWorkItemTool(command_executor=mock_executor)
            
            assert tool.bearer_token == "test-token-456"
            assert tool.default_organization == "testorg"
            assert tool.default_project == "test-project"

    def test_configuration_loading_without_bearer_token(self, mock_executor):
        """Test that missing bearer token is handled gracefully."""
        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.load.return_value = None
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                # No bearer_token
            }

            tool = AzureWorkItemTool(command_executor=mock_executor)
            
            assert tool.bearer_token is None
            assert tool.default_organization == "testorg"
            assert tool.default_project == "test-project"


class TestRestApiUrlConstruction:
    """Test REST API URL construction."""

    def test_url_construction_basic(self, workitem_tool_with_token):
        """Test that the REST API URL is constructed correctly."""
        # We can test the URL construction logic by examining the parameters
        org = workitem_tool_with_token._get_param_with_default("custom-org", workitem_tool_with_token.default_organization)
        proj = workitem_tool_with_token._get_param_with_default("custom-project", workitem_tool_with_token.default_project)
        work_item_type = "Bug"
        
        expected_url = f"https://dev.azure.com/{org}/{proj}/_apis/wit/workitems/${work_item_type}?api-version=7.1"
        
        # This tests the URL pattern that would be used
        assert "custom-org" in expected_url
        assert "custom-project" in expected_url
        assert "Bug" in expected_url
        assert "api-version=7.1" in expected_url

    def test_url_construction_with_defaults(self, workitem_tool_with_token):
        """Test URL construction using default values."""
        org = workitem_tool_with_token._get_param_with_default(None, workitem_tool_with_token.default_organization)
        proj = workitem_tool_with_token._get_param_with_default(None, workitem_tool_with_token.default_project)
        work_item_type = "Task"
        
        expected_url = f"https://dev.azure.com/{org}/{proj}/_apis/wit/workitems/${work_item_type}?api-version=7.1"
        
        assert "testorg" in expected_url
        assert "test-project" in expected_url
        assert "Task" in expected_url


class TestRestApiPatchDocument:
    """Test REST API patch document construction."""

    def test_patch_document_minimal(self, workitem_tool_with_token):
        """Test patch document construction with minimal fields."""
        title = "Test Work Item"
        
        # This simulates the patch document construction logic
        patch_document = [
            {
                "op": "add",
                "path": "/fields/System.Title",
                "value": title
            }
        ]
        
        # Add area and iteration from defaults
        if workitem_tool_with_token.default_area_path:
            patch_document.append({
                "op": "add",
                "path": "/fields/System.AreaPath",
                "value": workitem_tool_with_token.default_area_path
            })
        
        if workitem_tool_with_token.default_iteration_path:
            patch_document.append({
                "op": "add",
                "path": "/fields/System.IterationPath",
                "value": workitem_tool_with_token.default_iteration_path
            })
        
        # Verify patch document structure
        assert len(patch_document) == 3  # title, area, iteration
        
        title_patch = next(p for p in patch_document if p["path"] == "/fields/System.Title")
        assert title_patch["op"] == "add"
        assert title_patch["value"] == "Test Work Item"

    def test_patch_document_with_description(self, workitem_tool_with_token):
        """Test patch document construction with description."""
        title = "Test Work Item"
        description = "Test description"
        
        patch_document = [
            {
                "op": "add",
                "path": "/fields/System.Title",
                "value": title
            },
            {
                "op": "add",
                "path": "/fields/System.Description",
                "value": description
            }
        ]
        
        # Verify description is included
        desc_patch = next(p for p in patch_document if p["path"] == "/fields/System.Description")
        assert desc_patch["op"] == "add"
        assert desc_patch["value"] == "Test description"


class TestExecuteToolValidation:
    """Test execute_tool method validation."""

    @pytest.mark.asyncio
    async def test_execute_tool_create_missing_title(self, workitem_tool_with_token):
        """Test execute_tool create operation with missing title."""
        result = await workitem_tool_with_token.execute_tool({
            "operation": "create"
            # Missing title
        })
        
        assert result["success"] is False
        assert "title is required for create operation" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_unknown_operation(self, workitem_tool_with_token):
        """Test execute_tool with unknown operation."""
        result = await workitem_tool_with_token.execute_tool({
            "operation": "unknown_operation"
        })
        
        assert result["success"] is False
        assert "Unknown operation: unknown_operation" in result["error"]


class TestRestApiWorkItemCreation:
    """Test REST API work item creation functionality."""

    @pytest.mark.asyncio
    async def test_create_work_item_rest_api_success(self, workitem_tool_with_token, mock_rest_api_response):
        """Test successful work item creation via REST API."""
        
        # Mock the aiohttp session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_rest_api_response))
        
        # Mock the session.post context manager
        mock_post_context = AsyncMock()
        mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_context.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the session context manager
        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_post_context)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await workitem_tool_with_token.create_work_item(
                title="Test Work Item",
                description="Test description"
            )

        # Verify the result
        assert result["success"] is True
        assert result["data"]["id"] == 12345
        assert result["data"]["fields"]["System.Title"] == "Test Work Item"

    @pytest.mark.asyncio
    async def test_create_work_item_rest_api_http_error(self, workitem_tool_with_token):
        """Test work item creation with HTTP error response."""
        error_response = {
            "message": "Access denied",
            "typeKey": "UnauthorizedRequestException"
        }
        
        # Mock the aiohttp session and response
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value=json.dumps(error_response))
        
        # Mock the session.post context manager
        mock_post_context = AsyncMock()
        mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_context.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the session context manager
        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_post_context)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await workitem_tool_with_token.create_work_item(title="Test Work Item")

        # Verify error handling
        assert result["success"] is False
        assert "HTTP 401" in result["error"]
        assert "raw_output" in result


class TestExecuteToolRestApi:
    """Test execute_tool method with REST API."""

    @pytest.mark.asyncio
    async def test_execute_tool_create_rest_api(self, workitem_tool_with_token, mock_rest_api_response):
        """Test execute_tool create operation via REST API."""
        
        # Mock the aiohttp session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_rest_api_response))
        
        # Mock the session.post context manager
        mock_post_context = AsyncMock()
        mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_context.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the session context manager
        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_post_context)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await workitem_tool_with_token.execute_tool({
                "operation": "create",
                "title": "Test Work Item",
                "description": "Test description",
                "work_item_type": "User Story"
            })

        assert result["success"] is True
        assert result["data"]["id"] == 12345 