# Step 6: Basic Webview UI

## Overview
Create the foundational webview UI for the Prompt Store panel, including HTML structure, basic styling, and JavaScript communication with the extension.

## Objectives
- Create responsive webview layout
- Implement VS Code webview messaging
- Build basic UI components (tree view, buttons, search)
- Establish CSS styling following VS Code themes
- Set up communication between webview and extension

## Tasks

### 6.1 Webview Provider Implementation
Implement `PromptStoreProvider` class:

```typescript
class PromptStoreProvider implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;
    private disposables: vscode.Disposable[] = [];
    
    resolveWebviewView(webviewView: vscode.WebviewView): void
    refresh(): void
    postMessage(message: any): void
    private setupMessageHandling(): void
    private getHtmlContent(): string
}
```

### 6.2 HTML Structure
Create semantic HTML structure in `webview/promptStore/index.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wu Wei Prompt Store</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="prompt-store-container">
        <header class="store-header">
            <h2>Wu Wei Prompt Store</h2>
            <div class="header-actions">
                <button id="configure-directory" class="action-button">
                    📁 Configure Directory
                </button>
            </div>
        </header>
        
        <div class="search-section">
            <input type="text" id="search-input" placeholder="🔍 Search prompts..." />
            <div class="search-filters">
                <select id="category-filter">
                    <option value="">All Categories</option>
                </select>
                <select id="tag-filter">
                    <option value="">All Tags</option>
                </select>
            </div>
        </div>
        
        <main class="prompt-list-container">
            <div id="prompt-tree" class="prompt-tree">
                <!-- Prompt tree will be populated dynamically -->
            </div>
            
            <div id="empty-state" class="empty-state" style="display: none;">
                <div class="empty-content">
                    <h3>No Prompt Directory Configured</h3>
                    <p>Configure a directory to start managing your prompts</p>
                    <button id="configure-directory-empty" class="primary-button">
                        📁 Select Directory
                    </button>
                </div>
            </div>
            
            <div id="loading-state" class="loading-state" style="display: none;">
                <div class="loading-spinner"></div>
                <p>Loading prompts...</p>
            </div>
        </main>
        
        <footer class="store-footer">
            <div class="footer-actions">
                <button id="new-prompt" class="action-button">➕ New Prompt</button>
                <button id="refresh-store" class="action-button">🔄 Refresh</button>
            </div>
        </footer>
    </div>
    
    <script src="main.js"></script>
</body>
</html>
```

### 6.3 CSS Styling
Create VS Code-compatible styling in `webview/promptStore/style.css`:

```css
/* VS Code theme variables */
:root {
    --vscode-font-family: var(--vscode-font-family);
    --vscode-font-size: var(--vscode-font-size);
    --vscode-foreground: var(--vscode-foreground);
    --vscode-background: var(--vscode-sideBar-background);
    --vscode-button-background: var(--vscode-button-background);
    --vscode-button-foreground: var(--vscode-button-foreground);
    --vscode-input-background: var(--vscode-input-background);
    --vscode-input-border: var(--vscode-input-border);
    --vscode-list-hoverBackground: var(--vscode-list-hoverBackground);
    --vscode-list-activeSelectionBackground: var(--vscode-list-activeSelectionBackground);
}

body {
    font-family: var(--vscode-font-family);
    font-size: var(--vscode-font-size);
    color: var(--vscode-foreground);
    background: var(--vscode-background);
    margin: 0;
    padding: 0;
    height: 100vh;
    overflow: hidden;
}

.prompt-store-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

.store-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    border-bottom: 1px solid var(--vscode-input-border);
}

.store-header h2 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
}

.search-section {
    padding: 8px 12px;
    border-bottom: 1px solid var(--vscode-input-border);
}

#search-input {
    width: 100%;
    padding: 6px 8px;
    background: var(--vscode-input-background);
    border: 1px solid var(--vscode-input-border);
    color: var(--vscode-foreground);
    border-radius: 3px;
    box-sizing: border-box;
}

.search-filters {
    display: flex;
    gap: 8px;
    margin-top: 8px;
}

.search-filters select {
    flex: 1;
    padding: 4px 6px;
    background: var(--vscode-input-background);
    border: 1px solid var(--vscode-input-border);
    color: var(--vscode-foreground);
    border-radius: 3px;
}

.prompt-list-container {
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;
}

.prompt-tree {
    padding: 0 12px;
}

.tree-node {
    display: flex;
    align-items: center;
    padding: 4px 8px;
    cursor: pointer;
    border-radius: 3px;
    user-select: none;
}

.tree-node:hover {
    background: var(--vscode-list-hoverBackground);
}

.tree-node.selected {
    background: var(--vscode-list-activeSelectionBackground);
}

.tree-node.folder {
    font-weight: 500;
}

.tree-node .icon {
    margin-right: 6px;
    font-size: 12px;
}

.tree-node .name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.tree-children {
    margin-left: 16px;
}

.empty-state, .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 200px;
    text-align: center;
    padding: 20px;
}

.empty-content h3 {
    margin: 0 0 8px 0;
    font-size: 16px;
}

.empty-content p {
    margin: 0 0 16px 0;
    opacity: 0.8;
}

.loading-spinner {
    width: 24px;
    height: 24px;
    border: 2px solid var(--vscode-input-border);
    border-top: 2px solid var(--vscode-button-background);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 12px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.store-footer {
    border-top: 1px solid var(--vscode-input-border);
    padding: 8px 12px;
}

.footer-actions {
    display: flex;
    gap: 8px;
}

.action-button, .primary-button {
    padding: 6px 12px;
    border: 1px solid var(--vscode-input-border);
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    border-radius: 3px;
    cursor: pointer;
    font-size: 12px;
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

.action-button:hover, .primary-button:hover {
    opacity: 0.9;
}

.primary-button {
    background: var(--vscode-button-background);
    border-color: var(--vscode-button-background);
}

@media (max-width: 300px) {
    .search-filters {
        flex-direction: column;
    }
    
    .footer-actions {
        flex-direction: column;
    }
}
```

### 6.4 JavaScript Communication
Implement webview JavaScript in `webview/promptStore/main.js`:

```javascript
(function() {
    const vscode = acquireVsCodeApi();
    
    // State management
    let currentState = {
        prompts: [],
        selectedPrompt: null,
        searchQuery: '',
        categoryFilter: '',
        tagFilter: ''
    };
    
    // DOM elements
    const elements = {
        searchInput: document.getElementById('search-input'),
        categoryFilter: document.getElementById('category-filter'),
        tagFilter: document.getElementById('tag-filter'),
        promptTree: document.getElementById('prompt-tree'),
        emptyState: document.getElementById('empty-state'),
        loadingState: document.getElementById('loading-state'),
        configureDirectoryBtn: document.getElementById('configure-directory'),
        configureDirectoryEmptyBtn: document.getElementById('configure-directory-empty'),
        newPromptBtn: document.getElementById('new-prompt'),
        refreshStoreBtn: document.getElementById('refresh-store')
    };
    
    // Event handlers
    function setupEventHandlers() {
        elements.searchInput.addEventListener('input', handleSearch);
        elements.categoryFilter.addEventListener('change', handleCategoryFilter);
        elements.tagFilter.addEventListener('change', handleTagFilter);
        elements.configureDirectoryBtn.addEventListener('click', configureDirectory);
        elements.configureDirectoryEmptyBtn.addEventListener('click', configureDirectory);
        elements.newPromptBtn.addEventListener('click', createNewPrompt);
        elements.refreshStoreBtn.addEventListener('click', refreshStore);
    }
    
    // Message handling
    window.addEventListener('message', event => {
        const message = event.data;
        
        switch (message.type) {
            case 'updatePrompts':
                updatePrompts(message.prompts);
                break;
            case 'updateConfig':
                updateConfig(message.config);
                break;
            case 'showLoading':
                showLoadingState();
                break;
            case 'hideLoading':
                hideLoadingState();
                break;
            case 'showError':
                showError(message.error);
                break;
        }
    });
    
    // UI update functions
    function updatePrompts(prompts) {
        currentState.prompts = prompts;
        renderPromptTree();
        updateFilters();
        
        if (prompts.length === 0) {
            showEmptyState();
        } else {
            hideEmptyState();
        }
    }
    
    function renderPromptTree() {
        const filteredPrompts = filterPrompts(currentState.prompts);
        const treeHTML = buildTreeHTML(organizePrompts(filteredPrompts));
        elements.promptTree.innerHTML = treeHTML;
        
        // Attach click handlers to tree nodes
        elements.promptTree.querySelectorAll('.tree-node[data-type="file"]').forEach(node => {
            node.addEventListener('click', () => handlePromptClick(node.dataset.path));
        });
        
        elements.promptTree.querySelectorAll('.tree-node[data-type="folder"]').forEach(node => {
            node.addEventListener('click', () => handleFolderClick(node));
        });
    }
    
    function buildTreeHTML(treeData) {
        return treeData.map(node => {
            if (node.type === 'folder') {
                return `
                    <div class="tree-node folder" data-type="folder" data-path="${node.path}">
                        <span class="icon">${node.expanded ? '📂' : '📁'}</span>
                        <span class="name">${node.name}</span>
                    </div>
                    <div class="tree-children" style="display: ${node.expanded ? 'block' : 'none'}">
                        ${buildTreeHTML(node.children)}
                    </div>
                `;
            } else {
                return `
                    <div class="tree-node file" data-type="file" data-path="${node.path}">
                        <span class="icon">📄</span>
                        <span class="name">${node.name}</span>
                    </div>
                `;
            }
        }).join('');
    }
    
    // Event handler implementations
    function handleSearch(event) {
        currentState.searchQuery = event.target.value;
        renderPromptTree();
    }
    
    function handlePromptClick(promptPath) {
        vscode.postMessage({
            type: 'openPrompt',
            path: promptPath
        });
    }
    
    function configureDirectory() {
        vscode.postMessage({
            type: 'configureDirectory'
        });
    }
    
    function createNewPrompt() {
        vscode.postMessage({
            type: 'createNewPrompt'
        });
    }
    
    function refreshStore() {
        vscode.postMessage({
            type: 'refreshStore'
        });
    }
    
    // Utility functions
    function showEmptyState() {
        elements.emptyState.style.display = 'flex';
        elements.promptTree.style.display = 'none';
    }
    
    function hideEmptyState() {
        elements.emptyState.style.display = 'none';
        elements.promptTree.style.display = 'block';
    }
    
    function showLoadingState() {
        elements.loadingState.style.display = 'flex';
    }
    
    function hideLoadingState() {
        elements.loadingState.style.display = 'none';
    }
    
    // Initialize
    setupEventHandlers();
    
    // Request initial data
    vscode.postMessage({
        type: 'webviewReady'
    });
})();
```

### 6.5 Extension Integration
Update PromptStoreProvider to handle messages:

```typescript
private setupMessageHandling(): void {
    this._view!.webview.onDidReceiveMessage(
        async (message) => {
            switch (message.type) {
                case 'webviewReady':
                    await this.sendInitialData();
                    break;
                case 'configureDirectory':
                    await this.configureDirectory();
                    break;
                case 'openPrompt':
                    await this.openPrompt(message.path);
                    break;
                case 'createNewPrompt':
                    await this.createNewPrompt();
                    break;
                case 'refreshStore':
                    await this.refreshStore();
                    break;
            }
        },
        undefined,
        this.disposables
    );
}
```

## Testing Requirements

### 6.6 Unit Tests
Test scenarios for:
- Webview provider registration
- Message handling between extension and webview
- HTML content generation
- CSS responsiveness
- JavaScript event handling

### 6.7 Integration Tests
- Full webview lifecycle
- Communication with backend services
- Configuration integration
- Error handling and recovery

## Acceptance Criteria
- [ ] Webview displays correctly in VS Code sidebar
- [ ] All UI components render properly
- [ ] Responsive design works at different panel widths
- [ ] Message communication between webview and extension works
- [ ] Event handlers are properly attached
- [ ] Loading and empty states display correctly
- [ ] Styling follows VS Code theme conventions
- [ ] All interactive elements are functional
- [ ] Accessibility considerations are met

## Dependencies
- **Step 5**: Configuration management must be implemented
- VS Code Webview API
- HTML/CSS/JavaScript fundamentals
- VS Code theming system

## Estimated Effort
**6-8 hours**

## Files to Implement
1. `src/promptStore/PromptStoreProvider.ts` (webview provider)
2. `src/webview/promptStore/index.html` (HTML structure)
3. `src/webview/promptStore/style.css` (styling)
4. `src/webview/promptStore/main.js` (JavaScript functionality)
5. `test/promptStore/PromptStoreProvider.test.ts` (unit tests)

## Next Step
Proceed to **Step 7: Prompt Tree Rendering** to implement the dynamic prompt list functionality.
