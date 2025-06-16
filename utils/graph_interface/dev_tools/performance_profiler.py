"""
Performance profiling utility for Neo4j Graph Interface development.

This module provides tools for profiling and benchmarking graph operations
to identify performance bottlenecks and optimization opportunities.
"""

import time
import statistics
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager

from ..neo4j_client import Neo4jClient
from ..config import Neo4jConfig


@dataclass
class PerformanceMetric:
    """Represents a single performance measurement."""
    operation_name: str
    execution_time: float
    memory_usage: Optional[int] = None
    result_count: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""
    operation_name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    median_time: float
    std_dev: float
    operations_per_second: float
    timestamp: datetime = field(default_factory=datetime.now)
    individual_times: List[float] = field(default_factory=list)


class PerformanceProfiler:
    """
    Profile and benchmark Neo4j graph operations.

    This class provides utilities for:
    - Timing individual operations
    - Running benchmarks with multiple iterations
    - Comparing performance between different approaches
    - Tracking performance over time
    - Generating performance reports
    """

    def __init__(self, client: Optional[Neo4jClient] = None):
        """
        Initialize the performance profiler.

        Args:
            client: Neo4j client instance. If None, creates a new one.
        """
        self.client = client or Neo4jClient()
        self.metrics: List[PerformanceMetric] = []
        self.benchmarks: List[BenchmarkResult] = []

    @contextmanager
    def profile_operation(self, operation_name: str, **metadata):
        """
        Context manager for profiling an operation.

        Args:
            operation_name: Name of the operation being profiled
            **metadata: Additional metadata to store with the metric

        Usage:
            with profiler.profile_operation("create_node"):
                # Your operation here
                pass
        """
        start_time = time.time()
        start_memory = self._get_memory_usage()

        try:
            yield
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage()

            execution_time = end_time - start_time
            memory_delta = end_memory - start_memory if start_memory and end_memory else None

            metric = PerformanceMetric(
                operation_name=operation_name,
                execution_time=execution_time,
                memory_usage=memory_delta,
                timestamp=datetime.now(),
                metadata={
                    **metadata,
                    'success': success,
                    'error': error if not success else None
                }
            )

            self.metrics.append(metric)

    def benchmark_operation(
        self,
        operation_func: Callable,
        operation_name: str,
        iterations: int = 100,
        warmup_iterations: int = 10,
        **kwargs
    ) -> BenchmarkResult:
        """
        Benchmark an operation by running it multiple times.

        Args:
            operation_func: Function to benchmark
            operation_name: Name of the operation
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations
            **kwargs: Arguments to pass to the operation function

        Returns:
            BenchmarkResult with timing statistics
        """
        print(f"Benchmarking {operation_name}...")
        print(f"Warmup: {warmup_iterations} iterations")
        print(f"Benchmark: {iterations} iterations")

        # Warmup phase
        for _ in range(warmup_iterations):
            try:
                operation_func(**kwargs)
            except Exception as e:
                print(f"Warning: Warmup iteration failed: {e}")

        # Benchmark phase
        times = []
        successful_iterations = 0

        for i in range(iterations):
            start_time = time.time()
            try:
                operation_func(**kwargs)
                end_time = time.time()
                times.append(end_time - start_time)
                successful_iterations += 1
            except Exception as e:
                print(f"Warning: Iteration {i+1} failed: {e}")

        if not times:
            raise RuntimeError("All benchmark iterations failed")

        # Calculate statistics
        total_time = sum(times)
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        median_time = statistics.median(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0.0
        ops_per_second = successful_iterations / total_time if total_time > 0 else 0

        result = BenchmarkResult(
            operation_name=operation_name,
            iterations=successful_iterations,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            median_time=median_time,
            std_dev=std_dev,
            operations_per_second=ops_per_second,
            individual_times=times
        )

        self.benchmarks.append(result)
        self._print_benchmark_result(result)

        return result

    def benchmark_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        iterations: int = 100,
        warmup_iterations: int = 10
    ) -> BenchmarkResult:
        """
        Benchmark a Cypher query.

        Args:
            query: Cypher query to benchmark
            parameters: Query parameters
            iterations: Number of iterations
            warmup_iterations: Number of warmup iterations

        Returns:
            BenchmarkResult
        """
        def query_func():
            return self.client.execute_query(query, parameters or {})

        return self.benchmark_operation(
            query_func,
            f"Query: {query[:50]}...",
            iterations,
            warmup_iterations
        )

    def compare_queries(
        self,
        queries: Dict[str, str],
        parameters: Optional[Dict[str, Any]] = None,
        iterations: int = 50
    ) -> Dict[str, BenchmarkResult]:
        """
        Compare the performance of multiple queries.

        Args:
            queries: Dictionary of query_name -> query_string
            parameters: Parameters for all queries
            iterations: Number of iterations per query

        Returns:
            Dictionary of query_name -> BenchmarkResult
        """
        print(f"Comparing {len(queries)} queries...")
        results = {}

        for name, query in queries.items():
            print(f"\nBenchmarking: {name}")
            result = self.benchmark_query(query, parameters, iterations)
            results[name] = result

        # Print comparison summary
        self._print_query_comparison(results)

        return results

    def profile_graph_operations(self, operations: List[Callable], operation_names: List[str]):
        """
        Profile a series of graph operations.

        Args:
            operations: List of operation functions to profile
            operation_names: Names for each operation
        """
        if len(operations) != len(operation_names):
            raise ValueError("Number of operations must match number of names")

        print("Profiling graph operations...")

        for operation, name in zip(operations, operation_names):
            with self.profile_operation(name):
                operation()

        # Print summary
        self._print_profiling_summary()

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all performance metrics.

        Returns:
            Dictionary with performance statistics
        """
        if not self.metrics:
            return {"message": "No performance metrics collected"}

        # Group metrics by operation name
        operations = {}
        for metric in self.metrics:
            if metric.operation_name not in operations:
                operations[metric.operation_name] = []
            operations[metric.operation_name].append(metric.execution_time)

        # Calculate statistics for each operation
        operation_stats = {}
        for op_name, times in operations.items():
            operation_stats[op_name] = {
                'count': len(times),
                'total_time': sum(times),
                'avg_time': statistics.mean(times),
                'min_time': min(times),
                'max_time': max(times),
                'median_time': statistics.median(times),
                'std_dev': statistics.stdev(times) if len(times) > 1 else 0.0
            }

        return {
            'total_operations': len(self.metrics),
            'unique_operations': len(operations),
            'total_time': sum(m.execution_time for m in self.metrics),
            'operation_statistics': operation_stats,
            'benchmarks_run': len(self.benchmarks),
            'generated_at': datetime.now().isoformat()
        }

    def get_slowest_operations(self, limit: int = 10) -> List[PerformanceMetric]:
        """
        Get the slowest operations.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of slowest PerformanceMetric objects
        """
        sorted_metrics = sorted(self.metrics, key=lambda m: m.execution_time, reverse=True)
        return sorted_metrics[:limit]

    def export_metrics(self, filename: str):
        """
        Export performance metrics to a JSON file.

        Args:
            filename: Output filename
        """
        export_data = {
            'metrics': [
                {
                    'operation_name': m.operation_name,
                    'execution_time': m.execution_time,
                    'memory_usage': m.memory_usage,
                    'result_count': m.result_count,
                    'timestamp': m.timestamp.isoformat(),
                    'metadata': m.metadata
                }
                for m in self.metrics
            ],
            'benchmarks': [
                {
                    'operation_name': b.operation_name,
                    'iterations': b.iterations,
                    'total_time': b.total_time,
                    'avg_time': b.avg_time,
                    'min_time': b.min_time,
                    'max_time': b.max_time,
                    'median_time': b.median_time,
                    'std_dev': b.std_dev,
                    'operations_per_second': b.operations_per_second,
                    'timestamp': b.timestamp.isoformat()
                }
                for b in self.benchmarks
            ],
            'summary': self.get_performance_summary()
        }

        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"Exported performance data to {filename}")

    def clear_metrics(self):
        """Clear all collected metrics and benchmarks."""
        self.metrics.clear()
        self.benchmarks.clear()
        print("Performance metrics cleared")

    def _get_memory_usage(self) -> Optional[int]:
        """Get current memory usage in bytes."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            return None

    def _print_benchmark_result(self, result: BenchmarkResult):
        """Print benchmark result summary."""
        print(f"\nBenchmark Results for: {result.operation_name}")
        print(f"Iterations: {result.iterations}")
        print(f"Total Time: {result.total_time:.4f}s")
        print(f"Average Time: {result.avg_time*1000:.2f}ms")
        print(f"Min Time: {result.min_time*1000:.2f}ms")
        print(f"Max Time: {result.max_time*1000:.2f}ms")
        print(f"Median Time: {result.median_time*1000:.2f}ms")
        print(f"Std Dev: {result.std_dev*1000:.2f}ms")
        print(f"Operations/sec: {result.operations_per_second:.2f}")

    def _print_query_comparison(self, results: Dict[str, BenchmarkResult]):
        """Print query comparison results."""
        print("\n" + "="*60)
        print("QUERY PERFORMANCE COMPARISON")
        print("="*60)

        # Sort by average time
        sorted_results = sorted(results.items(), key=lambda x: x[1].avg_time)

        print(f"{'Query':<30} {'Avg Time (ms)':<15} {'Ops/sec':<10}")
        print("-" * 60)

        for name, result in sorted_results:
            print(f"{name[:29]:<30} {result.avg_time*1000:<15.2f} {result.operations_per_second:<10.2f}")

        # Show relative performance
        if len(sorted_results) > 1:
            fastest = sorted_results[0][1]
            print(f"\nRelative Performance (vs fastest '{sorted_results[0][0]}'):")
            for name, result in sorted_results[1:]:
                speedup = result.avg_time / fastest.avg_time
                print(f"  {name}: {speedup:.2f}x slower")

    def _print_profiling_summary(self):
        """Print profiling summary."""
        if not self.metrics:
            return

        recent_metrics = self.metrics[-10:]  # Last 10 operations

        print("\nProfiling Summary (Last 10 operations):")
        print(f"{'Operation':<30} {'Time (ms)':<12} {'Status':<10}")
        print("-" * 55)

        for metric in recent_metrics:
            status = "SUCCESS" if metric.metadata.get('success', True) else "FAILED"
            print(f"{metric.operation_name[:29]:<30} {metric.execution_time*1000:<12.2f} {status:<10}")


def main():
    """Main function for running the profiler interactively."""
    profiler = PerformanceProfiler()

    print("Neo4j Performance Profiler")
    print("Type 'help' for available commands, 'quit' to exit")

    while True:
        try:
            command = input("\nprofiler> ").strip()

            if command.lower() in ['quit', 'exit']:
                break
            elif command.lower() == 'help':
                print_help()
            elif command.lower() == 'summary':
                summary = profiler.get_performance_summary()
                print(json.dumps(summary, indent=2))
            elif command.lower() == 'slowest':
                slowest = profiler.get_slowest_operations(5)
                print("Top 5 slowest operations:")
                for i, metric in enumerate(slowest, 1):
                    print(f"{i}. {metric.operation_name}: {metric.execution_time*1000:.2f}ms")
            elif command.lower() == 'clear':
                profiler.clear_metrics()
            elif command.lower().startswith('benchmark '):
                query = command[10:]  # Remove 'benchmark ' prefix
                profiler.benchmark_query(query)
            else:
                print("Unknown command. Type 'help' for available commands.")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


def print_help():
    """Print help information."""
    print("""
Available commands:
  benchmark <query>  - Benchmark a Cypher query
  summary           - Show performance summary
  slowest           - Show slowest operations
  clear             - Clear performance metrics
  help              - Show this help
  quit/exit         - Exit the profiler
    """)


if __name__ == "__main__":
    main()
