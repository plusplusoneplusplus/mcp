# Step 4: File Watching System

## Overview
Implement real-time file system monitoring to automatically update the prompt store when files are added, modified, or deleted in the configured directory.

## Objectives
- Monitor prompt directory for file system changes
- Debounce rapid file changes
- Update prompt store in real-time
- Handle file watcher lifecycle
- Provide efficient change notifications

## Tasks

### 4.1 File Watcher Implementation
Implement `PromptFileWatcher` class with the following functionality:

```typescript
class PromptFileWatcher {
    private watcher: chokidar.FSWatcher | null = null;
    private eventEmitter: EventEmitter;
    
    start(rootPath: string): void
    stop(): void
    pause(): void
    resume(): void
    isWatching(): boolean
    
    // Events
    on(event: 'fileAdded', callback: (filePath: string) => void): void
    on(event: 'fileChanged', callback: (filePath: string) => void): void
    on(event: 'fileDeleted', callback: (filePath: string) => void): void
    on(event: 'directoryAdded', callback: (dirPath: string) => void): void
    on(event: 'directoryDeleted', callback: (dirPath: string) => void): void
}
```

### 4.2 Change Detection
Monitor for the following file system events:
- File creation (new prompts)
- File modification (content/metadata changes)
- File deletion (prompt removal)
- File renaming (move operations)
- Directory creation (new categories)
- Directory deletion (category removal)

### 4.3 Event Debouncing
- Debounce rapid file changes (e.g., during save operations)
- Batch multiple changes within a time window
- Handle editor auto-save scenarios
- Prevent excessive UI updates

### 4.4 File Filtering
- Only watch markdown files (`.md`, `.markdown`)
- Ignore temporary files (`.tmp`, `.swp`, etc.)
- Ignore hidden files and directories
- Respect VS Code workspace exclusion patterns
- Support custom ignore patterns

### 4.5 Error Handling
Handle file watcher errors:
- File system permission changes
- Network drive disconnections
- File system limits exceeded
- Watcher crashes and recovery
- Platform-specific limitations

## Implementation Details

### 4.5.1 Watcher Initialization
```typescript
start(rootPath: string): void {
    this.stop(); // Clean up existing watcher
    
    this.watcher = chokidar.watch(rootPath, {
        ignored: [
            /(^|[\/\\])\../, // Ignore hidden files
            /\.tmp$/, /\.swp$/, /~$/, // Ignore temp files
            /node_modules/, // Ignore common directories
        ],
        persistent: true,
        ignoreInitial: true,
        followSymlinks: false,
        depth: 10, // Reasonable depth limit
        awaitWriteFinish: {
            stabilityThreshold: 500,
            pollInterval: 100
        }
    });
    
    this.setupEventHandlers();
}
```

### 4.5.2 Event Handler Setup
```typescript
private setupEventHandlers(): void {
    if (!this.watcher) return;
    
    this.watcher
        .on('add', (filePath) => this.handleFileAdded(filePath))
        .on('change', (filePath) => this.handleFileChanged(filePath))
        .on('unlink', (filePath) => this.handleFileDeleted(filePath))
        .on('addDir', (dirPath) => this.handleDirectoryAdded(dirPath))
        .on('unlinkDir', (dirPath) => this.handleDirectoryDeleted(dirPath))
        .on('error', (error) => this.handleWatcherError(error));
}
```

### 4.5.3 Debounced Event Processing
```typescript
private debouncedEvents = new Map<string, NodeJS.Timeout>();

private handleFileChanged(filePath: string): void {
    // Clear existing timeout for this file
    const existingTimeout = this.debouncedEvents.get(filePath);
    if (existingTimeout) {
        clearTimeout(existingTimeout);
    }
    
    // Set new debounced timeout
    const timeout = setTimeout(() => {
        this.debouncedEvents.delete(filePath);
        if (this.isMarkdownFile(filePath)) {
            this.eventEmitter.emit('fileChanged', filePath);
        }
    }, this.debounceMs);
    
    this.debouncedEvents.set(filePath, timeout);
}
```

### 4.5.4 Integration with PromptManager
```typescript
// In PromptStoreProvider or main coordinator
private setupFileWatching(): void {
    this.fileWatcher.on('fileAdded', async (filePath) => {
        try {
            const prompt = await this.promptManager.loadPrompt(filePath);
            this.addPromptToStore(prompt);
            this.notifyUI('promptAdded', prompt);
        } catch (error) {
            this.logger.error('Failed to load new prompt:', error);
        }
    });
    
    this.fileWatcher.on('fileChanged', async (filePath) => {
        try {
            const prompt = await this.promptManager.loadPrompt(filePath);
            this.updatePromptInStore(prompt);
            this.notifyUI('promptUpdated', prompt);
        } catch (error) {
            this.logger.error('Failed to reload changed prompt:', error);
        }
    });
    
    this.fileWatcher.on('fileDeleted', (filePath) => {
        this.removePromptFromStore(filePath);
        this.notifyUI('promptDeleted', filePath);
    });
}
```

## Performance Considerations

### 4.6 Optimization Strategies
- Use efficient file watching library (chokidar)
- Implement event coalescing for rapid changes
- Limit watch depth to prevent excessive monitoring
- Use polling fallback for network drives
- Monitor watcher resource usage

### 4.7 Resource Management
- Properly dispose of watchers when not needed
- Clear event listeners and timers
- Monitor memory usage for long-running watches
- Handle file system resource limits

## Configuration Options

### 4.8 Watcher Settings
```typescript
interface FileWatcherConfig {
    enabled: boolean;
    debounceMs: number;
    maxDepth: number;
    followSymlinks: boolean;
    ignorePatterns: string[];
    usePolling: boolean;
    pollingInterval: number;
}
```

### 4.9 VS Code Settings
```json
{
  "wu-wei.promptStore.fileWatcher.enabled": true,
  "wu-wei.promptStore.fileWatcher.debounceMs": 500,
  "wu-wei.promptStore.fileWatcher.maxDepth": 10,
  "wu-wei.promptStore.fileWatcher.ignorePatterns": [
    "*.tmp",
    "*.swp",
    "*~",
    ".git/**"
  ]
}
```

## Testing Requirements

### 4.10 Unit Tests
Test scenarios for:
- Basic file watching setup and teardown
- Event debouncing functionality
- File filtering logic
- Error handling and recovery
- Resource cleanup

### 4.11 Integration Tests
- Real file system operations
- Multiple rapid file changes
- Directory structure changes
- Watcher lifecycle management
- Performance under load

### 4.12 Test Utilities
```typescript
class FileSystemTestHelper {
    async createTestFile(path: string, content: string): Promise<void>
    async modifyTestFile(path: string, content: string): Promise<void>
    async deleteTestFile(path: string): Promise<void>
    async createTestDirectory(path: string): Promise<void>
    waitForEvents(count: number, timeoutMs?: number): Promise<void>
}
```

## Acceptance Criteria
- [ ] Successfully monitors directory for file changes
- [ ] Debounces rapid file system events appropriately
- [ ] Handles all types of file system operations
- [ ] Recovers gracefully from watcher errors
- [ ] Integrates smoothly with PromptManager
- [ ] Respects configuration settings
- [ ] Performance remains stable during intensive file operations
- [ ] Properly cleans up resources when disabled
- [ ] All unit and integration tests pass
- [ ] Works consistently across different operating systems

## Dependencies
- **Step 1**: Project setup completed
- **Step 2**: MetadataParser implemented
- **Step 3**: File system operations implemented
- Chokidar library for file watching
- Node.js EventEmitter for event handling

## Estimated Effort
**4-5 hours**

## Files to Implement
1. `src/promptStore/PromptFileWatcher.ts` (main implementation)
2. `src/promptStore/types.ts` (add file watcher types)
3. `test/promptStore/PromptFileWatcher.test.ts` (unit tests)
4. `test/promptStore/integration/fileWatching.test.ts` (integration tests)
5. `test/utils/FileSystemTestHelper.ts` (test utilities)

## Next Step
Proceed to **Step 5: Basic Configuration Management** to handle user settings and directory selection.
