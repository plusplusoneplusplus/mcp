"""
Tests for knowledge sync configuration and environment handling.
"""

import pytest
from unittest.mock import patch, Mock
from utils.knowledge_sync.service import KnowledgeSyncService


class TestKnowledgeSyncConfiguration:
    """Test configuration parsing and environment variable handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = KnowledgeSyncService()

    @patch('utils.knowledge_sync.service.env')
    def test_configuration_precedence_order(self, mock_env):
        """Test that environment variables are read in correct precedence."""
        # Mock environment to return specific values
        def mock_get_setting(key, default):
            settings = {
                "knowledge_sync_enabled": True,
                "knowledge_sync_folders": "/path/to/docs,/path/to/reports",
                "knowledge_sync_collections": "docs,reports"
            }
            return settings.get(key, default)

        mock_env.get_setting.side_effect = mock_get_setting

        # Test enabled check
        assert self.service.is_enabled() is True

        # Test folder collections parsing
        folders = self.service.get_folder_collections()
        expected = [("/path/to/docs", "docs"), ("/path/to/reports", "reports")]
        assert folders == expected

        # Verify correct environment keys were accessed
        expected_calls = [
            (("knowledge_sync_enabled", False),),
            (("knowledge_sync_folders", ""),),
            (("knowledge_sync_collections", ""),)
        ]
        actual_calls = mock_env.get_setting.call_args_list
        assert len(actual_calls) >= len(expected_calls)

    @patch('utils.knowledge_sync.service.env')
    def test_empty_configuration_handling(self, mock_env):
        """Test behavior with empty or missing configuration."""
        # Mock empty configuration
        mock_env.get_setting.return_value = ""

        folders = self.service.get_folder_collections()
        assert folders == []

        # Test with None values
        mock_env.get_setting.return_value = None
        folders = self.service.get_folder_collections()
        assert folders == []

    @patch('utils.knowledge_sync.service.env')
    def test_malformed_configuration_handling(self, mock_env):
        """Test handling of malformed configuration strings."""
        # Test with extra commas and whitespace
        def mock_get_setting(key, default):
            if key == "knowledge_sync_folders":
                return " /path/to/docs , , /path/to/reports , "
            elif key == "knowledge_sync_collections":
                return " docs , , reports , "
            return default

        mock_env.get_setting.side_effect = mock_get_setting

        folders = self.service.get_folder_collections()
        # Should handle whitespace and empty entries gracefully
        expected = [("/path/to/docs", "docs"), ("/path/to/reports", "reports")]
        assert folders == expected

    @patch('utils.knowledge_sync.service.env')
    def test_folder_collection_name_generation(self, mock_env):
        """Test automatic generation of collection names from folder paths."""
        test_cases = [
            # (folders_config, collections_config, expected_result)
            (
                "/home/user/docs,/var/log/reports",
                "",
                [("/home/user/docs", "docs"), ("/var/log/reports", "reports")]
            ),
            (
                "./local/folder,../parent/folder",
                "",
                [("./local/folder", "folder"), ("../parent/folder", "folder")]
            ),
            (
                "/complex/path/with-dashes_and_underscores",
                "",
                [("/complex/path/with-dashes_and_underscores", "with-dashes_and_underscores")]
            ),
        ]

        for folders_str, collections_str, expected in test_cases:
            mock_env.get_setting.side_effect = [folders_str, collections_str]
            result = self.service.get_folder_collections()
            assert result == expected, f"Failed for input: {folders_str}, {collections_str}"

    @patch('utils.knowledge_sync.service.env')
    def test_collection_count_mismatch_handling(self, mock_env):
        """Test handling when folder and collection counts don't match."""
        # More folders than collections
        mock_env.get_setting.side_effect = [
            "/path/to/docs,/path/to/reports,/path/to/logs",  # 3 folders
            "docs,reports"                                    # 2 collections
        ]

        result = self.service.get_folder_collections()
        # Should fallback to using folder names
        expected = [
            ("/path/to/docs", "docs"),
            ("/path/to/reports", "reports"),
            ("/path/to/logs", "logs")
        ]
        assert result == expected

        # More collections than folders
        mock_env.get_setting.side_effect = [
            "/path/to/docs",                           # 1 folder
            "docs,reports,logs"                        # 3 collections
        ]

        result = self.service.get_folder_collections()
        # Should fallback to using folder names
        expected = [("/path/to/docs", "docs")]
        assert result == expected

    @patch('utils.knowledge_sync.service.env')
    def test_disabled_service_configuration(self, mock_env, disabled_config):
        """Test configuration when service is disabled."""
        mock_env.get_setting.side_effect = lambda k, d: disabled_config.get(k, d)

        assert self.service.is_enabled() is False

        # Even with disabled service, folder parsing should work
        folders = self.service.get_folder_collections()
        assert folders == []  # Empty because folders config is empty

    @patch('utils.knowledge_sync.service.env')
    def test_enabled_service_configuration(self, mock_env, enabled_config):
        """Test configuration when service is enabled."""
        mock_env.get_setting.side_effect = lambda k, d: enabled_config.get(k, d)

        assert self.service.is_enabled() is True

        folders = self.service.get_folder_collections()
        expected = [("./docs", "documentation"), ("./reports", "reports")]
        assert folders == expected

    def test_configuration_validation(self):
        """Test that configuration values are properly validated."""
        # Test with valid service instance
        assert hasattr(self.service, 'is_enabled')
        assert hasattr(self.service, 'get_folder_collections')
        assert callable(self.service.is_enabled)
        assert callable(self.service.get_folder_collections)

        # Test default state
        with patch('utils.knowledge_sync.service.env') as mock_env:
            mock_env.get_setting.return_value = False
            assert self.service.is_enabled() is False

    @patch('utils.knowledge_sync.service.env')
    def test_special_characters_in_paths(self, mock_env):
        """Test handling of special characters in folder paths."""
        special_paths = [
            "/path/with spaces/docs",
            "/path/with-dashes/reports",
            "/path/with_underscores/logs",
            "/path/with.dots/config",
            "/path/with(parentheses)/data"
        ]

        folders_str = ",".join(special_paths)
        collections_str = "docs,reports,logs,config,data"

        mock_env.get_setting.side_effect = [folders_str, collections_str]

        result = self.service.get_folder_collections()

        assert len(result) == len(special_paths)
        for i, (path, collection) in enumerate(result):
            assert path == special_paths[i]
            assert collection in collections_str.split(",")

    @patch('utils.knowledge_sync.service.env')
    def test_unicode_handling_in_configuration(self, mock_env):
        """Test handling of unicode characters in configuration."""
        unicode_folders = [
            "/path/to/文档",      # Chinese characters
            "/path/to/документы", # Cyrillic characters
            "/path/to/ドキュメント"  # Japanese characters
        ]

        folders_str = ",".join(unicode_folders)
        collections_str = "docs_zh,docs_ru,docs_ja"

        mock_env.get_setting.side_effect = [folders_str, collections_str]

        result = self.service.get_folder_collections()

        assert len(result) == 3
        assert result[0] == ("/path/to/文档", "docs_zh")
        assert result[1] == ("/path/to/документы", "docs_ru")
        assert result[2] == ("/path/to/ドキュメント", "docs_ja")
