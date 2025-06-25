/**
 * JavaScript for the Prompt Store webview
 * Following wu wei principles: simple, natural interactions that flow smoothly
 */

// Get the VS Code API
const vscode = acquireVsCodeApi();

// State management
let prompts = [];
let filteredPrompts = [];
let currentFilter = {
    query: '',
    category: '',
    sortBy: 'name'
};

// DOM elements
let searchInput;
let categoryFilter;
let sortFilter;
let promptsContainer;
let refreshBtn;

/**
 * Initialize the webview
 */
function initialize() {
    // Get DOM elements
    searchInput = document.getElementById('search-input');
    categoryFilter = document.getElementById('category-filter');
    sortFilter = document.getElementById('sort-filter');
    promptsContainer = document.getElementById('prompts-container');
    refreshBtn = document.getElementById('refresh-btn');

    // Setup event listeners
    setupEventListeners();

    // Request initial prompts
    requestPrompts();
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Search input
    searchInput.addEventListener('input', debounce(handleSearch, 300));

    // Filter dropdowns
    categoryFilter.addEventListener('change', handleCategoryFilter);
    sortFilter.addEventListener('change', handleSortFilter);

    // Refresh button
    refreshBtn.addEventListener('click', handleRefresh);

    // Listen for messages from the extension
    window.addEventListener('message', handleMessage);
}

/**
 * Handle messages from the extension
 */
function handleMessage(event) {
    const message = event.data;

    switch (message.type) {
        case 'promptsLoaded':
            handlePromptsLoaded(message.payload);
            break;

        case 'promptSelected':
            handlePromptSelected(message.payload);
            break;

        case 'error':
            handleError(message.error);
            break;

        case 'configUpdated':
            handleConfigUpdated(message.payload);
            break;
    }
}

/**
 * Handle prompts loaded
 */
function handlePromptsLoaded(loadedPrompts) {
    prompts = loadedPrompts || [];
    updateCategoryFilter();
    applyFilters();
    renderPrompts();
}

/**
 * Handle prompt selected
 */
function handlePromptSelected(result) {
    if (result.success) {
        // Show success feedback
        showNotification('Prompt inserted successfully', 'success');
    } else {
        showNotification('Failed to insert prompt', 'error');
    }
}

/**
 * Handle error
 */
function handleError(error) {
    showNotification(error, 'error');
    console.error('Webview error:', error);
}

/**
 * Handle configuration updated
 */
function handleConfigUpdated(config) {
    // Update UI based on new configuration
    console.log('Configuration updated:', config);
}

/**
 * Request prompts from the extension
 */
function requestPrompts() {
    sendMessage({
        type: 'getPrompts'
    });
}

/**
 * Handle search input
 */
function handleSearch(event) {
    currentFilter.query = event.target.value.trim();
    searchPrompts();
}

/**
 * Handle category filter change
 */
function handleCategoryFilter(event) {
    currentFilter.category = event.target.value;
    searchPrompts();
}

/**
 * Handle sort filter change
 */
function handleSortFilter(event) {
    currentFilter.sortBy = event.target.value;
    searchPrompts();
}

/**
 * Handle refresh button click
 */
function handleRefresh() {
    refreshBtn.disabled = true;
    refreshBtn.innerHTML = '<span class="codicon codicon-loading codicon-modifier-spin"></span>';

    sendMessage({
        type: 'refreshPrompts'
    });

    // Re-enable button after a delay
    setTimeout(() => {
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = '<span class="codicon codicon-refresh"></span>';
    }, 2000);
}

/**
 * Search prompts with current filter
 */
function searchPrompts() {
    const filter = {
        query: currentFilter.query || undefined,
        category: currentFilter.category || undefined
    };

    sendMessage({
        type: 'searchPrompts',
        payload: filter
    });
}

/**
 * Apply local filters and sorting
 */
function applyFilters() {
    filteredPrompts = [...prompts];

    // Apply sorting
    filteredPrompts.sort((a, b) => {
        let comparison = 0;

        switch (currentFilter.sortBy) {
            case 'name':
                comparison = a.metadata.title.localeCompare(b.metadata.title);
                break;
            case 'modified':
                comparison = new Date(a.lastModified).getTime() - new Date(b.lastModified).getTime();
                comparison = -comparison; // Most recent first
                break;
            case 'category':
                comparison = (a.metadata.category || '').localeCompare(b.metadata.category || '');
                break;
            case 'author':
                comparison = (a.metadata.author || '').localeCompare(b.metadata.author || '');
                break;
        }

        return comparison;
    });
}

/**
 * Render prompts in the container
 */
function renderPrompts() {
    if (!filteredPrompts || filteredPrompts.length === 0) {
        promptsContainer.innerHTML = '<div class="empty-state">No prompts found</div>';
        return;
    }

    const html = filteredPrompts.map(prompt => createPromptCard(prompt)).join('');
    promptsContainer.innerHTML = html;

    // Add click handlers
    const promptCards = promptsContainer.querySelectorAll('.prompt-card');
    promptCards.forEach((card, index) => {
        card.addEventListener('click', () => selectPrompt(filteredPrompts[index].id));
    });
}

/**
 * Create HTML for a prompt card
 */
function createPromptCard(prompt) {
    const tags = prompt.metadata.tags || [];
    const tagsHtml = tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('');

    const parametersCount = prompt.metadata.parameters ? prompt.metadata.parameters.length : 0;
    const parametersHtml = parametersCount > 0 ?
        `<span class="parameters-indicator" title="${parametersCount} parameters">⚙️ ${parametersCount}</span>` : '';

    const modifiedDate = new Date(prompt.lastModified).toLocaleDateString();

    const validationClass = prompt.isValid ? '' : 'invalid';
    const validationIcon = prompt.isValid ? '' : '<span class="validation-error" title="Validation errors">⚠️</span>';

    return `
        <div class="prompt-card ${validationClass}" data-id="${prompt.id}">
            <div class="prompt-header">
                <h3 class="prompt-title">${escapeHtml(prompt.metadata.title)}</h3>
                <div class="prompt-meta">
                    ${validationIcon}
                    ${parametersHtml}
                </div>
            </div>
            
            ${prompt.metadata.description ?
            `<p class="prompt-description">${escapeHtml(prompt.metadata.description)}</p>` : ''
        }
            
            <div class="prompt-footer">
                <div class="prompt-info">
                    <span class="category">${escapeHtml(prompt.metadata.category || 'General')}</span>
                    <span class="author">${escapeHtml(prompt.metadata.author || 'Unknown')}</span>
                    <span class="modified">${modifiedDate}</span>
                </div>
                ${tagsHtml ? `<div class="tags">${tagsHtml}</div>` : ''}
            </div>
        </div>
    `;
}

/**
 * Select a prompt
 */
function selectPrompt(promptId) {
    sendMessage({
        type: 'selectPrompt',
        payload: promptId
    });
}

/**
 * Update category filter options
 */
function updateCategoryFilter() {
    const categories = [...new Set(prompts.map(p => p.metadata.category).filter(Boolean))];
    categories.sort();

    const currentValue = categoryFilter.value;
    categoryFilter.innerHTML = '<option value="">All Categories</option>';

    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;
        categoryFilter.appendChild(option);
    });

    // Restore selection if still valid
    if (categories.includes(currentValue)) {
        categoryFilter.value = currentValue;
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Add to page
    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);

    // Remove after delay
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => document.body.removeChild(notification), 300);
    }, 3000);
}

/**
 * Send message to extension
 */
function sendMessage(message) {
    vscode.postMessage(message);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Debounce function calls
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}
