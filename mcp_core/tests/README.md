# MCP Core Tests

This directory contains tests for the mcp_core package, which provides a decoupled implementation of the tools system for MCP.

## Test Files

- **test_types.py**: Tests the basic functionality of the type definitions in mcp_core/types.py
- **test_tools.py**: Tests the tools loading from tools.yaml and plugin integration
- **test_conversion.py**: Tests the conversion between mcp_core types and mcp types

## Running Tests

You can run all tests using:

```bash
python run_tests.py
```

Or run individual tests:

```bash
python test_types.py
python test_tools.py
python test_conversion.py
```

## Test Requirements

The tests require:
- PyYAML
- mcp package (for testing conversion)
- The MCP server directory with tools.yaml file

## Notes

These tests were originally part of the server directory but were moved to mcp_core/tests to maintain proper project organization and to ensure mcp_core is tested independently. 