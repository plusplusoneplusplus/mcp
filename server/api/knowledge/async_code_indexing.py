"""
Async code indexing API endpoints with status reporting.

This module provides asynchronous code indexing endpoints that show
what step is currently running during the indexing process.
"""

import json
import asyncio
import threading
import time
from pathlib import Path
from starlette.requests import Request
from starlette.responses import JSONResponse

# Import existing indexing functions
from utils.code_indexing.generator import run_ctags
from utils.code_indexing.tree_sitter_parser import MultiLanguageParser
from utils.code_indexing.outline import generate_outline_from_ctags

from .tools import (
    is_git_repository,
    get_git_tracked_files,
    should_index_file,
    create_indexing_subfolder,
    get_path_hash
)


class SimpleStatusTracker:
    """Simple status tracker for code indexing operations."""

    def __init__(self, token: str):
        self.token = token
        self.status = "starting"
        self.message = "Initializing..."
        self.start_time = time.time()
        self.lock = threading.Lock()

    def update(self, status: str, message: str):
        """Update status information."""
        with self.lock:
            self.status = status
            self.message = message

    def get_status(self) -> dict:
        """Get current status."""
        with self.lock:
            runtime = time.time() - self.start_time
            return {
                "token": self.token,
                "status": self.status,
                "message": self.message,
                "runtime": runtime,
                "start_time": self.start_time
            }


# Global status tracker storage
status_trackers = {}


async def run_ctags_indexing_async(source_path: str, languages: str, tracker: SimpleStatusTracker):
    """Run CTags indexing with status updates."""
    try:
        tracker.update("running", "Initializing CTags indexing...")
        await asyncio.sleep(0.1)  # Allow status update to be visible

        source_dir = Path(source_path)

        # Create .code_indexing directory
        tracker.update("running", "Setting up output directories...")
        server_dir = Path(__file__).resolve().parent.parent.parent
        base_indexing_dir = server_dir / ".code_indexing"
        base_indexing_dir.mkdir(exist_ok=True)

        # Create subfolder
        code_indexing_dir = create_indexing_subfolder(base_indexing_dir, source_path)

        # Git repository check
        tracker.update("running", "Checking git repository status...")
        is_git_repo = is_git_repository(source_dir)
        git_tracked_files = None
        git_info = {"is_git_repo": is_git_repo, "tracked_files_count": 0, "path_hash": get_path_hash(source_path)}

        if is_git_repo:
            tracker.update("running", "Getting git tracked files...")
            git_tracked_files = get_git_tracked_files(source_dir)
            git_info["tracked_files_count"] = len(git_tracked_files)

        # Generate ctags
        tags_file = code_indexing_dir / "tags.json"
        outline_file = code_indexing_dir / "outline.json"

        # Remove existing files
        if tags_file.exists():
            tags_file.unlink()
        if outline_file.exists():
            outline_file.unlink()

        # Process git tracked files if needed
        additional_args = None
        tracked_files_list = None
        if is_git_repo and git_tracked_files:
            tracker.update("running", "Preparing git tracked files list...")
            tracked_files_list = code_indexing_dir / "git_tracked_files.txt"

            valid_files = []
            with open(tracked_files_list, 'w') as f:
                for file_path in git_tracked_files:
                    full_path = source_dir / file_path
                    if full_path.exists() and full_path.is_file():
                        try:
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as test_file:
                                test_file.read(1)
                            f.write(f"{file_path}\n")
                            valid_files.append(file_path)
                        except (PermissionError, OSError):
                            continue

            if valid_files:
                additional_args = ["-L", str(tracked_files_list)]
                tracker.update("running", f"Running CTags on {len(valid_files)} git-tracked files...")
            else:
                tracker.update("failed", "No valid files found for processing")
                return {"success": False, "error": "No valid files found"}
        else:
            tracker.update("running", "Running CTags on all source files...")

        # Run CTags
        exit_code = run_ctags(
            str(source_dir), str(tags_file), languages, additional_args
        )

        # Clean up temporary file
        if tracked_files_list and tracked_files_list.exists():
            tracked_files_list.unlink()

        if exit_code != 0:
            tracker.update("failed", f"CTags generation failed with exit code {exit_code}")
            return {
                "success": False,
                "error": f"ctags generation failed with exit code {exit_code}",
                "git_info": git_info,
                "output_files": {
                    "tags": str(tags_file),
                    "outline": str(outline_file),
                    "base_dir": str(base_indexing_dir),
                    "subfolder": str(code_indexing_dir)
                }
            }

        # CTags completed successfully
        tracker.update("running", "CTags generation completed successfully! Now generating code outline...")
        await asyncio.sleep(0.1)  # Allow status update to be visible

        # Generate outline
        outline_data = None
        try:
            if tags_file.exists() and tags_file.stat().st_size > 0:
                outline_data = generate_outline_from_ctags(str(tags_file))
                with open(outline_file, 'w') as f:
                    json.dump(outline_data, f, indent=2)
            else:
                outline_data = {
                    "classes": [],
                    "text_outline": "",
                    "plantuml_outline": "",
                    "stats": {"total_classes": 0, "total_functions": 0, "total_members": 0, "total_tags": 0}
                }
                with open(outline_file, 'w') as f:
                    json.dump(outline_data, f, indent=2)
        except Exception as e:
            print(f"Outline generation failed: {str(e)}")
            outline_data = {
                "error": f"Outline generation failed: {str(e)}",
                "classes": [],
                "text_outline": "",
                "plantuml_outline": "",
                "stats": {"total_classes": 0, "total_functions": 0, "total_members": 0, "total_tags": 0}
            }
            with open(outline_file, 'w') as f:
                json.dump(outline_data, f, indent=2)

        # Outline generation completed
        tracker.update("running", "Code outline generated successfully! Reading and preparing final results...")
        await asyncio.sleep(0.1)  # Allow status update to be visible

        # Read and return results
        tags_data = []
        try:
            if tags_file.exists() and tags_file.stat().st_size > 0:
                with open(tags_file, 'r') as f:
                    tags_data = [json.loads(line) for line in f if line.strip()]
        except Exception as e:
            print(f"Failed to read tags file: {str(e)}")
            tags_data = []

        result = {
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
        }

        tracker.update("completed", f"CTags indexing completed! Generated {len(tags_data)} tags.")
        return result

    except Exception as e:
        tracker.update("failed", f"Indexing failed: {str(e)}")
        return {"success": False, "error": str(e)}


async def run_tree_sitter_indexing_async(source_path: str, tracker: SimpleStatusTracker):
    """Run Tree-sitter indexing with status updates."""
    try:
        tracker.update("running", "Initializing Tree-sitter indexing...")
        await asyncio.sleep(0.1)  # Allow status update to be visible

        source_dir = Path(source_path)

        # Create .code_indexing directory
        tracker.update("running", "Setting up output directories...")
        server_dir = Path(__file__).resolve().parent.parent.parent
        base_indexing_dir = server_dir / ".code_indexing"
        base_indexing_dir.mkdir(exist_ok=True)

        # Create subfolder
        code_indexing_dir = create_indexing_subfolder(base_indexing_dir, source_path)

        # Git repository check
        tracker.update("running", "Checking git repository status...")
        is_git_repo = is_git_repository(source_dir)
        git_tracked_files = None
        git_info = {"is_git_repo": is_git_repo, "tracked_files_count": 0, "path_hash": get_path_hash(source_path)}

        if is_git_repo:
            tracker.update("running", "Getting git tracked files...")
            git_tracked_files = get_git_tracked_files(source_dir)
            git_info["tracked_files_count"] = len(git_tracked_files)

        # Initialize parser
        tracker.update("running", "Initializing Tree-sitter parser...")
        parser = MultiLanguageParser()

        # Supported extensions
        supported_extensions = {
            '.py': 'python',
            '.cpp': 'cpp', '.cxx': 'cpp', '.cc': 'cpp', '.c': 'cpp',
            '.h': 'cpp', '.hpp': 'cpp', '.hxx': 'cpp',
            '.js': 'javascript', '.jsx': 'javascript', '.ts': 'javascript',
            '.java': 'java'
        }

        # Collect files to process
        tracker.update("running", "Scanning for source files...")
        all_files = []
        for file_path in source_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in supported_extensions:
                if should_index_file(file_path, source_dir, git_tracked_files):
                    all_files.append(file_path)

        tracker.update("running", f"Parsing {len(all_files)} source files...")

        parsed_files = []
        total_functions = 0
        total_classes = 0
        skipped_files = 0

        # Process files
        for i, file_path in enumerate(all_files):
            if i % 10 == 0:  # Update status every 10 files
                tracker.update("running", f"Parsing files... ({i + 1}/{len(all_files)})")
                await asyncio.sleep(0.01)  # Allow other tasks to run

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

        # Update git info
        git_info["processed_files"] = len(parsed_files)
        git_info["skipped_files"] = len(all_files) - len(parsed_files)

        # Parsing completed
        tracker.update("running", f"File parsing completed! Found {total_functions} functions and {total_classes} classes. Saving results...")
        await asyncio.sleep(0.1)  # Allow status update to be visible

        # Save results
        results_file = code_indexing_dir / "tree_sitter_analysis.json"
        with open(results_file, 'w') as f:
            json.dump(parsed_files, f, indent=2)

        result = {
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
        }

        tracker.update("completed", f"Tree-sitter indexing completed! Processed {len(parsed_files)} files.")
        return result

    except Exception as e:
        tracker.update("failed", f"Indexing failed: {str(e)}")
        return {"success": False, "error": str(e)}


async def api_code_indexing_async(request: Request):
    """Start asynchronous code indexing job."""
    try:
        data = await request.json()
        source_path = data.get("source_path")
        method = data.get("method")  # "ctags" or "tree-sitter"
        languages = data.get("languages", "C++,Python,JavaScript,Java")

        if not source_path:
            return JSONResponse(
                {"success": False, "error": "source_path is required"},
                status_code=400
            )

        if not method or method not in ["ctags", "tree-sitter"]:
            return JSONResponse(
                {"success": False, "error": "method must be 'ctags' or 'tree-sitter'"},
                status_code=400
            )

        source_dir = Path(source_path)
        if not source_dir.exists() or not source_dir.is_dir():
            return JSONResponse(
                {"success": False, "error": f"Source directory '{source_path}' does not exist or is not a directory"},
                status_code=400
            )

        # Generate unique token
        import uuid
        token = str(uuid.uuid4())

        # Create status tracker
        tracker = SimpleStatusTracker(token)
        status_trackers[token] = tracker

        # Start async task
        if method == "ctags":
            asyncio.create_task(run_ctags_indexing_async(source_path, languages, tracker))
        else:  # tree-sitter
            asyncio.create_task(run_tree_sitter_indexing_async(source_path, tracker))

        return JSONResponse({
            "success": True,
            "status_token": token,
            "message": f"Code indexing started. Use /api/code-indexing/status/{token} to check status.",
            "method": method,
            "source_path": source_path
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_code_indexing_status(request: Request):
    """Get status of a code indexing job."""
    try:
        token = request.path_params.get("token")
        if not token:
            return JSONResponse({"error": "Missing status token"}, status_code=400)

        if token not in status_trackers:
            return JSONResponse({"error": "Status token not found"}, status_code=404)

        tracker = status_trackers[token]
        status = tracker.get_status()

        # Clean up completed/failed jobs after 1 hour
        if status["status"] in ["completed", "failed"] and status["runtime"] > 3600:
            del status_trackers[token]

        return JSONResponse(status)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
