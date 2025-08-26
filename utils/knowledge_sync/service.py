"""
Knowledge Sync Service for MCP.

This module provides manual knowledge synchronization of predefined folders into the vector store
via web interface controls.
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
import threading
import time

from config import env
from plugins.knowledge_indexer.tool import KnowledgeIndexerTool


class KnowledgeSyncService:
    """Service for synchronizing knowledge folders to vector store via web interface."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.indexer_tool = KnowledgeIndexerTool()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="knowledge_sync")

    def is_enabled(self) -> bool:
        """Check if knowledge sync is enabled."""
        return env.get_setting("knowledge_sync_enabled", False)

    def get_folder_collections(self) -> List[Tuple[str, str]]:
        """Parse and return list of (folder_path, collection_name) tuples."""
        folders_str = (env.get_setting("knowledge_sync_folders", "") or "").strip()
        collections_str = (env.get_setting("knowledge_sync_collections", "") or "").strip()

        if not folders_str:
            return []

        # Parse comma-separated values
        folders = [f.strip() for f in folders_str.split(",") if f.strip()]
        collections = [c.strip() for c in collections_str.split(",") if c.strip()]

        # If collections not specified, use folder names as collection names
        if not collections:
            collections = [Path(folder).name for folder in folders]

        # Ensure equal number of folders and collections
        if len(folders) != len(collections):
            self.logger.warning(
                f"Mismatch between folder count ({len(folders)}) and collection count ({len(collections)}). "
                f"Using folder names as collections."
            )
            collections = [Path(folder).name for folder in folders]

        return list(zip(folders, collections))

    def resolve_folder_path(self, folder_path: str) -> Optional[Path]:
        """Resolve folder path to absolute path."""
        path = Path(folder_path)

        # If already absolute, return as-is
        if path.is_absolute():
            return path if path.exists() else None

        # Try relative to git root
        git_root = env.get_git_root()
        if git_root:
            git_relative = Path(git_root) / path
            if git_relative.exists():
                return git_relative

        # Try relative to current working directory
        cwd_relative = Path.cwd() / path
        if cwd_relative.exists():
            return cwd_relative

        return None

    def collect_markdown_files(self, folder_path: Path) -> List[Dict[str, Any]]:
        """Collect all markdown files from a folder recursively."""
        markdown_files = []

        try:
            for md_file in folder_path.rglob("*.md"):
                if md_file.is_file():
                    try:
                        with open(md_file, "r", encoding="utf-8") as f:
                            content = f.read()

                        # Get relative path from the indexed folder
                        rel_path = md_file.relative_to(folder_path)

                        # Use forward slashes for cross-platform consistency
                        filename = str(rel_path).replace("\\", "/")

                        markdown_files.append({
                            "filename": filename,
                            "content": content,
                            "encoding": "utf-8"
                        })
                    except Exception as e:
                        self.logger.warning(f"Failed to read file {md_file}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to scan folder {folder_path}: {e}")

        return markdown_files

    async def index_folder(self, folder_path: str, collection_name: str, overwrite: bool = False) -> Dict[str, Any]:
        """Index a single folder into a collection."""
        self.logger.info(f"Starting indexing of folder '{folder_path}' into collection '{collection_name}' (overwrite={overwrite})")

        # Resolve folder path
        resolved_path = self.resolve_folder_path(folder_path)
        if not resolved_path:
            error_msg = f"Folder not found: {folder_path}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg, "folder": folder_path, "collection": collection_name}

        # Collect markdown files
        markdown_files = self.collect_markdown_files(resolved_path)
        if not markdown_files:
            warning_msg = f"No markdown files found in folder: {folder_path}"
            self.logger.warning(warning_msg)
            return {"success": True, "warning": warning_msg, "folder": folder_path, "collection": collection_name, "imported_files": 0, "resolved_path": str(resolved_path)}

        # Prepare indexing arguments
        indexer_args = {
            "files": markdown_files,
            "collection": collection_name,
            "overwrite": overwrite
        }

        try:
            # Execute indexing
            result = await self.indexer_tool.execute_tool(indexer_args)
            result["folder"] = folder_path
            result["collection"] = collection_name
            result["resolved_path"] = str(resolved_path)
            return result
        except Exception as e:
            error_msg = f"Failed to index folder '{folder_path}': {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg, "folder": folder_path, "collection": collection_name}

    async def run_manual_sync(self, resync: bool = False) -> Dict[str, Any]:
        """Run manual knowledge sync for all configured folders."""
        if not self.is_enabled():
            return {"success": False, "error": "Knowledge sync is not enabled"}

        folder_collections = self.get_folder_collections()
        if not folder_collections:
            return {"success": False, "error": "No folders configured for sync"}

        action = "re-syncing" if resync else "syncing"
        self.logger.info(f"Starting manual {action} for {len(folder_collections)} folders")

        results = []
        total_imported = 0
        total_errors = 0

        for folder_path, collection_name in folder_collections:
            try:
                result = await self.index_folder(folder_path, collection_name, overwrite=resync)
                results.append(result)

                if result.get("success", False):
                    imported_count = result.get("imported_files", 0)
                    total_imported += imported_count
                    self.logger.info(f"Successfully indexed {imported_count} files from '{folder_path}'")
                else:
                    total_errors += 1
                    self.logger.error(f"Failed to index folder '{folder_path}': {result.get('error', 'Unknown error')}")

            except Exception as e:
                error_msg = f"Unexpected error indexing folder '{folder_path}': {str(e)}"
                self.logger.error(error_msg)
                results.append({"success": False, "error": error_msg, "folder": folder_path, "collection": collection_name})
                total_errors += 1

        summary = {
            "success": total_errors == 0,
            "action": action,
            "resync": resync,
            "total_folders": len(folder_collections),
            "successful_folders": len(folder_collections) - total_errors,
            "failed_folders": total_errors,
            "total_imported_files": total_imported,
            "results": results
        }

        if summary["success"]:
            self.logger.info(f"Manual {action} completed successfully: {total_imported} files synced from {len(folder_collections)} folders")
        else:
            self.logger.warning(f"Manual {action} completed with {total_errors} errors: {total_imported} files synced from {summary['successful_folders']} folders")

        return summary

    async def start_knowledge_sync_service(self):
        """Initialize the knowledge sync service."""
        if not self.is_enabled():
            self.logger.info("Knowledge sync service disabled")
            return

        self.logger.info("Knowledge sync service initialized")

    def shutdown(self):
        """Shutdown the knowledge sync service."""
        self.logger.info("Shutting down knowledge sync service")

        try:
            self._executor.shutdown(wait=True, timeout=30)
        except Exception as e:
            self.logger.warning(f"Error shutting down executor: {e}")


# Global service instance
knowledge_sync_service = KnowledgeSyncService()
