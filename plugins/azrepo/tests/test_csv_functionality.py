"""
Tests for CSV conversion and data formatting functionality.
"""

import pytest
import json
import pandas as pd
from unittest.mock import AsyncMock


class TestConvertPrToDf:
    """Test the convert_pr_to_df method."""

    def test_convert_pr_to_df_basic(self, azure_repo_client):
        """Test basic PR to DataFrame conversion."""
        prs_data = [
            {
                "pullRequestId": 123,
                "title": "Test PR 1",
                "sourceRefName": "refs/heads/feature/test1",
                "targetRefName": "refs/heads/main",
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
                "createdBy": {
                    "displayName": "Jane Smith",
                    "uniqueName": "jane.smith@abc.com"
                },
                "creationDate": "2024-01-14T15:45:00.000Z"
            }
        ]

        df = azure_repo_client.convert_pr_to_df(prs_data)

        # Check DataFrame structure
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ['id', 'creator', 'date', 'title', 'source_ref', 'target_ref']

        # Check first row data
        assert df.iloc[0]['id'] == 123
        assert df.iloc[0]['creator'] == 'john.doe@abc.com'
        assert df.iloc[0]['title'] == 'Test PR 1'
        assert df.iloc[0]['source_ref'] == 'feature/test1'
        assert df.iloc[0]['target_ref'] == 'main'

        # Check second row data
        assert df.iloc[1]['id'] == 124
        assert df.iloc[1]['creator'] == 'jane.smith@abc.com'
        assert df.iloc[1]['title'] == 'Test PR 2'
        assert df.iloc[1]['source_ref'] == 'feature/test2'
        assert df.iloc[1]['target_ref'] == 'main'

    def test_convert_pr_to_df_empty_list(self, azure_repo_client):
        """Test conversion with empty PR list."""
        df = azure_repo_client.convert_pr_to_df([])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert list(df.columns) == ['id', 'creator', 'date', 'title', 'source_ref', 'target_ref']

    def test_convert_pr_to_df_removes_refs_prefix(self, azure_repo_client):
        """Test that refs/heads/ prefix is properly removed from branch names."""
        prs_data = [
            {
                "pullRequestId": 123,
                "title": "Test PR",
                "sourceRefName": "refs/heads/feature/complex-branch-name",
                "targetRefName": "refs/heads/develop",
                "createdBy": {
                    "uniqueName": "test.user@abc.com"
                },
                "creationDate": "2024-01-15T10:30:00.000Z"
            }
        ]

        df = azure_repo_client.convert_pr_to_df(prs_data)

        assert df.iloc[0]['source_ref'] == 'feature/complex-branch-name'
        assert df.iloc[0]['target_ref'] == 'develop'

    def test_convert_pr_to_df_preserves_full_email(self, azure_repo_client):
        """Test that full email addresses are preserved in creator names."""
        prs_data = [
            {
                "pullRequestId": 123,
                "title": "Test PR",
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "createdBy": {
                    "uniqueName": "test.user@abc.com"
                },
                "creationDate": "2024-01-15T10:30:00.000Z"
            }
        ]

        df = azure_repo_client.convert_pr_to_df(prs_data)

        assert df.iloc[0]['creator'] == 'test.user@abc.com'

    def test_convert_pr_to_df_date_formatting(self, azure_repo_client):
        """Test that dates are properly formatted."""
        prs_data = [
            {
                "pullRequestId": 123,
                "title": "Test PR",
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "createdBy": {
                    "uniqueName": "test.user@abc.com"
                },
                "creationDate": "2024-01-15T10:30:45.123Z"
            }
        ]

        df = azure_repo_client.convert_pr_to_df(prs_data)

        # Check that date is formatted as expected (MM/dd/yy HH:MM:SS)
        date_str = df.iloc[0]['date']
        assert isinstance(date_str, str)
        # The exact format depends on timezone, but should be in MM/dd/yy HH:MM:SS format
        assert len(date_str.split(' ')) == 2  # Should have date and time parts
        assert '/' in date_str  # Should have date separators
        assert ':' in date_str  # Should have time separators


class TestListPullRequestsWithCsv:
    """Test the updated list_pull_requests method that returns CSV data."""

    @pytest.mark.asyncio
    async def test_list_pull_requests_returns_csv(
        self, azure_repo_client, mock_pr_list_response_with_csv_fields
    ):
        """Test that list_pull_requests returns CSV data when successful."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_pr_list_response_with_csv_fields
        )

        result = await azure_repo_client.list_pull_requests()

        assert result["success"] is True
        assert "data" in result

        # Check that data is CSV string
        csv_data = result["data"]
        assert isinstance(csv_data, str)

        # Check CSV headers
        lines = csv_data.strip().split('\n')
        headers = lines[0]
        assert headers == "id,creator,date,title,source_ref,target_ref"

        # Check that we have data rows
        assert len(lines) == 3  # Header + 2 data rows

        # Check first data row
        first_row = lines[1].split(',')
        assert first_row[0] == '123'  # id
        assert first_row[1] == 'john.doe@abc.com'  # creator
        assert 'Test PR 1' in first_row[3]  # title
        assert first_row[4] == 'feature/test1'  # source_ref
        assert first_row[5] == 'main'  # target_ref

    @pytest.mark.asyncio
    async def test_list_pull_requests_csv_conversion_failure(self, azure_repo_client):
        """Test list_pull_requests when CSV conversion fails."""
        # Mock _run_az_command to return data that will cause conversion to fail
        mock_response = {
            "success": True,
            "data": [
                {
                    # Missing required fields for conversion
                    "pullRequestId": 123,
                    "title": "Test PR"
                    # Missing pullRequestId, createdBy, etc.
                }
            ]
        }
        azure_repo_client._run_az_command = AsyncMock(return_value=mock_response)

        result = await azure_repo_client.list_pull_requests()

        assert result["success"] is False
        assert "Failed to convert PRs to CSV" in result["error"]

    @pytest.mark.asyncio
    async def test_list_pull_requests_empty_data_returns_empty_csv(self, azure_repo_client):
        """Test list_pull_requests with empty data returns empty CSV."""
        mock_response = {
            "success": True,
            "data": []
        }
        azure_repo_client._run_az_command = AsyncMock(return_value=mock_response)

        result = await azure_repo_client.list_pull_requests()

        assert result["success"] is True
        csv_data = result["data"]

        # Should have headers but no data rows
        lines = csv_data.strip().split('\n')
        assert len(lines) == 1  # Only header row
        assert lines[0] == "id,creator,date,title,source_ref,target_ref"

    @pytest.mark.asyncio
    async def test_list_pull_requests_command_failure_returns_original_error(self, azure_repo_client):
        """Test that command failures are passed through unchanged."""
        mock_response = {
            "success": False,
            "error": "Azure CLI command failed"
        }
        azure_repo_client._run_az_command = AsyncMock(return_value=mock_response)

        result = await azure_repo_client.list_pull_requests()

        assert result["success"] is False
        assert result["error"] == "Azure CLI command failed"

    @pytest.mark.asyncio
    async def test_list_pull_requests_no_data_field_returns_original(self, azure_repo_client):
        """Test that responses without data field are returned unchanged."""
        mock_response = {
            "success": True,
            "message": "No pull requests found"
        }
        azure_repo_client._run_az_command = AsyncMock(return_value=mock_response)

        result = await azure_repo_client.list_pull_requests()

        assert result == mock_response


class TestCsvIntegration:
    """Integration tests for CSV functionality."""

    @pytest.mark.asyncio
    async def test_end_to_end_csv_workflow(self, azure_repo_client):
        """Test complete end-to-end CSV workflow."""
        # Mock the Azure CLI command execution
        azure_repo_client.executor.execute_async = AsyncMock(
            return_value={"token": "test_token"}
        )
        azure_repo_client.executor.query_process = AsyncMock(
            return_value={
                "success": True,
                "output": json.dumps([
                    {
                        "pullRequestId": 123,
                        "title": "Fix authentication bug",
                        "sourceRefName": "refs/heads/feature/auth-fix",
                        "targetRefName": "refs/heads/main",
                        "createdBy": {
                            "uniqueName": "john.doe@abc.com"
                        },
                        "creationDate": "2024-01-15T10:30:00.000Z"
                    },
                    {
                        "pullRequestId": 124,
                        "title": "Add new feature",
                        "sourceRefName": "refs/heads/feature/new-feature",
                        "targetRefName": "refs/heads/develop",
                        "createdBy": {
                            "uniqueName": "jane.smith@abc.com"
                        },
                        "creationDate": "2024-01-14T15:45:00.000Z"
                    }
                ])
            }
        )

        # Execute via the tool interface
        result = await azure_repo_client.execute_tool({
            "operation": "list_pull_requests",
            "status": "active"
        })

        # Verify successful CSV response
        assert result["success"] is True
        csv_data = result["data"]

        # Parse and verify CSV content
        lines = csv_data.strip().split('\n')
        assert len(lines) == 3  # Header + 2 data rows

        # Verify header
        assert lines[0] == "id,creator,date,title,source_ref,target_ref"

        # Verify data content (basic checks)
        assert "123" in lines[1]
        assert "john.doe@abc.com" in lines[1]
        assert "Fix authentication bug" in lines[1]
        assert "feature/auth-fix" in lines[1]
        assert "main" in lines[1]

        assert "124" in lines[2]
        assert "jane.smith@abc.com" in lines[2]
        assert "Add new feature" in lines[2]
        assert "feature/new-feature" in lines[2]
        assert "develop" in lines[2]

    @pytest.mark.asyncio
    async def test_csv_with_special_characters_in_title(self, azure_repo_client):
        """Test CSV handling with special characters in PR titles."""
        azure_repo_client.executor.execute_async = AsyncMock(
            return_value={"token": "test_token"}
        )
        azure_repo_client.executor.query_process = AsyncMock(
            return_value={
                "success": True,
                "output": json.dumps([
                    {
                        "pullRequestId": 123,
                        "title": "Fix bug with \"quotes\" and, commas",
                        "sourceRefName": "refs/heads/feature/bug-fix",
                        "targetRefName": "refs/heads/main",
                        "createdBy": {
                            "uniqueName": "test.user@abc.com"
                        },
                        "creationDate": "2024-01-15T10:30:00.000Z"
                    }
                ])
            }
        )

        result = await azure_repo_client.execute_tool({
            "operation": "list_pull_requests"
        })

        assert result["success"] is True
        csv_data = result["data"]

        # Verify that CSV properly handles special characters
        # pandas.to_csv() should properly escape quotes and commas
        assert "Fix bug with \"quotes\" and, commas" in csv_data or \
               "\"Fix bug with \"\"quotes\"\" and, commas\"" in csv_data
