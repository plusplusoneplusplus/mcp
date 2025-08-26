"""
Integration tests for the knowledge sync service.

These tests verify the end-to-end functionality with real file system operations
and mocked external dependencies.
"""

import pytest
from unittest.mock import patch, AsyncMock
from utils.knowledge_sync.service import KnowledgeSyncService


class TestKnowledgeSyncIntegration:
    """Integration tests for knowledge sync functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = KnowledgeSyncService()

    @pytest.mark.asyncio
    @patch('utils.knowledge_sync.service.env')
    async def test_complete_sync_workflow(self, mock_env, temp_workspace, mock_indexer_tool):
        """Test complete sync workflow from configuration to execution."""
        # Setup environment configuration
        mock_env.get_setting.side_effect = lambda key, default: {
            "knowledge_sync_enabled": True,
            "knowledge_sync_folders": f"{temp_workspace}/docs,{temp_workspace}/reports",
            "knowledge_sync_collections": "documentation,reports"
        }.get(key, default)

        # Replace the indexer tool with mock
        self.service.indexer_tool = mock_indexer_tool

        # Execute complete sync
        result = await self.service.run_manual_sync()

        # Verify results
        assert result["success"] is True
        assert result["action"] == "syncing"
        assert result["total_folders"] == 2
        assert result["successful_folders"] == 2
        assert result["failed_folders"] == 0
        assert result["total_imported_files"] == 4  # 2 files per folder

        # Verify indexer was called for both folders
        assert mock_indexer_tool.execute_tool.call_count == 2

    @pytest.mark.asyncio
    @patch('utils.knowledge_sync.service.env')
    async def test_resync_workflow(self, mock_env, temp_workspace, mock_indexer_tool):
        """Test re-sync workflow with overwrite enabled."""
        # Setup environment configuration
        mock_env.get_setting.side_effect = lambda key, default: {
            "knowledge_sync_enabled": True,
            "knowledge_sync_folders": f"{temp_workspace}/docs",
            "knowledge_sync_collections": "documentation"
        }.get(key, default)

        # Replace the indexer tool with mock
        self.service.indexer_tool = mock_indexer_tool

        # Execute re-sync
        result = await self.service.run_manual_sync(resync=True)

        # Verify results
        assert result["success"] is True
        assert result["action"] == "re-syncing"
        assert result["resync"] is True

        # Verify indexer was called with overwrite=True
        mock_indexer_tool.execute_tool.assert_called_once()
        call_args = mock_indexer_tool.execute_tool.call_args
        assert call_args[0][0]["overwrite"] is True

    @pytest.mark.asyncio
    @patch('utils.knowledge_sync.service.env')
    async def test_single_folder_sync(self, mock_env, temp_workspace, mock_indexer_tool):
        """Test syncing a single folder directly."""
        # Replace the indexer tool with mock
        self.service.indexer_tool = mock_indexer_tool

        docs_path = f"{temp_workspace}/docs"
        result = await self.service.index_folder(docs_path, "test_collection", overwrite=False)

        # Verify results
        assert result["success"] is True
        assert result["folder"] == docs_path
        assert result["collection"] == "test_collection"
        assert "resolved_path" in result

        # Verify indexer was called with correct files
        mock_indexer_tool.execute_tool.assert_called_once()
        call_args = mock_indexer_tool.execute_tool.call_args[0][0]

        assert call_args["collection"] == "test_collection"
        assert call_args["overwrite"] is False
        assert len(call_args["files"]) == 3  # Should find 3 markdown files

        # Check that files were collected correctly
        filenames = {f["filename"] for f in call_args["files"]}
        assert "readme.md" in filenames
        assert "api.md" in filenames
        assert "guides/advanced.md" in filenames

    @pytest.mark.asyncio
    async def test_markdown_file_collection_accuracy(self, temp_workspace):
        """Test that markdown collection accurately filters and reads files."""
        from pathlib import Path

        docs_path = Path(temp_workspace) / "docs"
        markdown_files = self.service.collect_markdown_files(docs_path)

        # Should find exactly 3 markdown files
        assert len(markdown_files) == 3

        # Check filenames are relative to the scanned directory
        filenames = {f["filename"] for f in markdown_files}
        expected_files = {"readme.md", "api.md", "guides/advanced.md"}
        assert filenames == expected_files

        # Verify content is correctly read
        readme_file = next(f for f in markdown_files if f["filename"] == "readme.md")
        assert "Sample Documentation" in readme_file["content"]
        assert readme_file["encoding"] == "utf-8"

        # Check that non-markdown files were ignored
        for file_info in markdown_files:
            assert file_info["filename"].endswith(".md")

    @pytest.mark.asyncio
    @patch('utils.knowledge_sync.service.env')
    async def test_error_handling_mixed_results(self, mock_env, temp_workspace):
        """Test handling of mixed success/failure results."""
        # Setup configuration with one valid and one invalid folder
        mock_env.get_setting.side_effect = lambda key, default: {
            "knowledge_sync_enabled": True,
            "knowledge_sync_folders": f"{temp_workspace}/docs,/nonexistent/folder",
            "knowledge_sync_collections": "documentation,invalid"
        }.get(key, default)

        # Execute sync
        result = await self.service.run_manual_sync()

        # Verify mixed results
        assert result["success"] is False  # Overall failure due to one error
        assert result["total_folders"] == 2
        assert result["successful_folders"] == 0  # First one should fail due to missing indexer
        assert result["failed_folders"] == 2

        # Check individual results
        assert len(result["results"]) == 2

        # Both should fail - first due to indexer issues, second due to missing folder
        for folder_result in result["results"]:
            assert folder_result["success"] is False
            assert "error" in folder_result

    @pytest.mark.asyncio
    async def test_service_lifecycle(self, mock_env):
        """Test service startup and shutdown lifecycle."""
        with patch('utils.knowledge_sync.service.env', mock_env):
            # Test disabled service startup
            mock_env.get_setting.return_value = False
            await self.service.start_knowledge_sync_service()

            # Test enabled service startup
            mock_env.get_setting.return_value = True
            await self.service.start_knowledge_sync_service()

            # Test shutdown
            self.service.shutdown()

            # Should complete without exceptions
