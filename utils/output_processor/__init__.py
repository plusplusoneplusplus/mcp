"""Output processing utilities for managing and transforming command outputs.

This module provides various strategies for handling large outputs including
truncation, chunking, and compression approaches.
"""

from .output_limiter import OutputLimiter

__all__ = ['OutputLimiter'] 