"""Aggregation operations for data summarization."""

from typing import Any, Dict, Optional, List
from collections import Counter

from .base import BaseOperation


class AggregateOperation(BaseOperation):
    """
    Aggregate data using various aggregation functions.

    Config:
        - function: Aggregation function (sum, avg, count, min, max, group_by, concat)
        - field: Field to aggregate on (for group_by)
        - separator: Separator for concat (default: ", ")

    Inputs:
        - items: List of items or values to aggregate
        - Or multiple named inputs that will be collected into a list

    Returns:
        Result of aggregation based on function type
    """

    def validate(self) -> Optional[str]:
        """Validate that function is specified."""
        function = self.config.get("function")
        if not function:
            return "aggregate operation requires 'function' in config"

        valid_functions = ["sum", "avg", "count", "min", "max", "group_by", "concat"]
        if function not in valid_functions:
            return f"Invalid function '{function}'. Valid: {', '.join(valid_functions)}"

        return None

    async def execute(self) -> Dict[str, Any]:
        """Execute aggregation."""
        function = self.config.get("function")

        # Collect items to aggregate
        if "items" in self.inputs:
            items = self.inputs["items"]
            if not isinstance(items, list):
                items = [items]
        else:
            # Collect all inputs into a list
            items = list(self.inputs.values())

        # Execute aggregation function
        if function == "sum":
            result = self._sum(items)
        elif function == "avg":
            result = self._avg(items)
        elif function == "count":
            result = self._count(items)
        elif function == "min":
            result = self._min(items)
        elif function == "max":
            result = self._max(items)
        elif function == "group_by":
            result = self._group_by(items)
        elif function == "concat":
            result = self._concat(items)
        else:
            result = {"error": f"Unknown function: {function}"}

        return {
            "function": function,
            "item_count": len(items),
            "result": result,
        }

    def _sum(self, items: List[Any]) -> Any:
        """Sum numeric values."""
        try:
            numeric_items = [float(x) for x in items if x is not None]
            return sum(numeric_items)
        except (ValueError, TypeError):
            return {"error": "Cannot sum non-numeric values"}

    def _avg(self, items: List[Any]) -> Any:
        """Calculate average of numeric values."""
        try:
            numeric_items = [float(x) for x in items if x is not None]
            if not numeric_items:
                return 0
            return sum(numeric_items) / len(numeric_items)
        except (ValueError, TypeError):
            return {"error": "Cannot average non-numeric values"}

    def _count(self, items: List[Any]) -> int:
        """Count items."""
        return len([x for x in items if x is not None])

    def _min(self, items: List[Any]) -> Any:
        """Find minimum value."""
        try:
            valid_items = [x for x in items if x is not None]
            return min(valid_items) if valid_items else None
        except (ValueError, TypeError):
            return {"error": "Cannot find min of incomparable values"}

    def _max(self, items: List[Any]) -> Any:
        """Find maximum value."""
        try:
            valid_items = [x for x in items if x is not None]
            return max(valid_items) if valid_items else None
        except (ValueError, TypeError):
            return {"error": "Cannot find max of incomparable values"}

    def _group_by(self, items: List[Any]) -> Dict[str, List[Any]]:
        """Group items by field."""
        field = self.config.get("field")
        if not field:
            # Count occurrences
            return dict(Counter(str(x) for x in items if x is not None))

        # Group by field
        groups = {}
        for item in items:
            if isinstance(item, dict) and field in item:
                key = str(item[field])
                if key not in groups:
                    groups[key] = []
                groups[key].append(item)

        return groups

    def _concat(self, items: List[Any]) -> str:
        """Concatenate items as strings."""
        separator = self.config.get("separator", ", ")
        valid_items = [str(x) for x in items if x is not None]
        return separator.join(valid_items)
