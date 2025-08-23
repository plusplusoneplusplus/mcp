"""Command-line interfaces for code indexing utilities.

This module provides the main entry points for the command-line tools.
"""

# Import main functions from their respective modules
from .outline import main_outline
from .generator import main_generator

# Re-export for convenience
__all__ = ["main_outline", "main_generator"]
