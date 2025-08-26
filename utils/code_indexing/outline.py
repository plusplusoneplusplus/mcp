"""Ctags outline parsing and rendering functionality.

This module provides functions to parse ctags JSON output and render it as
text outlines or PlantUML diagrams.
"""

import argparse
import json
import sys
from collections import OrderedDict
from typing import List, Dict, Any, Optional, Tuple

CLASS_KINDS = {"class", "struct", "interface"}
MEMBER_KINDS = {"member"}
METHOD_KINDS = {"method", "function"}


def access_mark(access: Optional[str]) -> str:
    """Convert access level to UML notation.

    Args:
        access: Access level string (public, private, protected, or None)

    Returns:
        UML access marker: + for public, - for private, # for protected, ~ for unknown
    """
    return {"public": "+", "private": "-", "protected": "#"}.get(access or "", "~")


def type_name(typeref: Any, fallback: Optional[str] = None) -> Optional[str]:
    """Extract type name from typeref field.

    Args:
        typeref: Type reference from ctags (string or dict)
        fallback: Fallback value if type cannot be extracted

    Returns:
        Extracted type name or fallback value
    """
    if typeref is None:
        return fallback
    if isinstance(typeref, str):
        return typeref.split(":")[-1] or fallback
    if isinstance(typeref, dict):
        name = typeref.get("name")
        if name:
            return name
    return fallback


def load_tags(ndjson_path: str) -> List[Dict[str, Any]]:
    """Load tags from ctags NDJSON output file.

    Args:
        ndjson_path: Path to NDJSON file containing ctags output

    Returns:
        List of tag dictionaries
    """
    tags = []
    with open(ndjson_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("_type") == "tag":
                tags.append(obj)
    return tags


def build_index(
    tags: List[Dict[str, Any]]
) -> Tuple[List[str], Dict[str, List[Dict[str, Any]]]]:
    """Build index of classes and their members from tags.

    Args:
        tags: List of tag dictionaries from ctags

    Returns:
        Tuple of (class_names, class_members_dict) where:
        - class_names: List of class names in order
        - class_members_dict: Dict mapping class names to their tag rows
    """
    classes = OrderedDict()
    for tag in tags:
        if tag.get("kind") in CLASS_KINDS:
            classes[tag["name"]] = True

    by_class = {}
    for cls in classes.keys():
        rows = []
        for tag in tags:
            kind = tag.get("kind")
            # Include the class row itself
            if tag.get("name") == cls and kind in CLASS_KINDS:
                rows.append(tag)
                continue
            # Include anything scoped to the class (members/methods/etc.)
            if tag.get("scope") == cls and tag.get("scopeKind"):
                rows.append(tag)
        by_class[cls] = rows
    return list(classes.keys()), by_class


def render_text(
    classes: List[str],
    by_class: Dict[str, List[Dict[str, Any]]],
    only: Optional[str] = None,
    show_file: bool = False,
) -> str:
    """Render class outline as text.

    Args:
        classes: List of class names
        by_class: Dict mapping class names to their tag rows
        only: If specified, only render this class
        show_file: Whether to show file information

    Returns:
        Text representation of class outline
    """
    out_lines = []
    names = [only] if only else classes
    for cls in names:
        rows = by_class.get(cls, [])
        out_lines.append(f"class {cls}")
        if show_file:
            # Show where the class itself is declared (first class row path)
            for row in rows:
                if row.get("kind") in CLASS_KINDS:
                    out_lines.append(f"  ~ file: {row.get('path')}")
                    break

        # Members
        for row in rows:
            if row.get("kind") in MEMBER_KINDS:
                mark = access_mark(row.get("access"))
                type_str = type_name(row.get("typeref"), row.get("type"))
                suffix = f": {type_str}" if type_str else ""
                out_lines.append(f"  {mark} {row.get('name')}{suffix}")

        # Methods / functions scoped to the class
        for row in rows:
            if row.get("kind") in METHOD_KINDS:
                mark = access_mark(row.get("access"))
                sig = row.get("signature") or "()"
                out_lines.append(f"  {mark} {row.get('name')}{sig}")
    return "\n".join(out_lines)


def render_plantuml(
    classes: List[str],
    by_class: Dict[str, List[Dict[str, Any]]],
    only: Optional[str] = None,
) -> str:
    """Render class outline as PlantUML diagram.

    Args:
        classes: List of class names
        by_class: Dict mapping class names to their tag rows
        only: If specified, only render this class

    Returns:
        PlantUML representation of class outline
    """
    out = []
    out.append("@startuml")
    names = [only] if only else classes
    for cls in names:
        rows = by_class.get(cls, [])
        out.append(f"class {cls} {{")
        for row in rows:
            if row.get("kind") in MEMBER_KINDS:
                mark = access_mark(row.get("access"))
                type_str = type_name(row.get("typeref"), row.get("type"))
                suffix = f": {type_str}" if type_str else ""
                out.append(f"  {mark} {row.get('name')}{suffix}")
        for row in rows:
            if row.get("kind") in METHOD_KINDS:
                mark = access_mark(row.get("access"))
                sig = row.get("signature") or "()"
                out.append(f"  {mark} {row.get('name')}{sig}")
        out.append("}")
    out.append("@enduml")
    return "\n".join(out)


def main_outline() -> None:
    """Main entry point for ctags outline rendering."""
    parser = argparse.ArgumentParser(
        description="Render class outline from Universal-ctags NDJSON"
    )
    parser.add_argument("tags", help="Path to tags.json (NDJSON from Universal ctags)")
    parser.add_argument("--only", help="Render only this class name")
    parser.add_argument(
        "--by-file", action="store_true", help="Show file of class declaration"
    )
    parser.add_argument(
        "--plantuml", action="store_true", help="Emit PlantUML instead of text"
    )
    args = parser.parse_args()

    tags = load_tags(args.tags)
    if not tags:
        print(
            "No tag entries found. Ensure you used: --output-format=json",
            file=sys.stderr,
        )
        sys.exit(1)

    classes, by_class = build_index(tags)

    if args.plantuml:
        print(render_plantuml(classes, by_class, args.only))
    else:
        print(render_text(classes, by_class, args.only, args.by_file))


def generate_outline_from_ctags(tags_file_path: str) -> Dict[str, Any]:
    """Generate outline data structure from ctags JSON file.

    Args:
        tags_file_path: Path to the ctags JSON file

    Returns:
        Dictionary containing outline data with text and plantuml formats
    """
    tags = load_tags(tags_file_path)
    if not tags:
        return {"error": "No tag entries found in file"}

    classes, by_class = build_index(tags)

    # Generate both text and PlantUML formats
    text_outline = render_text(classes, by_class, show_file=True)
    plantuml_outline = render_plantuml(classes, by_class)

    # Also generate stats
    total_classes = len(classes)
    total_functions = sum(
        1 for tag in tags
        if tag.get("kind") in METHOD_KINDS
    )
    total_members = sum(
        1 for tag in tags
        if tag.get("kind") in MEMBER_KINDS
    )

    return {
        "classes": classes,
        "class_details": by_class,
        "text_outline": text_outline,
        "plantuml_outline": plantuml_outline,
        "stats": {
            "total_classes": total_classes,
            "total_functions": total_functions,
            "total_members": total_members,
            "total_tags": len(tags)
        }
    }


if __name__ == "__main__":
    main_outline()
