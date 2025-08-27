"""
Code viewer API endpoints.

This module contains endpoints for browsing and searching through indexed code,
including class definitions and code structure visualization.
"""

import json
import shutil
from pathlib import Path
from starlette.requests import Request
from starlette.responses import JSONResponse


def calculate_class_relevance_score(class_info, query):
    """Calculate relevance score for a class based on search query."""
    if not query:
        return 0

    class_name = class_info.get("name", "").lower()
    file_path = class_info.get("file_path", "").lower()
    query_lower = query.lower()

    score = 0
    match_type = ''

    # Exact name match gets highest priority
    if class_name == query_lower:
        score = 1000
        match_type = 'exact-name'
    # Name starts with query
    elif class_name.startswith(query_lower):
        score = 800
        match_type = 'name-prefix'
    # Name contains query
    elif query_lower in class_name:
        score = 600
        match_type = 'name-contains'
    # File path contains query
    elif query_lower in file_path:
        score = 400
        match_type = 'path-contains'
    else:
        return 0  # No match

    # Boost score for shorter class names (more specific matches)
    if 'name' in match_type:
        score += max(0, 100 - len(class_name))

    # Boost score based on member count (more complete class definitions)
    members = class_info.get("members", [])
    if members:
        score += min(50, len(members) * 2)

    # Boost score for ctags source (usually more complete info)
    if class_info.get("source") == "ctags":
        score += 20

    return score


async def api_code_viewer_paths(request: Request):
    """Get all available indexed code paths."""
    try:
        server_dir = Path(__file__).resolve().parent.parent.parent  # server/api/knowledge -> server
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

        # Get optional search query parameter
        search_query = request.query_params.get("search", "").strip()

        server_dir = Path(__file__).resolve().parent.parent.parent  # server/api/knowledge -> server
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

        # Remove duplicates based on name and file_path
        seen = set()
        unique_classes = []
        for class_info in class_info_list:
            key = (class_info["name"], class_info["file_path"])
            if key not in seen:
                seen.add(key)
                unique_classes.append(class_info)

        # Apply search filtering and relevance scoring if search query provided
        if search_query:
            # Filter and score classes based on search query
            scored_classes = []
            for class_info in unique_classes:
                score = calculate_class_relevance_score(class_info, search_query)
                if score > 0:  # Only include matches
                    class_info["_relevance_score"] = score
                    scored_classes.append(class_info)

            # Sort by relevance score (highest first), then by name
            scored_classes.sort(key=lambda x: (-x["_relevance_score"], x["name"].lower()))

            # Limit to top 20 results for search
            final_classes = scored_classes[:20]
        else:
            # No search query - return all classes sorted by name
            unique_classes.sort(key=lambda x: x["name"].lower())
            final_classes = unique_classes

        return JSONResponse({
            "success": True,
            "classes": final_classes,
            "total_count": len(final_classes),
            "original_path": original_source_path,
            "search_query": search_query if search_query else None
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def api_code_viewer_cleanup(request: Request):
    """Delete an indexed code path and all its associated files."""
    try:
        # Parse request body
        body = await request.json()
        path_hash = body.get("path_hash")

        if not path_hash:
            return JSONResponse(
                {"success": False, "error": "path_hash is required"},
                status_code=400
            )

        server_dir = Path(__file__).resolve().parent.parent.parent  # server/api/knowledge -> server
        base_indexing_dir = server_dir / ".code_indexing"
        code_indexing_dir = base_indexing_dir / path_hash

        if not code_indexing_dir.exists():
            return JSONResponse(
                {"success": False, "error": f"No indexed data found for hash: {path_hash}"},
                status_code=404
            )

        # Get the original path from meta.txt for logging
        original_path = "unknown"
        meta_file = code_indexing_dir / "meta.txt"
        if meta_file.exists():
            try:
                with open(meta_file, 'r') as f:
                    meta_content = f.read()
                for line in meta_content.split('\n'):
                    if line.startswith('Original Path: '):
                        original_path = line[15:].strip()
                        break
            except Exception:
                pass

        # Remove the entire directory
        shutil.rmtree(code_indexing_dir)

        return JSONResponse({
            "success": True,
            "message": f"Successfully removed indexed data for path: {original_path}",
            "removed_hash": path_hash
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
