"""
Query debugging utility for Neo4j Graph Interface development.

This module provides tools for debugging, profiling, and analyzing Cypher queries
during development and testing.
"""

import time
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..neo4j_client import Neo4jClient
from ..config import Neo4jConfig


@dataclass
class QueryProfile:
    """Profile information for a Cypher query."""
    query: str
    parameters: Dict[str, Any]
    execution_time: float
    result_count: int
    plan: Optional[Dict[str, Any]]
    profile_data: Optional[Dict[str, Any]]
    timestamp: datetime
    success: bool
    error: Optional[str] = None


class QueryDebugger:
    """
    Debug and profile Cypher queries for development purposes.

    This class provides utilities for:
    - Profiling query execution time
    - Analyzing query plans
    - Debugging query results
    - Tracking query performance over time
    """

    def __init__(self, client: Optional[Neo4jClient] = None):
        """
        Initialize the query debugger.

        Args:
            client: Neo4j client instance. If None, creates a new one.
        """
        self.client = client or Neo4jClient()
        self.query_history: List[QueryProfile] = []
        self.debug_mode = True

    def execute_and_profile(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        include_plan: bool = True,
        include_profile: bool = True
    ) -> QueryProfile:
        """
        Execute a query and collect profiling information.

        Args:
            query: Cypher query to execute
            parameters: Query parameters
            include_plan: Whether to include query plan
            include_profile: Whether to include detailed profiling

        Returns:
            QueryProfile with execution details
        """
        parameters = parameters or {}
        start_time = time.time()

        try:
            # Execute the main query
            result = self.client.execute_query(query, parameters)
            execution_time = time.time() - start_time
            result_count = len(result) if isinstance(result, list) else 1

            # Get query plan if requested
            plan = None
            if include_plan:
                plan_query = f"EXPLAIN {query}"
                try:
                    plan_result = self.client.execute_query(plan_query, parameters)
                    plan = plan_result[0] if plan_result else None
                except Exception as e:
                    if self.debug_mode:
                        print(f"Warning: Could not get query plan: {e}")

            # Get detailed profile if requested
            profile_data = None
            if include_profile:
                profile_query = f"PROFILE {query}"
                try:
                    profile_result = self.client.execute_query(profile_query, parameters)
                    profile_data = profile_result[0] if profile_result else None
                except Exception as e:
                    if self.debug_mode:
                        print(f"Warning: Could not get query profile: {e}")

            profile = QueryProfile(
                query=query,
                parameters=parameters,
                execution_time=execution_time,
                result_count=result_count,
                plan=plan,
                profile_data=profile_data,
                timestamp=datetime.now(),
                success=True
            )

        except Exception as e:
            execution_time = time.time() - start_time
            profile = QueryProfile(
                query=query,
                parameters=parameters,
                execution_time=execution_time,
                result_count=0,
                plan=None,
                profile_data=None,
                timestamp=datetime.now(),
                success=False,
                error=str(e)
            )

        self.query_history.append(profile)

        if self.debug_mode:
            self._print_profile_summary(profile)

        return profile

    def analyze_slow_queries(self, threshold_ms: float = 100.0) -> List[QueryProfile]:
        """
        Analyze queries that took longer than the specified threshold.

        Args:
            threshold_ms: Threshold in milliseconds

        Returns:
            List of slow query profiles
        """
        threshold_seconds = threshold_ms / 1000.0
        slow_queries = [
            profile for profile in self.query_history
            if profile.execution_time > threshold_seconds
        ]

        # Sort by execution time (slowest first)
        slow_queries.sort(key=lambda x: x.execution_time, reverse=True)

        if self.debug_mode and slow_queries:
            print(f"\nFound {len(slow_queries)} slow queries (>{threshold_ms}ms):")
            for i, profile in enumerate(slow_queries[:5], 1):  # Show top 5
                print(f"{i}. {profile.execution_time*1000:.2f}ms - {profile.query[:50]}...")

        return slow_queries

    def compare_queries(self, query1: str, query2: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Compare the performance of two queries.

        Args:
            query1: First query to compare
            query2: Second query to compare
            parameters: Parameters for both queries

        Returns:
            Comparison results
        """
        print("Comparing query performance...")

        profile1 = self.execute_and_profile(query1, parameters)
        profile2 = self.execute_and_profile(query2, parameters)

        comparison = {
            'query1': {
                'query': query1,
                'execution_time': profile1.execution_time,
                'result_count': profile1.result_count,
                'success': profile1.success
            },
            'query2': {
                'query': query2,
                'execution_time': profile2.execution_time,
                'result_count': profile2.result_count,
                'success': profile2.success
            },
            'performance_difference': {
                'time_diff_ms': (profile2.execution_time - profile1.execution_time) * 1000,
                'faster_query': 'query1' if profile1.execution_time < profile2.execution_time else 'query2',
                'speedup_factor': max(profile1.execution_time, profile2.execution_time) / min(profile1.execution_time, profile2.execution_time)
            }
        }

        if self.debug_mode:
            self._print_comparison_results(comparison)

        return comparison

    def debug_query_step_by_step(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """
        Debug a query by breaking it down into steps.

        Args:
            query: Query to debug
            parameters: Query parameters
        """
        print(f"Debugging query step by step:")
        print(f"Query: {query}")
        print(f"Parameters: {parameters}")
        print("-" * 50)

        # Try to execute with EXPLAIN first
        try:
            explain_result = self.client.execute_query(f"EXPLAIN {query}", parameters)
            print("Query plan:")
            print(json.dumps(explain_result, indent=2, default=str))
        except Exception as e:
            print(f"Could not get query plan: {e}")

        print("-" * 50)

        # Execute with PROFILE
        try:
            profile_result = self.client.execute_query(f"PROFILE {query}", parameters)
            print("Profile data:")
            print(json.dumps(profile_result, indent=2, default=str))
        except Exception as e:
            print(f"Could not get profile data: {e}")

        print("-" * 50)

        # Execute the actual query
        profile = self.execute_and_profile(query, parameters)
        print(f"Execution result: {'SUCCESS' if profile.success else 'FAILED'}")
        if profile.error:
            print(f"Error: {profile.error}")

    def get_query_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about executed queries.

        Returns:
            Dictionary with query statistics
        """
        if not self.query_history:
            return {"message": "No queries executed yet"}

        successful_queries = [p for p in self.query_history if p.success]
        failed_queries = [p for p in self.query_history if not p.success]

        execution_times = [p.execution_time for p in successful_queries]

        stats = {
            'total_queries': len(self.query_history),
            'successful_queries': len(successful_queries),
            'failed_queries': len(failed_queries),
            'success_rate': len(successful_queries) / len(self.query_history) * 100,
            'execution_times': {
                'min_ms': min(execution_times) * 1000 if execution_times else 0,
                'max_ms': max(execution_times) * 1000 if execution_times else 0,
                'avg_ms': sum(execution_times) / len(execution_times) * 1000 if execution_times else 0
            },
            'most_common_errors': self._get_common_errors(failed_queries)
        }

        return stats

    def export_profiles(self, filename: str):
        """
        Export query profiles to a JSON file.

        Args:
            filename: Output filename
        """
        profiles_data = []
        for profile in self.query_history:
            profiles_data.append({
                'query': profile.query,
                'parameters': profile.parameters,
                'execution_time': profile.execution_time,
                'result_count': profile.result_count,
                'timestamp': profile.timestamp.isoformat(),
                'success': profile.success,
                'error': profile.error
            })

        with open(filename, 'w') as f:
            json.dump(profiles_data, f, indent=2)

        print(f"Exported {len(profiles_data)} query profiles to {filename}")

    def clear_history(self):
        """Clear query history."""
        self.query_history.clear()
        print("Query history cleared")

    def _print_profile_summary(self, profile: QueryProfile):
        """Print a summary of the query profile."""
        status = "SUCCESS" if profile.success else "FAILED"
        print(f"[{status}] {profile.execution_time*1000:.2f}ms - {profile.result_count} results")
        if profile.error:
            print(f"  Error: {profile.error}")

    def _print_comparison_results(self, comparison: Dict[str, Any]):
        """Print query comparison results."""
        print("\nQuery Comparison Results:")
        print(f"Query 1: {comparison['query1']['execution_time']*1000:.2f}ms ({comparison['query1']['result_count']} results)")
        print(f"Query 2: {comparison['query2']['execution_time']*1000:.2f}ms ({comparison['query2']['result_count']} results)")

        perf_diff = comparison['performance_difference']
        print(f"Difference: {abs(perf_diff['time_diff_ms']):.2f}ms")
        print(f"Faster query: {perf_diff['faster_query']}")
        print(f"Speedup factor: {perf_diff['speedup_factor']:.2f}x")

    def _get_common_errors(self, failed_queries: List[QueryProfile]) -> List[Tuple[str, int]]:
        """Get most common error messages."""
        error_counts = {}
        for profile in failed_queries:
            if profile.error:
                error_counts[profile.error] = error_counts.get(profile.error, 0) + 1

        # Sort by frequency
        return sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]


def main():
    """Main function for running the query debugger interactively."""
    debugger = QueryDebugger()

    print("Neo4j Query Debugger")
    print("Type 'help' for available commands, 'quit' to exit")

    while True:
        try:
            command = input("\nquery_debugger> ").strip()

            if command.lower() in ['quit', 'exit']:
                break
            elif command.lower() == 'help':
                print_help()
            elif command.lower() == 'stats':
                stats = debugger.get_query_statistics()
                print(json.dumps(stats, indent=2))
            elif command.lower() == 'slow':
                slow_queries = debugger.analyze_slow_queries()
                print(f"Found {len(slow_queries)} slow queries")
            elif command.lower() == 'clear':
                debugger.clear_history()
            elif command.startswith('profile '):
                query = command[8:]  # Remove 'profile ' prefix
                debugger.execute_and_profile(query)
            elif command.startswith('debug '):
                query = command[6:]  # Remove 'debug ' prefix
                debugger.debug_query_step_by_step(query)
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
  profile <query>  - Profile a Cypher query
  debug <query>    - Debug a query step by step
  stats            - Show query statistics
  slow             - Show slow queries
  clear            - Clear query history
  help             - Show this help
  quit/exit        - Exit the debugger
    """)


if __name__ == "__main__":
    main()
