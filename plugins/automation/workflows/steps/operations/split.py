"""Split operation for dividing work into smaller tasks (Map phase)."""

from typing import Any, Dict, Optional, List

from .base import BaseOperation


class SplitOperation(BaseOperation):
    """
    Split work into smaller tasks for parallel processing (Map phase of map-reduce).

    This operation divides input into multiple smaller tasks that can be processed
    in parallel by downstream steps.

    Config:
        - strategy: Split strategy (by_items, by_count, by_chunk_size, custom)
        - count: Number of splits (for by_count)
        - chunk_size: Size of each chunk (for by_chunk_size)
        - expression: Custom split expression (for custom)

    Inputs:
        - items: List or data to split
        - Or a single input that will be split based on strategy

    Returns:
        - tasks: List of split tasks
        - task_count: Number of tasks created
        - metadata: Information about the split

    Example:
        # Split by count - create N tasks
        config:
          operation: split
          strategy: by_count
          count: 5
        inputs:
          items: ["task1", "task2", "task3", "task4", "task5", "task6"]
        # Result: 5 tasks with ~2 items each

        # Split by items - one task per item
        config:
          operation: split
          strategy: by_items
        inputs:
          items: ["area1", "area2", "area3"]
        # Result: 3 tasks, one for each item

        # Split by chunk size
        config:
          operation: split
          strategy: by_chunk_size
          chunk_size: 2
        inputs:
          items: [1, 2, 3, 4, 5, 6]
        # Result: 3 tasks with 2 items each
    """

    def validate(self) -> Optional[str]:
        """Validate split configuration."""
        strategy = self.config.get("strategy", "by_items")

        valid_strategies = ["by_items", "by_count", "by_chunk_size", "custom"]
        if strategy not in valid_strategies:
            return f"Invalid strategy '{strategy}'. Valid: {', '.join(valid_strategies)}"

        if strategy == "by_count" and "count" not in self.config:
            return "by_count strategy requires 'count' in config"

        if strategy == "by_chunk_size" and "chunk_size" not in self.config:
            return "by_chunk_size strategy requires 'chunk_size' in config"

        if strategy == "custom" and "expression" not in self.config:
            return "custom strategy requires 'expression' in config"

        return None

    async def execute(self) -> Dict[str, Any]:
        """Execute split operation."""
        # Get items to split
        if "items" in self.inputs:
            items = self.inputs["items"]
        else:
            # Use first input value
            items = next(iter(self.inputs.values()), [])

        # Ensure items is a list
        if not isinstance(items, list):
            items = [items]

        strategy = self.config.get("strategy", "by_items")

        # Execute split strategy
        if strategy == "by_items":
            tasks = self._split_by_items(items)
        elif strategy == "by_count":
            tasks = self._split_by_count(items)
        elif strategy == "by_chunk_size":
            tasks = self._split_by_chunk_size(items)
        elif strategy == "custom":
            tasks = self._split_custom(items)
        else:
            tasks = [{"items": items}]

        return {
            "tasks": tasks,
            "task_count": len(tasks),
            "metadata": {
                "strategy": strategy,
                "original_item_count": len(items),
                "split_config": self.config,
            },
        }

    def _split_by_items(self, items: List[Any]) -> List[Dict[str, Any]]:
        """
        Split into one task per item.

        Args:
            items: List of items

        Returns:
            List of tasks, one per item
        """
        return [{"item": item, "index": i} for i, item in enumerate(items)]

    def _split_by_count(self, items: List[Any]) -> List[Dict[str, Any]]:
        """
        Split into N tasks with roughly equal distribution.

        Args:
            items: List of items

        Returns:
            List of N tasks
        """
        count = self.config.get("count", 1)
        if count <= 0:
            count = 1

        # Calculate chunk size
        chunk_size = max(1, len(items) // count)

        tasks = []
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            if chunk:  # Only add non-empty chunks
                tasks.append({
                    "items": chunk,
                    "chunk_index": len(tasks),
                    "chunk_size": len(chunk),
                })

        # If we have more tasks than requested, merge the last ones
        while len(tasks) > count and len(tasks) > 1:
            last = tasks.pop()
            tasks[-1]["items"].extend(last["items"])
            tasks[-1]["chunk_size"] = len(tasks[-1]["items"])

        return tasks

    def _split_by_chunk_size(self, items: List[Any]) -> List[Dict[str, Any]]:
        """
        Split into chunks of specified size.

        Args:
            items: List of items

        Returns:
            List of tasks with chunk_size items each
        """
        chunk_size = self.config.get("chunk_size", 1)
        if chunk_size <= 0:
            chunk_size = 1

        tasks = []
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            tasks.append({
                "items": chunk,
                "chunk_index": len(tasks),
                "chunk_size": len(chunk),
            })

        return tasks

    def _split_custom(self, items: List[Any]) -> List[Dict[str, Any]]:
        """
        Split using custom expression.

        The expression should return a list of tasks.

        Args:
            items: List of items

        Returns:
            List of custom tasks
        """
        expression = self.config.get("expression", "")
        if not expression:
            return [{"items": items}]

        try:
            namespace = {"items": items, "len": len, "range": range}
            result = eval(expression, {"__builtins__": {}}, namespace)

            if isinstance(result, list):
                # Ensure each result is a dict
                tasks = []
                for i, item in enumerate(result):
                    if isinstance(item, dict):
                        tasks.append(item)
                    else:
                        tasks.append({"item": item, "index": i})
                return tasks
            else:
                return [{"result": result}]
        except Exception as e:
            # Fallback to simple split on error
            return [{"items": items, "error": f"Custom split failed: {str(e)}"}]
