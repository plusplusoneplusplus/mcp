# Wu Wei Extension Tests

This directory contains the test suite for the Wu Wei VS Code extension, organized with a clean separation between unit and integration tests for optimal performance and developer experience.

## Quick Start

```bash
# Fast unit tests (recommended during development)
npm run test:unit

# Full integration tests (before committing)
npm run test:integration

# All tests (runs both unit and integration sequentially)
npm run test:all

# Or use the main test command (runs all tests)
npm test

# Or use the helper script
./scripts/test.sh unit
./scripts/test.sh integration
./scripts/test.sh all
```

## Clean Test Structure

### 🚀 Unit Tests (`test:unit`)
**Fast, isolated tests (~5 seconds)**

- **Location**: `unit/`
- **Purpose**: Test pure JavaScript/TypeScript logic
- **Environment**: Node.js only (no VS Code APIs)
- **When to use**: During active development for quick feedback

**Directory Structure:**
```
unit/
└── shared/
    └── promptManager.test.ts    # Shared prompt manager utilities
```

### 🔧 Integration Tests (`test:integration`)
**VS Code environment tests (~30-60 seconds)**

- **Location**: `integration/`
- **Purpose**: Test VS Code extension functionality
- **Environment**: VS Code Test Electron
- **When to use**: Before commits, for VS Code API testing

**Directory Structure:**
```
integration/
├── extension/
│   ├── extension.test.ts        # Extension activation and commands
│   └── chatParticipant.test.ts  # Chat participant functionality
├── promptStore/
│   ├── manager.test.ts          # PromptManager integration
│   ├── configuration.test.ts    # Configuration management
│   ├── fileOperations.test.ts   # File operations
│   ├── templates.test.ts        # Template management
│   ├── sessionState.test.ts     # Session state management
│   ├── provider.test.ts         # PromptStore provider
│   ├── serviceAdapter.test.ts   # Service adapter
│   ├── fileWatcher.test.ts      # File watching
│   ├── metadataParser.test.ts   # Metadata parsing (suite)
│   ├── metadataParserCore.test.ts # Metadata parsing (core)
│   ├── commands.test.ts         # Command handling
│   ├── promptManager.test.ts    # Core PromptManager functionality
│   ├── basicFileOps.test.ts     # Basic file operations
│   ├── fileWatching.test.ts     # File watching integration
│   └── configuration.test.ts    # Configuration integration
├── fileSystem/
│   ├── fileSystem.test.ts       # File system integration
│   └── fileSystemIntegration.test.ts # File system integration (suite)
└── tsx/
    └── promptTsxIntegration.test.ts # TSX prompt integration
```

## Test Organization

```
src/test/
├── unit/                    # Pure unit tests (Node.js only)
│   ├── utils/              # Utility function tests
│   └── shared/             # Shared component tests
├── integration/            # VS Code integration tests
│   ├── extension/          # Core extension functionality
│   ├── promptStore/        # PromptStore features
│   ├── fileSystem/         # File system operations
│   └── tsx/               # TSX prompt functionality
├── runUnitTests.ts         # Unit test runner
├── runIntegrationTests.ts  # Integration test runner
└── suiteIntegration/      # Integration test configuration
```

## Test Coverage Summary

**Total Test Files: 20**

**Unit Tests (1 file):**
- Shared prompt manager utilities (variable resolution, rendering, validation)
- No VS Code API dependencies
- Fast execution for development feedback

**Integration Tests (19 files):**
- Extension functionality requiring VS Code APIs
- PromptStore features with VS Code integration
- Cross-component integration scenarios
- TSX prompt functionality

## Benefits of Clean Structure

### ✅ **Simplified Test Runners**
- Unit tests: `unit/**/*.test.js` (simple glob pattern)
- Integration tests: `integration/**/*.test.js` (simple glob pattern)
- No complex exclusion patterns needed

### ✅ **Clear Organization**
- Test type immediately obvious from directory location
- Easier to add new tests in the right place
- Follows common testing conventions

### ✅ **Better Performance**
- Unit tests run in ~5 seconds for quick feedback
- Integration tests run separately when needed
- No need to run slow tests during active development

### ✅ **Easier Maintenance**
- Simple directory structure
- Clear separation of concerns
- Standard patterns developers expect

## Writing Tests

### Unit Tests
- Place in `unit/` directory
- No `import * as vscode` statements
- Test pure logic and utilities
- Use temporary files for file system testing
- Fast execution required

### Integration Tests  
- Place in `integration/` directory
- Can use VS Code APIs freely
- Test extension commands, webviews, etc.
- Extension activation testing
- VS Code workspace integration

## Development Workflow

1. **Active Development**: Use `npm run test:unit` for immediate feedback
2. **Feature Complete**: Run `npm run test:integration` to verify VS Code integration  
3. **Pre-commit**: Run `npm run test:all` for comprehensive validation

## Test Runners

### runUnitTests.ts
- Runs tests from: `unit/**/*.test.js`
- Fast execution for development
- No VS Code dependencies

### runIntegrationTests.ts  
- Runs tests from: `integration/**/*.test.js`
- Full VS Code environment testing
- Extension functionality validation

All test cases have been organized into this clean structure, ensuring comprehensive coverage while maintaining fast development feedback loops and easier maintenance.

## Debugging Tests

### Unit Tests
```bash
# Debug with Node.js tools
node --inspect-brk ./out/test/runUnitTests.js
```

### Integration Tests
```bash
# Use VS Code's test debugging
# Set breakpoints and use "Debug Tests" in VS Code
```

## Adding New Tests

### For Unit Tests
1. Create in `utils/` or `tests/` subdirectory
2. Avoid VS Code API dependencies
3. Focus on pure logic testing
4. Ensure fast execution

### For Integration Tests
1. Create in `suite/`, `promptStore/`, or `integration/`
2. Use VS Code APIs as needed
3. Test extension functionality
4. Include in integration test patterns

## Migration Notes

- Existing tests automatically categorized
- No breaking changes to test structure
- Legacy `npm run test` still works
- New scripts provide better performance

## See Also

- [Testing Plan](../../docs/testing-plan.md) - Comprehensive testing strategy
- [Test Helper Script](../../scripts/test.sh) - Convenient test execution

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
