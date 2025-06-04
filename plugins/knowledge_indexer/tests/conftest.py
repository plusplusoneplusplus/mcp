"""Pytest configuration for knowledge indexer plugin tests."""

import sys
import os
from pathlib import Path

# Add the project root to the Python path so we can import modules
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Set up environment variables for testing
os.environ.setdefault("MCP_REGISTER_CODE_TOOLS", "true")
os.environ.setdefault("MCP_REGISTER_YAML_TOOLS", "false")  # Disable YAML tools for simpler testing 