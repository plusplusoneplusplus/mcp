# MCP Tools Tests

This directory contains tests for the mcp_tools package, which provides utility tools for the MCP system.

## Test Files

- **test_browser_utils.py**: Tests for the browser automation utilities in mcp_tools/browser_utils.py
- **test_command_executor_integration.py**: Integration tests for the command executor functionality
- **test_command_executor_async.py**: Tests for asynchronous command execution
- **test_command_executor.py**: Tests for command executor functionality

## Running Tests

You can run all tests using pytest directly:

```bash
python -m pytest mcp_tools/tests
```

Or use the provided script:

```bash
python mcp_tools/tests/run_tests.py
```

To run a specific test file:

```bash
python -m pytest mcp_tools/tests/test_browser_utils.py
```

## Test Configuration

The tests use pytest and pytest-asyncio for testing asynchronous code. Custom markers are defined in conftest.py:

- `integration`: Marks tests as integration tests
- `asyncio`: Marks tests as asyncio tests

## Requirements

The tests require:
- pytest
- pytest-asyncio
- psutil (for process management in tests)
- playwright (for browser-related tests)

## Notes

These tests were originally part of the server directory but were moved to mcp_tools/tests to maintain proper project organization and to keep tests closer to the modules they are testing.

## Issues and TODOs

The tests currently have some failures due to API differences between the original implementations and the current modules. The following issues need to be addressed:

1. **Browser Utils Tests**: The `BrowserClient` API is different from the old `BrowserUtils` API.
   - The `get_page_html()` method has different parameters.

2. **Command Executor Tests**: The `CommandExecutor` API is different from the old `CommandExecutorV2` API.
   - Some response keys are missing (e.g., 'pid', 'duration')
   - Some return values have different formats
   - Some error messages have changed

These tests need to be updated to match the current API of the modules they are testing. 