"""
Code indexing API endpoints.

This module contains endpoints for code analysis using ctags and tree-sitter
parsers to extract code structure information.
"""

import json
from pathlib import Path
from starlette.requests import Request
from starlette.responses import JSONResponse

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
        server_dir = Path(__file__).resolve().parent.parent.parent  # server/api/knowledge -> server
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
        server_dir = Path(__file__).resolve().parent.parent.parent  # server/api/knowledge -> server
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
