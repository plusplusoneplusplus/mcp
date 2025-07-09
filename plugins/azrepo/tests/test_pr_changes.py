"""
Tests for pull request changes/diff operations.
"""

import json
import pytest
from contextlib import contextmanager
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Optional, Dict, Any

from plugins.azrepo.tests.test_helpers import (
    mock_auth_headers,
    mock_identity_resolution,
    assert_success_response,
)

from ..pr_tool import AzurePullRequestTool


@contextmanager
def mock_pr_changes_azure_http_client(
    method: str = "get",
    status_code: int = 200,
    response_data: Optional[dict] = None,
    error_message: Optional[str] = None,
    raw_response_text: Optional[str] = None,
):
    """
    Helper function to mock AzureHttpClient responses for PR changes tests.
    """
    # Prepare the response data
    json_parse_error = None
    if raw_response_text is not None:
        text_payload = raw_response_text
        try:
            json_payload = json.loads(text_payload)
        except json.JSONDecodeError as e:
            json_payload = {"error": "invalid json in mock"}
            json_parse_error = e
    else:
        if status_code < 300 and response_data is None:
            # Default successful response with sample changes
            response_data = create_sample_changes_response()

        json_payload = (
            response_data if status_code < 300 else {"message": error_message}
        )
        text_payload = json.dumps(json_payload)

    # Create the standardized AzureHttpClient response format
    if status_code < 300:
        if json_parse_error:
            mock_result = {
                "success": False,
                "error": f"Failed to parse response: {json_parse_error}",
                "status_code": status_code,
                "raw_response": text_payload
            }
        else:
            mock_result = {
                "success": True,
                "data": json_payload,
                "status_code": status_code,
                "raw_response": text_payload
            }
    else:
        # Format error message the same way as the real AzureHttpClient
        if status_code == 404:
            error_msg = "Resource not found"
        else:
            error_msg = f"HTTP {status_code}: {error_message or text_payload}"

        mock_result = {
            "success": False,
            "error": error_msg,
            "status_code": status_code,
            "raw_response": text_payload
        }

    # Create the mock AzureHttpClient
    mock_client = MagicMock()
    mock_client.request = AsyncMock(return_value=mock_result)

    # Set up the async context manager
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # Patch the correct import path for PR tool and yield the mock client
    with patch("plugins.azrepo.pr_tool.AzureHttpClient", return_value=mock_client):
        yield mock_client


def create_sample_changes_response() -> Dict[str, Any]:
    """Create a sample Azure DevOps pull request changes response."""
    return {
        "changeEntries": [
            {
                "changeId": 1,
                "changeType": "add",
                "item": {
                    "path": "/src/new_feature.py",
                    "gitObjectType": "blob",
                    "objectId": "abc123def456",
                    "originalObjectId": None
                }
            },
            {
                "changeId": 2,
                "changeType": "edit",
                "item": {
                    "path": "/src/existing_file.py",
                    "gitObjectType": "blob",
                    "objectId": "def456abc123",
                    "originalObjectId": "original123"
                }
            },
            {
                "changeId": 3,
                "changeType": "delete",
                "item": {
                    "path": "/src/old_feature.py",
                    "gitObjectType": "blob",
                    "objectId": None,
                    "originalObjectId": "old123abc"
                }
            },
            {
                "changeId": 4,
                "changeType": "rename",
                "item": {
                    "path": "/src/renamed_file.py",
                    "gitObjectType": "blob",
                    "objectId": "renamed123",
                    "originalObjectId": "original456"
                },
                "sourceItem": {
                    "path": "/src/original_file.py",
                    "gitObjectType": "blob"
                }
            },
            {
                "changeId": 5,
                "changeType": "add",
                "item": {
                    "path": "/docs",
                    "gitObjectType": "tree",
                    "objectId": "tree123",
                    "originalObjectId": None
                }
            }
        ]
    }


def create_empty_changes_response() -> Dict[str, Any]:
    """Create an empty Azure DevOps pull request changes response."""
    return {"changeEntries": []}


def create_large_changes_response() -> Dict[str, Any]:
    """Create a large Azure DevOps pull request changes response for pagination testing."""
    changes = []
    for i in range(100):
        changes.append({
            "changeId": i + 1,
            "changeType": "edit",
            "item": {
                "path": f"/src/file_{i:03d}.py",
                "gitObjectType": "blob",
                "objectId": f"obj{i:03d}abc",
                "originalObjectId": f"orig{i:03d}def"
            }
        })
    return {"changeEntries": changes}


# Removed incorrect fixture definition - using the one from conftest.py


class TestGetPullRequestChanges:
    """Test the get_changes method using the REST API."""

    @pytest.mark.asyncio
    async def test_get_changes_basic(self, azure_pr_tool):
        """Test basic pull request changes retrieval."""
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_auth_headers():
            with mock_pr_changes_azure_http_client(
                method="get", response_data=create_sample_changes_response()
            ) as mock_client:
                result = await azure_pr_tool.get_changes(pull_request_id=123)

                # Verify API call
                mock_client.request.assert_called_once()
                call_args, call_kwargs = mock_client.request.call_args

                assert call_args[0] == "GET"
                assert "pullrequests/123/iterations/1/changes" in call_args[1]
                params = call_kwargs["params"]
                assert params["api-version"] == "7.0"
                assert params["$compareTo"] == 0

                # Verify response structure
                assert_success_response(result)
                assert "data" in result
                assert "count" in result
                assert result["count"] == 5

                # Verify parsed data structure
                data = result["data"]
                assert "changeEntries" in data
                assert len(data["changeEntries"]) == 5

    @pytest.mark.asyncio
    async def test_get_changes_with_custom_iteration(self, azure_pr_tool):
        """Test pull request changes with custom iteration parameters."""
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_auth_headers():
            with mock_pr_changes_azure_http_client(
                method="get", response_data=create_sample_changes_response()
            ) as mock_client:
                result = await azure_pr_tool.get_changes(
                    pull_request_id=456,
                    iteration_id=2,
                    compare_to=1
                )

                # Verify API call with custom parameters
                call_args, call_kwargs = mock_client.request.call_args
                assert "pullrequests/456/iterations/2/changes" in call_args[1]
                params = call_kwargs["params"]
                assert params["$compareTo"] == 1

                assert_success_response(result)

    @pytest.mark.asyncio
    async def test_get_changes_with_pagination(self, azure_pr_tool):
        """Test pull request changes with pagination parameters."""
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_auth_headers():
            with mock_pr_changes_azure_http_client(
                method="get", response_data=create_large_changes_response()
            ) as mock_client:
                result = await azure_pr_tool.get_changes(
                    pull_request_id=789,
                    top=50,
                    skip=25
                )

                # Verify API call with pagination parameters
                call_args, call_kwargs = mock_client.request.call_args
                params = call_kwargs["params"]
                assert params["$top"] == 50
                assert params["$skip"] == 25

                assert_success_response(result)

    @pytest.mark.asyncio
    async def test_get_changes_empty_response(self, azure_pr_tool):
        """Test pull request changes with empty response."""
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_auth_headers():
            with mock_pr_changes_azure_http_client(
                method="get", response_data=create_empty_changes_response()
            ) as mock_client:
                result = await azure_pr_tool.get_changes(pull_request_id=999)

                assert_success_response(result)
                assert result["count"] == 0
                assert len(result["data"]["changeEntries"]) == 0

    @pytest.mark.asyncio
    async def test_get_changes_not_found(self, azure_pr_tool):
        """Test pull request changes with PR not found."""
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_auth_headers():
            with mock_pr_changes_azure_http_client(
                method="get", status_code=404, error_message="PR not found"
            ) as mock_client:
                result = await azure_pr_tool.get_changes(pull_request_id=999)

                assert not result["success"]
                assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_get_changes_missing_parameters(self, azure_pr_tool):
        """Test pull request changes with missing required parameters."""
        # Don't set default values
        result = await azure_pr_tool.get_changes(pull_request_id=123)

        assert not result["success"]
        assert "Organization, project, and repository are required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_changes_missing_pr_id(self, azure_pr_tool):
        """Test pull request changes with missing PR ID."""
        result = await azure_pr_tool.get_changes(pull_request_id=None)

        assert not result["success"]
        assert "Pull request ID is required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_changes_with_overrides(self, azure_pr_tool):
        """Test pull request changes with parameter overrides."""
        azure_pr_tool.default_organization = "default-org"
        azure_pr_tool.default_project = "default-project"
        azure_pr_tool.default_repository = "default-repo"

        with mock_auth_headers():
            with mock_pr_changes_azure_http_client(
                method="get", response_data=create_sample_changes_response()
            ) as mock_client:
                result = await azure_pr_tool.get_changes(
                    pull_request_id=123,
                    organization="custom-org",
                    project="custom-project",
                    repository="custom-repo"
                )

                # Verify API call uses overridden parameters
                call_args, call_kwargs = mock_client.request.call_args
                url = call_args[1]
                assert "custom-org" in url
                assert "custom-project" in url
                assert "custom-repo" in url

                assert_success_response(result)

    @pytest.mark.asyncio
    async def test_get_changes_api_error(self, azure_pr_tool):
        """Test pull request changes with API error."""
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_auth_headers():
            with mock_pr_changes_azure_http_client(
                method="get", status_code=500, error_message="Internal server error"
            ) as mock_client:
                result = await azure_pr_tool.get_changes(pull_request_id=123)

                assert not result["success"]
                assert "500" in result["error"]

    @pytest.mark.asyncio
    async def test_get_changes_malformed_response(self, azure_pr_tool):
        """Test pull request changes with malformed API response."""
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        # Test with invalid JSON structure that will fail Pydantic parsing
        malformed_response = {
            "changeEntries": [
                {
                    "changeId": "invalid_id",  # Should be int, not string
                    "changeType": None,  # Should be string, not None
                    "item": "invalid_item"  # Should be dict, not string
                }
            ]
        }

        with mock_auth_headers():
            with mock_pr_changes_azure_http_client(
                method="get", response_data=malformed_response
            ) as mock_client:
                result = await azure_pr_tool.get_changes(pull_request_id=123)

                # Should still succeed but return raw data instead of parsed structure
                assert_success_response(result)
                assert "data" in result
                assert result["data"] == malformed_response

    @pytest.mark.asyncio
    async def test_execute_tool_get_changes(self, azure_pr_tool):
        """Test get_changes operation through execute_tool interface."""
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_auth_headers():
            with mock_pr_changes_azure_http_client(
                method="get", response_data=create_sample_changes_response()
            ) as mock_client:
                result = await azure_pr_tool.execute_tool({
                    "operation": "get_changes",
                    "pull_request_id": 123,
                    "iteration_id": 2,
                    "compare_to": 1,
                    "top": 10
                })

                # Verify API call with parameters
                call_args, call_kwargs = mock_client.request.call_args
                assert "pullrequests/123/iterations/2/changes" in call_args[1]
                params = call_kwargs["params"]
                assert params["$compareTo"] == 1
                assert params["$top"] == 10

                assert_success_response(result)


class TestPullRequestChangesParsing:
    """Test the parsing and helper methods for pull request changes."""

    def test_change_item_properties(self):
        """Test PullRequestChangeItem computed properties."""
        from plugins.azrepo.types import PullRequestChangeItem

        # Test file change
        change_data = {
            "changeId": 1,
            "changeType": "edit",
            "item": {
                "path": "/src/test.py",
                "gitObjectType": "blob",
                "objectId": "abc123"
            }
        }

        change = PullRequestChangeItem(**change_data)
        assert change.file_path == "/src/test.py"
        assert change.change_type == "edit"
        assert change.is_file is True
        assert change.original_path is None

    def test_renamed_file_properties(self):
        """Test PullRequestChangeItem properties for renamed files."""
        from plugins.azrepo.types import PullRequestChangeItem

        # Test renamed file
        change_data = {
            "changeId": 2,
            "changeType": "rename",
            "item": {
                "path": "/src/new_name.py",
                "gitObjectType": "blob",
                "objectId": "def456"
            },
            "sourceItem": {
                "path": "/src/old_name.py",
                "gitObjectType": "blob"
            }
        }

        change = PullRequestChangeItem(**change_data)
        assert change.file_path == "/src/new_name.py"
        assert change.change_type == "rename"
        assert change.is_file is True
        assert change.original_path == "/src/old_name.py"

    def test_folder_change_properties(self):
        """Test PullRequestChangeItem properties for folder changes."""
        from plugins.azrepo.types import PullRequestChangeItem

        # Test folder change
        change_data = {
            "changeId": 3,
            "changeType": "add",
            "item": {
                "path": "/src/newfolder",
                "gitObjectType": "tree",
                "objectId": "tree123"
            }
        }

        change = PullRequestChangeItem(**change_data)
        assert change.file_path == "/src/newfolder"
        assert change.change_type == "add"
        assert change.is_file is False

    def test_changes_filtering_methods(self):
        """Test PullRequestChanges filtering helper methods."""
        from plugins.azrepo.types import PullRequestChanges, PullRequestChangeItem

        # Create sample changes
        changes_data = create_sample_changes_response()
        changes = PullRequestChanges(**changes_data)

        # Test file_changes filter (excludes folders)
        file_changes = changes.file_changes
        assert len(file_changes) == 4  # Excludes the tree/folder entry

        # Test added_files
        added_files = changes.added_files
        assert len(added_files) == 1
        assert added_files[0].file_path == "/src/new_feature.py"

        # Test modified_files
        modified_files = changes.modified_files
        assert len(modified_files) == 1
        assert modified_files[0].file_path == "/src/existing_file.py"

        # Test deleted_files
        deleted_files = changes.deleted_files
        assert len(deleted_files) == 1
        assert deleted_files[0].file_path == "/src/old_feature.py"

        # Test renamed_files
        renamed_files = changes.renamed_files
        assert len(renamed_files) == 1
        assert renamed_files[0].file_path == "/src/renamed_file.py"
        assert renamed_files[0].original_path == "/src/original_file.py"
