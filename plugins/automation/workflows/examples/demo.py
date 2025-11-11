#!/usr/bin/env python3
"""
Quick demo of AI-powered task decomposition.

Shows how Claude intelligently breaks down exploration goals.

Usage:
    uv run python -m plugins.automation.workflows.examples.demo
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.automation.workflows.steps.operations import AISplitOperation


async def main():
    print("\n" + "=" * 80)
    print("AI-POWERED TASK DECOMPOSITION DEMO")
    print("=" * 80 + "\n")

    # Configure the AI split operation
    config = {
        "model": "haiku",      # Fast model for task decomposition
        "max_tasks": 6,        # Allow up to 6 parallel tasks
        "min_tasks": 3,        # Require at least 3 tasks
    }

    inputs = {
        "goal": "Understand how the MCP workflow system orchestrates AI agents",
        "codebase_path": ".",  # Current directory (git root)
        "focus_areas": ["architecture", "execution flow", "error handling"],
        "constraints": "Focus on the core workflow engine and step execution"
    }

    print("🎯 Goal:")
    print(f"   {inputs['goal']}\n")

    print("📍 Focus Areas:")
    for area in inputs['focus_areas']:
        print(f"   • {area}")
    print()

    print("⏳ Asking Claude to decompose this into focused exploration tasks...\n")
    print("-" * 80 + "\n")

    # Create and execute operation
    operation = AISplitOperation(config, inputs)

    # Validate
    error = operation.validate()
    if error:
        print(f"❌ Validation error: {error}")
        return

    try:
        # Execute AI split
        result = await operation.execute()

        # Display results
        print("✅ AI Task Decomposition Complete!\n")
        print("=" * 80)
        print(f"AI REASONING:")
        print("=" * 80)
        print(result['reasoning'])
        print()

        print("=" * 80)
        print(f"GENERATED TASKS ({result['task_count']} tasks)")
        print("=" * 80 + "\n")

        for task in result['tasks']:
            print(f"📋 Task {task['index'] + 1}: {task['title']}")
            print(f"   Type: {task['type']}")
            print(f"   Priority: {task.get('priority', 'N/A')}")
            print(f"   Complexity: {task.get('estimated_complexity', 'N/A')}")
            print(f"   Query: {task['query']}")
            print()

        print("=" * 80)
        print("METADATA")
        print("=" * 80)
        print(f"Goal: {result['metadata']['goal']}")
        print(f"Codebase: {result['metadata'].get('codebase_path', 'N/A')}")
        print(f"Model: {result['metadata'].get('model', 'haiku')}")
        print(f"Max Tasks: {result['metadata'].get('max_tasks', 'N/A')}")
        print(f"Min Tasks: {result['metadata'].get('min_tasks', 'N/A')}")
        print()

        print("💡 Next Steps:")
        print("   • These tasks can now be executed in parallel by ExploreAgent")
        print("   • Each task will store findings in session files")
        print("   • A summarize operation will aggregate all results")
        print("   • See README.md for full workflow examples")
        print()

    except Exception as e:
        print(f"❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
