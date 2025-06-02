"""
Shared fixtures for Azure Repo Client tests.
"""

import pytest
from unittest.mock import MagicMock

from ..repo_tool import AzureRepoClient
from ..pr_tool import AzurePullRequestTool
from ..workitem_tool import AzureWorkItemTool


@pytest.fixture
def azure_repo_client():
    """Create an AzureRepoClient instance for testing."""
    # Mock the command executor to avoid registry dependency
    mock_executor = MagicMock()
    return AzureRepoClient(command_executor=mock_executor)


@pytest.fixture
def azure_pr_tool():
    """Create an AzurePullRequestTool instance for testing."""
    # Mock the command executor to avoid registry dependency
    mock_executor = MagicMock()
    return AzurePullRequestTool(command_executor=mock_executor)


@pytest.fixture
def azure_workitem_tool():
    """Create an AzureWorkItemTool instance for testing."""
    # Mock the command executor to avoid registry dependency
    mock_executor = MagicMock()
    return AzureWorkItemTool(command_executor=mock_executor)


@pytest.fixture
def mock_command_success_response():
    """Create a mock successful command response."""
    return {
        "success": True,
        "data": {
            "id": 123,
            "title": "Test PR",
            "sourceRefName": "refs/heads/feature/test",
            "targetRefName": "refs/heads/main",
            "status": "active",
        },
    }


@pytest.fixture
def mock_pr_list_response():
    """Create a mock PR list response."""
    return {
        "success": True,
        "data": [
            {
                "pullRequestId": 123,
                "title": "Test PR 1",
                "sourceRefName": "refs/heads/feature/test1",
                "targetRefName": "refs/heads/main",
                "status": "active",
                "createdBy": {
                    "displayName": "John Doe",
                    "uniqueName": "john.doe@abc.com",
                },
                "creationDate": "2024-01-15T10:30:00.000Z",
            },
            {
                "pullRequestId": 124,
                "title": "Test PR 2",
                "sourceRefName": "refs/heads/feature/test2",
                "targetRefName": "refs/heads/main",
                "status": "completed",
                "createdBy": {
                    "displayName": "Jane Smith",
                    "uniqueName": "jane.smith@abc.com",
                },
                "creationDate": "2024-01-14T15:45:00.000Z",
            },
        ],
    }


@pytest.fixture
def mock_pr_list_response_with_csv_fields():
    """Create a mock PR list response with all fields needed for CSV conversion."""
    return {
        "success": True,
        "data": [
            {
                "pullRequestId": 123,
                "title": "Test PR 1",
                "sourceRefName": "refs/heads/feature/test1",
                "targetRefName": "refs/heads/main",
                "status": "active",
                "createdBy": {
                    "displayName": "John Doe",
                    "uniqueName": "john.doe@abc.com",
                },
                "creationDate": "2024-01-15T10:30:00.000Z",
            },
            {
                "pullRequestId": 124,
                "title": "Test PR 2",
                "sourceRefName": "refs/heads/feature/test2",
                "targetRefName": "refs/heads/main",
                "status": "completed",
                "createdBy": {
                    "displayName": "Jane Smith",
                    "uniqueName": "jane.smith@abc.com",
                },
                "creationDate": "2024-01-14T15:45:00.000Z",
            },
        ],
    }


@pytest.fixture
def mock_git_repo():
    """Create a mock git repository."""
    mock_repo = MagicMock()
    mock_commit = MagicMock()
    mock_commit.hexsha = "a1b2c3d4e5f6789012345678901234567890abcd"
    mock_commit.message = "Fix authentication bug\n\nDetailed description here"
    mock_repo.head.commit = mock_commit
    return mock_repo


@pytest.fixture
def mock_repo_list_response():
    """Create a mock repository list response."""
    return {
        "success": True,
        "data": [
            {
                "id": "repo1-id",
                "name": "test-repo-1",
                "url": "https://dev.azure.com/org/project/_git/test-repo-1",
                "defaultBranch": "refs/heads/main",
                "size": 1024000,
            },
            {
                "id": "repo2-id",
                "name": "test-repo-2",
                "url": "https://dev.azure.com/org/project/_git/test-repo-2",
                "defaultBranch": "refs/heads/master",
                "size": 2048000,
            },
        ],
    }


@pytest.fixture
def mock_repo_details_response():
    """Create a mock repository details response."""
    return {
        "success": True,
        "data": {
            "id": "repo1-id",
            "name": "test-repo-1",
            "url": "https://dev.azure.com/org/project/_git/test-repo-1",
            "defaultBranch": "refs/heads/main",
            "size": 1024000,
            "project": {"id": "project-id", "name": "test-project"},
        },
    }


@pytest.fixture
def mock_workitem_response():
    """Create a mock work item response."""
    return {
        "success": True,
        "data": {
            "id": 12345,
            "fields": {
                "System.Id": 12345,
                "System.Title": "Test Work Item",
                "System.State": "Active",
                "System.WorkItemType": "Bug",
                "System.AssignedTo": {
                    "displayName": "John Doe",
                    "uniqueName": "john.doe@company.com",
                },
            },
        },
    }
