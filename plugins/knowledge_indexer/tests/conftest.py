"""Pytest configuration for knowledge indexer plugin tests."""

import sys
import os
from pathlib import Path

# Add the project root to the Python path so we can import modules
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Set up environment variables for testing
os.environ.setdefault("MCP_REGISTER_CODE_TOOLS", "true")
os.environ.setdefault(
    "MCP_REGISTER_YAML_TOOLS", "false"
)  # Disable YAML tools for simpler testing


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running (deselect with '-m \"not slow\"')"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark integration tests based on file name."""
    for item in items:
        # Mark tests in test_integration.py as integration tests
        if "test_integration" in item.fspath.basename:
            item.add_marker("integration")
        
        # Mark tests with @pytest.mark.slow as slow
        if item.get_closest_marker("slow"):
            item.add_marker("slow")
