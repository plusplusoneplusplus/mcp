"""
Shared utilities and base classes for the API modules.

This module contains common imports, tool instance getters, and utility functions
used across all API modules.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path so we can import plugins
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tempfile
import shutil
import base64
import time
import psutil
import json
import datetime
import csv
import io
from typing import Dict, List, Any, Optional, Union
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route
from utils.vector_store.markdown_segmenter import MarkdownSegmenter
from utils.vector_store.vector_store import ChromaVectorStore

# Import the knowledge tools directly
from plugins.knowledge_indexer.tool import (
    KnowledgeIndexerTool,
    KnowledgeQueryTool,
    KnowledgeCollectionManagerTool,
)
from config import env

# Vector store path constant for backward compatibility
PERSIST_DIR = env.get_vector_store_path()

# Global tool instances (lazy initialized)
_knowledge_indexer = None
_knowledge_query = None
_knowledge_collections = None
_command_executor = None


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


def get_command_executor():
    """Get or create the command executor instance."""
    global _command_executor
    if _command_executor is None:
        from mcp_tools.dependency import injector
        _command_executor = injector.get_tool_instance("command_executor")
    return _command_executor


def get_tool_history_directory() -> Optional[Path]:
    """Get the tool history directory path if tool history is enabled."""
    if not env.is_tool_history_enabled():
        return None
    
    base_path = env.get_tool_history_path()
    if not os.path.isabs(base_path):
        current_dir = Path(__file__).resolve().parent.parent
        base_path = current_dir / base_path
    
    history_dir = Path(base_path)
    if history_dir.exists() and history_dir.is_dir():
        return history_dir
    return None


def parse_invocation_id(dir_name: str) -> Optional[Dict[str, Any]]:
    """Parse invocation ID from directory name format: YYYY-MM-DD_HH-MM-SS_microseconds_toolname"""
    try:
        parts = dir_name.split('_')
        if len(parts) >= 4:
            date_part = parts[0]
            time_part = parts[1] + '_' + parts[2]
            microseconds = parts[3]
            tool_name = '_'.join(parts[4:]) if len(parts) > 4 else 'unknown'
            
            # Parse the timestamp
            timestamp_str = f"{date_part}_{time_part}"
            timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S_%f")
            
            return {
                "invocation_id": dir_name,
                "timestamp": timestamp,
                "tool_name": tool_name
            }
    except Exception:
        pass
    return None


def read_tool_history_record(invocation_dir: Path) -> Optional[Dict[str, Any]]:
    """Read tool history record from an invocation directory."""
    record_file = invocation_dir / "record.jsonl"
    if not record_file.exists():
        return None
    
    try:
        with open(record_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    except Exception:
        pass
    return None 