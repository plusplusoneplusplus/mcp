# Wu Wei Extension Testing

This directory contains the test suite for the Wu Wei VS Code extension.

## Test Structure

```
src/test/
├── runTest.ts          # Test runner entry point
└── suite/
    ├── index.ts        # Test suite configuration
    └── extension.test.ts # Basic extension tests
```

## Running Tests

### Local Development
```bash
# Run all tests
npm test

# Watch mode for development
npm run test:watch

# Run linter
npm run lint

# Compile TypeScript
npm run compile
```

### CI/CD
Tests are automatically run on:
- Pull requests to `main` or `develop` branches
- Pushes to `main` or `develop` branches

## Test Philosophy

Following Wu Wei principles, our tests are:
- **Simple**: Focus on essential functionality
- **Natural**: Test the natural flow of the extension
- **Minimal**: Avoid over-testing, trust the framework
- **Flowing**: Tests should run smoothly without friction

## Current Test Coverage

✅ Extension activation and deactivation  
✅ Command registration verification  
✅ Configuration accessibility  
✅ Basic module exports

## Adding New Tests

When adding new tests, follow these guidelines:

1. **Keep it simple**: Test one thing at a time
2. **Use descriptive names**: Make test purpose clear
3. **Follow BDD style**: Use `describe` and `it` blocks
4. **Mock external dependencies**: Keep tests isolated
5. **Test behavior, not implementation**: Focus on what the user experiences

## Example Test

```typescript
describe('Wu Wei Feature', () => {
    it('should flow naturally without friction', async () => {
        // Arrange
        const context = createMockContext();
        
        // Act
        const result = await featureUnderTest(context);
        
        // Assert
        assert.ok(result.flows.naturally);
    });
});
```

---

*"The sage does not attempt anything very big, and thus achieves greatness."* - Lao Tzu
