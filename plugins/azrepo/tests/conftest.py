"""
Shared fixtures for Azure Repo Client tests.
"""

import pytest
from unittest.mock import MagicMock

from ..tool import AzureRepoClient


@pytest.fixture
def azure_repo_client():
    """Create an AzureRepoClient instance for testing."""
    # Mock the command executor to avoid registry dependency
    mock_executor = MagicMock()
    return AzureRepoClient(command_executor=mock_executor)


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
                    "uniqueName": "john.doe@abc.com"
                },
                "creationDate": "2024-01-15T10:30:00.000Z"
            },
            {
                "pullRequestId": 124,
                "title": "Test PR 2",
                "sourceRefName": "refs/heads/feature/test2",
                "targetRefName": "refs/heads/main",
                "status": "completed",
                "createdBy": {
                    "displayName": "Jane Smith",
                    "uniqueName": "jane.smith@abc.com"
                },
                "creationDate": "2024-01-14T15:45:00.000Z"
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
                    "uniqueName": "john.doe@abc.com"
                },
                "creationDate": "2024-01-15T10:30:00.000Z"
            },
            {
                "pullRequestId": 124,
                "title": "Test PR 2",
                "sourceRefName": "refs/heads/feature/test2",
                "targetRefName": "refs/heads/main",
                "status": "completed",
                "createdBy": {
                    "displayName": "Jane Smith",
                    "uniqueName": "jane.smith@abc.com"
                },
                "creationDate": "2024-01-14T15:45:00.000Z"
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
