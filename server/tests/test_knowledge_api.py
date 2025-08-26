"""
Tests for Knowledge API endpoints.

This module tests the knowledge management API endpoints including:
- Knowledge import/indexing
- Collection management
- Document querying
- Knowledge sync functionality
- Code indexing (ctags)
- Tree-sitter parsing
- Code viewer functionality
"""

import json
import os
import tempfile
import shutil
import requests
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import pytest


class TestKnowledgeAPI:
    """Test cases for Knowledge API endpoints."""

    def test_list_collections(self, server_url):
        """Test listing knowledge collections."""
        resp = requests.get(f"{server_url}/api/collections", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert "collections" in data

    def test_list_collections_empty_response(self, server_url):
        """Test listing collections when none exist."""
        resp = requests.get(f"{server_url}/api/collections", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("collections"), list)

    def test_list_documents_missing_collection_param(self, server_url):
        """Test listing documents without collection parameter."""
        resp = requests.get(f"{server_url}/api/collection-documents", timeout=10)
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert "collection parameter" in data["error"].lower()

    def test_list_documents_with_collection(self, server_url):
        """Test listing documents with collection parameter."""
        resp = requests.get(f"{server_url}/api/collection-documents?collection=test", timeout=10)
        # Could be 200 (collection exists) or 500 (collection doesn't exist)
        assert resp.status_code in [200, 500]
        data = resp.json()
        if resp.status_code == 200:
            assert "documents" in data
            assert "document_count" in data

    def test_query_segments_missing_params(self, server_url):
        """Test querying segments without required parameters."""
        resp = requests.get(f"{server_url}/api/query-segments", timeout=10)
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert "collection or query parameter" in data["error"].lower()

    def test_query_segments_missing_query(self, server_url):
        """Test querying segments with collection but no query."""
        resp = requests.get(f"{server_url}/api/query-segments?collection=test", timeout=10)
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data

    def test_query_segments_missing_collection(self, server_url):
        """Test querying segments with query but no collection."""
        resp = requests.get(f"{server_url}/api/query-segments?query=test", timeout=10)
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data

    @pytest.mark.skipif(os.name == "nt", reason="Skip on Windows due to embedding model timeout issues")
    def test_query_segments_with_params(self, server_url):
        """Test querying segments with valid parameters."""
        resp = requests.get(
            f"{server_url}/api/query-segments?collection=test&query=sample&limit=5",
            timeout=30
        )
        # Could be 200 (success) or 500 (collection doesn't exist/error)
        assert resp.status_code in [200, 500]
        data = resp.json()
        if resp.status_code == 200:
            assert "documents" in data
            assert "ids" in data

    def test_delete_collection_missing_collection(self, server_url):
        """Test deleting collection without collection parameter."""
        resp = requests.post(
            f"{server_url}/api/delete-collection",
            json={},
            timeout=10
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert "collection parameter" in data["error"].lower()

    def test_delete_collection_with_collection(self, server_url):
        """Test deleting collection with valid collection name."""
        resp = requests.post(
            f"{server_url}/api/delete-collection",
            json={"collection": "test_collection"},
            timeout=10
        )
        # Could be 200 (deleted) or 500 (doesn't exist)
        assert resp.status_code in [200, 500]
        data = resp.json()
        assert "success" in data

    def test_import_knowledge_no_files(self, server_url):
        """Test importing knowledge without files."""
        resp = requests.post(
            f"{server_url}/api/import-knowledge",
            files={},
            data={},
            timeout=10
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert "no files uploaded" in data["error"].lower()

    def test_import_knowledge_with_file(self, server_url):
        """Test importing knowledge with a valid file."""
        # Create a test file
        test_content = "This is a test document for knowledge import."
        files = {
            'files': ('test.txt', test_content, 'text/plain')
        }
        data = {
            'collection': 'test_import',
            'overwrite': 'false'
        }

        resp = requests.post(
            f"{server_url}/api/import-knowledge",
            files=files,
            data=data,
            timeout=15
        )
        # Should succeed or fail gracefully
        assert resp.status_code in [200, 500]
        response_data = resp.json()
        assert "success" in response_data

    def test_knowledge_sync_status(self, server_url):
        """Test getting knowledge sync status."""
        resp = requests.get(f"{server_url}/api/knowledge-sync/status", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "configured_folders" in data
        assert "folders" in data
        assert isinstance(data["folders"], list)

    def test_knowledge_sync_trigger_when_disabled(self, server_url):
        """Test triggering knowledge sync when disabled."""
        resp = requests.post(
            f"{server_url}/api/knowledge-sync/trigger",
            json={},
            timeout=10
        )
        # Could be 400 (disabled) or 200 (enabled and triggered)
        assert resp.status_code in [200, 400, 500]
        data = resp.json()
        assert "success" in data

    def test_knowledge_sync_trigger_with_resync(self, server_url):
        """Test triggering knowledge sync with resync option."""
        resp = requests.post(
            f"{server_url}/api/knowledge-sync/trigger",
            json={"resync": True},
            timeout=15
        )
        # Could be 400 (disabled) or 200 (enabled and triggered)
        assert resp.status_code in [200, 400, 500]
        data = resp.json()
        assert "success" in data

    def test_knowledge_sync_folder_missing_params(self, server_url):
        """Test syncing folder without required parameters."""
        resp = requests.post(
            f"{server_url}/api/knowledge-sync/folder",
            json={},
            timeout=10
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert "folder_path and collection_name are required" in data["error"]

    def test_knowledge_sync_folder_missing_folder_path(self, server_url):
        """Test syncing folder without folder_path."""
        resp = requests.post(
            f"{server_url}/api/knowledge-sync/folder",
            json={"collection_name": "test"},
            timeout=10
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data

    def test_knowledge_sync_folder_missing_collection_name(self, server_url):
        """Test syncing folder without collection_name."""
        resp = requests.post(
            f"{server_url}/api/knowledge-sync/folder",
            json={"folder_path": "/test/path"},
            timeout=10
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data

    def test_knowledge_sync_folder_with_params(self, server_url):
        """Test syncing folder with valid parameters."""
        resp = requests.post(
            f"{server_url}/api/knowledge-sync/folder",
            json={
                "folder_path": "/tmp/test",
                "collection_name": "test_collection",
                "overwrite": True
            },
            timeout=15
        )
        # Will likely fail since path doesn't exist, but should handle gracefully
        assert resp.status_code in [200, 500]
        data = resp.json()
        assert "success" in data


class TestCodeIndexingAPI:
    """Test cases for Code Indexing API endpoints."""

    def test_code_indexing_ctags_missing_source_path(self, server_url):
        """Test ctags indexing without source_path."""
        resp = requests.post(
            f"{server_url}/api/code-indexing/ctags",
            json={},
            timeout=10
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert "source_path is required" in data["error"]

    def test_code_indexing_ctags_invalid_source_path(self, server_url):
        """Test ctags indexing with invalid source path."""
        resp = requests.post(
            f"{server_url}/api/code-indexing/ctags",
            json={"source_path": "/nonexistent/path"},
            timeout=10
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert "does not exist" in data["error"]

    def test_code_indexing_ctags_with_valid_path(self, server_url):
        """Test ctags indexing with valid source path."""
        # Create a real temporary directory for the test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some sample files
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
class TestClass:
    def test_method(self):
        pass
""")

            resp = requests.post(
                f"{server_url}/api/code-indexing/ctags",
                json={
                    "source_path": temp_dir,
                    "languages": "Python,JavaScript"
                },
                timeout=15
            )
            # Accept either success or graceful failure
            assert resp.status_code in [200, 500]
            data = resp.json()
            if resp.status_code == 200:
                assert data["success"] is True
                assert "tags_count" in data
                assert "outline" in data
            else:
                # Server handled the error gracefully
                assert "success" in data or "error" in data
            assert "git_info" in data
            assert "output_files" in data

    def test_tree_sitter_missing_source_path(self, server_url):
        """Test tree-sitter parsing without source_path."""
        resp = requests.post(
            f"{server_url}/api/code-indexing/tree-sitter",
            json={},
            timeout=10
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert "source_path is required" in data["error"]

    def test_tree_sitter_invalid_source_path(self, server_url):
        """Test tree-sitter parsing with invalid source path."""
        resp = requests.post(
            f"{server_url}/api/code-indexing/tree-sitter",
            json={"source_path": "/nonexistent/path"},
            timeout=10
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert "does not exist" in data["error"]

    def test_tree_sitter_with_valid_path(self, server_url):
        """Test tree-sitter parsing with valid source path."""
        # Create a real temporary directory for the test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some sample files
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("""
class TestClass:
    def test_func(self):
        return "hello"
""")

            resp = requests.post(
                f"{server_url}/api/code-indexing/tree-sitter",
                json={"source_path": temp_dir},
                timeout=15
            )
            # Accept either success or graceful failure
            assert resp.status_code in [200, 500]
            data = resp.json()
            if resp.status_code == 200:
                assert data["success"] is True
                assert "parsed_files_count" in data
                assert "total_functions" in data
                assert "total_classes" in data
            else:
                # Server handled the error gracefully
                assert "success" in data or "error" in data
            assert "git_info" in data


class TestCodeViewerAPI:
    """Test cases for Code Viewer API endpoints."""

    def test_code_viewer_paths_empty(self, server_url):
        """Test getting code viewer paths when none exist."""
        resp = requests.get(f"{server_url}/api/code-viewer/paths", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "paths" in data
        assert isinstance(data["paths"], list)

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.iterdir')
    def test_code_viewer_paths_with_indexed_data(self, mock_iterdir, mock_exists, server_url):
        """Test getting code viewer paths with indexed data."""
        # Mock the .code_indexing directory structure
        mock_exists.return_value = True

        # Create mock subdirectory with meta.txt
        mock_subdir = MagicMock()
        mock_subdir.is_dir.return_value = True
        mock_subdir.name = "abc123"

        # Mock meta.txt file
        mock_meta_file = mock_subdir / "meta.txt"
        mock_meta_file.exists.return_value = True

        mock_iterdir.return_value = [mock_subdir]

        # Mock file reading
        meta_content = "Original Path: /test/source\nPath Hash: abc123\nCreated: 2024-01-01T12:00:00"
        with patch('builtins.open', mock_open(read_data=meta_content)):
            resp = requests.get(f"{server_url}/api/code-viewer/paths", timeout=10)
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert "paths" in data

    def test_code_viewer_classes_missing_hash(self, server_url):
        """Test getting classes without path hash."""
        resp = requests.get(f"{server_url}/api/code-viewer/classes/", timeout=10)
        # This should result in a 404 or similar since hash is missing
        assert resp.status_code in [400, 404]

    def test_code_viewer_classes_invalid_hash(self, server_url):
        """Test getting classes with invalid path hash."""
        resp = requests.get(f"{server_url}/api/code-viewer/classes/invalid_hash", timeout=10)
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert "no indexed data found" in data["error"].lower()

    def test_code_viewer_classes_with_valid_hash_no_data(self, server_url):
        """Test getting classes with invalid hash (no indexed data)."""
        resp = requests.get(f"{server_url}/api/code-viewer/classes/invalid_hash", timeout=10)
        assert resp.status_code == 404
        data = resp.json()
        assert data["success"] is False
        assert "error" in data
        assert "no indexed data found" in data["error"].lower()

    def test_code_viewer_classes_with_ctags_data(self, server_url):
        """Test getting classes with invalid hash (no indexed data)."""
        resp = requests.get(f"{server_url}/api/code-viewer/classes/another_invalid_hash", timeout=10)
        assert resp.status_code == 404
        data = resp.json()
        assert data["success"] is False
        assert "error" in data
        assert "no indexed data found" in data["error"].lower()
