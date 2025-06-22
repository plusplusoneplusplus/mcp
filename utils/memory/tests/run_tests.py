#!/usr/bin/env python3
"""
Test runner for memory module tests.
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Import test modules
try:
    # Try relative imports first (when run as module)
    from .test_types import (
        TestMemoryType,
        TestMemoryEntry,
        TestConversationEntry,
        TestContextEntry
    )
    from .test_conversation_memory import TestConversationMemory
    from .test_context_memory import TestContextMemory
    from .test_memory_manager import TestMemoryManager
except ImportError:
    # Fall back to direct imports (when run as script)
    import sys
    from pathlib import Path
    test_dir = Path(__file__).parent
    sys.path.insert(0, str(test_dir))

    from test_types import (
        TestMemoryType,
        TestMemoryEntry,
        TestConversationEntry,
        TestContextEntry
    )
    from test_conversation_memory import TestConversationMemory
    from test_context_memory import TestContextMemory
    from test_memory_manager import TestMemoryManager

if __name__ == "__main__":
    # Create a test suite
    test_suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestMemoryType,
        TestMemoryEntry,
        TestConversationEntry,
        TestContextEntry,
        TestConversationMemory,
        TestContextMemory,
        TestMemoryManager,
    ]

    for test_class in test_classes:
        test_suite.addTest(unittest.makeSuite(test_class))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Memory Module Test Summary")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")

    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}")

    # Exit with non-zero code if tests failed
    sys.exit(not result.wasSuccessful())
