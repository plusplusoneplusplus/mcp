"""
Sample Python project for testing ctags functionality.

This package demonstrates various Python constructs including:
- Classes and inheritance
- Abstract base classes and protocols
- Type hints and generics
- Decorators and properties
- Async/await patterns
- Exception handling
"""

__version__ = "1.0.0"
__author__ = "Test Suite"

from .geometry import Shape, Rectangle, Circle, Triangle, AreaCalculator
from .math_utils import Vector2D, MathUtils, StatisticsCalculator
from .async_utils import AsyncProcessor, ProcessingJob
from .data_structures import BinaryTree, LinkedList, Stack, Queue

__all__ = [
    "Shape",
    "Rectangle",
    "Circle",
    "Triangle",
    "AreaCalculator",
    "Vector2D",
    "MathUtils",
    "StatisticsCalculator",
    "AsyncProcessor",
    "ProcessingJob",
    "BinaryTree",
    "LinkedList",
    "Stack",
    "Queue",
]
