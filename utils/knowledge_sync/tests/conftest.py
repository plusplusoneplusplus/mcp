"""
Pytest configuration and shared fixtures for knowledge sync tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace with test files."""
    temp_dir = tempfile.mkdtemp(prefix="knowledge_sync_test_")

    # Create directory structure
    docs_dir = Path(temp_dir) / "docs"
    docs_dir.mkdir()

    reports_dir = Path(temp_dir) / "reports"
    reports_dir.mkdir()

    # Copy fixture files
    fixtures_dir = Path(__file__).parent / "fixtures"
    shutil.copy2(fixtures_dir / "sample_doc.md", docs_dir / "readme.md")
    shutil.copy2(fixtures_dir / "api_reference.md", docs_dir / "api.md")
    shutil.copy2(fixtures_dir / "empty_file.md", reports_dir / "empty.md")

    # Create subdirectory with markdown
    advanced_dir = docs_dir / "guides"
    advanced_dir.mkdir()
    (advanced_dir / "advanced.md").write_text("# Advanced Guide\nAdvanced topics here.")

    # Create non-markdown files (should be ignored)
    (docs_dir / "config.json").write_text('{"test": true}')
    (docs_dir / "image.png").write_bytes(b"PNG fake data")

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def mock_env():
    """Mock environment configuration."""
    mock = Mock()
    mock.get_setting.return_value = False
    mock.get_git_root.return_value = None
    return mock

@pytest.fixture
def mock_indexer_tool():
    """Mock knowledge indexer tool."""
    mock = Mock()
    mock.execute_tool = AsyncMock(return_value={
        "success": True,
        "imported_files": 2,
        "total_segments": 5,
        "processed_files": [
            {"filename": "readme.md", "segments": 3},
            {"filename": "api.md", "segments": 2}
        ]
    })
    return mock

@pytest.fixture
def enabled_config():
    """Configuration fixture for enabled knowledge sync."""
    return {
        "knowledge_sync_enabled": True,
        "knowledge_sync_folders": "./docs,./reports",
        "knowledge_sync_collections": "documentation,reports"
    }

@pytest.fixture
def disabled_config():
    """Configuration fixture for disabled knowledge sync."""
    return {
        "knowledge_sync_enabled": False,
        "knowledge_sync_folders": "",
        "knowledge_sync_collections": ""
    }
