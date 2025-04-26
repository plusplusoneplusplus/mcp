# Config Module Tests

This directory contains unit tests for the config module.

## Running Tests

To run all tests, use one of the following methods:

From the `config` directory:

```bash
# Run tests using unittest discovery
python -m unittest discover -s tests

# Or with more verbose output
python -m unittest discover -v -s tests
```

## Test Files

- `test_manager.py` - Tests for the EnvironmentManager class
- `test_types.py` - Tests for the config types (RepositoryInfo, EnvironmentProvider, EnvironmentVariables)

## Adding Tests

When adding new tests:

1. Create a new file named `test_*.py` in this directory
2. Follow the standard unittest pattern (see existing test files)
3. Run the tests to ensure they pass

## Coverage

To run tests with coverage report (requires the `coverage` package):

```bash
# Install coverage if not already installed
pip install coverage

# Run tests with coverage
cd ..  # Make sure you're in the config directory
coverage run -m unittest discover -s tests

# Generate coverage report
coverage report -m
``` 