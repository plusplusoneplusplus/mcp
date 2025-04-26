#!/usr/bin/env python3
"""Script to run all tests for the config module."""

import unittest
import sys
import os

# Add parent directory to path so we can import config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Find all test modules in the tests directory
test_loader = unittest.TestLoader()
test_suite = test_loader.discover('tests', pattern='test_*.py', top_level_dir=os.path.dirname(__file__))

# Run the tests
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(test_suite)

# Exit with non-zero code if tests failed
sys.exit(not result.wasSuccessful()) 