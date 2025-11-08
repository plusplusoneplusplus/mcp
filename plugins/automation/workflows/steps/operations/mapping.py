"""Mapping operations for data transformation."""

from typing import Any, Dict, Optional, List

from .base import BaseOperation


class MapOperation(BaseOperation):
    """
    Map/transform data using various mapping functions.

    Config:
        - function: Mapping function (extract, project, compute, transform)
        - fields: Fields to extract/project (for extract/project)
        - expression: Python expression for compute/transform
        - output_field: Output field name (for compute)

    Inputs:
        - items: List of items to map
        - Or multiple named inputs that will be collected into a list

    Returns:
        - mapped_items: List of transformed items
        - item_count: Number of items processed
    """

    def validate(self) -> Optional[str]:
        """Validate that function is specified."""
        function = self.config.get("function")
        if not function:
            return "map operation requires 'function' in config"

        valid_functions = ["extract", "project", "compute", "transform"]
        if function not in valid_functions:
            return f"Invalid function '{function}'. Valid: {', '.join(valid_functions)}"

        return None

    async def execute(self) -> Dict[str, Any]:
        """Execute mapping."""
        # Collect items to map
        if "items" in self.inputs:
            items = self.inputs["items"]
            if not isinstance(items, list):
                items = [items]
        else:
            # Collect all inputs into a list
            items = list(self.inputs.values())

        function = self.config.get("function")

        # Apply mapping function
        if function == "extract":
            mapped_items = self._extract(items)
        elif function == "project":
            mapped_items = self._project(items)
        elif function == "compute":
            mapped_items = self._compute(items)
        elif function == "transform":
            mapped_items = self._transform(items)
        else:
            mapped_items = items

        return {
            "mapped_items": mapped_items,
            "item_count": len(mapped_items),
            "original_count": len(items),
        }

    def _extract(self, items: List[Any]) -> List[Any]:
        """
        Extract specific fields from items.

        Returns list of field values or dicts with specified fields.
        """
        fields = self.config.get("fields", [])
        if isinstance(fields, str):
            fields = [fields]

        result = []
        for item in items:
            if not isinstance(item, dict):
                continue

            if len(fields) == 1:
                # Single field - return value directly
                result.append(item.get(fields[0]))
            else:
                # Multiple fields - return dict
                extracted = {field: item.get(field) for field in fields}
                result.append(extracted)

        return result

    def _project(self, items: List[Any]) -> List[Dict[str, Any]]:
        """
        Project items to new structure with field mapping.

        Config should have 'projection' dict mapping new_field -> source_field
        """
        projection = self.config.get("projection", {})

        result = []
        for item in items:
            if not isinstance(item, dict):
                result.append(item)
                continue

            projected = {}
            for new_field, source_field in projection.items():
                # Support dot notation for nested fields
                value = self._get_nested_value(item, source_field)
                projected[new_field] = value

            result.append(projected)

        return result

    def _compute(self, items: List[Any]) -> List[Any]:
        """
        Compute new field based on expression.

        Adds computed field to each item.
        """
        expression = self.config.get("expression")
        output_field = self.config.get("output_field", "computed")

        if not expression:
            return items

        result = []
        for item in items:
            # Create a copy to avoid mutating original
            if isinstance(item, dict):
                new_item = item.copy()
            else:
                new_item = {"value": item}

            # Evaluate expression with item in namespace
            try:
                namespace = {"item": new_item, "value": item}
                computed_value = eval(expression, {"__builtins__": {}}, namespace)
                new_item[output_field] = computed_value
            except Exception as e:
                new_item[output_field] = {"error": str(e)}

            result.append(new_item)

        return result

    def _transform(self, items: List[Any]) -> List[Any]:
        """
        Transform items using custom expression.

        Expression should return the transformed item.
        """
        expression = self.config.get("expression")
        if not expression:
            return items

        result = []
        for item in items:
            try:
                namespace = {"item": item}
                transformed = eval(expression, {"__builtins__": {}}, namespace)
                result.append(transformed)
            except Exception as e:
                result.append({"error": str(e), "original": item})

        return result

    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """
        Get value from nested dict using dot notation.

        Example: 'user.profile.name' -> obj['user']['profile']['name']
        """
        parts = path.split(".")
        current = obj

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None

        return current
