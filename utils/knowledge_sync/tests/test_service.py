"""
Unit tests for the KnowledgeSyncService class.
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import pytest
import asyncio

# Import the service to test
from utils.knowledge_sync.service import KnowledgeSyncService


class TestKnowledgeSyncService:
    """Test cases for KnowledgeSyncService."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.service = KnowledgeSyncService()
        self.temp_dir = None

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_temp_structure(self):
        """Create a temporary directory structure for testing."""
        self.temp_dir = tempfile.mkdtemp(prefix="knowledge_sync_test_")

        # Create test markdown files
        docs_dir = Path(self.temp_dir) / "docs"
        docs_dir.mkdir()

        (docs_dir / "readme.md").write_text("# Documentation\nThis is test documentation.")
        (docs_dir / "api.md").write_text("# API Reference\nAPI documentation here.")

        # Create subdirectory with markdown
        sub_dir = docs_dir / "advanced"
        sub_dir.mkdir()
        (sub_dir / "advanced.md").write_text("# Advanced Topics\nAdvanced documentation.")

        # Create non-markdown files (should be ignored)
        (docs_dir / "config.json").write_text('{"test": true}')
        (docs_dir / "image.png").write_bytes(b"fake image data")

        # Create another folder
        reports_dir = Path(self.temp_dir) / "reports"
        reports_dir.mkdir()
        (reports_dir / "summary.md").write_text("# Summary Report\nTest report content.")

        return self.temp_dir

    @patch('utils.knowledge_sync.service.env')
    def test_is_enabled_true(self, mock_env):
        """Test is_enabled returns True when knowledge sync is enabled."""
        mock_env.get_setting.return_value = True
        assert self.service.is_enabled() is True
        mock_env.get_setting.assert_called_once_with("knowledge_sync_enabled", False)

    @patch('utils.knowledge_sync.service.env')
    def test_is_enabled_false(self, mock_env):
        """Test is_enabled returns False when knowledge sync is disabled."""
        mock_env.get_setting.return_value = False
        assert self.service.is_enabled() is False
        mock_env.get_setting.assert_called_once_with("knowledge_sync_enabled", False)

    @patch('utils.knowledge_sync.service.env')
    def test_get_folder_collections_empty(self, mock_env):
        """Test get_folder_collections with empty configuration."""
        mock_env.get_setting.side_effect = ["", ""]  # Empty folders and collections
        result = self.service.get_folder_collections()
        assert result == []

    @patch('utils.knowledge_sync.service.env')
    def test_get_folder_collections_matched(self, mock_env):
        """Test get_folder_collections with matched folders and collections."""
        mock_env.get_setting.side_effect = [
            "/path/to/docs,/path/to/reports",  # folders
            "documentation,reports"            # collections
        ]
        result = self.service.get_folder_collections()
        expected = [("/path/to/docs", "documentation"), ("/path/to/reports", "reports")]
        assert result == expected

    @patch('utils.knowledge_sync.service.env')
    def test_get_folder_collections_auto_names(self, mock_env):
        """Test get_folder_collections automatically generates collection names."""
        mock_env.get_setting.side_effect = [
            "/path/to/docs,/path/to/reports",  # folders
            ""                                 # empty collections
        ]
        result = self.service.get_folder_collections()
        expected = [("/path/to/docs", "docs"), ("/path/to/reports", "reports")]
        assert result == expected

    @patch('utils.knowledge_sync.service.env')
    def test_get_folder_collections_mismatched(self, mock_env):
        """Test get_folder_collections with mismatched counts."""
        mock_env.get_setting.side_effect = [
            "/path/to/docs,/path/to/reports",  # 2 folders
            "documentation"                    # 1 collection
        ]
        result = self.service.get_folder_collections()
        # Should fallback to folder names when mismatch
        expected = [("/path/to/docs", "docs"), ("/path/to/reports", "reports")]
        assert result == expected

    def test_resolve_folder_path_absolute_exists(self):
        """Test resolve_folder_path with existing absolute path."""
        temp_dir = self.create_temp_structure()
        docs_path = Path(temp_dir) / "docs"

        result = self.service.resolve_folder_path(str(docs_path))
        assert result == docs_path
        assert result.exists()

    def test_resolve_folder_path_absolute_not_exists(self):
        """Test resolve_folder_path with non-existing absolute path."""
        result = self.service.resolve_folder_path("/non/existent/path")
        assert result is None

    @patch('utils.knowledge_sync.service.env')
    def test_resolve_folder_path_relative_to_git_root(self, mock_env):
        """Test resolve_folder_path with relative path to git root."""
        temp_dir = self.create_temp_structure()
        mock_env.get_git_root.return_value = temp_dir

        result = self.service.resolve_folder_path("docs")
        expected = Path(temp_dir) / "docs"
        assert result == expected

    @patch('utils.knowledge_sync.service.env')
    def test_resolve_folder_path_relative_to_cwd(self, mock_env):
        """Test resolve_folder_path with relative path to current directory."""
        temp_dir = self.create_temp_structure()
        mock_env.get_git_root.return_value = None

        # Change to temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = self.service.resolve_folder_path("docs")
            expected = Path(temp_dir) / "docs"
            assert result.resolve() == expected.resolve()
        finally:
            os.chdir(original_cwd)

    def test_collect_markdown_files(self):
        """Test collect_markdown_files gathers all markdown files recursively."""
        temp_dir = self.create_temp_structure()
        docs_path = Path(temp_dir) / "docs"

        result = self.service.collect_markdown_files(docs_path)

        # Should find 3 markdown files, not the json or png files
        assert len(result) == 3

        # Check filenames (relative to docs folder)
        filenames = {item["filename"] for item in result}
        expected_files = {"readme.md", "api.md", "advanced/advanced.md"}
        assert filenames == expected_files

        # Check content is read correctly
        readme_content = next(item for item in result if item["filename"] == "readme.md")
        assert "# Documentation" in readme_content["content"]
        assert readme_content["encoding"] == "utf-8"

    def test_collect_markdown_files_empty_directory(self):
        """Test collect_markdown_files with empty directory."""
        temp_dir = tempfile.mkdtemp()
        try:
            result = self.service.collect_markdown_files(Path(temp_dir))
            assert result == []
        finally:
            shutil.rmtree(temp_dir)

    def test_collect_markdown_files_no_markdown(self):
        """Test collect_markdown_files with no markdown files."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create non-markdown files
            (Path(temp_dir) / "test.txt").write_text("text file")
            (Path(temp_dir) / "data.json").write_text("{}")

            result = self.service.collect_markdown_files(Path(temp_dir))
            assert result == []
        finally:
            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_index_folder_success(self):
        """Test successful folder indexing."""
        temp_dir = self.create_temp_structure()
        docs_path = str(Path(temp_dir) / "docs")

        # Mock the indexer tool
        mock_result = {
            "success": True,
            "imported_files": 3,
            "total_segments": 5
        }
        self.service.indexer_tool.execute_tool = AsyncMock(return_value=mock_result)

        result = await self.service.index_folder(docs_path, "test_collection", overwrite=False)

        assert result["success"] is True
        assert result["imported_files"] == 3
        assert result["folder"] == docs_path
        assert "resolved_path" in result

    @pytest.mark.asyncio
    async def test_index_folder_not_found(self):
        """Test index_folder with non-existent folder."""
        result = await self.service.index_folder("/non/existent/path", "test_collection")

        assert result["success"] is False
        assert "Folder not found" in result["error"]
        assert result["collection"] == "test_collection"

    @pytest.mark.asyncio
    async def test_index_folder_no_markdown_files(self):
        """Test index_folder with folder containing no markdown files."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create non-markdown files
            (Path(temp_dir) / "test.txt").write_text("text file")

            result = await self.service.index_folder(temp_dir, "test_collection")

            assert result["success"] is True
            assert "No markdown files found" in result["warning"]
            assert result["imported_files"] == 0
        finally:
            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_index_folder_indexer_failure(self):
        """Test index_folder when indexer tool fails."""
        temp_dir = self.create_temp_structure()
        docs_path = str(Path(temp_dir) / "docs")

        # Mock the indexer tool to raise an exception
        self.service.indexer_tool.execute_tool = AsyncMock(
            side_effect=Exception("Indexer failed")
        )

        result = await self.service.index_folder(docs_path, "test_collection")

        assert result["success"] is False
        assert "Failed to index folder" in result["error"]
        assert "Indexer failed" in result["error"]

    @pytest.mark.asyncio
    @patch('utils.knowledge_sync.service.env')
    async def test_run_manual_sync_disabled(self, mock_env):
        """Test run_manual_sync when service is disabled."""
        mock_env.get_setting.return_value = False

        result = await self.service.run_manual_sync()

        assert result["success"] is False
        assert "Knowledge sync is not enabled" in result["error"]

    @pytest.mark.asyncio
    @patch('utils.knowledge_sync.service.env')
    async def test_run_manual_sync_no_folders(self, mock_env):
        """Test run_manual_sync with no configured folders."""
        mock_env.get_setting.side_effect = [True, "", ""]  # enabled, but no folders

        result = await self.service.run_manual_sync()

        assert result["success"] is False
        assert "No folders configured for sync" in result["error"]

    @pytest.mark.asyncio
    @patch('utils.knowledge_sync.service.env')
    async def test_run_manual_sync_success(self, mock_env):
        """Test successful manual sync operation."""
        temp_dir = self.create_temp_structure()

        # Mock environment settings
        mock_env.get_setting.side_effect = [
            True,                                           # enabled
            f"{temp_dir}/docs,{temp_dir}/reports",         # folders
            "documentation,reports"                         # collections
        ]
        mock_env.get_git_root.return_value = temp_dir

        # Mock successful indexing for both folders
        mock_result = {"success": True, "imported_files": 3}
        self.service.index_folder = AsyncMock(return_value=mock_result)

        result = await self.service.run_manual_sync(resync=False)

        assert result["success"] is True
        assert result["action"] == "syncing"
        assert result["resync"] is False
        assert result["total_folders"] == 2
        assert result["successful_folders"] == 2
        assert result["failed_folders"] == 0
        assert result["total_imported_files"] == 6  # 3 files per folder

    @pytest.mark.asyncio
    @patch('utils.knowledge_sync.service.env')
    async def test_run_manual_sync_with_errors(self, mock_env):
        """Test manual sync with some folder errors."""
        temp_dir = self.create_temp_structure()

        # Mock environment settings
        mock_env.get_setting.side_effect = [
            True,                                           # enabled
            f"{temp_dir}/docs,/nonexistent",               # folders (one invalid)
            "documentation,invalid"                         # collections
        ]

        # Mock indexing results - one success, one failure
        async def mock_index_folder(folder_path, collection_name, overwrite=False):
            if "nonexistent" in folder_path:
                return {"success": False, "error": "Folder not found"}
            return {"success": True, "imported_files": 3}

        self.service.index_folder = AsyncMock(side_effect=mock_index_folder)

        result = await self.service.run_manual_sync()

        assert result["success"] is False  # Overall failure due to errors
        assert result["total_folders"] == 2
        assert result["successful_folders"] == 1
        assert result["failed_folders"] == 1
        assert result["total_imported_files"] == 3

    @pytest.mark.asyncio
    @patch('utils.knowledge_sync.service.env')
    async def test_run_manual_sync_resync_mode(self, mock_env):
        """Test manual sync in re-sync mode."""
        temp_dir = self.create_temp_structure()

        # Mock environment settings
        mock_env.get_setting.side_effect = [
            True,                              # enabled
            f"{temp_dir}/docs",               # folders
            "documentation"                    # collections
        ]

        # Mock successful indexing
        mock_result = {"success": True, "imported_files": 3}
        self.service.index_folder = AsyncMock(return_value=mock_result)

        result = await self.service.run_manual_sync(resync=True)

        assert result["success"] is True
        assert result["action"] == "re-syncing"
        assert result["resync"] is True

        # Verify index_folder was called with overwrite=True
        self.service.index_folder.assert_called_once_with(
            f"{temp_dir}/docs", "documentation", overwrite=True
        )

    @pytest.mark.asyncio
    @patch('utils.knowledge_sync.service.env')
    async def test_start_knowledge_sync_service_disabled(self, mock_env):
        """Test service startup when disabled."""
        mock_env.get_setting.return_value = False

        await self.service.start_knowledge_sync_service()

        # Should not raise any exceptions, just log and return
        mock_env.get_setting.assert_called_once_with("knowledge_sync_enabled", False)

    @pytest.mark.asyncio
    @patch('utils.knowledge_sync.service.env')
    async def test_start_knowledge_sync_service_enabled(self, mock_env):
        """Test service startup when enabled."""
        mock_env.get_setting.return_value = True

        await self.service.start_knowledge_sync_service()

        # Should not raise any exceptions
        mock_env.get_setting.assert_called_once_with("knowledge_sync_enabled", False)

    def test_shutdown(self):
        """Test service shutdown."""
        # Mock the executor
        mock_executor = Mock()
        self.service._executor = mock_executor

        self.service.shutdown()

        mock_executor.shutdown.assert_called_once_with(wait=True, timeout=30)

    def test_shutdown_with_exception(self):
        """Test service shutdown handles executor exceptions."""
        # Mock the executor to raise an exception
        mock_executor = Mock()
        mock_executor.shutdown.side_effect = Exception("Shutdown error")
        self.service._executor = mock_executor

        # Should not raise exception
        self.service.shutdown()

        mock_executor.shutdown.assert_called_once_with(wait=True, timeout=30)
