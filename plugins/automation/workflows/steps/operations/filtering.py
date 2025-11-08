"""Filtering operations for data selection."""

from typing import Any, Dict, Optional, List

from .base import BaseOperation


class FilterOperation(BaseOperation):
    """
    Filter data based on conditions.

    Config:
        - condition: Filter condition type (equals, contains, greater_than, less_than, regex, custom)
        - field: Field to filter on (for dict items)
        - value: Value to compare against
        - keep_matching: Whether to keep matching items (default: True)

    Inputs:
        - items: List of items to filter
        - Or multiple named inputs that will be collected into a list

    Returns:
        - filtered_items: List of items that match the filter
        - removed_count: Number of items removed
        - kept_count: Number of items kept
    """

    def validate(self) -> Optional[str]:
        """Validate that condition is specified."""
        condition = self.config.get("condition")
        if not condition:
            return "filter operation requires 'condition' in config"

        valid_conditions = [
            "equals",
            "not_equals",
            "contains",
            "not_contains",
            "greater_than",
            "less_than",
            "regex",
            "custom",
        ]
        if condition not in valid_conditions:
            return (
                f"Invalid condition '{condition}'. Valid: {', '.join(valid_conditions)}"
            )

        return None

    async def execute(self) -> Dict[str, Any]:
        """Execute filtering."""
        # Collect items to filter
        if "items" in self.inputs:
            items = self.inputs["items"]
            if not isinstance(items, list):
                items = [items]
        else:
            # Collect all inputs into a list
            items = list(self.inputs.values())

        condition = self.config.get("condition")
        keep_matching = self.config.get("keep_matching", True)

        # Apply filter
        filtered_items = []
        for item in items:
            matches = self._evaluate_condition(item, condition)
            if (matches and keep_matching) or (not matches and not keep_matching):
                filtered_items.append(item)

        return {
            "filtered_items": filtered_items,
            "removed_count": len(items) - len(filtered_items),
            "kept_count": len(filtered_items),
            "original_count": len(items),
        }

    def _evaluate_condition(self, item: Any, condition: str) -> bool:
        """
        Evaluate if item matches condition.

        Returns:
            True if item matches condition
        """
        field = self.config.get("field")
        value = self.config.get("value")

        # Get item value
        if field and isinstance(item, dict):
            item_value = item.get(field)
        else:
            item_value = item

        # Evaluate condition
        if condition == "equals":
            return item_value == value
        elif condition == "not_equals":
            return item_value != value
        elif condition == "contains":
            try:
                return value in str(item_value)
            except TypeError:
                return False
        elif condition == "not_contains":
            try:
                return value not in str(item_value)
            except TypeError:
                return True
        elif condition == "greater_than":
            try:
                return float(item_value) > float(value)
            except (ValueError, TypeError):
                return False
        elif condition == "less_than":
            try:
                return float(item_value) < float(value)
            except (ValueError, TypeError):
                return False
        elif condition == "regex":
            import re

            try:
                return bool(re.search(value, str(item_value)))
            except re.error:
                return False
        elif condition == "custom":
            # Custom condition via Python expression
            # This is advanced and potentially unsafe - use with caution
            expression = self.config.get("expression")
            if expression:
                try:
                    # Limited namespace for safety
                    namespace = {"item": item, "value": value, "field": field}
                    return bool(eval(expression, {"__builtins__": {}}, namespace))
                except Exception:
                    return False
            return False
        else:
            return False
