"""
Transform operations for workflow steps.

Provides pluggable operation system for data transformation, aggregation, and analysis.
"""

from .base import BaseOperation, OperationRegistry
from .comparison import ComparisonOperation, ConsensusVerificationOperation
from .aggregation import AggregateOperation
from .filtering import FilterOperation
from .mapping import MapOperation
from .split import SplitOperation
from .ai_split import AISplitOperation
from .exploration import ExplorationOperation
from .summarize import SummarizeOperation

# Global operation registry
registry = OperationRegistry()

# Register built-in operations
registry.register("compare_results", ComparisonOperation)
registry.register("verify_consensus", ConsensusVerificationOperation)
registry.register("aggregate", AggregateOperation)
registry.register("filter", FilterOperation)
registry.register("map", MapOperation)

# Register map-reduce exploration operations
registry.register("split", SplitOperation)  # Deterministic split
registry.register("ai_split", AISplitOperation)  # AI-powered intelligent split
registry.register("explore", ExplorationOperation)
registry.register("summarize", SummarizeOperation)

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
