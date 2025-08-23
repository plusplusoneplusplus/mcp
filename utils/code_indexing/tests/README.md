# Code Indexing Tests

This directory contains comprehensive test cases for the code indexing utilities (`generate_ctags.py` and `ctags_to_outline.py`) using both unittest and pytest frameworks.

## Test Structure

```
tests/
├── README.md                      # This file
├── run_tests.py                   # Unittest-based test runner
├── run_pytest.py                  # Pytest-based test runner
├── pytest.ini                    # Pytest configuration
├── conftest.py                    # Pytest fixtures and configuration
├── test_generate_ctags.py         # Unittest tests for generate_ctags.py
├── test_ctags_to_outline.py       # Unittest tests for ctags_to_outline.py
├── test_generate_ctags_pytest.py  # Pytest tests for generate_ctags.py
├── test_ctags_to_outline_pytest.py # Pytest tests for ctags_to_outline.py
├── test_integration_pytest.py     # Pytest integration tests
├── sample_cpp_project/            # Test C++ project
│   ├── include/
│   │   ├── geometry/
│   │   │   └── Shape.h            # Abstract shapes with inheritance
│   │   └── utils/
│   │       └── MathUtils.h        # Math utilities and templates
│   ├── src/
│   │   ├── Shape.cpp              # Shape implementations
│   │   └── MathUtils.cpp          # Math utility implementations
│   └── main.cpp                   # Demo application
└── sample_rust_project/           # Test Rust project
    ├── Cargo.toml                 # Rust project configuration
    └── src/
        ├── lib.rs                 # Library root with traits and generics
        ├── geometry.rs            # Geometry module with shapes
        ├── utils.rs               # Utility functions and structures
        ├── collections.rs         # Custom data structures
        └── main.rs                # Application entry point
```

## Sample Projects

### C++ Project Features

The sample C++ project demonstrates various language constructs that ctags should detect:

- **Classes and Inheritance**: `Shape` (abstract base), `Rectangle`, `Circle`
- **Templates**: `Vector2D<T>` with explicit instantiations
- **Access Modifiers**: public, private, protected members and methods
- **Static Members**: Constants and static methods
- **Namespaces**: `geometry` and `utils` namespaces
- **Function Overloading**: Multiple constructors and operators
- **Complex Types**: STL containers, smart pointers

### Rust Project Features

The sample Rust project includes Rust-specific constructs:

- **Structs and Enums**: Various data structures with different field types
- **Traits**: `Shape`, `Drawable`, `Processable`, `Serializable`
- **Generics**: Generic types and functions with constraints
- **Modules**: Multiple modules with visibility modifiers
- **Implementations**: Trait implementations for structs
- **Error Handling**: Custom error types and Result usage
- **Lifetimes**: Functions with lifetime parameters
- **Macros**: Derived traits and procedural macros

## Test Frameworks

This test suite supports both **unittest** (Python standard library) and **pytest** (modern testing framework):

### Unittest Tests
- **`test_generate_ctags.py`** - Traditional unittest format
- **`test_ctags_to_outline.py`** - Traditional unittest format
- **`run_tests.py`** - Custom test runner with integration tests

### Pytest Tests
- **`test_generate_ctags_pytest.py`** - Modern pytest format with fixtures and parametrized tests
- **`test_ctags_to_outline_pytest.py`** - Pytest format with comprehensive fixtures
- **`test_integration_pytest.py`** - Integration tests using pytest framework
- **`conftest.py`** - Shared fixtures and pytest configuration
- **`run_pytest.py`** - Enhanced pytest runner with options

## Running Tests

### Prerequisites

1. **Universal ctags**: Required for tag generation
   ```bash
   # macOS
   brew install ctags

   # Ubuntu/Debian
   sudo apt install universal-ctags

   # Verify installation
   ctags --version
   ```

2. **Python 3.6+**: Required for running tests

3. **Pytest** (optional): For modern test features
   ```bash
   pip install pytest pytest-html pytest-cov pytest-xdist
   ```

### Unittest Commands

1. **Check Dependencies**:
   ```bash
   python run_tests.py --check-deps
   ```

2. **Run All Tests**:
   ```bash
   python run_tests.py
   ```

3. **Run Only Unit Tests**:
   ```bash
   python run_tests.py --unit
   ```

4. **Run Only Integration Tests**:
   ```bash
   python run_tests.py --integration
   ```

5. **Verbose Output**:
   ```bash
   python run_tests.py --verbose
   ```

### Pytest Commands

1. **Run All Tests**:
   ```bash
   python -m pytest
   # or
   python run_pytest.py
   ```

2. **Run Specific Test Categories**:
   ```bash
   # Unit tests only
   python run_pytest.py --unit

   # Integration tests only
   python run_pytest.py --integration

   # Fast tests (exclude slow ones)
   python run_pytest.py --fast
   ```

3. **Advanced Pytest Options**:
   ```bash
   # With coverage report
   python run_pytest.py --coverage

   # Parallel execution
   python run_pytest.py --parallel

   # Verbose output with coverage
   python run_pytest.py --verbose --coverage --cov-html

   # Run specific test file
   python -m pytest test_generate_ctags_pytest.py -v

   # Run specific test class
   python -m pytest test_ctags_to_outline_pytest.py::TestAccessMark -v

   # Run with markers
   python -m pytest -m "not slow" -v
   ```

4. **Parametrized Test Examples**:
   ```bash
   # See all parametrized variations
   python -m pytest test_generate_ctags_pytest.py::test_parametrized_languages -v
   python -m pytest test_ctags_to_outline_pytest.py::TestAccessMark -v
   ```

### Individual Test Files

You can also run individual test files directly:

```bash
# Unit tests for generate_ctags.py
python -m unittest test_generate_ctags

# Unit tests for ctags_to_outline.py
python -m unittest test_ctags_to_outline

# Run with verbose output
python -m unittest test_generate_ctags -v

# Pytest versions
python -m pytest test_generate_ctags_pytest.py -v
python -m pytest test_ctags_to_outline_pytest.py -v
python -m pytest test_integration_pytest.py -v
```

## Test Coverage

### generate_ctags.py Tests

- **Function Tests**: Parameter validation, command building, error handling
- **Integration Tests**: Actual ctags execution with sample projects
- **Error Scenarios**: Missing directories, ctags not found, execution failures
- **Command Line**: Argument parsing and option handling

### ctags_to_outline.py Tests

- **Parsing Tests**: JSON tag loading, malformed data handling
- **Index Building**: Class and member organization
- **Rendering Tests**: Text and PlantUML output generation
- **Edge Cases**: Empty data, missing fields, complex inheritance

### Integration Tests

- **Multi-Language**: C++ and Rust project processing
- **End-to-End**: Complete workflow from source to outline
- **Real Data**: Tests with actual ctags output
- **Performance**: Large project handling

### Pytest-Specific Features

- **Parametrized Tests**: Multiple test cases from single test function
- **Fixtures**: Reusable test setup and teardown
- **Markers**: Categorize and filter tests (unit, integration, slow, performance)
- **Better Output**: Cleaner test output and failure reporting
- **Coverage Integration**: Built-in coverage reporting support
- **Parallel Execution**: Run tests in parallel for faster execution
- **Plugin Ecosystem**: Extensible with many available plugins

## Expected Test Results

When all dependencies are available, you should see output like:

```
==================================================
Code Indexing Utilities Test Suite
==================================================
Checking dependencies...
✓ ctags found: Universal Ctags
✓ Python 3.x.x
✓ C++ sample project found
✓ Rust sample project found

Running unit tests...
test_successful_ctags_execution ... ok
test_ctags_with_custom_languages ... ok
test_render_text_basic ... ok
test_render_plantuml_basic ... ok
...

Running integration tests...
test_cpp_project_ctags_generation ... ok
test_outline_generation_from_cpp_tags ... ok
...

==================================================
✓ All tests passed!
```

**Pytest Output Example:**
```
=================== test session starts ===================
platform darwin -- Python 3.11.12, pytest-8.4.0
collected 47 items

test_generate_ctags_pytest.py::TestGenerateCtags::test_nonexistent_source_directory PASSED [ 10%]
test_ctags_to_outline_pytest.py::TestAccessMark::test_access_mark_conversion[public-+] PASSED [ 21%]
test_integration_pytest.py::TestCppProjectIntegration::test_cpp_ctags_generation PASSED [ 95%]
...

=================== 47 passed in 2.45s ===================
```

## Troubleshooting

### Common Issues

1. **ctags not found**:
   - Install universal-ctags as shown above
   - Ensure it's in your PATH

2. **Rust tags not generated**:
   - Some ctags versions don't support Rust
   - Tests will skip Rust-specific functionality

3. **Import errors**:
   - Ensure you're running from the correct directory
   - Check Python path includes parent directory

4. **Permission errors**:
   - Ensure write permissions in test directory
   - Check temporary directory access

### Test Debugging

To debug failing tests:

1. Run with verbose output: `python run_tests.py -v`
2. Run individual test methods: `python -m unittest test_module.TestClass.test_method -v`
3. Check ctags output manually: `ctags --version` and test on sample files
4. Inspect generated tag files in the temporary directory

## Contributing

When adding new tests:

### For Unittest
1. **Unit Tests**: Add to appropriate test_*.py file
2. **Integration Tests**: Add to run_tests.py IntegrationTestSuite
3. **Follow**: Existing unittest patterns

### For Pytest
1. **Unit Tests**: Add to appropriate test_*_pytest.py file
2. **Integration Tests**: Add to test_integration_pytest.py
3. **Fixtures**: Add reusable fixtures to conftest.py
4. **Parametrized**: Use @pytest.mark.parametrize for multiple test cases
5. **Markers**: Use appropriate markers (unit, integration, slow, performance)

### General Guidelines
1. **Sample Code**: Add to sample projects for new language features
2. **Documentation**: Update this README with new test descriptions
3. **Coverage**: Ensure good coverage of edge cases and error conditions
4. **Both Frameworks**: Consider adding tests to both unittest and pytest versions for comprehensive coverage

### Pytest Best Practices
- Use fixtures for setup/teardown instead of setUp/tearDown methods
- Leverage parametrized tests for testing multiple inputs
- Use descriptive test names that clearly indicate what is being tested
- Group related tests into classes
- Use markers to categorize tests appropriately
