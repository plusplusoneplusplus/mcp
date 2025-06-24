# Step 3: File System Operations

## Overview
Implement the core file system operations for discovering, reading, and monitoring markdown files in the configured prompt directory.

## Objectives
- Discover all markdown files in configured directory
- Support nested directory structures
- Handle file system permissions and errors
- Provide efficient file operations
- Create foundation for file watching

## Tasks

### 3.1 Directory Scanning
Implement `PromptManager` methods for file discovery:

```typescript
class PromptManager {
    async scanDirectory(rootPath: string): Promise<string[]>
    async loadPrompt(filePath: string): Promise<Prompt>
    async loadAllPrompts(rootPath: string): Promise<Prompt[]>
    async savePrompt(prompt: Prompt): Promise<void>
    async deletePrompt(filePath: string): Promise<void>
    async createPrompt(name: string, category?: string): Promise<Prompt>
}
```

### 3.2 File Discovery Logic
- Recursively scan configured directory
- Filter for markdown files (`.md`, `.markdown`)
- Ignore hidden files and directories (starting with `.`)
- Support configurable ignore patterns
- Handle symbolic links appropriately
- Respect VS Code workspace exclude patterns

### 3.3 File Reading Operations
- Read file contents with proper encoding (UTF-8)
- Handle large files efficiently
- Get file metadata (size, modification time, permissions)
- Parse content through MetadataParser
- Cache file statistics for performance

### 3.4 File Writing Operations
- Create new prompt files with template
- Update existing prompt files
- Preserve file permissions and timestamps
- Handle concurrent modifications
- Atomic write operations (write to temp, then rename)

### 3.5 Directory Management
- Create category directories as needed
- Handle directory creation permissions
- Validate directory paths
- Support relative and absolute paths
- Handle network drives and special file systems

### 3.6 Error Handling
Comprehensive error handling for:
- Permission denied errors
- File not found errors
- Network drive timeouts
- Disk space issues
- File locking conflicts
- Invalid characters in filenames

## Implementation Details

### 3.6.1 File Discovery
```typescript
async scanDirectory(rootPath: string): Promise<string[]> {
    const files: string[] = [];
    const stack = [rootPath];
    
    while (stack.length > 0) {
        const currentPath = stack.pop()!;
        
        try {
            const entries = await fs.readdir(currentPath, { withFileTypes: true });
            
            for (const entry of entries) {
                if (entry.isDirectory() && !entry.name.startsWith('.')) {
                    stack.push(path.join(currentPath, entry.name));
                } else if (this.isMarkdownFile(entry.name)) {
                    files.push(path.join(currentPath, entry.name));
                }
            }
        } catch (error) {
            this.logger.error(`Failed to scan directory ${currentPath}:`, error);
        }
    }
    
    return files;
}
```

### 3.6.2 Atomic File Operations
```typescript
async savePrompt(prompt: Prompt): Promise<void> {
    const tempPath = `${prompt.filePath}.tmp`;
    const content = this.generateFileContent(prompt);
    
    try {
        await fs.writeFile(tempPath, content, 'utf8');
        await fs.rename(tempPath, prompt.filePath);
    } catch (error) {
        // Cleanup temp file on error
        try {
            await fs.unlink(tempPath);
        } catch (cleanupError) {
            // Log but don't throw cleanup errors
        }
        throw error;
    }
}
```

### 3.6.3 File Content Generation
```typescript
private generateFileContent(prompt: Prompt): string {
    let content = '';
    
    if (Object.keys(prompt.metadata).length > 0) {
        content += '---\n';
        content += yaml.stringify(prompt.metadata);
        content += '---\n\n';
    }
    
    content += prompt.content;
    return content;
}
```

## Performance Considerations

### 3.7 Optimization Strategies
- Batch file operations where possible
- Use streaming for large files
- Implement file stat caching
- Debounce rapid file system operations
- Lazy load file contents (metadata first)

### 3.8 Memory Management
- Limit concurrent file operations
- Stream large files instead of loading into memory
- Clear caches periodically
- Monitor memory usage during batch operations

## Testing Requirements

### 3.9 Unit Tests
Test scenarios for:
- Directory scanning with nested folders
- File reading with various encodings
- File writing with different content types
- Error handling for permission issues
- Performance with large directory structures
- Concurrent file operations

### 3.10 Integration Tests
- Test with real file system
- Verify behavior on different operating systems
- Test network drive scenarios
- Validate file watcher integration points

### 3.11 Test Directory Structure
```
test/fixtures/prompt-directories/
├── simple/
│   ├── prompt1.md
│   └── prompt2.md
├── nested/
│   ├── category1/
│   │   └── nested-prompt.md
│   └── category2/
│       └── another-prompt.md
├── mixed/
│   ├── valid-prompt.md
│   ├── invalid-yaml.md
│   └── .hidden-file.md
└── empty/
```

## Acceptance Criteria
- [ ] Successfully discovers all markdown files in directory tree
- [ ] Handles various file system errors gracefully
- [ ] Performs well with directories containing 1000+ files
- [ ] Supports atomic file operations
- [ ] Properly handles file encoding issues
- [ ] Works across different operating systems
- [ ] Memory usage stays reasonable during operations
- [ ] All unit and integration tests pass
- [ ] Logging provides sufficient detail for debugging

## Dependencies
- **Step 1**: Project setup completed
- **Step 2**: MetadataParser implemented and tested
- Node.js fs/promises API
- Path manipulation utilities

## Estimated Effort
**6-8 hours**

## Files to Implement
1. `src/promptStore/PromptManager.ts` (main implementation)
2. `src/promptStore/utils/fileUtils.ts` (helper utilities)
3. `test/promptStore/PromptManager.test.ts` (unit tests)
4. `test/promptStore/integration/fileSystem.test.ts` (integration tests)
5. `test/fixtures/prompt-directories/` (test directory structures)

## Next Step
Proceed to **Step 4: File Watching System** to add real-time file system monitoring.
