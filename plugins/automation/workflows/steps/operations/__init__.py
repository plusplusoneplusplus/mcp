"""
Transform operations for workflow steps.

Provides pluggable operation system for data transformation, aggregation, and analysis.
"""

from .base import BaseOperation, OperationRegistry
from .comparison import ComparisonOperation, ConsensusVerificationOperation
from .aggregation import AggregateOperation
from .filtering import FilterOperation
from .mapping import MapOperation
from .exploration import ExplorationOperation
from .summarize import SummarizeOperation
from .decompose import DecomposeOperation

# Global operation registry
registry = OperationRegistry()

# Register built-in operations
registry.register("compare_results", ComparisonOperation)
registry.register("verify_consensus", ConsensusVerificationOperation)
registry.register("aggregate", AggregateOperation)
registry.register("filter", FilterOperation)
registry.register("map", MapOperation)

# Register AI exploration operations
registry.register("explore", ExplorationOperation)
registry.register("summarize", SummarizeOperation)
registry.register("decompose", DecomposeOperation)  # AI-powered task decomposition

__all__ = [
    "BaseOperation",
    "OperationRegistry",
    "ComparisonOperation",
    "ConsensusVerificationOperation",
    "AggregateOperation",
    "FilterOperation",
    "MapOperation",
    "SplitOperation",
    "ExplorationOperation",
    "SummarizeOperation",
    "registry",
]
