# Step 1: Project Setup and Dependencies

## Overview
Set up the foundational structure and dependencies for the Prompt Store feature within the Wu Wei extension.

## Objectives
- Create the basic file structure for prompt store components
- Add necessary dependencies for YAML parsing and file watching
- Set up TypeScript interfaces and types
- Create basic logging integration

## Tasks

### 1.1 File Structure Setup
Create the following files in the `src/` directory:

```
src/
├── promptStore/
│   ├── index.ts                    # Main exports
│   ├── PromptStoreProvider.ts      # Webview provider
│   ├── PromptManager.ts            # Core business logic
│   ├── PromptFileWatcher.ts        # File system monitoring
│   ├── MetadataParser.ts           # YAML frontmatter parsing
│   ├── types.ts                    # TypeScript interfaces
│   └── constants.ts                # Configuration constants
└── webview/
    └── promptStore/
        ├── index.html              # Webview HTML template
        ├── main.js                 # Webview JavaScript
        └── style.css               # Webview styles
```

### 1.2 Package Dependencies
Add the following dependencies to `package.json`:

```json
{
  "dependencies": {
    "yaml": "^2.3.4",
    "chokidar": "^3.5.3"
  },
  "devDependencies": {
    "@types/yaml": "^1.9.7"
  }
}
```

### 1.3 TypeScript Interfaces
Create comprehensive type definitions in `src/promptStore/types.ts`:

- `Prompt` interface
- `PromptMetadata` interface
- `ParameterDef` interface
- `PromptStoreConfig` interface
- `FileWatcherEvent` interface

### 1.4 Constants Configuration
Define configuration constants in `src/promptStore/constants.ts`:

- Default metadata schema
- File patterns for markdown detection
- Validation rules
- UI configuration defaults

### 1.5 Logging Integration
- Extend existing logger with prompt store specific logging categories
- Add debug levels for file operations, metadata parsing, and UI events
- Create structured logging for performance monitoring

## Acceptance Criteria
- [ ] All file structure is created with empty/skeleton implementations
- [ ] Dependencies are installed and TypeScript compiles without errors
- [ ] All interfaces are properly typed and exported
- [ ] Constants are centralized and configurable
- [ ] Logging integration works with existing Wu Wei logger
- [ ] No breaking changes to existing extension functionality

## Dependencies
- Requires existing Wu Wei extension structure
- Depends on current logging system

## Estimated Effort
**2-3 hours**

## Files to Create
1. `src/promptStore/index.ts`
2. `src/promptStore/PromptStoreProvider.ts`
3. `src/promptStore/PromptManager.ts`
4. `src/promptStore/PromptFileWatcher.ts`
5. `src/promptStore/MetadataParser.ts`
6. `src/promptStore/types.ts`
7. `src/promptStore/constants.ts`
8. `src/webview/promptStore/index.html`
9. `src/webview/promptStore/main.js`
10. `src/webview/promptStore/style.css`

## Next Step
Proceed to **Step 2: Metadata Parser Implementation** once project structure is established.
