"""
Transform operations for workflow steps.

Provides pluggable operation system for data transformation, aggregation, and analysis.
"""

from .base import BaseOperation, OperationRegistry
from .comparison import ComparisonOperation, ConsensusVerificationOperation
from .aggregation import AggregateOperation
from .filtering import FilterOperation
from .mapping import MapOperation

# Global operation registry
registry = OperationRegistry()

# Register built-in operations
registry.register("compare_results", ComparisonOperation)
registry.register("verify_consensus", ConsensusVerificationOperation)
registry.register("aggregate", AggregateOperation)
registry.register("filter", FilterOperation)
registry.register("map", MapOperation)

__all__ = [
    "BaseOperation",
    "OperationRegistry",
    "ComparisonOperation",
    "ConsensusVerificationOperation",
    "AggregateOperation",
    "FilterOperation",
    "MapOperation",
    "registry",
]
