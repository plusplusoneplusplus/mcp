# Knowledge Indexer Integration Tests

This directory contains both unit tests and integration tests for the knowledge indexer plugin.

## Test Structure

```
tests/
├── test_knowledge_tools.py    # Unit tests (mocked dependencies)
├── test_integration.py        # Integration tests (real ChromaDB)
├── conftest.py               # Pytest configuration and fixtures
├── fixtures/                 # Test data and expected results
│   └── sample_documents/     # Sample markdown documents
└── README.md                # This file
```

## Test Categories

### Unit Tests (`test_knowledge_tools.py`)
- Fast execution with mocked dependencies
- Test individual component functionality
- Isolated from external dependencies
- Run by default in CI/CD pipelines

### Integration Tests (`test_integration.py`)
- Use real ChromaDB instances
- Test end-to-end workflows
- Validate actual database operations
- Test concurrency and isolation
- Performance and memory testing

## Running Tests

### Run All Tests
```bash
pytest plugins/knowledge_indexer/tests/
```

### Run Only Unit Tests (Fast)
```bash
pytest plugins/knowledge_indexer/tests/ -m "not integration"
```

### Run Only Integration Tests
```bash
pytest plugins/knowledge_indexer/tests/ -m "integration"
```

### Run Tests Excluding Slow Tests
```bash
pytest plugins/knowledge_indexer/tests/ -m "not slow"
```

### Run with Verbose Output
```bash
pytest plugins/knowledge_indexer/tests/ -v
```

### Run with Coverage
```bash
pytest plugins/knowledge_indexer/tests/ --cov=plugins.knowledge_indexer
```

## Test Markers

- `@pytest.mark.integration`: Marks tests that use real database instances
- `@pytest.mark.slow`: Marks tests that take longer to execute
- `@pytest.mark.asyncio`: Marks async tests (handled automatically)

## Integration Test Features

### Real Database Operations
- Actual ChromaDB instance creation and management
- Real embedding generation and storage
- Persistent storage testing
- Collection lifecycle management

### Isolation and Cleanup
- Unique temporary directories per test
- Unique collection names using UUIDs
- Automatic cleanup after test completion
- No interference between parallel tests

### Concurrency Testing
- Parallel indexing operations
- Concurrent read/write access
- Database isolation between collections
- Thread safety validation

### Error Handling
- Invalid directory handling
- Database corruption recovery
- Permission error scenarios
- Resource limitation testing

### Performance Testing
- Large document indexing
- Memory usage monitoring
- Query performance validation
- Scalability testing

## Test Data

### Sample Documents
The `fixtures/sample_documents/` directory contains:
- Representative markdown documents
- Various content types (text, tables, code blocks)
- Different encoding formats (UTF-8, Base64)
- Large documents for performance testing

### Expected Results
Test expectations are defined inline within test methods to ensure:
- Successful operation completion
- Correct data persistence
- Proper error handling
- Expected performance characteristics

## CI/CD Integration

### Fast Pipeline (Unit Tests Only)
```bash
pytest plugins/knowledge_indexer/tests/ -m "not integration" --timeout=60
```

### Full Pipeline (All Tests)
```bash
pytest plugins/knowledge_indexer/tests/ --timeout=300
```

### Performance Pipeline (Integration + Performance)
```bash
pytest plugins/knowledge_indexer/tests/ -m "integration" --timeout=600
```

## Troubleshooting

### Common Issues

1. **ChromaDB Installation**: Ensure ChromaDB is properly installed
   ```bash
   pip install chromadb>=0.4.22
   ```

2. **Sentence Transformers**: Ensure sentence-transformers is available
   ```bash
   pip install sentence-transformers>=4.0.0
   ```

3. **Temporary Directory Cleanup**: Tests automatically clean up, but manual cleanup:
   ```bash
   rm -rf /tmp/test_chroma_*
   ```

4. **Permission Issues**: Ensure write permissions for temporary directories

### Debug Mode
Run tests with debug output:
```bash
pytest plugins/knowledge_indexer/tests/ -v -s --log-cli-level=DEBUG
```

## Contributing

When adding new integration tests:

1. Use unique temporary directories and collection names
2. Implement proper cleanup in finally blocks
3. Add appropriate test markers (`@pytest.mark.integration`, `@pytest.mark.slow`)
4. Test both success and failure scenarios
5. Validate real database state, not just return values
6. Consider performance implications for CI/CD

## Best Practices

### Test Isolation
- Each test should be completely independent
- Use unique identifiers (UUIDs) for collections and directories
- Clean up resources even if tests fail

### Resource Management
- Monitor memory usage in performance tests
- Set reasonable timeouts for long-running operations
- Use appropriate test data sizes

### Error Testing
- Test both expected and unexpected error conditions
- Validate error messages and recovery behavior
- Ensure graceful degradation

### Documentation
- Document test purpose and expected behavior
- Include setup and teardown requirements
- Explain any complex test scenarios 