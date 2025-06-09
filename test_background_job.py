#!/usr/bin/env python3
"""
Test script to verify that start_time is included in background jobs API response.
"""
import asyncio
import time
import requests
from mcp_tools.command_executor.executor import CommandExecutor


async def test_background_job_start_time():
    """Test that background jobs include start_time in API response."""
    print("Testing background job start_time functionality...")

    # Create a command executor
    executor = CommandExecutor()

    # Start a background job
    print("Starting background job...")
    result = await executor.execute_async('sleep 5')
    token = result["token"]
    pid = result["pid"]

    print(f"Started job with token: {token}")
    print(f"PID: {pid}")

    # Wait a moment for the job to be registered
    await asyncio.sleep(1)

    # Test the API endpoint
    print("\nTesting API endpoint...")
    try:
        response = requests.get("http://localhost:8000/api/background-jobs")
        if response.status_code == 200:
            data = response.json()
            jobs = data.get("jobs", [])

            print(f"Found {len(jobs)} jobs")

            # Find our job
            our_job = None
            for job in jobs:
                if job.get("token") == token:
                    our_job = job
                    break

            if our_job:
                print(f"Found our job: {our_job}")

                # Check if start_time is present
                if "start_time" in our_job and our_job["start_time"] is not None:
                    print("✅ SUCCESS: start_time is present in the job data")
                    start_time = our_job["start_time"]
                    current_time = time.time()
                    print(f"Start time: {start_time}")
                    print(f"Current time: {current_time}")
                    print(f"Job has been running for: {current_time - start_time:.2f} seconds")
                else:
                    print("❌ FAILURE: start_time is missing or None in the job data")
            else:
                print(f"❌ FAILURE: Could not find job with token {token}")
        else:
            print(f"❌ FAILURE: API request failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ FAILURE: Error making API request: {e}")

    # Clean up - terminate the job
    print("\nCleaning up...")
    try:
        executor.terminate_by_token(token)
        print("Job terminated successfully")
    except Exception as e:
        print(f"Error terminating job: {e}")


if __name__ == "__main__":
    asyncio.run(test_background_job_start_time())
