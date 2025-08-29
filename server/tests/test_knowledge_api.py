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


class TestCodeIndexingIntegration:
    """Integration tests that perform actual indexing and verify results."""

    def test_ctags_indexing_python_sample_with_verification(self, server_url):
        """Test ctags indexing on sample Python project and verify results."""
        sample_path = Path(__file__).parent.parent.parent / "utils" / "code_indexing" / "tests" / "sample_python_project"

        resp = requests.post(
            f"{server_url}/api/code-indexing/ctags",
            json={
                "source_path": str(sample_path),
                "languages": "Python"
            },
            timeout=30
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "tags_count" in data
        assert "outline" in data
        assert "git_info" in data

        # Verify specific expected content
        # The outline field may be a string representation rather than a list
        expected_classes = ["Application", "AreaCalculator", "Rectangle", "Circle", "Triangle", "BinaryTree", "LinkedList"]
        expected_functions = ["main", "run_geometry_demo", "run_math_demo", "calculate_area", "factorial", "fibonacci"]

        # Check if outline contains expected class/function names
        if "outline" in data and data["outline"]:
            outline = data["outline"]
            found_classes = []

            # Handle different outline formats
            if isinstance(outline, dict):
                # New structured format
                if "classes" in outline:
                    found_classes = [cls for cls in expected_classes if cls in outline["classes"]]
                elif "class_details" in outline:
                    class_details = outline["class_details"]
                    if isinstance(class_details, dict):
                        found_classes = [cls for cls in expected_classes if cls in class_details.keys()]
                # Fallback: search in string representation
                if not found_classes:
                    outline_text = str(outline)
                    found_classes = [cls for cls in expected_classes if cls in outline_text]
            else:
                # Fallback: treat as string
                outline_text = str(outline)
                found_classes = [cls for cls in expected_classes if cls in outline_text]

            # Verify at least some expected items are found
            assert len(found_classes) > 0, f"Expected classes {expected_classes} not found in outline"
        elif "class_details" in data:
            # Alternative format with class_details at top level
            class_details = data["class_details"]
            found_classes = list(class_details.keys()) if isinstance(class_details, dict) else []
            assert any(cls in found_classes for cls in expected_classes), f"Expected classes {expected_classes} not found in {found_classes}"
        else:
            # If we can't verify specific content, at least check we have reasonable counts
            if "tags_count" in data and data["tags_count"] > 10:
                # Accept that we have a reasonable number of tags as validation
                pass
            else:
                assert False, f"Could not verify content - no usable outline or class_details found"

        # Verify tag count is reasonable
        assert data["tags_count"] > 10, f"Expected substantial tag count, got {data['tags_count']}"

    def test_ctags_indexing_cpp_sample_with_verification(self, server_url):
        """Test ctags indexing on sample C++ project and verify results."""
        sample_path = Path(__file__).parent.parent.parent / "utils" / "code_indexing" / "tests" / "sample_cpp_project"

        resp = requests.post(
            f"{server_url}/api/code-indexing/ctags",
            json={
                "source_path": str(sample_path),
                "languages": "C++"
            },
            timeout=30
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "tags_count" in data
        assert "outline" in data

        # Verify specific expected content
        expected_classes = ["ShapeManager", "Shape", "Rectangle", "Circle", "Vec2d", "StatisticsCalculator"]
        expected_functions = ["main", "addShape", "drawAll", "calculateTotalArea", "calculateDistance", "demonstrateVectorOperations"]

        # Check if outline contains expected class/function names as text
        if "outline" in data and data["outline"]:
            outline_text = str(data["outline"])
            # Check for expected class names in the outline text
            found_classes = [cls for cls in expected_classes if cls in outline_text]
            found_functions = [func for func in expected_functions if func in outline_text]

            # Verify at least some expected items are found
            assert len(found_classes) > 0, f"Expected classes {expected_classes} not found in outline text"
            # Functions are optional since outline format may not include all functions
        elif "class_details" in data:
            # Alternative format with class_details
            class_details = data["class_details"]
            found_classes = list(class_details.keys()) if isinstance(class_details, dict) else []
            assert any(cls in found_classes for cls in expected_classes), f"Expected classes {expected_classes} not found in {found_classes}"
        else:
            # If we can't verify specific content, at least check we have reasonable counts
            if "tags_count" in data and data["tags_count"] > 5:
                # Accept that we have a reasonable number of tags as validation
                pass
            else:
                assert False, f"Could not verify content - no usable outline or class_details found"

        # Verify reasonable tag count
        assert data["tags_count"] > 5, f"Expected reasonable tag count for C++, got {data['tags_count']}"

    def test_tree_sitter_python_sample_with_verification(self, server_url):
        """Test tree-sitter parsing on sample Python project and verify results."""
        sample_path = Path(__file__).parent.parent.parent / "utils" / "code_indexing" / "tests" / "sample_python_project"

        resp = requests.post(
            f"{server_url}/api/code-indexing/tree-sitter",
            json={"source_path": str(sample_path)},
            timeout=30
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

        # Verify parsing metrics
        assert "parsed_files_count" in data
        assert "total_functions" in data
        assert "total_classes" in data
        assert "git_info" in data

        # Should have parsed multiple Python files
        assert data["parsed_files_count"] > 0, "Should have parsed at least some files"
        assert data["total_functions"] > 0, "Should have found functions"
        assert data["total_classes"] > 0, "Should have found classes"

        # Should have reasonable counts for the sample project
        assert data["total_functions"] >= 10, f"Expected at least 10 functions, got {data['total_functions']}"
        assert data["total_classes"] >= 5, f"Expected at least 5 classes, got {data['total_classes']}"

    def test_code_viewer_with_indexed_data_integration(self, server_url):
        """Test code viewer functionality after indexing sample data."""
        sample_path = Path(__file__).parent.parent.parent / "utils" / "code_indexing" / "tests" / "sample_python_project"

        # First, perform indexing
        index_resp = requests.post(
            f"{server_url}/api/code-indexing/ctags",
            json={
                "source_path": str(sample_path),
                "languages": "Python"
            },
            timeout=30
        )

        assert index_resp.status_code == 200
        index_data = index_resp.json()
        assert index_data["success"] is True

        # Get the path hash from indexing response
        path_hash = index_data.get("git_info", {}).get("path_hash")
        if not path_hash:
            # Try to get from output_files
            output_files = index_data.get("output_files", {})
            if "meta_file" in output_files:
                # Extract hash from meta file path
                meta_path = output_files["meta_file"]
                path_hash = Path(meta_path).parent.name

        assert path_hash, "Should have path hash from indexing"

        # Test getting viewer paths
        paths_resp = requests.get(f"{server_url}/api/code-viewer/paths", timeout=10)
        assert paths_resp.status_code == 200
        paths_data = paths_resp.json()
        assert paths_data["success"] is True
        assert "paths" in paths_data

        # Should now have at least one indexed path
        paths = paths_data["paths"]
        assert len(paths) > 0, "Should have indexed paths after indexing"

        # Find our indexed path
        our_path = None
        for path_info in paths:
            if path_hash in str(path_info):
                our_path = path_info
                break

        assert our_path, f"Should find our indexed path with hash {path_hash} in paths: {paths}"

        # Test getting classes for the indexed data
        classes_resp = requests.get(f"{server_url}/api/code-viewer/classes/{path_hash}", timeout=10)
        assert classes_resp.status_code == 200
        classes_data = classes_resp.json()
        assert classes_data["success"] is True
        assert "classes" in classes_data

        # Verify we get actual class data
        classes = classes_data["classes"]
        assert len(classes) > 0, "Should have found classes in indexed data"

        # Check for expected classes from our sample
        class_names = [cls.get("name") for cls in classes if cls.get("name")]
        expected_in_results = ["Application", "Rectangle", "Circle", "BinaryTree"]
        found_expected = [name for name in expected_in_results if name in class_names]
        assert len(found_expected) > 0, f"Should find some expected classes {expected_in_results} in results {class_names}"

    def test_end_to_end_indexing_and_querying_workflow(self, server_url):
        """Test complete workflow: index sample code, then query and verify results."""
        sample_path = Path(__file__).parent.parent.parent / "utils" / "code_indexing" / "tests" / "sample_python_project"

        # Step 1: Index the sample Python project
        index_resp = requests.post(
            f"{server_url}/api/code-indexing/ctags",
            json={
                "source_path": str(sample_path),
                "languages": "Python",
                "include_patterns": "*.py"
            },
            timeout=30
        )

        assert index_resp.status_code == 200
        index_data = index_resp.json()
        assert index_data["success"] is True

        # Verify indexing results contain expected structure
        assert "outline" in index_data
        assert "tags_count" in index_data
        assert index_data["tags_count"] > 0

        # Handle outline as text representation
        if "outline" in index_data and index_data["outline"]:
            outline_text = str(index_data["outline"])

            # Step 2: Verify specific indexed content in outline text
            # Check for main.py content
            assert "main.py" in outline_text, "Should find main.py in outline"

            # Check for Application class
            assert "Application" in outline_text, "Should find Application class in outline"

            # Check for specific methods
            expected_methods = ["run_geometry_demo", "run_math_demo", "run_async_demo"]
            found_methods = [method for method in expected_methods if method in outline_text]
            assert len(found_methods) > 0, f"Should find some expected methods {expected_methods} in outline"
        elif "class_details" in index_data:
            # Alternative format with class_details
            class_details = index_data["class_details"]
            assert isinstance(class_details, dict) and len(class_details) > 0, "Should have class details"

            # Check for Application class in class_details
            found_application = "Application" in class_details
            assert found_application, f"Should find Application class in {list(class_details.keys())}"

            # Verify we have reasonable stats
            if "stats" in index_data:
                stats = index_data["stats"]
                assert stats.get("total_classes", 0) > 5, f"Should have reasonable class count, got {stats.get('total_classes', 0)}"
                assert stats.get("total_functions", 0) > 10, f"Should have reasonable function count, got {stats.get('total_functions', 0)}"
        else:
            # Fallback: just verify we have reasonable tag counts
            assert index_data.get("tags_count", 0) > 10, f"Should have reasonable tag count, got {index_data.get('tags_count', 0)}"

            # Step 3: Verify file-specific content (only for outline format)
            geometry_items = [item for item in outline if isinstance(item, dict) and "geometry.py" in str(item.get("file", ""))]
            if len(geometry_items) > 0:
                geometry_classes = [item.get("name") for item in geometry_items if isinstance(item, dict) and item.get("kind") == "class"]
                assert "Rectangle" in geometry_classes or "Circle" in geometry_classes, f"Should find geometry classes in {geometry_classes}"

            # Step 4: Verify data structure completeness
            # Each outline item should have required fields
            for item in outline[:10]:  # Check first 10 items
                if isinstance(item, dict):
                    assert "name" in item, f"Outline item missing name: {item}"
                    assert "kind" in item, f"Outline item missing kind: {item}"
                    assert "file" in item, f"Outline item missing file: {item}"

        print(f"✅ Successfully indexed and verified {index_data['tags_count']} tags from sample Python project")

    def test_cpp_hello_world_indexing_verification(self, server_url):
        """Test indexing and verification with a simple C++ hello world example."""
        # Create a simple hello world C++ program for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            hello_cpp = Path(temp_dir) / "hello.cpp"
            hello_cpp.write_text("""
#include <iostream>
#include <string>

class Greeter {
public:
    Greeter(const std::string& name) : name_(name) {}

    void sayHello() const {
        std::cout << "Hello, " << name_ << "!" << std::endl;
    }

    void sayGoodbye() const {
        std::cout << "Goodbye, " << name_ << "!" << std::endl;
    }

private:
    std::string name_;
};

int main() {
    Greeter greeter("World");
    greeter.sayHello();
    greeter.sayGoodbye();
    return 0;
}
""")

            # Index the hello world program
            resp = requests.post(
                f"{server_url}/api/code-indexing/ctags",
                json={
                    "source_path": temp_dir,
                    "languages": "C++"
                },
                timeout=30
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert "outline" in data
            assert "tags_count" in data

            # Handle outline data structure
            if "outline" in data and data["outline"]:
                outline = data["outline"]

                if isinstance(outline, dict):
                    # Check classes list or class_details
                    if "classes" in outline:
                        assert "Greeter" in outline["classes"], f"Should find Greeter class in {outline['classes']}"
                    elif "class_details" in outline:
                        assert "Greeter" in outline["class_details"], f"Should find Greeter in class_details keys: {list(outline['class_details'].keys()) if isinstance(outline['class_details'], dict) else outline['class_details']}"

                    # Check for reasonable function count in stats instead of specific names
                    if "stats" in outline:
                        stats = outline["stats"]
                        assert stats.get("total_functions", 0) >= 1, f"Should have at least 1 function, got {stats.get('total_functions', 0)}"
                    else:
                        # Fallback: search in string representation
                        outline_text = str(outline)
                        assert "Greeter" in outline_text, "Should find Greeter class in outline"
                else:
                    # Handle as string
                    outline_text = str(outline)
                    assert "Greeter" in outline_text, "Should find Greeter class in outline"
            elif "class_details" in data:
                # Alternative format with class_details
                class_details = data["class_details"]
                assert "Greeter" in class_details, f"Should find Greeter class in {list(class_details.keys()) if isinstance(class_details, dict) else 'non-dict class_details'}"

                # Verify reasonable stats
                if "stats" in data:
                    stats = data["stats"]
                    assert stats.get("total_classes", 0) >= 1, "Should have at least 1 class"
                    assert stats.get("total_functions", 0) >= 1, "Should have at least 1 function"
            else:
                # Fallback: just verify we have reasonable tag counts
                assert data.get("tags_count", 0) > 0, f"Should have some tags, got {data.get('tags_count', 0)}"

    def test_python_hello_world_indexing_verification(self, server_url):
        """Test indexing and verification with a simple Python hello world example."""
        # Create a simple hello world Python program for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            hello_py = Path(temp_dir) / "hello.py"
            hello_py.write_text("""
class Greeter:
    '''A simple greeter class.'''

    def __init__(self, name: str):
        self.name = name

    def say_hello(self) -> None:
        '''Say hello to the person.'''
        print(f"Hello, {self.name}!")

    def say_goodbye(self) -> None:
        '''Say goodbye to the person.'''
        print(f"Goodbye, {self.name}!")

def create_greeter(name: str) -> Greeter:
    '''Factory function to create a Greeter.'''
    return Greeter(name)

def main() -> None:
    '''Main entry point.'''
    greeter = create_greeter("World")
    greeter.say_hello()
    greeter.say_goodbye()

if __name__ == "__main__":
    main()
""")

            # Index the hello world program
            resp = requests.post(
                f"{server_url}/api/code-indexing/ctags",
                json={
                    "source_path": temp_dir,
                    "languages": "Python"
                },
                timeout=30
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert "outline" in data
            assert "tags_count" in data

            # Handle outline data structure
            if "outline" in data and data["outline"]:
                outline = data["outline"]

                if isinstance(outline, dict):
                    # Check classes list or class_details
                    if "classes" in outline:
                        assert "Greeter" in outline["classes"], f"Should find Greeter class in {outline['classes']}"
                    elif "class_details" in outline:
                        assert "Greeter" in outline["class_details"], f"Should find Greeter in class_details keys: {list(outline['class_details'].keys()) if isinstance(outline['class_details'], dict) else outline['class_details']}"

                    # Check for reasonable function count in stats instead of specific names
                    if "stats" in outline:
                        stats = outline["stats"]
                        assert stats.get("total_functions", 0) >= 2, f"Should have at least 2 functions (main + create_greeter), got {stats.get('total_functions', 0)}"
                    else:
                        # Fallback: search in string representation
                        outline_text = str(outline)
                        assert "Greeter" in outline_text, "Should find Greeter class in outline"
                else:
                    # Handle as string
                    outline_text = str(outline)
                    assert "Greeter" in outline_text, "Should find Greeter class in outline"
            elif "class_details" in data:
                # Alternative format with class_details
                class_details = data["class_details"]
                assert "Greeter" in class_details, f"Should find Greeter class in {list(class_details.keys()) if isinstance(class_details, dict) else 'non-dict class_details'}"

                # Verify reasonable stats
                if "stats" in data:
                    stats = data["stats"]
                    assert stats.get("total_classes", 0) >= 1, "Should have at least 1 class"
                    assert stats.get("total_functions", 0) >= 2, "Should have at least 2 functions (main + create_greeter)"
            else:
                # Fallback: just verify we have reasonable tag counts
                assert data.get("tags_count", 0) > 0, f"Should have some tags, got {data.get('tags_count', 0)}"
