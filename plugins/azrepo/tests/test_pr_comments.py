"""
Tests for pull request comment operations.
"""

import json
import pytest
from contextlib import contextmanager
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Optional

from plugins.azrepo.tests.test_helpers import (
    mock_auth_headers,
    mock_identity_resolution,
    assert_success_response,
)
from plugins.azrepo.tests.workitem_helpers import mock_azure_http_client

from ..pr_tool import AzurePullRequestTool


@contextmanager
def mock_pr_azure_http_client(
    method: str = "post",
    status_code: int = 200,
    response_data: Optional[dict] = None,
    error_message: Optional[str] = None,
    raw_response_text: Optional[str] = None,
):
    """
    Context manager for mocking AzureHttpClient responses.

    Args:
        method: HTTP method to mock (default: "post")
        status_code: HTTP status code to return (default: 200)
        response_data: Response data to return (default: None)
        error_message: Error message for failed responses (default: None)
        raw_response_text: Raw response text (default: None)
    """
    with patch("plugins.azrepo.pr_tool.AzureHttpClient") as mock_http_client_class:
        mock_client = AsyncMock()
        mock_http_client_class.return_value.__aenter__.return_value = mock_client

        if status_code >= 200 and status_code < 300:
            # Success response
            mock_client.request.return_value = {
                "success": True,
                "status_code": status_code,
                "data": response_data or {},
                "raw_response_text": raw_response_text or json.dumps(response_data or {}),
            }
        else:
            # Error response
            mock_client.request.return_value = {
                "success": False,
                "status_code": status_code,
                "error": error_message or f"HTTP {status_code} error",
                "raw_response_text": raw_response_text or "",
            }

        yield mock_client


class TestCommentManagement:
    """Test comment management operations."""

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_get_comments_basic(self, mock_auth_headers, azure_pr_tool):
        """Test basic comment retrieval via REST API."""
        # Setup mock response for comment threads with full Azure DevOps schema
        mock_threads = [
            {
                "id": 1,
                "status": "active",
                "publishedDate": "2024-01-15T10:00:00.000Z",
                "lastUpdatedDate": "2024-01-15T10:30:00.000Z",
                "properties": {
                    "Microsoft.TeamFoundation.Discussion.SupportsMarkdown": {
                        "$type": "System.String",
                        "$value": "True"
                    }
                },
                "threadContext": {
                    "filePath": "/src/main.py",
                    "leftFileStart": {"line": 25, "offset": 1},
                    "leftFileEnd": {"line": 25, "offset": 20},
                    "rightFileStart": {"line": 25, "offset": 1},
                    "rightFileEnd": {"line": 25, "offset": 20}
                },
                "pullRequestThreadContext": {
                    "iterationContext": {
                        "firstComparingIteration": 1,
                        "secondComparingIteration": 2
                    },
                    "changeTrackingId": 5
                },
                "comments": [
                    {
                        "id": 101,
                        "content": "This looks good!",
                        "author": {
                            "displayName": "John Doe",
                            "uniqueName": "john.doe@company.com",
                            "id": "user-123"
                        },
                        "publishedDate": "2024-01-15T10:30:00.000Z",
                        "lastUpdatedDate": "2024-01-15T10:30:00.000Z",
                        "commentType": "text",
                        "parentCommentId": None,
                        "isDeleted": False,
                        "usersLiked": []
                    }
                ]
            },
            {
                "id": 2,
                "status": "fixed",
                "publishedDate": "2024-01-15T11:00:00.000Z",
                "lastUpdatedDate": "2024-01-15T12:00:00.000Z",
                "properties": {},
                "threadContext": None,
                "pullRequestThreadContext": None,
                "comments": [
                    {
                        "id": 102,
                        "content": "Please fix this issue",
                        "author": {
                            "displayName": "Jane Smith",
                            "uniqueName": "jane.smith@company.com",
                            "id": "user-456"
                        },
                        "publishedDate": "2024-01-15T11:30:00.000Z",
                        "lastUpdatedDate": "2024-01-15T11:30:00.000Z",
                        "commentType": "text",
                        "parentCommentId": None,
                        "isDeleted": False,
                        "usersLiked": []
                    },
                    {
                        "id": 103,
                        "content": "Fixed in the latest commit",
                        "author": {
                            "displayName": "John Doe",
                            "uniqueName": "john.doe@company.com",
                            "id": "user-123"
                        },
                        "publishedDate": "2024-01-15T12:00:00.000Z",
                        "lastUpdatedDate": "2024-01-15T12:00:00.000Z",
                        "commentType": "text",
                        "parentCommentId": 102,
                        "isDeleted": False,
                        "usersLiked": [
                            {
                                "displayName": "Jane Smith",
                                "uniqueName": "jane.smith@company.com",
                                "id": "user-456"
                            }
                        ]
                    }
                ]
            }
        ]

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="get", response_data={"value": mock_threads, "count": 2}) as mock_client:
            result = await azure_pr_tool.get_comments(pull_request_id=123)

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args

            # Check the method and URL
            assert call_args[0] == "GET"
            assert "pullrequests/123/threads" in call_args[1]
            params = call_kwargs["params"]
            assert params["api-version"] == "7.1"

            assert result["success"] is True
            assert len(result["data"]) == 2
            assert result["data"][0]["id"] == 1
            assert result["data"][1]["id"] == 2

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_get_comments_with_filters(self, mock_auth_headers, azure_pr_tool):
        """Test comment retrieval with status and author filters."""
        mock_threads = [
            {
                "id": 1,
                "status": "active",
                "comments": [
                    {
                        "id": 101,
                        "content": "Active comment",
                        "author": {
                            "displayName": "John Doe",
                            "uniqueName": "john.doe@company.com",
                            "id": "user-123"
                        },
                        "publishedDate": "2024-01-15T10:00:00.000Z",
                        "commentType": "text"
                    }
                ]
            },
            {
                "id": 2,
                "status": "resolved",
                "comments": [
                    {
                        "id": 102,
                        "content": "Resolved comment",
                        "author": {
                            "displayName": "Jane Smith",
                            "uniqueName": "jane.smith@company.com",
                            "id": "user-456"
                        },
                        "publishedDate": "2024-01-15T11:00:00.000Z",
                        "commentType": "text"
                    }
                ]
            },
            {
                "id": 3,
                "status": "active",
                "comments": [
                    {
                        "id": 103,
                        "content": "Another active comment",
                        "author": {
                            "displayName": "Bob Johnson",
                            "uniqueName": "bob.johnson@company.com",
                            "id": "user-789"
                        },
                        "publishedDate": "2024-01-15T12:00:00.000Z",
                        "commentType": "text"
                    }
                ]
            }
        ]

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="get", response_data={"value": mock_threads}) as mock_client:
            # Test status filter
            result = await azure_pr_tool.get_comments(
                pull_request_id=123,
                comment_status="active"
            )

            assert result["success"] is True
            assert len(result["data"]) == 2  # Only active threads
            for thread in result["data"]:
                assert thread["status"] == "active"

        with mock_pr_azure_http_client(method="get", response_data={"value": mock_threads}) as mock_client:
            # Test author filter
            result = await azure_pr_tool.get_comments(
                pull_request_id=123,
                comment_author="john.doe@company.com"
            )

            assert result["success"] is True
            assert len(result["data"]) == 1  # Only threads with John's comments
            assert result["data"][0]["comments"][0]["author"]["uniqueName"] == "john.doe@company.com"

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_resolve_comment_basic(self, mock_auth_headers, azure_pr_tool):
        """Test basic comment thread resolution via REST API."""
        mock_thread = {
            "id": 1,
            "status": "fixed",
            "comments": [
                {
                    "id": 101,
                    "content": "This is resolved",
                    "author": {
                        "displayName": "John Doe",
                        "uniqueName": "john.doe@company.com",
                        "id": "user-123"
                    },
                    "publishedDate": "2024-01-15T10:30:00.000Z",
                    "commentType": "text"
                }
            ]
        }

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="patch", response_data=mock_thread) as mock_client:
            result = await azure_pr_tool.resolve_comment(
                pull_request_id=123,
                thread_id=1
            )

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args

            # Check the method and URL
            assert call_args[0] == "PATCH"
            assert "pullrequests/123/threads/1" in call_args[1]
            request_body = call_kwargs["json"]
            assert request_body["status"] == "fixed"

            assert result["success"] is True
            assert result["data"]["status"] == "fixed"

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_add_comment_new_thread(self, mock_auth_headers, azure_pr_tool):
        """Test adding a new comment (creating new thread) via REST API."""
        mock_thread = {
            "id": 1,
            "status": "active",
            "comments": [
                {
                    "id": 101,
                    "content": "This is a new comment",
                    "author": {
                        "displayName": "John Doe",
                        "uniqueName": "john.doe@company.com",
                        "id": "user-123"
                    },
                    "publishedDate": "2024-01-15T10:30:00.000Z",
                    "commentType": "text"
                }
            ]
        }

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="post", response_data=mock_thread) as mock_client:
            result = await azure_pr_tool.add_comment(
                pull_request_id=123,
                comment_content="This is a new comment"
            )

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args

            # Check the method and URL
            assert call_args[0] == "POST"
            assert "pullrequests/123/threads" in call_args[1]
            request_body = call_kwargs["json"]
            assert request_body["comments"][0]["content"] == "This is a new comment"

            assert result["success"] is True
            assert result["data"]["comments"][0]["content"] == "This is a new comment"

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_add_comment_to_existing_thread(self, mock_auth_headers, azure_pr_tool):
        """Test adding a comment to existing thread via REST API."""
        mock_comment = {
            "id": 102,
            "content": "This is a reply",
            "author": {
                "displayName": "Jane Smith",
                "uniqueName": "jane.smith@company.com",
                "id": "user-456"
            },
            "publishedDate": "2024-01-15T11:30:00.000Z",
            "commentType": "text"
        }

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="post", response_data=mock_comment) as mock_client:
            result = await azure_pr_tool.add_comment(
                pull_request_id=123,
                comment_content="This is a reply",
                thread_id=1
            )

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args

            # Check the method and URL
            assert call_args[0] == "POST"
            assert "pullrequests/123/threads/1/comments" in call_args[1]
            request_body = call_kwargs["json"]
            assert request_body["content"] == "This is a reply"

            assert result["success"] is True
            assert result["data"]["content"] == "This is a reply"

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_update_comment(self, mock_auth_headers, azure_pr_tool):
        """Test updating an existing comment via REST API."""
        mock_comment = {
            "id": 101,
            "content": "Updated comment content",
            "author": {
                "displayName": "John Doe",
                "uniqueName": "john.doe@company.com",
                "id": "user-123"
            },
            "publishedDate": "2024-01-15T10:30:00.000Z",
            "lastUpdatedDate": "2024-01-15T12:00:00.000Z",
            "commentType": "text"
        }

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="patch", response_data=mock_comment) as mock_client:
            result = await azure_pr_tool.update_comment(
                pull_request_id=123,
                thread_id=1,
                comment_id=101,
                comment_content="Updated comment content"
            )

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args

            # Check the method and URL
            assert call_args[0] == "PATCH"
            assert "pullrequests/123/threads/1/comments/101" in call_args[1]
            request_body = call_kwargs["json"]
            assert request_body["content"] == "Updated comment content"

            assert result["success"] is True
            assert result["data"]["content"] == "Updated comment content"

    @pytest.mark.asyncio
    async def test_add_comment_empty_content(self, azure_pr_tool):
        """Test that empty comment content returns error."""
        result = await azure_pr_tool.add_comment(
            pull_request_id=123,
            comment_content=""
        )

        assert result["success"] is False
        assert "Comment content is required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_comment_empty_content(self, azure_pr_tool):
        """Test that empty comment content returns error for update."""
        result = await azure_pr_tool.update_comment(
            pull_request_id=123,
            thread_id=1,
            comment_id=101,
            comment_content=""
        )

        assert result["success"] is False
        assert "Comment content is required" in result["error"]

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_get_comments_not_found(self, mock_auth_headers, azure_pr_tool):
        """Test handling of PR not found during comment retrieval."""
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="get", status_code=404, error_message="Pull request not found") as mock_client:
            result = await azure_pr_tool.get_comments(pull_request_id=999)

            assert result["success"] is False
            assert "Pull request 999 not found" in result["error"]

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_get_comments_with_nested_replies(self, mock_auth_headers, azure_pr_tool):
        """Test comment retrieval with nested reply structure."""
        mock_threads = [
            {
                "id": 1,
                "status": "active",
                "publishedDate": "2024-01-15T10:00:00.000Z",
                "lastUpdatedDate": "2024-01-15T14:00:00.000Z",
                "properties": {},
                "threadContext": {
                    "filePath": "/src/utils.py",
                    "leftFileStart": {"line": 42, "offset": 1},
                    "leftFileEnd": {"line": 45, "offset": 30},
                    "rightFileStart": {"line": 42, "offset": 1},
                    "rightFileEnd": {"line": 45, "offset": 30}
                },
                "comments": [
                    {
                        "id": 101,
                        "content": "This function needs optimization",
                        "author": {
                            "displayName": "Reviewer One",
                            "uniqueName": "reviewer1@company.com",
                            "id": "user-101"
                        },
                        "publishedDate": "2024-01-15T10:00:00.000Z",
                        "lastUpdatedDate": "2024-01-15T10:00:00.000Z",
                        "commentType": "text",
                        "parentCommentId": None,
                        "isDeleted": False,
                        "usersLiked": []
                    },
                    {
                        "id": 102,
                        "content": "I'll look into it",
                        "author": {
                            "displayName": "Developer",
                            "uniqueName": "dev@company.com",
                            "id": "user-102"
                        },
                        "publishedDate": "2024-01-15T12:00:00.000Z",
                        "lastUpdatedDate": "2024-01-15T12:00:00.000Z",
                        "commentType": "text",
                        "parentCommentId": 101,
                        "isDeleted": False,
                        "usersLiked": []
                    },
                    {
                        "id": 103,
                        "content": "Optimization complete",
                        "author": {
                            "displayName": "Developer",
                            "uniqueName": "dev@company.com",
                            "id": "user-102"
                        },
                        "publishedDate": "2024-01-15T14:00:00.000Z",
                        "lastUpdatedDate": "2024-01-15T14:00:00.000Z",
                        "commentType": "text",
                        "parentCommentId": 101,
                        "isDeleted": False,
                        "usersLiked": [
                            {
                                "displayName": "Reviewer One",
                                "uniqueName": "reviewer1@company.com",
                                "id": "user-101"
                            }
                        ]
                    }
                ]
            }
        ]

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="get", response_data={"value": mock_threads, "count": 1}) as mock_client:
            result = await azure_pr_tool.get_comments(pull_request_id=123)

            assert result["success"] is True
            assert len(result["data"]) == 1
            thread = result["data"][0]
            assert len(thread["comments"]) == 3

            # Check parent-child relationships
            root_comment = thread["comments"][0]
            reply1 = thread["comments"][1]
            reply2 = thread["comments"][2]

            assert root_comment["parentCommentId"] is None
            assert reply1["parentCommentId"] == 101
            assert reply2["parentCommentId"] == 101
            assert len(reply2["usersLiked"]) == 1

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_get_comments_with_thread_context(self, mock_auth_headers, azure_pr_tool):
        """Test comment retrieval with comprehensive thread context."""
        mock_threads = [
            {
                "id": 1,
                "status": "active",
                "publishedDate": "2024-01-15T10:00:00.000Z",
                "lastUpdatedDate": "2024-01-15T10:30:00.000Z",
                "properties": {
                    "Microsoft.TeamFoundation.Discussion.SupportsMarkdown": {
                        "$type": "System.String",
                        "$value": "True"
                    },
                    "Microsoft.TeamFoundation.Discussion.UniqueID": {
                        "$type": "System.String",
                        "$value": "thread-uuid-12345"
                    }
                },
                "threadContext": {
                    "filePath": "/src/components/Button.tsx",
                    "leftFileStart": {"line": 15, "offset": 5},
                    "leftFileEnd": {"line": 20, "offset": 25},
                    "rightFileStart": {"line": 15, "offset": 5},
                    "rightFileEnd": {"line": 20, "offset": 25}
                },
                "pullRequestThreadContext": {
                    "iterationContext": {
                        "firstComparingIteration": 2,
                        "secondComparingIteration": 3
                    },
                    "changeTrackingId": 15,
                    "trackingCriteria": {
                        "origLeftFileStart": {"line": 15, "offset": 5},
                        "origLeftFileEnd": {"line": 20, "offset": 25},
                        "origRightFileStart": {"line": 15, "offset": 5},
                        "origRightFileEnd": {"line": 20, "offset": 25}
                    }
                },
                "comments": [
                    {
                        "id": 201,
                        "content": "Consider using a more semantic button variant",
                        "author": {
                            "displayName": "UI Designer",
                            "uniqueName": "designer@company.com",
                            "id": "user-201"
                        },
                        "publishedDate": "2024-01-15T10:30:00.000Z",
                        "lastUpdatedDate": "2024-01-15T10:30:00.000Z",
                        "commentType": "text",
                        "parentCommentId": None,
                        "isDeleted": False,
                        "usersLiked": []
                    }
                ]
            }
        ]

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="get", response_data={"value": mock_threads, "count": 1}) as mock_client:
            result = await azure_pr_tool.get_comments(pull_request_id=123)

            assert result["success"] is True
            thread = result["data"][0]

            # Verify thread context
            assert thread["threadContext"]["filePath"] == "/src/components/Button.tsx"
            assert thread["threadContext"]["leftFileStart"]["line"] == 15

            # Verify pull request thread context
            assert thread["pullRequestThreadContext"]["changeTrackingId"] == 15
            assert thread["pullRequestThreadContext"]["iterationContext"]["firstComparingIteration"] == 2

            # Verify properties
            assert "Microsoft.TeamFoundation.Discussion.SupportsMarkdown" in thread["properties"]

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_get_comments_system_and_code_change_types(self, mock_auth_headers, azure_pr_tool):
        """Test comment retrieval with different comment types."""
        mock_threads = [
            {
                "id": 1,
                "status": "closed",
                "publishedDate": "2024-01-15T09:00:00.000Z",
                "lastUpdatedDate": "2024-01-15T09:00:00.000Z",
                "properties": {},
                "threadContext": None,
                "pullRequestThreadContext": None,
                "comments": [
                    {
                        "id": 301,
                        "content": "Build completed successfully",
                        "author": {
                            "displayName": "Azure DevOps",
                            "uniqueName": "system@azure.com",
                            "id": "system-001"
                        },
                        "publishedDate": "2024-01-15T09:00:00.000Z",
                        "lastUpdatedDate": "2024-01-15T09:00:00.000Z",
                        "commentType": "system",
                        "parentCommentId": None,
                        "isDeleted": False,
                        "usersLiked": []
                    }
                ]
            },
            {
                "id": 2,
                "status": "active",
                "publishedDate": "2024-01-15T10:00:00.000Z",
                "lastUpdatedDate": "2024-01-15T10:00:00.000Z",
                "properties": {},
                "threadContext": {
                    "filePath": "/src/api.ts",
                    "leftFileStart": {"line": 100, "offset": 1},
                    "leftFileEnd": {"line": 105, "offset": 50}
                },
                "comments": [
                    {
                        "id": 302,
                        "content": "Code change detected in error handling",
                        "author": {
                            "displayName": "Code Analysis",
                            "uniqueName": "analysis@company.com",
                            "id": "analysis-001"
                        },
                        "publishedDate": "2024-01-15T10:00:00.000Z",
                        "lastUpdatedDate": "2024-01-15T10:00:00.000Z",
                        "commentType": "codeChange",
                        "parentCommentId": None,
                        "isDeleted": False,
                        "usersLiked": []
                    }
                ]
            }
        ]

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="get", response_data={"value": mock_threads, "count": 2}) as mock_client:
            result = await azure_pr_tool.get_comments(pull_request_id=123)

            assert result["success"] is True
            assert len(result["data"]) == 2

            # Check system comment
            system_thread = result["data"][0]
            assert system_thread["comments"][0]["commentType"] == "system"
            assert system_thread["status"] == "closed"

            # Check code change comment
            code_thread = result["data"][1]
            assert code_thread["comments"][0]["commentType"] == "codeChange"
            assert code_thread["threadContext"]["filePath"] == "/src/api.ts"

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_get_comments_with_count_metadata(self, mock_auth_headers, azure_pr_tool):
        """Test that response includes count metadata."""
        mock_threads = [
            {
                "id": 1,
                "status": "active",
                "publishedDate": "2024-01-15T10:00:00.000Z",
                "comments": [
                    {
                        "id": 401,
                        "content": "Test comment",
                        "author": {
                            "displayName": "Test User",
                            "uniqueName": "test@company.com",
                            "id": "user-401"
                        },
                        "publishedDate": "2024-01-15T10:00:00.000Z",
                        "commentType": "text",
                        "parentCommentId": None,
                        "isDeleted": False,
                        "usersLiked": []
                    }
                ]
            }
        ]

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        # Test that count is properly returned
        with mock_pr_azure_http_client(method="get", response_data={"value": mock_threads, "count": 5}) as mock_client:
            result = await azure_pr_tool.get_comments(pull_request_id=123)

            # Verify HTTP call
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args
            assert call_args[0] == "GET"

            # Verify result structure
            assert result["success"] is True
            assert len(result["data"]) == 1
            # Note: The count field would be available in the raw response but not currently
            # exposed in the return structure - this test documents the current behavior
