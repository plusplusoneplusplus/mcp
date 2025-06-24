# Step 7: Prompt Tree Rendering

## Overview
Implement dynamic prompt tree rendering with hierarchical folder structure, search functionality, and interactive prompt selection.

## Objectives
- Display prompts in hierarchical tree structure
- Support folder-based organization
- Implement search and filtering
- Handle prompt selection and opening
- Optimize rendering performance for large collections

## Tasks

### 7.1 Tree Data Structure
Create efficient tree data structures:

```typescript
interface TreeNode {
    id: string;
    name: string;
    type: 'folder' | 'file';
    path: string;
    children?: TreeNode[];
    parent?: TreeNode;
    expanded?: boolean;
    metadata?: PromptMetadata;
}

interface TreeState {
    rootNodes: TreeNode[];
    expandedNodes: Set<string>;
    selectedNode?: string;
    searchQuery: string;
    filters: TreeFilters;
}

class PromptTreeManager {
    buildTree(prompts: Prompt[]): TreeNode[]
    filterTree(nodes: TreeNode[], query: string, filters: TreeFilters): TreeNode[]
    expandNode(nodeId: string): void
    collapseNode(nodeId: string): void
    selectNode(nodeId: string): void
    findNode(nodeId: string): TreeNode | undefined
}
```

### 7.2 Tree Building Algorithm
Implement efficient tree construction:

```typescript
buildTree(prompts: Prompt[]): TreeNode[] {
    const nodeMap = new Map<string, TreeNode>();
    const rootNodes: TreeNode[] = [];
    
    // Create all nodes first
    for (const prompt of prompts) {
        const pathParts = this.getPathParts(prompt.relativePath);
        let currentPath = '';
        
        for (let i = 0; i < pathParts.length; i++) {
            const part = pathParts[i];
            const isFile = i === pathParts.length - 1;
            currentPath = currentPath ? `${currentPath}/${part}` : part;
            
            if (!nodeMap.has(currentPath)) {
                const node: TreeNode = {
                    id: this.generateNodeId(currentPath),
                    name: isFile ? this.getDisplayName(prompt) : part,
                    type: isFile ? 'file' : 'folder',
                    path: currentPath,
                    children: isFile ? undefined : [],
                    expanded: false,
                    metadata: isFile ? prompt.metadata : undefined
                };
                
                nodeMap.set(currentPath, node);
            }
        }
    }
    
    // Build parent-child relationships
    for (const [path, node] of nodeMap.entries()) {
        const parentPath = this.getParentPath(path);
        
        if (parentPath && nodeMap.has(parentPath)) {
            const parent = nodeMap.get(parentPath)!;
            parent.children!.push(node);
            node.parent = parent;
        } else {
            rootNodes.push(node);
        }
    }
    
    // Sort nodes
    this.sortTree(rootNodes);
    
    return rootNodes;
}
```

### 7.3 Search and Filtering
Implement comprehensive search functionality:

```typescript
interface TreeFilters {
    category?: string;
    tags?: string[];
    author?: string;
    dateRange?: DateRange;
}

filterTree(nodes: TreeNode[], query: string, filters: TreeFilters): TreeNode[] {
    return nodes.map(node => {
        if (node.type === 'folder') {
            const filteredChildren = this.filterTree(node.children!, query, filters);
            
            if (filteredChildren.length > 0) {
                return { ...node, children: filteredChildren };
            }
            
            return null;
        } else {
            // File node - apply filters
            if (this.matchesSearch(node, query) && this.matchesFilters(node, filters)) {
                return node;
            }
            
            return null;
        }
    }).filter(node => node !== null) as TreeNode[];
}

private matchesSearch(node: TreeNode, query: string): boolean {
    if (!query) return true;
    
    const searchableText = [
        node.name,
        node.metadata?.title,
        node.metadata?.description,
        ...(node.metadata?.tags || [])
    ].filter(Boolean).join(' ').toLowerCase();
    
    return searchableText.includes(query.toLowerCase());
}

private matchesFilters(node: TreeNode, filters: TreeFilters): boolean {
    if (!node.metadata) return true;
    
    if (filters.category && node.metadata.category !== filters.category) {
        return false;
    }
    
    if (filters.tags && filters.tags.length > 0) {
        const nodeTags = node.metadata.tags || [];
        if (!filters.tags.some(tag => nodeTags.includes(tag))) {
            return false;
        }
    }
    
    if (filters.author && node.metadata.author !== filters.author) {
        return false;
    }
    
    if (filters.dateRange) {
        const nodeDate = node.metadata.updated || node.metadata.created;
        if (nodeDate && !this.isInDateRange(nodeDate, filters.dateRange)) {
            return false;
        }
    }
    
    return true;
}
```

### 7.4 Virtual Scrolling (Optional)
For large prompt collections, implement virtual scrolling:

```typescript
interface VirtualScrollConfig {
    itemHeight: number;
    containerHeight: number;
    overscan: number;
}

class VirtualTreeRenderer {
    private config: VirtualScrollConfig;
    private flattenedNodes: TreeNode[] = [];
    private visibleRange: { start: number; end: number } = { start: 0, end: 0 };
    
    flatten(nodes: TreeNode[]): TreeNode[] {
        const flattened: TreeNode[] = [];
        
        const traverse = (nodes: TreeNode[], depth: number = 0) => {
            for (const node of nodes) {
                flattened.push({ ...node, depth });
                
                if (node.type === 'folder' && node.expanded && node.children) {
                    traverse(node.children, depth + 1);
                }
            }
        };
        
        traverse(nodes);
        return flattened;
    }
    
    calculateVisibleRange(scrollTop: number): { start: number; end: number } {
        const start = Math.floor(scrollTop / this.config.itemHeight);
        const visibleCount = Math.ceil(this.config.containerHeight / this.config.itemHeight);
        const end = Math.min(
            start + visibleCount + this.config.overscan,
            this.flattenedNodes.length
        );
        
        return {
            start: Math.max(0, start - this.config.overscan),
            end
        };
    }
}
```

### 7.5 WebView Integration
Update webview JavaScript for tree rendering:

```javascript
class PromptTreeRenderer {
    constructor(container, vscode) {
        this.container = container;
        this.vscode = vscode;
        this.treeState = {
            nodes: [],
            expandedNodes: new Set(),
            selectedNode: null
        };
    }
    
    render(treeData) {
        this.treeState.nodes = treeData;
        this.container.innerHTML = this.buildTreeHTML(treeData);
        this.attachEventListeners();
    }
    
    buildTreeHTML(nodes, depth = 0) {
        return nodes.map(node => {
            const indent = depth * 16;
            const isExpanded = this.treeState.expandedNodes.has(node.id);
            
            if (node.type === 'folder') {
                return `
                    <div class="tree-node folder ${isExpanded ? 'expanded' : ''}" 
                         data-node-id="${node.id}" 
                         data-type="folder"
                         style="padding-left: ${indent}px">
                        <span class="expand-icon" data-action="toggle">
                            ${isExpanded ? '▼' : '▶'}
                        </span>
                        <span class="icon">📁</span>
                        <span class="name">${this.escapeHtml(node.name)}</span>
                        <span class="count">(${this.countFiles(node)})</span>
                    </div>
                    <div class="tree-children" style="display: ${isExpanded ? 'block' : 'none'}">
                        ${this.buildTreeHTML(node.children || [], depth + 1)}
                    </div>
                `;
            } else {
                const isSelected = this.treeState.selectedNode === node.id;
                return `
                    <div class="tree-node file ${isSelected ? 'selected' : ''}" 
                         data-node-id="${node.id}" 
                         data-type="file"
                         data-path="${node.path}"
                         style="padding-left: ${indent + 20}px"
                         title="${this.getTooltipText(node)}">
                        <span class="icon">📄</span>
                        <span class="name">${this.escapeHtml(node.name)}</span>
                        ${this.renderMetadataBadges(node.metadata)}
                    </div>
                `;
            }
        }).join('');
    }
    
    attachEventListeners() {
        this.container.addEventListener('click', (event) => {
            const target = event.target;
            const nodeElement = target.closest('.tree-node');
            
            if (!nodeElement) return;
            
            const nodeId = nodeElement.dataset.nodeId;
            const nodeType = nodeElement.dataset.type;
            const action = target.dataset.action;
            
            if (action === 'toggle' && nodeType === 'folder') {
                this.toggleFolder(nodeId);
            } else if (nodeType === 'file') {
                this.selectFile(nodeId, nodeElement.dataset.path);
            }
        });
    }
    
    toggleFolder(nodeId) {
        if (this.treeState.expandedNodes.has(nodeId)) {
            this.treeState.expandedNodes.delete(nodeId);
        } else {
            this.treeState.expandedNodes.add(nodeId);
        }
        
        this.render(this.treeState.nodes);
        
        // Persist expanded state
        this.vscode.postMessage({
            type: 'updateTreeState',
            expandedNodes: Array.from(this.treeState.expandedNodes)
        });
    }
    
    selectFile(nodeId, filePath) {
        this.treeState.selectedNode = nodeId;
        this.updateSelection();
        
        this.vscode.postMessage({
            type: 'openPrompt',
            path: filePath
        });
    }
    
    renderMetadataBadges(metadata) {
        if (!metadata) return '';
        
        const badges = [];
        
        if (metadata.category) {
            badges.push(`<span class="badge category">${metadata.category}</span>`);
        }
        
        if (metadata.tags && metadata.tags.length > 0) {
            badges.push(`<span class="badge tags">${metadata.tags.slice(0, 2).join(', ')}</span>`);
        }
        
        return badges.length > 0 ? `<div class="metadata-badges">${badges.join('')}</div>` : '';
    }
    
    getTooltipText(node) {
        if (!node.metadata) return node.name;
        
        const parts = [node.name];
        
        if (node.metadata.description) {
            parts.push(`Description: ${node.metadata.description}`);
        }
        
        if (node.metadata.tags && node.metadata.tags.length > 0) {
            parts.push(`Tags: ${node.metadata.tags.join(', ')}`);
        }
        
        return parts.join('\n');
    }
    
    countFiles(folderNode) {
        let count = 0;
        
        const traverse = (node) => {
            if (node.type === 'file') {
                count++;
            } else if (node.children) {
                node.children.forEach(traverse);
            }
        };
        
        if (folderNode.children) {
            folderNode.children.forEach(traverse);
        }
        
        return count;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
```

### 7.6 Enhanced CSS for Tree
Add tree-specific styling:

```css
.tree-node {
    display: flex;
    align-items: center;
    padding: 2px 4px;
    cursor: pointer;
    border-radius: 3px;
    user-select: none;
    min-height: 22px;
}

.tree-node:hover {
    background: var(--vscode-list-hoverBackground);
}

.tree-node.selected {
    background: var(--vscode-list-activeSelectionBackground);
    color: var(--vscode-list-activeSelectionForeground);
}

.tree-node.folder {
    font-weight: 500;
}

.expand-icon {
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    margin-right: 4px;
    cursor: pointer;
}

.tree-node .icon {
    margin-right: 6px;
    font-size: 12px;
    flex-shrink: 0;
}

.tree-node .name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
}

.tree-node .count {
    font-size: 11px;
    opacity: 0.7;
    margin-left: 4px;
}

.metadata-badges {
    display: flex;
    gap: 4px;
    margin-left: 8px;
}

.badge {
    font-size: 10px;
    padding: 1px 4px;
    border-radius: 2px;
    background: var(--vscode-badge-background);
    color: var(--vscode-badge-foreground);
}

.badge.category {
    background: var(--vscode-button-background);
}

.badge.tags {
    background: var(--vscode-inputValidation-infoBorder);
}

.tree-children {
    animation: expandFade 0.2s ease-out;
}

@keyframes expandFade {
    from { opacity: 0; }
    to { opacity: 1; }
}
```

## Performance Optimizations

### 7.7 Optimization Strategies
- Implement tree node recycling for large lists
- Use efficient diff algorithms for updates
- Debounce search input
- Lazy load folder contents
- Cache rendered HTML fragments

### 7.8 Memory Management
- Clean up event listeners on re-render
- Limit expanded nodes to prevent memory bloat
- Use weak references where appropriate
- Implement cleanup on webview disposal

## Testing Requirements

### 7.9 Unit Tests
Test scenarios for:
- Tree building with various folder structures
- Search and filtering functionality
- Node expansion and collapse
- Selection handling
- Performance with large datasets

### 7.10 Integration Tests
- End-to-end tree rendering
- WebView communication
- State persistence
- Error handling for malformed data

## Acceptance Criteria
- [ ] Tree displays prompts in hierarchical structure
- [ ] Folder expansion/collapse works smoothly
- [ ] Search filters prompts correctly
- [ ] Selection state is maintained
- [ ] Performance is acceptable with 1000+ prompts
- [ ] Metadata badges display correctly
- [ ] Tooltips show helpful information
- [ ] Tree state persists across sessions
- [ ] All interactions are responsive
- [ ] Error states are handled gracefully

## Dependencies
- **Step 6**: Basic webview UI must be implemented
- Tree data structures and algorithms
- WebView messaging system
- CSS styling foundation

## Estimated Effort
**8-10 hours**

## Files to Implement
1. `src/promptStore/PromptTreeManager.ts` (tree logic)
2. `src/webview/promptStore/treeRenderer.js` (webview tree rendering)
3. `src/webview/promptStore/tree.css` (tree-specific styling)
4. `test/promptStore/PromptTreeManager.test.ts` (unit tests)
5. `test/promptStore/integration/treeRendering.test.ts` (integration tests)

## Next Step
Proceed to **Step 8: File Operations** to implement prompt creation, editing, and deletion functionality.
