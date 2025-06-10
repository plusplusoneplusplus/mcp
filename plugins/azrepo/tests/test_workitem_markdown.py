"""
Tests for markdown conversion functionality in work item creation.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from plugins.azrepo.workitem_tool import AzureWorkItemTool
import plugins.azrepo.azure_rest_utils
from plugins.azrepo.tests.helpers import patch_azure_utils_env_manager


def mock_aiohttp_for_success(work_item_data=None):
    """Helper function to mock successful aiohttp calls."""
    if work_item_data is None:
        work_item_data = {
            "id": 12345,
            "fields": {
                "System.Title": "Test Work Item",
                "System.WorkItemType": "Task",
                "System.State": "New",
                "System.AreaPath": "TestArea\\SubArea",
                "System.IterationPath": "Sprint 1",
                "System.Description": "<h1>Test Description</h1>"
            }
        }

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=json.dumps(work_item_data))

    mock_session = MagicMock()
    mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    return patch("aiohttp.ClientSession", return_value=mock_session)


@pytest.fixture
def mock_executor():
    """Create a mock command executor."""
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
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token": "test-bearer-token-123"
        }

        with patch("plugins.azrepo.azure_rest_utils.env_manager") as mock_rest_env_manager:
            # Also mock the azure_rest_utils env_manager with the same values
            mock_rest_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "area_path": "TestArea\\SubArea",
                "iteration": "Sprint 1",
                "bearer_token": "test-bearer-token-123"
            }

            tool = AzureWorkItemTool(command_executor=mock_executor)
            return tool


class TestMarkdownConversion:
    """Test markdown conversion in work item creation."""

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_create_work_item_with_markdown_description(self, mock_env_manager, mock_rest_env_manager, workitem_tool):
        """Test work item creation with markdown description."""
        # Configure both mocks to return the same values
        config = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        markdown_description = """# Bug Report

## Description
The login functionality is **not working** properly.

## Steps to Reproduce
1. Navigate to login page
2. Enter valid credentials
3. Click login button

## Expected Result
User should be logged in successfully.

## Actual Result
Error message appears: `Invalid credentials`
"""

        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Login Bug",
                description=markdown_description
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_create_work_item_with_plain_text_description(self, mock_env_manager, mock_rest_env_manager, workitem_tool):
        """Test work item creation with plain text description."""
        # Configure both mocks to return the same values
        config = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        plain_description = "This is a simple plain text description without any markdown formatting."

        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Simple Task",
                description=plain_description
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_create_work_item_with_mixed_markdown(self, mock_env_manager, mock_rest_env_manager, workitem_tool):
        """Test work item creation with mixed markdown content."""
        # Configure both mocks to return the same values
        config = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        mixed_description = """## Feature Request

### Overview
We need to implement a new **authentication system** with the following features:

- Multi-factor authentication
- Single sign-on (SSO)
- Password reset functionality

### Technical Requirements
```python
# Example API endpoint
@app.route('/auth/login', methods=['POST'])
def login():
    return authenticate_user(request.json)
```

### Acceptance Criteria
1. Users can log in with email and password
2. MFA is required for admin accounts
3. Session timeout after 30 minutes of inactivity

> **Note**: This feature should be implemented in the next sprint.
"""

        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Authentication System",
                description=mixed_description,
                work_item_type="User Story"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_create_work_item_no_description(self, mock_env_manager, mock_rest_env_manager, workitem_tool):
        """Test work item creation without description."""
        # Configure both mocks to return the same values
        config = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Task Without Description"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_create_work_item_empty_description(self, mock_env_manager, mock_rest_env_manager, workitem_tool):
        """Test work item creation with empty description."""
        # Configure both mocks to return the same values
        config = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Task With Empty Description",
                description=""
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_execute_tool_with_markdown_description(self, mock_env_manager, mock_rest_env_manager, workitem_tool):
        """Test execute_tool with markdown description."""
        # Configure both mocks to return the same values
        config = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        markdown_description = """# Task Description

This task involves:
- **Analysis** of current system
- *Implementation* of new features
- Testing and validation

```bash
# Commands to run
npm install
npm test
```
"""

        with mock_aiohttp_for_success():
            arguments = {
                "operation": "create",
                "title": "Development Task",
                "description": markdown_description,
                "work_item_type": "Task"
            }

            result = await workitem_tool.execute_tool(arguments)

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_markdown_with_special_characters(self, mock_env_manager, mock_rest_env_manager, workitem_tool):
        """Test markdown conversion with special characters."""
        # Configure both mocks to return the same values
        config = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        special_description = """# Test with Special Characters

## Code Examples
```javascript
const message = "Hello, World!";
console.log(message);
```

## Links and Images
- Visit [Azure DevOps](https://dev.azure.com)
- See ![diagram](https://example.com/diagram.png)

## Quotes
> "Quality is not an act, it is a habit." - Aristotle

## Lists with Special Characters
1. Item with & ampersand
2. Item with < less than
3. Item with > greater than
4. Item with "quotes"
"""

        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Special Characters Test",
                description=special_description
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_markdown_table_conversion(self, mock_env_manager, mock_rest_env_manager, workitem_tool):
        """Test markdown table conversion."""
        # Configure both mocks to return the same values
        config = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        table_description = """# Test Results

## Summary Table

| Test Case | Status | Notes |
|-----------|--------|-------|
| Login     | ✅ Pass | Working correctly |
| Logout    | ❌ Fail | Session not cleared |
| Register  | ⚠️ Warning | Slow response time |

## Next Steps
- Fix logout issue
- Optimize registration performance
"""

        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Test Results Summary",
                description=table_description
            )

            assert result["success"] is True
            assert "data" in result
