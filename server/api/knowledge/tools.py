"""
Knowledge tool management and utility functions.

This module contains tool instance management and utility functions
for the knowledge management system.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path so we can import plugins
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import subprocess
import hashlib
from datetime import datetime

# Import the knowledge tools directly
from plugins.knowledge_indexer.tool import (
    KnowledgeIndexerTool,
    KnowledgeQueryTool,
    KnowledgeCollectionManagerTool,
)

# Global tool instances (lazy initialized)
_knowledge_indexer = None
_knowledge_query = None
_knowledge_collections = None


def get_knowledge_indexer():
    """Get or create the knowledge indexer tool instance."""
    global _knowledge_indexer
    if _knowledge_indexer is None:
        _knowledge_indexer = KnowledgeIndexerTool()
    return _knowledge_indexer


def get_knowledge_query():
    """Get or create the knowledge query tool instance."""
    global _knowledge_query
    if _knowledge_query is None:
        _knowledge_query = KnowledgeQueryTool()
    return _knowledge_query


def get_knowledge_collections():
    """Get or create the knowledge collections tool instance."""
    global _knowledge_collections
    if _knowledge_collections is None:
        _knowledge_collections = KnowledgeCollectionManagerTool()
    return _knowledge_collections


def is_git_repository(directory: Path) -> bool:
    """Check if a directory is under git version control."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def get_git_tracked_files(directory: Path) -> set:
    """Get set of git-tracked files relative to the directory."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            # Return set of relative paths
            return set(line.strip() for line in result.stdout.splitlines() if line.strip())
        return set()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return set()


def should_index_file(file_path: Path, source_dir: Path, git_tracked_files: set = None) -> bool:
    """Determine if a file should be indexed based on git tracking status."""
    try:
        relative_path = file_path.relative_to(source_dir)
        relative_path_str = str(relative_path)

        # If we have git tracked files list, only include tracked files
        if git_tracked_files is not None:
            return relative_path_str in git_tracked_files

        # If not a git repo, include all files
        return True
    except ValueError:
        # File is not under source_dir
        return False


def get_path_hash(path: str) -> str:
    """Generate a hash for the given path."""
    return hashlib.sha256(path.encode('utf-8')).hexdigest()[:16]


def create_indexing_subfolder(base_dir: Path, source_path: str) -> Path:
    """Create a hash-based subfolder for indexing results."""
    path_hash = get_path_hash(source_path)
    subfolder = base_dir / path_hash
    subfolder.mkdir(exist_ok=True)

    # Create meta.txt with original path info
    meta_file = subfolder / "meta.txt"
    with open(meta_file, 'w') as f:
        f.write(f"Original Path: {source_path}\n")
        f.write(f"Path Hash: {path_hash}\n")
        f.write(f"Created: {datetime.now().isoformat()}\n")

    return subfolder
