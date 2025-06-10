"""
Tests for markdown conversion functionality in work item creation.
"""

import pytest
from unittest.mock import patch
from plugins.azrepo.tests.helpers import patch_azure_utils_env_manager
from plugins.azrepo.tests.workitem_helpers import mock_aiohttp_response


class TestMarkdownConversion:
    """Test markdown conversion in work item creation."""

    @pytest.mark.asyncio
    async def test_create_work_item_with_markdown_description(self, azure_workitem_tool):
        """Test work item creation with markdown description."""
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

        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Login Bug",
                description=markdown_description
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_create_work_item_with_plain_text_description(self, azure_workitem_tool):
        """Test work item creation with plain text description."""
        plain_description = "This is a simple plain text description without any markdown formatting."

        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Simple Task",
                description=plain_description
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_create_work_item_with_mixed_markdown(self, azure_workitem_tool):
        """Test work item creation with mixed markdown content."""
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

        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Authentication System",
                description=mixed_description,
                work_item_type="User Story"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_create_work_item_no_description(self, azure_workitem_tool):
        """Test work item creation without description."""
        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Task Without Description"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_create_work_item_empty_description(self, azure_workitem_tool):
        """Test work item creation with empty description."""
        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Task With Empty Description",
                description=""
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_with_markdown_description(self, azure_workitem_tool):
        """Test execute_tool with markdown description."""
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

        with mock_aiohttp_response(method="post"):
            arguments = {
                "operation": "create",
                "title": "Development Task",
                "description": markdown_description,
                "work_item_type": "Task"
            }

            result = await azure_workitem_tool.execute_tool(arguments)

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_markdown_with_special_characters(self, azure_workitem_tool):
        """Test markdown conversion with special characters."""
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

        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Special Characters Test",
                description=special_description
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_markdown_table_conversion(self, azure_workitem_tool):
        """Test markdown table conversion."""
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

        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Test Results Summary",
                description=table_description
            )

            assert result["success"] is True
            assert "data" in result
