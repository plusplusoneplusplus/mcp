"""Code indexing utilities for parsing and analyzing source code.

This package provides utilities for generating ctags and converting them to
various outline formats including text and PlantUML.
"""

from .outline import (
    access_mark,
    type_name,
    load_tags,
    build_index,
    render_text,
    render_plantuml,
    CLASS_KINDS,
    MEMBER_KINDS,
    METHOD_KINDS,
)

from .generator import (
    run_ctags,
)

# CLI functions imported on demand to avoid circular imports

__all__ = [
    # Core outline functions
    "access_mark",
    "type_name",
    "load_tags",
    "build_index",
    "render_text",
    "render_plantuml",
    # Constants
    "CLASS_KINDS",
    "MEMBER_KINDS",
    "METHOD_KINDS",
    # Generator functions
    "run_ctags",
    # CLI functions (available through submodules)
]
