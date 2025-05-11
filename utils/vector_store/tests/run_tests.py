#!/usr/bin/env python3
"""
Test runner for markdown segmenter tests.
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Import test modules
from test_markdown_segmenter import TestMarkdownSegmenter

if __name__ == "__main__":
    # Create a test suite
    test_suite = unittest.TestSuite()

    # Add tests
    test_suite.addTest(unittest.makeSuite(TestMarkdownSegmenter))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Exit with non-zero code if tests failed
    sys.exit(not result.wasSuccessful())
