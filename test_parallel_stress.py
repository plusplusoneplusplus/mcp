#!/usr/bin/env python3
"""
Stress test script to verify pytest-xdist worker crash fix.
This script runs the problematic test multiple times in parallel to ensure stability.
"""

import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_test_iteration(iteration):
    """Run a single test iteration with pytest-xdist."""
    cmd = [
        "python", "-m", "pytest",
        "server/tests/test_mcp_client_connection.py::TestMCPClientConnection::test_mcp_protocol_handshake",
        "-n", "2", "-v", "--tb=short"
    ]

    start_time = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        duration = time.time() - start_time

        if result.returncode == 0:
            return {
                'iteration': iteration,
                'status': 'PASS',
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        else:
            return {
                'iteration': iteration,
                'status': 'FAIL',
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
    except subprocess.TimeoutExpired:
        return {
            'iteration': iteration,
            'status': 'TIMEOUT',
            'duration': time.time() - start_time,
            'stdout': '',
            'stderr': 'Test timed out after 120 seconds'
        }
    except Exception as e:
        return {
            'iteration': iteration,
            'status': 'ERROR',
            'duration': time.time() - start_time,
            'stdout': '',
            'stderr': str(e)
        }


def main():
    """Run stress test with multiple parallel iterations."""
    print("🧪 Starting pytest-xdist stress test for MCP protocol handshake")
    print("=" * 60)

    # Run 5 iterations in parallel
    num_iterations = 5
    max_workers = 3

    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all test iterations
        future_to_iteration = {
            executor.submit(run_test_iteration, i): i
            for i in range(1, num_iterations + 1)
        }

        # Collect results as they complete
        for future in as_completed(future_to_iteration):
            iteration = future_to_iteration[future]
            try:
                result = future.result()
                results.append(result)

                status_emoji = {
                    'PASS': '✅',
                    'FAIL': '❌',
                    'TIMEOUT': '⏰',
                    'ERROR': '💥'
                }

                emoji = status_emoji.get(result['status'], '❓')
                print(f"{emoji} Iteration {result['iteration']}: {result['status']} "
                      f"({result['duration']:.2f}s)")

                if result['status'] != 'PASS':
                    stderr_msg = result.get('stderr', 'No error details')
                    print(f"   Error details: {stderr_msg}")

            except Exception as exc:
                print(f"💥 Iteration {iteration} generated an exception: {exc}")
                results.append({
                    'iteration': iteration,
                    'status': 'EXCEPTION',
                    'duration': 0,
                    'stdout': '',
                    'stderr': str(exc)
                })

    # Summary
    print("\n" + "=" * 60)
    print("📊 STRESS TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] != 'PASS')
    avg_duration = sum(r['duration'] for r in results) / len(results) if results else 0.0

    print(f"Total iterations: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    success_rate = (passed/len(results)*100) if results else 0.0
    print(f"Success rate: {success_rate:.1f}%")
    print(f"Average duration: {avg_duration:.2f}s")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! The pytest-xdist fix is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. The fix may need additional work.")
        print("\nFailed test details:")
        for result in results:
            if result['status'] != 'PASS':
                print(f"  - Iteration {result['iteration']}: {result['status']}")
                if result.get('stderr'):
                    print(f"    Error: {result['stderr'][:200]}...")
        return 1


if __name__ == "__main__":
    sys.exit(main())
