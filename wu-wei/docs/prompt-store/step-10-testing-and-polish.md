# Step 10: Testing and Polish

## Overview
Comprehensive testing, performance optimization, and user experience polish for the Prompt Store feature. This final step ensures production readiness and smooth user experience.

## Objectives
- Create comprehensive test suite covering all functionality
- Optimize performance for large prompt collections
- Polish user interface and interactions
- Add comprehensive error handling and recovery
- Implement accessibility features
- Create user documentation and examples
- Performance benchmarking and optimization

## Tasks

### 10.1 Comprehensive Test Suite
Create complete test coverage for all components:

```typescript
// Test structure overview
test/
├── unit/
│   ├── MetadataParser.test.ts
│   ├── PromptManager.test.ts
│   ├── PromptFileWatcher.test.ts
│   ├── ConfigurationManager.test.ts
│   ├── FileOperationManager.test.ts
│   ├── TemplateManager.test.ts
│   └── PromptTreeManager.test.ts
├── integration/
│   ├── promptStoreWorkflow.test.ts
│   ├── fileSystemOperations.test.ts
│   ├── webviewCommunication.test.ts
│   └── extensionIntegration.test.ts
├── e2e/
│   ├── userWorkflows.test.ts
│   └── performanceTests.test.ts
└── fixtures/
    ├── sample-prompts/
    ├── test-configurations/
    └── mock-data/
```

### 10.2 Unit Test Implementation
Comprehensive unit tests for core components:

```typescript
// MetadataParser.test.ts
describe('MetadataParser', () => {
    let parser: MetadataParser;
    
    beforeEach(() => {
        parser = new MetadataParser();
    });
    
    describe('parseContent', () => {
        test('should parse valid YAML frontmatter', () => {
            const content = `---
title: "Test Prompt"
tags: ["test", "sample"]
---

# Test Content
This is a test prompt.`;
            
            const result = parser.parseContent(content);
            
            expect(result.success).toBe(true);
            expect(result.prompt?.metadata.title).toBe('Test Prompt');
            expect(result.prompt?.metadata.tags).toEqual(['test', 'sample']);
            expect(result.prompt?.content).toBe('# Test Content\nThis is a test prompt.');
        });
        
        test('should handle content without frontmatter', () => {
            const content = '# Simple Prompt\nJust content, no metadata.';
            
            const result = parser.parseContent(content);
            
            expect(result.success).toBe(true);
            expect(result.prompt?.content).toBe(content);
            expect(Object.keys(result.prompt?.metadata || {})).toHaveLength(0);
        });
        
        test('should handle malformed YAML', () => {
            const content = `---
title: "Test Prompt
invalid: yaml: structure
---

Content here`;
            
            const result = parser.parseContent(content);
            
            expect(result.success).toBe(false);
            expect(result.errors).toHaveLength(1);
            expect(result.errors[0].type).toBe('YAML_PARSE_ERROR');
        });
        
        test('should validate required fields', () => {
            const content = `---
description: "Missing title"
---

Content`;
            
            const result = parser.parseContent(content);
            
            if (result.success) {
                const validation = parser.validateMetadata(result.prompt!.metadata);
                expect(validation.isValid).toBe(true); // title is not required
            }
        });
    });
    
    describe('performance', () => {
        test('should handle large files efficiently', () => {
            const largeContent = `---
title: "Large Prompt"
---

${'# Large Content\n'.repeat(10000)}`;
            
            const startTime = Date.now();
            const result = parser.parseContent(largeContent);
            const endTime = Date.now();
            
            expect(result.success).toBe(true);
            expect(endTime - startTime).toBeLessThan(100); // Should parse in <100ms
        });
    });
});

// FileOperationManager.test.ts
describe('FileOperationManager', () => {
    let fileOps: FileOperationManager;
    let mockPromptManager: jest.Mocked<PromptManager>;
    let mockConfigManager: jest.Mocked<ConfigurationManager>;
    let testDir: string;
    
    beforeEach(async () => {
        testDir = await fs.mkdtemp(path.join(os.tmpdir(), 'prompt-store-test-'));
        
        mockConfigManager = createMockConfigManager({
            rootDirectory: testDir
        });
        
        mockPromptManager = createMockPromptManager();
        
        fileOps = new FileOperationManager(
            mockPromptManager,
            mockConfigManager,
            createMockLogger()
        );
    });
    
    afterEach(async () => {
        await fs.rm(testDir, { recursive: true, force: true });
    });
    
    describe('createNewPrompt', () => {
        test('should create prompt with basic options', async () => {
            const options = {
                name: 'Test Prompt',
                category: 'testing'
            };
            
            const result = await fileOps.createNewPrompt(options);
            
            expect(result.success).toBe(true);
            expect(result.filePath).toBeDefined();
            
            const content = await fs.readFile(result.filePath!, 'utf8');
            expect(content).toContain('title: "Test Prompt"');
            expect(content).toContain('category: testing');
        });
        
        test('should prevent duplicate names', async () => {
            const options = { name: 'Duplicate Test' };
            
            // Create first prompt
            const result1 = await fileOps.createNewPrompt(options);
            expect(result1.success).toBe(true);
            
            // Try to create duplicate
            const result2 = await fileOps.createNewPrompt(options);
            expect(result2.success).toBe(false);
            expect(result2.error).toContain('already exists');
        });
    });
    
    describe('deletePrompt', () => {
        test('should delete existing prompt', async () => {
            // Create a test prompt first
            const testFile = path.join(testDir, 'test-prompt.md');
            await fs.writeFile(testFile, '# Test\nContent here');
            
            // Mock user confirmation
            const mockShowWarningMessage = jest.spyOn(vscode.window, 'showWarningMessage')
                .mockResolvedValue('Delete' as any);
            
            const result = await fileOps.deletePrompt(testFile);
            
            expect(result.success).toBe(true);
            expect(await fs.access(testFile).catch(() => false)).toBe(false);
            
            mockShowWarningMessage.mockRestore();
        });
    });
});
```

### 10.3 Integration Test Implementation
End-to-end workflow testing:

```typescript
// promptStoreWorkflow.test.ts
describe('Prompt Store Workflow Integration', () => {
    let extension: vscode.Extension<any>;
    let promptStoreManager: PromptStoreManager;
    let testWorkspace: string;
    
    beforeAll(async () => {
        // Setup test workspace
        testWorkspace = await createTestWorkspace();
        
        // Activate extension
        extension = vscode.extensions.getExtension('wu-wei.extension')!;
        await extension.activate();
        
        promptStoreManager = extension.exports.promptStoreManager;
    });
    
    afterAll(async () => {
        await cleanupTestWorkspace(testWorkspace);
    });
    
    test('complete user workflow: setup, create, edit, delete', async () => {
        // 1. Configure directory
        await vscode.workspace.getConfiguration('wu-wei.promptStore')
            .update('rootDirectory', testWorkspace, vscode.ConfigurationTarget.Workspace);
        
        // Wait for configuration to take effect
        await waitForCondition(() => promptStoreManager.isConfigured(), 5000);
        
        // 2. Create new prompt
        const createResult = await promptStoreManager.createPrompt({
            name: 'Integration Test Prompt',
            category: 'testing'
        });
        
        expect(createResult.success).toBe(true);
        expect(createResult.filePath).toBeDefined();
        
        // 3. Verify prompt appears in tree
        const prompts = await promptStoreManager.getAllPrompts();
        expect(prompts).toHaveLength(1);
        expect(prompts[0].metadata.title).toBe('Integration Test Prompt');
        
        // 4. Open prompt in editor
        await promptStoreManager.openPrompt(createResult.filePath!);
        
        // Verify editor opened
        const activeEditor = vscode.window.activeTextEditor;
        expect(activeEditor?.document.uri.fsPath).toBe(createResult.filePath);
        
        // 5. Modify prompt and save
        const edit = new vscode.WorkspaceEdit();
        edit.replace(
            activeEditor!.document.uri,
            new vscode.Range(0, 0, activeEditor!.document.lineCount, 0),
            '---\ntitle: "Modified Prompt"\n---\n\n# Modified Content\nThis was changed.'
        );
        
        await vscode.workspace.applyEdit(edit);
        await activeEditor!.document.save();
        
        // 6. Verify changes reflected
        await waitForCondition(async () => {
            const updatedPrompts = await promptStoreManager.getAllPrompts();
            return updatedPrompts[0].metadata.title === 'Modified Prompt';
        }, 3000);
        
        // 7. Delete prompt
        const deleteResult = await promptStoreManager.deletePrompt(createResult.filePath!);
        expect(deleteResult.success).toBe(true);
        
        // 8. Verify prompt removed
        await waitForCondition(async () => {
            const finalPrompts = await promptStoreManager.getAllPrompts();
            return finalPrompts.length === 0;
        }, 3000);
    });
    
    test('file watcher integration', async () => {
        // Create file directly in file system
        const testFile = path.join(testWorkspace, 'external-prompt.md');
        await fs.writeFile(testFile, '# External Prompt\nCreated outside VS Code');
        
        // Wait for file watcher to detect
        await waitForCondition(async () => {
            const prompts = await promptStoreManager.getAllPrompts();
            return prompts.some(p => p.filePath === testFile);
        }, 3000);
        
        // Modify file externally
        await fs.writeFile(testFile, '# Modified External\nChanged content');
        
        // Wait for update to be detected
        await waitForCondition(async () => {
            const prompts = await promptStoreManager.getAllPrompts();
            const prompt = prompts.find(p => p.filePath === testFile);
            return prompt?.content.includes('Modified External');
        }, 3000);
        
        // Delete file externally
        await fs.unlink(testFile);
        
        // Verify removal detected
        await waitForCondition(async () => {
            const prompts = await promptStoreManager.getAllPrompts();
            return !prompts.some(p => p.filePath === testFile);
        }, 3000);
    });
});
```

### 10.4 Performance Optimization
Optimize for large prompt collections:

```typescript
// PerformanceOptimizer.ts
export class PerformanceOptimizer {
    private static readonly LARGE_COLLECTION_THRESHOLD = 500;
    private static readonly VIRTUAL_SCROLL_THRESHOLD = 100;
    
    static shouldUseVirtualScrolling(itemCount: number): boolean {
        return itemCount > this.VIRTUAL_SCROLL_THRESHOLD;
    }
    
    static shouldUseLazyLoading(itemCount: number): boolean {
        return itemCount > this.LARGE_COLLECTION_THRESHOLD;
    }
    
    // Debounced search to prevent excessive filtering
    static createDebouncedSearch(callback: Function, delay: number = 300): Function {
        let timeoutId: NodeJS.Timeout;
        
        return (...args: any[]) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => callback(...args), delay);
        };
    }
    
    // Batch file operations for better performance
    static async batchProcess<T>(
        items: T[],
        processor: (item: T) => Promise<any>,
        batchSize: number = 10
    ): Promise<any[]> {
        const results: any[] = [];
        
        for (let i = 0; i < items.length; i += batchSize) {
            const batch = items.slice(i, i + batchSize);
            const batchResults = await Promise.all(batch.map(processor));
            results.push(...batchResults);
            
            // Small delay between batches to prevent blocking
            if (i + batchSize < items.length) {
                await new Promise(resolve => setTimeout(resolve, 10));
            }
        }
        
        return results;
    }
}

// Optimized tree rendering
export class OptimizedTreeRenderer {
    private renderCache = new Map<string, string>();
    private lastRenderHash = '';
    
    render(treeData: TreeNode[], searchQuery: string, filters: TreeFilters): string {
        // Create hash of current render state
        const renderHash = this.createRenderHash(treeData, searchQuery, filters);
        
        // Return cached result if nothing changed
        if (renderHash === this.lastRenderHash && this.renderCache.has(renderHash)) {
            return this.renderCache.get(renderHash)!;
        }
        
        // Render tree
        const html = this.renderTree(treeData);
        
        // Cache result
        this.renderCache.set(renderHash, html);
        this.lastRenderHash = renderHash;
        
        // Limit cache size
        if (this.renderCache.size > 50) {
            const firstKey = this.renderCache.keys().next().value;
            this.renderCache.delete(firstKey);
        }
        
        return html;
    }
    
    private createRenderHash(treeData: TreeNode[], searchQuery: string, filters: TreeFilters): string {
        return JSON.stringify({
            treeData: treeData.map(n => ({ id: n.id, name: n.name, type: n.type })),
            searchQuery,
            filters
        });
    }
}
```

### 10.5 User Interface Polish
Enhance user experience with smooth interactions:

```typescript
// UI Enhancement CSS
const enhancedStyles = `
/* Smooth animations */
.tree-node {
    transition: all 0.2s ease;
}

.tree-node:hover {
    transform: translateX(2px);
}

/* Loading states */
.tree-loading {
    position: relative;
    opacity: 0.6;
}

.tree-loading::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
    animation: loading-shimmer 1.5s infinite;
}

@keyframes loading-shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

/* Enhanced search */
.search-section {
    position: relative;
}

.search-results-count {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 11px;
    opacity: 0.7;
}

/* Improved badges */
.metadata-badges {
    flex-wrap: wrap;
    gap: 2px;
}

.badge {
    font-size: 9px;
    padding: 2px 4px;
    border-radius: 4px;
    white-space: nowrap;
}

/* Context menu styles */
.context-menu {
    position: fixed;
    background: var(--vscode-menu-background);
    border: 1px solid var(--vscode-menu-border);
    border-radius: 4px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    z-index: 1000;
    min-width: 160px;
}

.context-menu-item {
    padding: 8px 12px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
}

.context-menu-item:hover {
    background: var(--vscode-menu-selectionBackground);
}

.context-menu-separator {
    height: 1px;
    background: var(--vscode-menu-separatorBackground);
    margin: 4px 0;
}
`;

// Enhanced JavaScript interactions
const uiEnhancements = `
// Context menu functionality
class ContextMenuManager {
    constructor(container) {
        this.container = container;
        this.currentMenu = null;
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        this.container.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            const treeNode = e.target.closest('.tree-node');
            if (treeNode) {
                this.showContextMenu(e, treeNode);
            }
        });
        
        document.addEventListener('click', () => {
            this.hideContextMenu();
        });
    }
    
    showContextMenu(event, treeNode) {
        this.hideContextMenu();
        
        const menu = this.createContextMenu(treeNode);
        menu.style.left = event.pageX + 'px';
        menu.style.top = event.pageY + 'px';
        
        document.body.appendChild(menu);
        this.currentMenu = menu;
    }
    
    createContextMenu(treeNode) {
        const menu = document.createElement('div');
        menu.className = 'context-menu';
        
        const menuItems = this.getMenuItems(treeNode);
        
        menuItems.forEach(item => {
            if (item.separator) {
                const separator = document.createElement('div');
                separator.className = 'context-menu-separator';
                menu.appendChild(separator);
            } else {
                const menuItem = document.createElement('div');
                menuItem.className = 'context-menu-item';
                menuItem.innerHTML = \`<span class="icon">\${item.icon}</span><span>\${item.label}</span>\`;
                menuItem.addEventListener('click', () => {
                    item.action(treeNode);
                    this.hideContextMenu();
                });
                menu.appendChild(menuItem);
            }
        });
        
        return menu;
    }
    
    getMenuItems(treeNode) {
        const isFile = treeNode.dataset.type === 'file';
        
        if (isFile) {
            return [
                { icon: '📝', label: 'Open', action: (node) => this.openPrompt(node) },
                { icon: '👁️', label: 'Preview', action: (node) => this.previewPrompt(node) },
                { separator: true },
                { icon: '📋', label: 'Duplicate', action: (node) => this.duplicatePrompt(node) },
                { icon: '✏️', label: 'Rename', action: (node) => this.renamePrompt(node) },
                { icon: '📁', label: 'Move to Category', action: (node) => this.movePrompt(node) },
                { separator: true },
                { icon: '🗑️', label: 'Delete', action: (node) => this.deletePrompt(node) }
            ];
        } else {
            return [
                { icon: '➕', label: 'New Prompt Here', action: (node) => this.newPromptInCategory(node) },
                { icon: '📁', label: 'New Subcategory', action: (node) => this.newSubcategory(node) },
                { separator: true },
                { icon: '✏️', label: 'Rename Category', action: (node) => this.renameCategory(node) },
                { icon: '🗑️', label: 'Delete Category', action: (node) => this.deleteCategory(node) }
            ];
        }
    }
}

// Keyboard navigation
class KeyboardNavigationManager {
    constructor(treeContainer) {
        this.treeContainer = treeContainer;
        this.selectedIndex = 0;
        this.setupKeyboardHandlers();
    }
    
    setupKeyboardHandlers() {
        this.treeContainer.addEventListener('keydown', (e) => {
            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    this.navigateDown();
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    this.navigateUp();
                    break;
                case 'Enter':
                    e.preventDefault();
                    this.activateSelected();
                    break;
                case 'Space':
                    e.preventDefault();
                    this.toggleSelected();
                    break;
            }
        });
    }
    
    navigateDown() {
        const nodes = this.getVisibleNodes();
        if (this.selectedIndex < nodes.length - 1) {
            this.selectedIndex++;
            this.updateSelection();
        }
    }
    
    navigateUp() {
        if (this.selectedIndex > 0) {
            this.selectedIndex--;
            this.updateSelection();
        }
    }
    
    updateSelection() {
        const nodes = this.getVisibleNodes();
        nodes.forEach((node, index) => {
            node.classList.toggle('keyboard-selected', index === this.selectedIndex);
        });
        
        // Scroll into view if needed
        const selectedNode = nodes[this.selectedIndex];
        if (selectedNode) {
            selectedNode.scrollIntoView({ block: 'nearest' });
        }
    }
}
`;
```

### 10.6 Accessibility Features
Implement accessibility best practices:

```typescript
// Accessibility enhancements
const accessibilityFeatures = `
/* ARIA attributes and roles */
.prompt-tree {
    role: 'tree';
    aria-label: 'Prompt Store Tree';
}

.tree-node {
    role: 'treeitem';
    tabindex: '-1';
    aria-selected: 'false';
}

.tree-node.selected {
    aria-selected: 'true';
}

.tree-node[data-type='folder'] {
    aria-expanded: 'false';
}

.tree-node[data-type='folder'].expanded {
    aria-expanded: 'true';
}

/* High contrast support */
@media (prefers-contrast: high) {
    .tree-node {
        border: 1px solid transparent;
    }
    
    .tree-node:focus {
        border-color: var(--vscode-focusBorder);
        outline: 2px solid var(--vscode-focusBorder);
    }
    
    .badge {
        border: 1px solid var(--vscode-foreground);
    }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
    .tree-node {
        transition: none !important;
    }
    
    .loading-spinner {
        animation: none !important;
    }
}

/* Screen reader support */
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}
`;

// JavaScript accessibility features
const accessibilityJS = `
class AccessibilityManager {
    constructor(treeContainer) {
        this.treeContainer = treeContainer;
        this.setupAccessibility();
    }
    
    setupAccessibility() {
        // Set up proper ARIA attributes
        this.updateAriaAttributes();
        
        // Handle focus management
        this.setupFocusManagement();
        
        // Provide screen reader announcements
        this.setupScreenReaderAnnouncements();
    }
    
    updateAriaAttributes() {
        const treeNodes = this.treeContainer.querySelectorAll('.tree-node');
        
        treeNodes.forEach((node, index) => {
            // Set tree item attributes
            node.setAttribute('aria-level', this.getNodeLevel(node));
            node.setAttribute('aria-setsize', this.getSiblingCount(node));
            node.setAttribute('aria-posinset', this.getPositionInSet(node));
            
            // Set expanded state for folders
            if (node.dataset.type === 'folder') {
                const isExpanded = node.classList.contains('expanded');
                node.setAttribute('aria-expanded', isExpanded.toString());
            }
        });
    }
    
    announceChange(message) {
        const announcement = document.createElement('div');
        announcement.className = 'sr-only';
        announcement.setAttribute('aria-live', 'polite');
        announcement.textContent = message;
        
        document.body.appendChild(announcement);
        
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
    }
    
    setupFocusManagement() {
        this.treeContainer.addEventListener('focus', (e) => {
            if (e.target === this.treeContainer) {
                // Focus first tree item when container receives focus
                const firstNode = this.treeContainer.querySelector('.tree-node');
                if (firstNode) {
                    firstNode.focus();
                }
            }
        });
    }
}
`;
```

### 10.7 Error Recovery and Resilience
Implement robust error recovery:

```typescript
export class ErrorRecoveryManager {
    private recoveryStrategies = new Map<string, Function>();
    
    constructor(private logger: Logger) {
        this.setupRecoveryStrategies();
    }
    
    private setupRecoveryStrategies(): void {
        this.recoveryStrategies.set('FILE_WATCHER_FAILED', async () => {
            this.logger.warn('File watcher failed, falling back to manual refresh');
            return { strategy: 'manual_refresh', success: true };
        });
        
        this.recoveryStrategies.set('METADATA_PARSE_ERROR', async (error, filePath) => {
            this.logger.warn(`Metadata parse error in ${filePath}, treating as plain markdown`);
            return { strategy: 'ignore_metadata', success: true };
        });
        
        this.recoveryStrategies.set('DIRECTORY_ACCESS_ERROR', async (error, directory) => {
            this.logger.error(`Cannot access directory ${directory}, prompting user`);
            const action = await vscode.window.showErrorMessage(
                `Cannot access prompt directory: ${directory}`,
                'Select New Directory',
                'Disable Prompt Store'
            );
            
            if (action === 'Select New Directory') {
                await vscode.commands.executeCommand('wu-wei.promptStore.selectDirectory');
                return { strategy: 'directory_reselection', success: true };
            } else if (action === 'Disable Prompt Store') {
                await vscode.workspace.getConfiguration('wu-wei.promptStore')
                    .update('enabled', false, vscode.ConfigurationTarget.Workspace);
                return { strategy: 'disable_feature', success: true };
            }
            
            return { strategy: 'no_action', success: false };
        });
    }
    
    async handleError(errorType: string, error: Error, context?: any): Promise<RecoveryResult> {
        const strategy = this.recoveryStrategies.get(errorType);
        
        if (strategy) {
            try {
                return await strategy(error, context);
            } catch (recoveryError) {
                this.logger.error('Recovery strategy failed:', recoveryError);
                return { strategy: 'recovery_failed', success: false };
            }
        }
        
        return { strategy: 'no_strategy', success: false };
    }
}

interface RecoveryResult {
    strategy: string;
    success: boolean;
    data?: any;
}
```

### 10.8 Performance Benchmarking
Create performance tests and benchmarks:

```typescript
// performanceTests.test.ts
describe('Performance Benchmarks', () => {
    test('tree rendering performance with large dataset', async () => {
        // Generate large dataset
        const largePromptSet = generateTestPrompts(1000);
        const treeManager = new PromptTreeManager();
        
        // Benchmark tree building
        const buildStart = performance.now();
        const tree = treeManager.buildTree(largePromptSet);
        const buildEnd = performance.now();
        
        expect(buildEnd - buildStart).toBeLessThan(100); // Should build in <100ms
        
        // Benchmark search filtering  
        const searchStart = performance.now();
        const filteredTree = treeManager.filterTree(tree, 'test', {});
        const searchEnd = performance.now();
        
        expect(searchEnd - searchStart).toBeLessThan(50); // Should filter in <50ms
    });
    
    test('file operations performance', async () => {
        const fileOps = new FileOperationManager();
        const testDir = await createTestDirectory();
        
        // Benchmark batch creation
        const createStart = performance.now();
        const createPromises = Array.from({ length: 100 }, (_, i) => 
            fileOps.createNewPrompt({ name: `Prompt ${i}` })
        );
        await Promise.all(createPromises);
        const createEnd = performance.now();
        
        expect(createEnd - createStart).toBeLessThan(5000); // 100 prompts in <5s
        
        // Benchmark batch loading
        const loadStart = performance.now();
        const prompts = await fileOps.loadAllPrompts(testDir);
        const loadEnd = performance.now();
        
        expect(loadEnd - loadStart).toBeLessThan(1000); // Load 100 prompts in <1s
        expect(prompts).toHaveLength(100);
    });
    
    test('memory usage stability', async () => {
        const initialMemory = process.memoryUsage().heapUsed;
        
        // Create and destroy many managers
        for (let i = 0; i < 100; i++) {
            const manager = new PromptStoreManager();
            await manager.initialize();
            manager.dispose();
        }
        
        // Force garbage collection if available
        if (global.gc) {
            global.gc();
        }
        
        const finalMemory = process.memoryUsage().heapUsed;
        const memoryIncrease = finalMemory - initialMemory;
        
        // Memory increase should be minimal (less than 10MB)
        expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024);
    });
});
```

### 10.9 User Documentation
Create comprehensive user documentation:

```markdown
# Wu Wei Prompt Store User Guide

## Getting Started

### Initial Setup
1. Open VS Code and ensure Wu Wei extension is installed
2. Open the Wu Wei Prompt Store panel from the sidebar
3. Click "Configure Directory" to select your prompts folder
4. Start creating and organizing your prompts!

## Creating Prompts

### Basic Prompt Creation
1. Click the "➕ New Prompt" button
2. Enter a name for your prompt
3. Optionally select a category
4. Choose a template or start from scratch
5. Edit your prompt in the VS Code editor

### Using Templates
Wu Wei provides several built-in templates:
- **Basic**: Simple prompt with metadata
- **Meeting Notes**: Structured meeting documentation
- **Code Review**: Code review prompt template
- **Feature Spec**: Feature specification template

### Adding Metadata
Add YAML frontmatter to your prompts for better organization:

\`\`\`yaml
---
title: "My Awesome Prompt"
description: "This prompt helps with..."
tags: ["productivity", "automation"]
category: "work"
author: "Your Name"
parameters:
  - name: "project_name"
    type: "string"
    required: true
  - name: "priority"
    type: "string"
    options: ["high", "medium", "low"]
    default: "medium"
---
\`\`\`

## Organizing Prompts

### Categories and Folders
- Create folders in your prompt directory for categories
- Prompts automatically organize by folder structure
- Use the category field in metadata for additional organization

### Tags and Search
- Add tags to your prompt metadata
- Use the search box to find prompts quickly
- Filter by category or tags using the dropdown filters

## Advanced Features

### Keyboard Shortcuts
- `Ctrl/Cmd + Shift + P` → "Wu Wei: New Prompt"
- `F2` → Rename selected prompt
- `Delete` → Delete selected prompt

### Batch Operations
- Select multiple prompts with Ctrl/Cmd + Click
- Use context menu for batch operations
- Export/import prompts for sharing

### Integration with Chat
- Right-click any prompt → "Insert into Chat"
- Prompts automatically integrate with Wu Wei chat features
```

## Acceptance Criteria
- [ ] Comprehensive test suite with >90% code coverage
- [ ] All performance benchmarks pass target thresholds
- [ ] UI polish and smooth animations implemented
- [ ] Accessibility features meet WCAG 2.1 guidelines
- [ ] Error recovery handles all common failure scenarios
- [ ] User documentation is complete and accurate
- [ ] Memory usage remains stable under load
- [ ] Performance is acceptable with 1000+ prompts
- [ ] All integration tests pass consistently
- [ ] Cross-platform compatibility verified

## Dependencies
- **Step 9**: Extension integration must be completed
- All previous implementation steps
- Testing frameworks and utilities
- Performance monitoring tools

## Estimated Effort
**10-12 hours**

## Files to Implement
1. `test/unit/` (comprehensive unit tests)
2. `test/integration/` (integration tests)
3. `test/e2e/` (end-to-end tests)
4. `src/promptStore/PerformanceOptimizer.ts` (performance optimizations)
5. `src/promptStore/ErrorRecoveryManager.ts` (error recovery)
6. `src/promptStore/AccessibilityManager.ts` (accessibility features)
7. `docs/prompt-store-user-guide.md` (user documentation)
8. `test/performance/benchmarks.test.ts` (performance tests)
9. Enhanced CSS and JavaScript for UI polish
10. Example prompts and templates

## Final Deliverable
A production-ready Prompt Store feature that seamlessly integrates with the Wu Wei extension, providing users with a powerful, intuitive, and performant prompt management system that embodies the Wu Wei philosophy of effortless automation.
