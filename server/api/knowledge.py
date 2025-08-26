"""
Knowledge management API endpoints.

This module contains all API endpoints related to knowledge indexing, querying,
and collection management.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path so we can import plugins
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import base64
from starlette.requests import Request
from starlette.responses import JSONResponse

# Import the knowledge tools directly
from plugins.knowledge_indexer.tool import (
    KnowledgeIndexerTool,
    KnowledgeQueryTool,
    KnowledgeCollectionManagerTool,
)

# Import knowledge sync service
from utils.knowledge_sync import knowledge_sync_service
from utils.code_indexing.generator import run_ctags
from utils.code_indexing.tree_sitter_parser import MultiLanguageParser
from utils.code_indexing.outline import generate_outline_from_ctags
from config import env
import json
import tempfile
import shutil
import subprocess
import hashlib
from datetime import datetime

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


async def api_import_knowledge(request: Request):
    """API endpoint that delegates to the knowledge_indexer tool."""
    try:
        form = await request.form()
        files = form.getlist("files")
        collection = form.get("collection") or "default"
        overwrite = form.get("overwrite") == "true"

        if not files:
            return JSONResponse(
                {"success": False, "error": "No files uploaded."}, status_code=400
            )

        # Convert uploaded files to the format expected by the tool
        file_data = []
        for upload in files:
            filename = getattr(upload, "filename", None) or getattr(
                upload, "name", None
            )
            if not filename:
                continue

            content = await upload.read()
            # Convert binary content to base64 for the tool
            content_b64 = base64.b64encode(content).decode("utf-8")

            file_data.append(
                {"filename": filename, "content": content_b64, "encoding": "base64"}
            )

        # Execute the knowledge indexer tool
        result = await get_knowledge_indexer().execute_tool(
            {"files": file_data, "collection": collection, "overwrite": overwrite}
        )

        # Return the result with appropriate status code
        status_code = 200 if result.get("success") else 500
        return JSONResponse(result, status_code=status_code)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_list_collections(request: Request):
    """API endpoint that delegates to the knowledge_collections tool."""
    try:
        # Execute the knowledge collections tool
        result = await get_knowledge_collections().execute_tool({"action": "list"})

        if result.get("success"):
            return JSONResponse({"collections": result.get("collections", [])})
        else:
            return JSONResponse(
                {"error": result.get("error", "Unknown error")}, status_code=500
            )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_list_documents(request: Request):
    """API endpoint that delegates to the knowledge_collections tool."""
    try:
        collection = request.query_params.get("collection")
        if not collection:
            return JSONResponse(
                {"error": "Missing collection parameter."}, status_code=400
            )

        # Execute the knowledge collections tool
        result = await get_knowledge_collections().execute_tool(
            {"action": "info", "collection": collection}
        )

        if result.get("success"):
            # Convert the tool result to match the original API format
            return JSONResponse(
                {
                    "ids": [],  # Tool doesn't return IDs in the same format
                    "documents": result.get("sample_documents", []),
                    "metadatas": [],  # Tool doesn't return metadata in the same format
                    "document_count": result.get("document_count", 0),
                }
            )
        else:
            return JSONResponse(
                {"error": result.get("error", "Unknown error")}, status_code=500
            )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_query_segments(request: Request):
    """API endpoint that delegates to the knowledge_query tool."""
    try:
        collection = request.query_params.get("collection")
        query_text = request.query_params.get("query")
        try:
            limit = int(request.query_params.get("limit", 3))
        except Exception:
            limit = 3

        if not collection or not query_text:
            return JSONResponse(
                {"error": "Missing collection or query parameter."}, status_code=400
            )

        # Execute the knowledge query tool
        result = await get_knowledge_query().execute_tool(
            {"query": query_text, "collection": collection, "limit": limit}
        )

        if result.get("success"):
            # Return the results in the expected format
            results_data = result.get("results", {})
            return JSONResponse(
                {
                    "ids": results_data.get("ids", []),
                    "documents": results_data.get("documents", []),
                    "metadatas": results_data.get("metadatas", []),
                    "distances": results_data.get("distances", []),
                }
            )
        else:
            return JSONResponse(
                {"error": result.get("error", "Unknown error")}, status_code=500
            )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_delete_collection(request: Request):
    """API endpoint that delegates to the knowledge_collections tool."""
    try:
        data = await request.json()
        collection = data.get("collection")

        if not collection:
            return JSONResponse(
                {"success": False, "error": "Missing collection parameter."},
                status_code=400,
            )

        # Execute the knowledge collections tool
        result = await get_knowledge_collections().execute_tool(
            {"action": "delete", "collection": collection}
        )

        # Return the result with appropriate status code
        status_code = 200 if result.get("success") else 500
        return JSONResponse(result, status_code=status_code)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_knowledge_sync_status(request: Request):
    """Get status of knowledge sync service."""
    try:
        folder_collections = knowledge_sync_service.get_folder_collections()

        status = {
            "enabled": knowledge_sync_service.is_enabled(),
            "configured_folders": len(folder_collections),
            "folders": [
                {
                    "path": folder,
                    "collection": collection,
                    "resolved_path": str(knowledge_sync_service.resolve_folder_path(folder)) if knowledge_sync_service.resolve_folder_path(folder) else None
                }
                for folder, collection in folder_collections
            ],
            "settings": {
                "knowledge_sync_enabled": knowledge_sync_service.is_enabled(),
            }
        }

        return JSONResponse(status)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_knowledge_sync_trigger(request: Request):
    """Manually trigger knowledge sync."""
    try:
        if not knowledge_sync_service.is_enabled():
            return JSONResponse(
                {"success": False, "error": "Knowledge sync is not enabled"},
                status_code=400
            )

        # Check if reindex parameter is provided
        data = {}
        try:
            data = await request.json()
        except:
            pass  # No JSON body, use default values

        resync = data.get("resync", False)
        result = await knowledge_sync_service.run_manual_sync(resync=resync)
        status_code = 200 if result.get("success") else 500
        return JSONResponse(result, status_code=status_code)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_knowledge_sync_folder(request: Request):
    """Sync a specific folder manually."""
    try:
        data = await request.json()
        folder_path = data.get("folder_path")
        collection_name = data.get("collection_name")
        overwrite = data.get("overwrite", False)

        if not folder_path or not collection_name:
            return JSONResponse(
                {"success": False, "error": "Both folder_path and collection_name are required"},
                status_code=400
            )

        result = await knowledge_sync_service.index_folder(folder_path, collection_name, overwrite=overwrite)
        status_code = 200 if result.get("success") else 500
        return JSONResponse(result, status_code=status_code)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_code_indexing_ctags(request: Request):
    """Generate ctags and outline for a source directory."""
    try:
        data = await request.json()
        source_path = data.get("source_path")
        languages = data.get("languages", "C++,Python,JavaScript,Java")

        if not source_path:
            return JSONResponse(
                {"success": False, "error": "source_path is required"},
                status_code=400
            )

        source_dir = Path(source_path)
        if not source_dir.exists() or not source_dir.is_dir():
            return JSONResponse(
                {"success": False, "error": f"Source directory '{source_path}' does not exist or is not a directory"},
                status_code=400
            )

        # Create .code_indexing directory in server/ directory
        server_dir = Path(__file__).resolve().parent.parent  # server/api -> server
        base_indexing_dir = server_dir / ".code_indexing"
        base_indexing_dir.mkdir(exist_ok=True)

        # Create subfolder based on source path hash
        code_indexing_dir = create_indexing_subfolder(base_indexing_dir, source_path)

        # Check if this is a git repository and get tracked files
        is_git_repo = is_git_repository(source_dir)
        git_tracked_files = None
        git_info = {"is_git_repo": is_git_repo, "tracked_files_count": 0, "path_hash": get_path_hash(source_path)}

        if is_git_repo:
            git_tracked_files = get_git_tracked_files(source_dir)
            git_info["tracked_files_count"] = len(git_tracked_files)

        # Generate ctags
        tags_file = code_indexing_dir / "tags.json"
        outline_file = code_indexing_dir / "outline.json"

        # Remove existing files to avoid ctags refusing to overwrite
        if tags_file.exists():
            tags_file.unlink()
        if outline_file.exists():
            outline_file.unlink()

        # For ctags, if it's a git repo, we need to create a file list of only tracked files
        if is_git_repo and git_tracked_files:
            # Create a temporary file with list of git-tracked files for ctags
            tracked_files_list = code_indexing_dir / "git_tracked_files.txt"
            try:
                valid_files = []
                with open(tracked_files_list, 'w') as f:
                    for file_path in git_tracked_files:
                        # Only include files that exist, are readable, and have supported extensions
                        full_path = source_dir / file_path
                        if full_path.exists() and full_path.is_file():
                            try:
                                # Test if file is readable
                                with open(full_path, 'r', encoding='utf-8', errors='ignore') as test_file:
                                    test_file.read(1)  # Try to read first character
                                # Write relative path since ctags will run from source directory
                                f.write(f"{file_path}\n")
                                valid_files.append(file_path)
                            except (PermissionError, OSError) as e:
                                print(f"Skipping unreadable file {full_path}: {e}")
                                continue

                print(f"Created file list with {len(valid_files)} files for ctags")

                # Only run ctags if we have files to process
                if valid_files:
                    # Generate ctags with file list using absolute paths (no working directory change)
                    exit_code = run_ctags(
                        source_dir=str(source_dir),
                        output_file=str(tags_file),
                        languages=languages,
                        additional_args=["-L", str(tracked_files_list)]
                    )
                else:
                    print("No valid files found for ctags processing")
                    # Create empty tags file
                    tags_file.touch()
                    exit_code = 0

            finally:
                # Clean up temporary file
                tracked_files_list.unlink(missing_ok=True)
        else:
            # Generate ctags normally (all files) using absolute paths
            exit_code = run_ctags(
                source_dir=str(source_dir),
                output_file=str(tags_file),
                languages=languages
            )

        if exit_code != 0:
            return JSONResponse(
                {
                    "success": False, 
                    "error": f"ctags generation failed with exit code {exit_code}",
                    "git_info": git_info,
                    "output_files": {
                        "tags": str(tags_file),
                        "outline": str(outline_file),
                        "base_dir": str(base_indexing_dir),
                        "subfolder": str(code_indexing_dir)
                    }
                },
                status_code=500
            )

        # Generate outline
        outline_data = None
        try:
            if tags_file.exists() and tags_file.stat().st_size > 0:
                outline_data = generate_outline_from_ctags(str(tags_file))
                with open(outline_file, 'w') as f:
                    json.dump(outline_data, f, indent=2)
            else:
                # Create empty outline for empty tags file
                outline_data = {"classes": [], "text_outline": "", "plantuml_outline": "", "stats": {"total_classes": 0, "total_functions": 0, "total_members": 0, "total_tags": 0}}
                with open(outline_file, 'w') as f:
                    json.dump(outline_data, f, indent=2)
        except Exception as e:
            print(f"Outline generation failed: {str(e)}")
            # Create minimal outline data
            outline_data = {"error": f"Outline generation failed: {str(e)}", "classes": [], "text_outline": "", "plantuml_outline": "", "stats": {"total_classes": 0, "total_functions": 0, "total_members": 0, "total_tags": 0}}
            with open(outline_file, 'w') as f:
                json.dump(outline_data, f, indent=2)

        # Read and return the results
        tags_data = []
        try:
            if tags_file.exists() and tags_file.stat().st_size > 0:
                with open(tags_file, 'r') as f:
                    tags_data = [json.loads(line) for line in f if line.strip()]
        except Exception as e:
            print(f"Failed to read tags file: {str(e)}")
            tags_data = []

        return JSONResponse({
            "success": True,
            "tags_count": len(tags_data),
            "outline": outline_data,
            "git_info": git_info,
            "output_files": {
                "tags": str(tags_file),
                "outline": str(outline_file),
                "base_dir": str(base_indexing_dir),
                "subfolder": str(code_indexing_dir)
            }
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_code_indexing_tree_sitter(request: Request):
    """Parse source code using tree-sitter for multiple languages."""
    try:
        data = await request.json()
        source_path = data.get("source_path")

        if not source_path:
            return JSONResponse(
                {"success": False, "error": "source_path is required"},
                status_code=400
            )

        source_dir = Path(source_path)
        if not source_dir.exists() or not source_dir.is_dir():
            return JSONResponse(
                {"success": False, "error": f"Source directory '{source_path}' does not exist or is not a directory"},
                status_code=400
            )

        # Create .code_indexing directory in server/ directory
        server_dir = Path(__file__).resolve().parent.parent  # server/api -> server
        base_indexing_dir = server_dir / ".code_indexing"
        base_indexing_dir.mkdir(exist_ok=True)

        # Create subfolder based on source path hash
        code_indexing_dir = create_indexing_subfolder(base_indexing_dir, source_path)

        # Check if this is a git repository and get tracked files
        is_git_repo = is_git_repository(source_dir)
        git_tracked_files = None
        git_info = {"is_git_repo": is_git_repo, "tracked_files_count": 0, "path_hash": get_path_hash(source_path)}

        if is_git_repo:
            git_tracked_files = get_git_tracked_files(source_dir)
            git_info["tracked_files_count"] = len(git_tracked_files)

        # Initialize parser
        parser = MultiLanguageParser()

        # Parse all supported files in the directory
        supported_extensions = {
            '.py': 'python',
            '.cpp': 'cpp', '.cxx': 'cpp', '.cc': 'cpp', '.c': 'cpp',
            '.h': 'cpp', '.hpp': 'cpp', '.hxx': 'cpp',
            '.js': 'javascript', '.jsx': 'javascript', '.ts': 'javascript',
            '.java': 'java'
        }

        parsed_files = []
        total_functions = 0
        total_classes = 0
        skipped_files = 0

        for file_path in source_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in supported_extensions:
                # Check if file should be indexed based on git status
                if not should_index_file(file_path, source_dir, git_tracked_files):
                    skipped_files += 1
                    continue

                try:
                    language = supported_extensions[file_path.suffix]
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    analysis = parser.analyze_code(content, language)
                    analysis['file_path'] = str(file_path.relative_to(source_dir))
                    analysis['language'] = language

                    parsed_files.append(analysis)
                    total_functions += len(analysis.get('functions', []))
                    total_classes += len(analysis.get('classes', []))

                except Exception as e:
                    # Log error but continue with other files
                    print(f"Error parsing {file_path}: {e}")
                    continue

        # Update git info with processing stats
        git_info["processed_files"] = len(parsed_files)
        git_info["skipped_files"] = skipped_files

        # Save results
        results_file = code_indexing_dir / "tree_sitter_analysis.json"
        with open(results_file, 'w') as f:
            json.dump(parsed_files, f, indent=2)

        return JSONResponse({
            "success": True,
            "parsed_files_count": len(parsed_files),
            "total_functions": total_functions,
            "total_classes": total_classes,
            "git_info": git_info,
            "results": parsed_files,
            "output_files": {
                "tree_sitter": str(results_file),
                "base_dir": str(base_indexing_dir),
                "subfolder": str(code_indexing_dir)
            }
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_code_viewer_paths(request: Request):
    """Get all available indexed code paths."""
    try:
        server_dir = Path(__file__).resolve().parent.parent  # server/api -> server
        base_indexing_dir = server_dir / ".code_indexing"

        if not base_indexing_dir.exists():
            return JSONResponse({
                "success": True,
                "paths": []
            })

        paths = []

        # Scan all subdirectories for indexed paths
        for subfolder in base_indexing_dir.iterdir():
            if subfolder.is_dir():
                meta_file = subfolder / "meta.txt"
                if meta_file.exists():
                    try:
                        # Read meta.txt to get original path info
                        with open(meta_file, 'r') as f:
                            meta_content = f.read()

                        # Parse meta.txt content
                        original_path = None
                        path_hash = None
                        created = None

                        for line in meta_content.split('\n'):
                            if line.startswith('Original Path: '):
                                original_path = line[15:].strip()
                            elif line.startswith('Path Hash: '):
                                path_hash = line[11:].strip()
                            elif line.startswith('Created: '):
                                created = line[9:].strip()

                        if original_path and path_hash:
                            paths.append({
                                "original_path": original_path,
                                "hash": path_hash,
                                "created": created,
                                "subfolder": str(subfolder)
                            })
                    except Exception as e:
                        print(f"Error reading meta file {meta_file}: {e}")
                        continue

        # Sort paths by creation date (newest first)
        paths.sort(key=lambda x: x.get("created", ""), reverse=True)

        return JSONResponse({
            "success": True,
            "paths": paths
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_code_viewer_classes(request: Request):
    """Get class definitions with file path information for a specific indexed path."""
    try:
        path_parts = request.url.path.split('/')
        if len(path_parts) < 4:
            return JSONResponse(
                {"success": False, "error": "Path hash is required"},
                status_code=400
            )

        path_hash = path_parts[-1]  # Last part of the URL path

        server_dir = Path(__file__).resolve().parent.parent  # server/api -> server
        base_indexing_dir = server_dir / ".code_indexing"
        code_indexing_dir = base_indexing_dir / path_hash

        if not code_indexing_dir.exists():
            return JSONResponse(
                {"success": False, "error": f"No indexed data found for hash: {path_hash}"},
                status_code=404
            )

        class_info_list = []

        # Get the original source path from meta.txt
        original_source_path = None
        meta_file = code_indexing_dir / "meta.txt"
        if meta_file.exists():
            try:
                with open(meta_file, 'r') as f:
                    meta_content = f.read()
                for line in meta_content.split('\n'):
                    if line.startswith('Original Path: '):
                        original_source_path = line[15:].strip()
                        break
            except Exception as e:
                print(f"Error reading meta.txt: {e}")

        # Try to read from tags.json first (from ctags) - this has the most detailed info
        tags_file = code_indexing_dir / "tags.json"
        if tags_file.exists():
            try:
                with open(tags_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            tag_data = json.loads(line)

                            # Look for class definitions
                            if (tag_data.get("_type") == "tag" and
                                tag_data.get("kind") == "class"):

                                class_name = tag_data.get("name", "")
                                file_path = tag_data.get("path", "")
                                line_number = tag_data.get("line", 0)

                                # Make file path relative to original source if possible
                                relative_path = file_path
                                if original_source_path and file_path.startswith(original_source_path):
                                    relative_path = file_path[len(original_source_path):].lstrip('/')

                                class_info_list.append({
                                    "name": class_name,
                                    "file_path": relative_path,
                                    "full_path": file_path,
                                    "line": line_number,
                                    "source": "ctags",
                                    "members": []  # Will be populated in second pass
                                })
                        except json.JSONDecodeError:
                            # Skip invalid JSON lines
                            continue
            except Exception as e:
                print(f"Error reading tags.json: {e}")

        # Second pass: collect members for each class
        if class_info_list and tags_file.exists():
            try:
                class_lookup = {cls["name"]: cls for cls in class_info_list}

                with open(tags_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            tag_data = json.loads(line)

                            # Look for class members (methods, variables)
                            if (tag_data.get("_type") == "tag" and
                                tag_data.get("kind") in ["member", "method", "function", "variable"] and
                                tag_data.get("scope") in class_lookup):

                                scope_class = tag_data.get("scope")
                                member_name = tag_data.get("name", "")
                                member_kind = tag_data.get("kind", "")
                                signature = tag_data.get("signature", "")
                                access = tag_data.get("access", "public")

                                # Skip some internal/private members to keep UML clean
                                if not member_name.startswith("__") or member_name in ["__init__", "__del__", "__enter__", "__exit__"]:
                                    class_lookup[scope_class]["members"].append({
                                        "name": member_name,
                                        "kind": member_kind,
                                        "signature": signature,
                                        "access": access
                                    })
                        except json.JSONDecodeError:
                            continue

                # Sort members by kind (methods first, then variables) and name
                for class_info in class_info_list:
                    class_info["members"].sort(key=lambda m: (
                        0 if m["kind"] in ["member", "method", "function"] else 1,
                        m["name"]
                    ))

            except Exception as e:
                print(f"Error reading class members from tags.json: {e}")

        # If no classes from tags, try outline.json (from ctags outline generation)
        if not class_info_list:
            outline_file = code_indexing_dir / "outline.json"
            if outline_file.exists():
                try:
                    with open(outline_file, 'r') as f:
                        outline_data = json.load(f)

                    # Extract classes from outline data
                    if isinstance(outline_data, dict) and "classes" in outline_data:
                        classes = outline_data["classes"]
                        for class_name in classes:
                            class_info_list.append({
                                "name": class_name,
                                "file_path": "Unknown",
                                "full_path": "Unknown",
                                "line": 0,
                                "source": "outline",
                                "members": []
                            })
                except Exception as e:
                    print(f"Error reading outline.json: {e}")

        # If still no classes, try tree-sitter analysis
        if not class_info_list:
            tree_sitter_file = code_indexing_dir / "tree_sitter_analysis.json"
            if tree_sitter_file.exists():
                try:
                    with open(tree_sitter_file, 'r') as f:
                        tree_sitter_data = json.load(f)

                    # Extract class names from tree-sitter analysis
                    for file_analysis in tree_sitter_data:
                        file_path = file_analysis.get("file_path", "Unknown")

                        if "classes" in file_analysis:
                            for class_info in file_analysis["classes"]:
                                class_name = ""
                                line_number = 0

                                if isinstance(class_info, dict):
                                    class_name = class_info.get("name", "")
                                    line_number = class_info.get("line", 0)
                                elif isinstance(class_info, str):
                                    class_name = class_info

                                if class_name:
                                    class_info_list.append({
                                        "name": class_name,
                                        "file_path": file_path,
                                        "full_path": file_path,
                                        "line": line_number,
                                        "source": "tree-sitter",
                                        "members": []
                                    })
                except Exception as e:
                    print(f"Error reading tree_sitter_analysis.json: {e}")

        # Remove duplicates based on name and file_path, then sort
        seen = set()
        unique_classes = []
        for class_info in class_info_list:
            key = (class_info["name"], class_info["file_path"])
            if key not in seen:
                seen.add(key)
                unique_classes.append(class_info)

        # Sort by class name
        unique_classes.sort(key=lambda x: x["name"].lower())

        return JSONResponse({
            "success": True,
            "classes": unique_classes,
            "total_count": len(unique_classes),
            "original_path": original_source_path
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
