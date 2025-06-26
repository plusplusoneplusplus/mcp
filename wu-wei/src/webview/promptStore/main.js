/**
 * JavaScript for the Prompt Store webview
 * Following wu wei principles: simple, natural interactions that flow smoothly
 */

(function () {
    const vscode = acquireVsCodeApi();

    // State management
    let currentState = {
        prompts: [],
        selectedPrompt: null,
        searchQuery: '',
        categoryFilter: '',
        tagFilter: ''
    };

    // Context menu state
    let contextMenu = null;

    // DOM elements
    const elements = {
        searchInput: document.getElementById('search-input'),
        categoryFilter: document.getElementById('category-filter'),
        tagFilter: document.getElementById('tag-filter'),
        promptTree: document.getElementById('prompt-tree'),
        emptyState: document.getElementById('empty-state'),
        loadingState: document.getElementById('loading-state')
    };

    // Event handlers
    function setupEventHandlers() {
        elements.searchInput.addEventListener('input', handleSearch);
        elements.categoryFilter.addEventListener('change', handleCategoryFilter);
        elements.tagFilter.addEventListener('change', handleTagFilter);

        // Add global click handler to hide context menu
        document.addEventListener('click', hideContextMenu);

        // Prevent context menu from bubbling up
        document.addEventListener('contextmenu', (e) => {
            const treeNode = e.target.closest('.tree-node[data-type="file"]');
            if (treeNode) {
                e.preventDefault();
                showContextMenu(e, treeNode);
            }
        });
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

    // Context menu functions
    function showContextMenu(event, treeNode) {
        hideContextMenu(); // Hide any existing menu

        const promptPath = treeNode.dataset.path;
        const promptName = treeNode.querySelector('.name').textContent;

        contextMenu = document.createElement('div');
        contextMenu.className = 'context-menu';
        contextMenu.innerHTML = `
            <div class="context-menu-item" data-action="open">
                <span class="icon">📝</span>
                <span class="label">Open</span>
            </div>
            <div class="context-menu-item" data-action="rename">
                <span class="icon">✏️</span>
                <span class="label">Rename</span>
            </div>
            <div class="context-menu-item" data-action="duplicate">
                <span class="icon">📋</span>
                <span class="label">Duplicate</span>
            </div>
            <div class="context-menu-separator"></div>
            <div class="context-menu-item context-menu-item--danger" data-action="delete">
                <span class="icon">🗑️</span>
                <span class="label">Delete</span>
            </div>
        `;

        // Position the menu
        contextMenu.style.position = 'absolute';
        contextMenu.style.left = event.clientX + 'px';
        contextMenu.style.top = event.clientY + 'px';
        contextMenu.style.zIndex = '1000';

        // Add click handlers
        contextMenu.addEventListener('click', (e) => {
            e.stopPropagation();
            const action = e.target.closest('.context-menu-item')?.dataset.action;
            if (action) {
                handleContextMenuAction(action, promptPath, promptName);
                hideContextMenu();
            }
        });

        document.body.appendChild(contextMenu);

        // Adjust position if menu goes off screen
        const menuRect = contextMenu.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        if (menuRect.right > viewportWidth) {
            contextMenu.style.left = (event.clientX - menuRect.width) + 'px';
        }
        if (menuRect.bottom > viewportHeight) {
            contextMenu.style.top = (event.clientY - menuRect.height) + 'px';
        }
    }

    function hideContextMenu() {
        if (contextMenu) {
            contextMenu.remove();
            contextMenu = null;
        }
    }

    function handleContextMenuAction(action, promptPath, promptName) {
        switch (action) {
            case 'open':
                handlePromptClick(promptPath);
                break;
            case 'rename':
                handleRenamePrompt(promptPath, promptName);
                break;
            case 'duplicate':
                handleDuplicatePrompt(promptPath, promptName);
                break;
            case 'delete':
                handleDeletePrompt(promptPath, promptName);
                break;
        }
    }

    function handleRenamePrompt(promptPath, currentName) {
        const newName = prompt(`Enter new name for "${currentName}":`, currentName);
        if (newName && newName.trim() && newName !== currentName) {
            vscode.postMessage({
                type: 'renamePrompt',
                path: promptPath,
                newName: newName.trim()
            });
        }
    }

    function handleDuplicatePrompt(promptPath, currentName) {
        const newName = prompt(`Enter name for duplicate of "${currentName}":`, `${currentName} (Copy)`);
        if (newName && newName.trim()) {
            vscode.postMessage({
                type: 'duplicatePrompt',
                path: promptPath,
                newName: newName.trim()
            });
        }
    }

    function handleDeletePrompt(promptPath, promptName) {
        if (confirm(`Are you sure you want to delete "${promptName}"? This action cannot be undone.`)) {
            vscode.postMessage({
                type: 'deletePrompt',
                path: promptPath
            });
        }
    }

    // UI update functions
    function updatePrompts(prompts) {
        console.log('Received prompts:', prompts); // Debug log
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
            node.addEventListener('click', (e) => {
                // Only handle left click for opening
                if (e.button === 0) {
                    handlePromptClick(node.dataset.path);
                }
            });
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

    function organizePrompts(prompts) {
        // Basic organization for now - just return as flat list
        // TODO: Implement proper tree structure
        return prompts
            .filter(prompt => prompt && (prompt.metadata?.title || prompt.fileName)) // Filter out invalid prompts
            .map(prompt => ({
                type: 'file',
                path: prompt.filePath,
                name: prompt.metadata?.title || prompt.fileName || 'Untitled'
            }));
    }

    function filterPrompts(prompts) {
        return prompts.filter(prompt => {
            const matchesSearch = !currentState.searchQuery ||
                prompt.metadata?.title?.toLowerCase().includes(currentState.searchQuery.toLowerCase()) ||
                prompt.metadata?.description?.toLowerCase().includes(currentState.searchQuery.toLowerCase()) ||
                prompt.fileName?.toLowerCase().includes(currentState.searchQuery.toLowerCase());

            const matchesCategory = !currentState.categoryFilter ||
                prompt.metadata?.category === currentState.categoryFilter;

            const matchesTag = !currentState.tagFilter ||
                prompt.metadata?.tags?.includes(currentState.tagFilter);

            return matchesSearch && matchesCategory && matchesTag;
        });
    }

    function updateFilters() {
        // Update category filter options
        const categories = [...new Set(currentState.prompts.map(p => p.metadata?.category).filter(Boolean))];
        elements.categoryFilter.innerHTML = '<option value="">All Categories</option>' +
            categories.map(cat => `<option value="${cat}">${cat}</option>`).join('');

        // Update tag filter options
        const allTags = currentState.prompts.flatMap(p => p.metadata?.tags || []);
        const uniqueTags = [...new Set(allTags)];
        elements.tagFilter.innerHTML = '<option value="">All Tags</option>' +
            uniqueTags.map(tag => `<option value="${tag}">${tag}</option>`).join('');
    }

    function updateConfig(config) {
        // Handle configuration updates
        console.log('Received config:', config); // Debug log
    }

    // Event handler implementations
    function handleSearch(event) {
        currentState.searchQuery = event.target.value;
        renderPromptTree();
    }

    function handleCategoryFilter(event) {
        currentState.categoryFilter = event.target.value;
        renderPromptTree();
    }

    function handleTagFilter(event) {
        currentState.tagFilter = event.target.value;
        renderPromptTree();
    }

    function handlePromptClick(promptPath) {
        vscode.postMessage({
            type: 'openPrompt',
            path: promptPath
        });
    }

    function handleFolderClick(node) {
        // Toggle folder expansion
        const children = node.nextElementSibling;
        const icon = node.querySelector('.icon');

        if (children.style.display === 'none') {
            children.style.display = 'block';
            icon.textContent = '📂';
        } else {
            children.style.display = 'none';
            icon.textContent = '📁';
        }
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

    function showError(error) {
        // Simple error display for now
        console.error('Prompt Store Error:', error);
        // TODO: Implement proper error UI
    }

    // Initialize
    setupEventHandlers();

    // Show loading state and request initial data
    showLoadingState();
    vscode.postMessage({
        type: 'webviewReady'
    });
})();
