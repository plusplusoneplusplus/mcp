#!/usr/bin/env python3
"""
Main application demonstrating various Python constructs for ctags testing.

This script showcases:
- Module imports and usage
- Async/await patterns
- Exception handling
- Context managers
- Type annotations
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.geometry import (
    AreaCalculator,
    Rectangle,
    Circle,
    Triangle,
    ShapeFactory,
    calculate_total_area,
)
from src.math_utils import Vector2D, MathUtils, StatisticsCalculator, solve_quadratic
from src.async_utils import AsyncProcessor, ProcessingJob, simple_task
from src.data_structures import BinaryTree, LinkedList, Stack, Queue


class Application:
    """Main application class."""

    def __init__(self):
        self.calculator = AreaCalculator()
        self.math_utils = MathUtils()
        self.stats = StatisticsCalculator[float]()
        self.factory = ShapeFactory()
        self.shapes = []

    def run_geometry_demo(self) -> None:
        """Demonstrate geometry functionality."""
        print("\n=== Geometry Demo ===")

        # Create shapes
        self.shapes = [
            self.factory.create_rectangle(5.0, 3.0, "red"),
            self.factory.create_circle(2.5, "blue"),
            self.factory.create_triangle(3.0, 4.0, 5.0, "green"),
            self.factory.create_square(4.0, "yellow"),
        ]

        # Calculate areas
        for shape in self.shapes:
            area = self.calculator.calculate_area(shape)
            print(f"{shape.name}: {area:.2f} sq units ({shape.color})")

        # Find largest shape
        largest = self.calculator.find_largest_shape(self.shapes)
        if largest:
            print(f"Largest shape: {largest.name} with area {largest.area():.2f}")

        # Total area
        total = calculate_total_area(self.shapes)
        print(f"Total area: {total:.2f} sq units")

    def run_math_demo(self) -> None:
        """Demonstrate math utilities."""
        print("\n=== Math Demo ===")

        # Vector operations
        v1 = Vector2D(3.0, 4.0)
        v2 = Vector2D(1.0, 2.0)
        result = self.math_utils.add_vectors(v1, v2)

        print(f"Vector {v1} + {v2} = {result}")
        print(
            f"Distance between vectors: {self.math_utils.calculate_distance(v1, v2):.2f}"
        )

        # Mathematical functions
        print(f"Factorial of 5: {self.math_utils.factorial(5)}")
        print(f"Fibonacci of 10: {self.math_utils.fibonacci(10)}")
        print(f"Is 17 prime? {self.math_utils.is_prime(17)}")

        # Statistics
        data = [1.5, 2.3, 3.7, 4.1, 5.9, 2.8, 3.4, 4.6, 5.2, 1.9]
        self.stats.add_values(data)

        print(f"Statistics for {data}:")
        print(f"  Mean: {self.stats.mean():.2f}")
        print(f"  Median: {self.stats.median():.2f}")
        print(f"  Min: {self.stats.min()}")
        print(f"  Max: {self.stats.max()}")
        print(f"  Std Dev: {self.stats.std_dev():.2f}")

        # Quadratic equation
        roots = solve_quadratic(1, -5, 6)  # x² - 5x + 6 = 0
        print(f"Roots of x² - 5x + 6 = 0: {roots}")

    def run_data_structures_demo(self) -> None:
        """Demonstrate data structures."""
        print("\n=== Data Structures Demo ===")

        # Binary tree
        tree = BinaryTree[int]()
        values = [5, 3, 7, 2, 4, 6, 8, 1, 9]
        for value in values:
            tree.insert(value)

        print(f"Binary tree (size {len(tree)}):")
        print(f"  Inorder: {list(tree.inorder_traversal())}")
        print(f"  Height: {tree.height}")

        # Linked list
        linked_list = LinkedList[str]()
        words = ["hello", "world", "from", "python"]
        for word in words:
            linked_list.append(word)

        print(f"Linked list: {linked_list}")
        print(f"  First: {linked_list.head}")
        print(f"  Last: {linked_list.tail}")

        # Stack operations
        stack = Stack[int]()
        for i in range(1, 6):
            stack.push(i)

        print(f"Stack: {stack}")
        print(f"  Popped: {stack.pop()}")
        print(f"  After pop: {stack}")

        # Queue operations
        queue = Queue[str]()
        for item in ["first", "second", "third"]:
            queue.enqueue(item)

        print(f"Queue: {queue}")
        print(f"  Dequeued: {queue.dequeue()}")
        print(f"  After dequeue: {queue}")

    async def run_async_demo(self) -> None:
        """Demonstrate async functionality."""
        print("\n=== Async Demo ===")

        # Create async processor
        processor = AsyncProcessor(max_workers=3)

        async with processor.managed_processing():
            # Submit jobs
            job_ids = []
            for i in range(5):
                job_id = await processor.create_and_submit_job(
                    f"task-{i}", simple_task, 0.5, f"Result {i}"  # duration  # value
                )
                job_ids.append(job_id)

            print(f"Submitted {len(job_ids)} async jobs")

            # Wait for results
            results = []
            for job_id in job_ids:
                try:
                    result = await processor.wait_for_job(job_id, timeout=2.0)
                    results.append(result)
                    print(f"  {job_id}: {result}")
                except Exception as e:
                    print(f"  {job_id}: Failed - {e}")

            # Show statistics
            stats = processor.stats
            print(f"Processing stats: {stats}")

    def handle_exceptions_demo(self) -> None:
        """Demonstrate exception handling."""
        print("\n=== Exception Handling Demo ===")

        try:
            # This will raise an exception
            self.math_utils.factorial(-1)
        except ValueError as e:
            print(f"Caught ValueError: {e}")

        try:
            # Division by zero
            result = 10 / 0
        except ZeroDivisionError as e:
            print(f"Caught ZeroDivisionError: {e}")

        try:
            # Invalid triangle
            Triangle(-1, 2, 3)
        except ValueError as e:
            print(f"Caught ValueError from Triangle: {e}")

        print("Exception handling demo completed")

    async def run_all_demos(self) -> None:
        """Run all demonstration functions."""
        print("Python Sample Application")
        print("=" * 50)

        self.run_geometry_demo()
        self.run_math_demo()
        self.run_data_structures_demo()
        await self.run_async_demo()
        self.handle_exceptions_demo()

        print("\n" + "=" * 50)
        print("All demos completed successfully!")


def create_sample_config() -> Dict[str, Any]:
    """Create sample configuration dictionary."""
    return {
        "app_name": "Python Sample",
        "version": "1.0.0",
        "debug": True,
        "max_workers": 5,
        "timeout": 30.0,
        "features": {
            "geometry": True,
            "math_utils": True,
            "async_processing": True,
            "data_structures": True,
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    }


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration dictionary."""
    required_keys = ["app_name", "version", "features"]

    for key in required_keys:
        if key not in config:
            print(f"Missing required config key: {key}")
            return False

    if not isinstance(config["features"], dict):
        print("Features must be a dictionary")
        return False

    return True


async def main() -> None:
    """Main entry point."""
    config = create_sample_config()

    if not validate_config(config):
        print("Invalid configuration")
        sys.exit(1)

    app = Application()

    try:
        await app.run_all_demos()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
