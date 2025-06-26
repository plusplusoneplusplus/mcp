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
        console.log('📨 Webview received message:', message.type, message);

        switch (message.type) {
            case 'updatePrompts':
                console.log('🔄 Processing updatePrompts with data:', message.prompts);
                updatePrompts(message.prompts);
                break;
            case 'updateConfig':
                console.log('⚙️ Processing updateConfig with data:', message.config);
                updateConfig(message.config);
                break;
            case 'showLoading':
                console.log('⏳ Showing loading state');
                showLoadingState();
                break;
            case 'hideLoading':
                console.log('✅ Hiding loading state');
                hideLoadingState();
                break;
            case 'showError':
                console.log('❌ Showing error:', message.error);
                showError(message.error);
                break;
            default:
                console.log('❓ Unknown message type:', message.type);
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
    }    // UI update functions
    function updatePrompts(prompts) {
        console.log('🔍 updatePrompts called with:', prompts);
        console.log('📊 Current state before update:', currentState);

        if (!prompts || !Array.isArray(prompts)) {
            console.error('❌ Invalid prompts data received:', prompts);
            showError('Invalid prompts data received');
            return;
        }

        currentState.prompts = prompts;
        console.log('📝 Updated currentState.prompts:', currentState.prompts.length, 'items');

        renderPromptTree();
        updateFilters();

        if (prompts.length === 0) {
            console.log('📭 No prompts found, showing empty state');
            showEmptyState();
        } else {
            console.log('📚 Found', prompts.length, 'prompts, hiding empty state');
            hideEmptyState();
        }

        // Hide loading state when prompts are successfully updated
        hideLoadingState();
        console.log('✅ updatePrompts completed successfully');
    }

    function renderPromptTree() {
        console.log('🌲 renderPromptTree called with', currentState.prompts.length, 'prompts');

        const filteredPrompts = filterPrompts(currentState.prompts);
        console.log('🔍 Filtered to', filteredPrompts.length, 'prompts');

        const organizedPrompts = organizePrompts(filteredPrompts);
        console.log('📁 Organized into', organizedPrompts.length, 'tree nodes');

        const treeHTML = buildTreeHTML(organizedPrompts);
        console.log('🏗️ Generated HTML length:', treeHTML.length, 'characters');

        elements.promptTree.innerHTML = treeHTML;
        console.log('🖼️ Updated DOM with new HTML');

        // Attach click handlers to tree nodes
        const fileNodes = elements.promptTree.querySelectorAll('.tree-node[data-type="file"]');
        console.log('📄 Found', fileNodes.length, 'file nodes for click handlers');

        fileNodes.forEach(node => {
            node.addEventListener('click', (e) => {
                // Only handle left click for opening
                if (e.button === 0) {
                    handlePromptClick(node.dataset.path);
                }
            });
        });

        const folderNodes = elements.promptTree.querySelectorAll('.tree-node[data-type="folder"]');
        console.log('📁 Found', folderNodes.length, 'folder nodes for click handlers');

        folderNodes.forEach(node => {
            node.addEventListener('click', () => handleFolderClick(node));
        });

        console.log('✅ renderPromptTree completed');
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

        // Show error in the UI by temporarily replacing the empty state message
        if (elements.emptyState.style.display === 'flex') {
            const emptyContent = elements.emptyState.querySelector('.empty-content');
            if (emptyContent) {
                const originalContent = emptyContent.innerHTML;
                emptyContent.innerHTML = `
                    <h3>Error Loading Prompts</h3>
                    <p>${error}</p>
                    <button onclick="location.reload()" class="primary-button">
                        🔄 Retry
                    </button>
                `;

                // Restore original content after 5 seconds
                setTimeout(() => {
                    emptyContent.innerHTML = originalContent;
                }, 5000);
            }
        }

        // Hide loading state on error
        hideLoadingState();
    }

    // Initialize
    setupEventHandlers();

    // Enhanced initialization with retry mechanism
    function initialize() {
        console.log('🚀 Initializing webview...');
        console.log('📄 Document readyState:', document.readyState);
        console.log('🖼️ Elements found:', {
            searchInput: !!elements.searchInput,
            categoryFilter: !!elements.categoryFilter,
            tagFilter: !!elements.tagFilter,
            promptTree: !!elements.promptTree,
            emptyState: !!elements.emptyState,
            loadingState: !!elements.loadingState
        });

        showLoadingState();
        console.log('📤 Sending webviewReady message to extension');
        vscode.postMessage({
            type: 'webviewReady'
        });
    }

    // Initialize immediately
    console.log('🔧 Starting immediate initialization');
    initialize();

    // Also initialize when document is fully loaded (in case of timing issues)
    if (document.readyState === 'loading') {
        console.log('📄 Document still loading, adding DOMContentLoaded listener');
        document.addEventListener('DOMContentLoaded', () => {
            console.log('📄 DOMContentLoaded fired, reinitializing');
            initialize();
        });
    } else {
        console.log('📄 Document already loaded');
    }

    // Retry initialization after a short delay if no data received
    setTimeout(() => {
        console.log('⏰ Timeout check - prompts:', currentState.prompts.length, 'loading visible:', elements.loadingState.style.display === 'flex');
        if (currentState.prompts.length === 0 && elements.loadingState.style.display === 'flex') {
            console.log('🔄 No prompts received after timeout, retrying initialization...');
            initialize();
        }
    }, 2000);

    // Add a longer timeout for debugging
    setTimeout(() => {
        console.log('🕐 Extended timeout check (5s):');
        console.log('   - Prompts count:', currentState.prompts.length);
        console.log('   - Loading state visible:', elements.loadingState.style.display === 'flex');
        console.log('   - Empty state visible:', elements.emptyState.style.display === 'flex');
        console.log('   - Prompt tree content length:', elements.promptTree.innerHTML.length);
        console.log('   - Current state:', currentState);
    }, 5000);
})();
