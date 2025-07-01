// Wu Wei Agent Panel JavaScript

const vscode = acquireVsCodeApi();
let agentCapabilities = [];
let messageHistory = [];

// Prompt integration state
let availablePrompts = [];
let selectedPromptContext = null;
let promptVariables = {};
let promptMode = 'combined'; // Always use combined mode

// Input history navigation state
let inputHistory = [];
let historyIndex = -1;
let currentInput = '';

// DOM elements
const agentSelect = document.getElementById('agentSelect');
const methodSelect = document.getElementById('methodSelect');
const paramsInput = document.getElementById('paramsInput');
const agentTooltip = document.getElementById('agentTooltip');
const messageList = document.getElementById('messageList');
const historyIndicator = document.getElementById('historyIndicator');

// Message progress tracking
let processingMessages = new Map(); // Maps message IDs to their processing state
let messageExecutionMap = new Map(); // Maps message IDs to execution IDs for cancellation

// DOM elements - new prompt integration
const promptSelectorContainer = document.getElementById('promptSelectorContainer');
const promptSearch = document.getElementById('promptSearch');
const promptSelector = document.getElementById('promptSelector');
const variableEditorContainer = document.getElementById('variableEditorContainer');
const variableEditor = document.getElementById('variableEditor');
const promptOverviewContainer = document.getElementById('promptOverviewContainer');
const promptPreview = document.getElementById('promptPreview');
const parameterSubtitle = document.getElementById('parameterSubtitle');
const parametersLabel = document.getElementById('parametersLabel');

// Event listeners
agentSelect.addEventListener('change', updateMethodSelect);
methodSelect.addEventListener('change', updatePlaceholder);
paramsInput.addEventListener('keydown', handleKeyDown);
paramsInput.addEventListener('click', handleInputClick);
paramsInput.addEventListener('focus', handleInputFocus);

// Event listeners - new prompt integration
promptSearch.addEventListener('input', debounce(handlePromptSearch, 300));
promptSelector.addEventListener('change', handlePromptSelection);

// Initialize DOM content
document.addEventListener('DOMContentLoaded', function () {
    // DOM initialization handled in main initialization
});

// Execution tracking state
let pendingExecutions = [];
let executionHistory = [];
let durationUpdateInterval = null;

// Handle messages from extension
window.addEventListener('message', event => {
    const message = event.data;

    switch (message.command) {
        case 'updateAgentCapabilities':
            agentCapabilities = message.capabilities;
            updateAgentSelect();
            break;
        case 'updateMessageHistory':
            messageHistory = message.messages;
            updateMessageHistory();
            break;
        case 'messageProcessingComplete':
            handleMessageProcessingComplete(message.messageId, message.success);
            break;
        case 'updateAvailablePrompts':
            availablePrompts = message.prompts || [];
            updatePromptSelector();
            break;
        case 'promptSelected':
            selectedPromptContext = message.promptContext;
            handlePromptContextUpdate();
            break;
        case 'promptRendered':
            updatePromptPreview(message.rendered);
            break;
        case 'error':
            showError(message.error);
            break;
        // Phase 2: Execution tracking message handlers
        case 'executionStatusUpdate':
            handleExecutionStatusUpdate(message);
            break;
        case 'updatePendingExecutions':
            pendingExecutions = message.executions || [];
            updatePendingExecutionsDisplay();
            break;
        case 'updateExecutionHistory':
            executionHistory = message.history || [];
            updateExecutionHistoryDisplay(message.stats);
            break;
        case 'messageExecutionLink':
            // Store the link between messageId and executionId for cancellation
            messageExecutionMap.set(message.messageId, message.executionId);
            break;
    }
});

// Initialize collapse state from localStorage
function initializeCollapseState() {
    // Initialize agent selection collapse state
    const savedAgentState = localStorage.getItem('agentCollapsed');
    const agentSection = document.querySelector('.agent-selection');

    // Default to expanded for agent selection (false means not collapsed)
    const isAgentCollapsed = savedAgentState === 'true';

    if (isAgentCollapsed) {
        agentSection.classList.add('collapsed');
    }

    // Initialize prompt overview collapse state - collapsed by default
    const savedPromptOverviewState = localStorage.getItem('promptOverviewCollapsed');
    const promptOverviewSection = document.querySelector('.prompt-overview-section');

    // Default to collapsed if no saved state exists, otherwise use saved state
    const isPromptOverviewCollapsed = savedPromptOverviewState === null ? true : savedPromptOverviewState === 'true';

    if (promptOverviewSection && isPromptOverviewCollapsed) {
        promptOverviewSection.classList.add('collapsed');
    }
}

// Toggle agent selection collapse state
function toggleAgentCollapse() {
    const agentSection = document.querySelector('.agent-selection');
    const isCollapsed = agentSection.classList.contains('collapsed');

    if (isCollapsed) {
        agentSection.classList.remove('collapsed');
        localStorage.setItem('agentCollapsed', 'false');
    } else {
        agentSection.classList.add('collapsed');
        localStorage.setItem('agentCollapsed', 'true');
    }
}

// Toggle prompt overview collapse state
function togglePromptOverviewCollapse() {
    const promptOverviewSection = document.querySelector('.prompt-overview-section');
    const isCollapsed = promptOverviewSection.classList.contains('collapsed');

    if (isCollapsed) {
        promptOverviewSection.classList.remove('collapsed');
        localStorage.setItem('promptOverviewCollapsed', 'false');
    } else {
        promptOverviewSection.classList.add('collapsed');
        localStorage.setItem('promptOverviewCollapsed', 'true');
    }
}

// UI Management for Combined Mode
function updateUIForCombinedMode() {
    // Always show prompt selector
    promptSelectorContainer.style.display = 'block';

    // Only show variable editor if prompt has variables
    const hasVariables = selectedPromptContext?.parameters?.length > 0;
    variableEditorContainer.style.display = selectedPromptContext && hasVariables ? 'block' : 'none';

    // Show prompt overview section if prompt is selected
    promptOverviewContainer.style.display = selectedPromptContext ? 'block' : 'none';

    // Update subtitle based on whether a prompt is selected
    if (selectedPromptContext) {
        parameterSubtitle.textContent = 'Selected prompt will be combined with your custom message';
    } else {
        parameterSubtitle.textContent = 'Optionally select a prompt template and/or add your custom message';
    }
}

function updateInputLabelsAndPlaceholders() {
    // Update labels to reflect optional prompt usage
    parameterSubtitle.textContent = 'Optionally select a prompt template and/or add your custom message';
    parametersLabel.textContent = 'Message';
    paramsInput.placeholder = 'Enter your message or combine with a prompt template...';
}

// Prompt Search and Selection
function handlePromptSearch(event) {
    const query = event.target.value.toLowerCase();

    // Filter prompts based on search query
    const filteredPrompts = availablePrompts.filter(prompt => {
        return prompt.title.toLowerCase().includes(query) ||
            (prompt.description && prompt.description.toLowerCase().includes(query)) ||
            (prompt.category && prompt.category.toLowerCase().includes(query)) ||
            (prompt.tags && prompt.tags.some(tag => tag.toLowerCase().includes(query)));
    });

    updatePromptSelectorList(filteredPrompts);
}

function updatePromptSelector() {
    updatePromptSelectorList(availablePrompts);
}

function updatePromptSelectorList(prompts) {
    promptSelector.innerHTML = '';

    if (prompts.length === 0) {
        promptSelector.innerHTML = '<option value="">No prompts available</option>';
        return;
    }

    promptSelector.innerHTML = '<option value="">No prompt (message only)</option>';
    prompts.forEach(prompt => {
        const option = document.createElement('option');
        option.value = prompt.id;
        option.textContent = `${prompt.title} ${prompt.category ? `(${prompt.category})` : ''}`;
        option.title = prompt.description || prompt.title;
        promptSelector.appendChild(option);
    });
}

function handlePromptSelection() {
    const promptId = promptSelector.value;

    if (!promptId) {
        selectedPromptContext = null;
        clearVariableEditor();
        clearPromptPreview();
        updateUIForCombinedMode();
        return;
    }

    // Request prompt selection from extension
    vscode.postMessage({
        command: 'selectPrompt',
        promptId: promptId
    });
}

function handlePromptContextUpdate() {
    if (!selectedPromptContext) {
        return;
    }

    // Update variable editor
    generateVariableEditor(selectedPromptContext.parameters || []);

    // Update prompt preview (both full and collapsed)
    renderPromptPreview();

    // Show appropriate containers for combined mode
    updateUIForCombinedMode();
}

// Variable Editor
function generateVariableEditor(parameters) {
    variableEditor.innerHTML = '';

    if (!parameters || parameters.length === 0) {
        variableEditor.innerHTML = '<p class="no-variables">This prompt has no variables.</p>';
        promptVariables = {};
        return;
    }

    const form = document.createElement('div');
    form.className = 'variable-form';

    parameters.forEach(param => {
        const fieldContainer = createVariableField(param);
        form.appendChild(fieldContainer);
    });

    variableEditor.appendChild(form);
}

function createVariableField(param) {
    const container = document.createElement('div');
    container.className = 'variable-field';

    // Label
    const label = document.createElement('label');
    label.className = 'form-label';
    label.textContent = param.name;
    if (param.required) {
        label.classList.add('required');
        label.textContent += ' *';
    }

    // Description
    if (param.description) {
        const description = document.createElement('small');
        description.textContent = param.description;
        description.className = 'field-description';
        label.appendChild(document.createElement('br'));
        label.appendChild(description);
    }

    // Input
    const input = createVariableInput(param);

    container.appendChild(label);
    container.appendChild(input);

    return container;
}

function createVariableInput(param) {
    let input;

    switch (param.type) {
        case 'multiline':
            input = document.createElement('textarea');
            input.rows = 3;
            break;
        case 'number':
            input = document.createElement('input');
            input.type = 'number';
            break;
        case 'boolean':
            input = document.createElement('input');
            input.type = 'checkbox';
            break;
        case 'select':
            input = document.createElement('select');
            if (!param.required) {
                const emptyOption = document.createElement('option');
                emptyOption.value = '';
                emptyOption.textContent = `Select ${param.name}...`;
                input.appendChild(emptyOption);
            }
            if (param.options) {
                param.options.forEach(option => {
                    const optionElement = document.createElement('option');
                    optionElement.value = option;
                    optionElement.textContent = option;
                    input.appendChild(optionElement);
                });
            }
            break;
        case 'file':
            input = document.createElement('input');
            input.type = 'file';
            break;
        default: // string
            input = document.createElement('input');
            input.type = 'text';
            break;
    }

    input.name = param.name;
    input.placeholder = param.placeholder || `Enter ${param.name}...`;
    input.required = param.required || false;

    if (param.defaultValue !== undefined) {
        if (param.type === 'boolean') {
            input.checked = Boolean(param.defaultValue);
        } else {
            input.value = String(param.defaultValue);
        }
        promptVariables[param.name] = param.defaultValue;
    }

    // Event listener for value changes
    const eventType = param.type === 'boolean' ? 'change' : 'input';
    input.addEventListener(eventType, (e) => {
        let value;
        if (param.type === 'boolean') {
            value = e.target.checked;
        } else if (param.type === 'number') {
            value = e.target.value ? Number(e.target.value) : undefined;
        } else {
            value = e.target.value || undefined;
        }

        promptVariables[param.name] = value;
        renderPromptPreview();
    });

    return input;
}

function clearVariableEditor() {
    variableEditor.innerHTML = '<p class="no-variables">Select a prompt to configure variables</p>';
    promptVariables = {};
}

// Prompt Preview
function renderPromptPreview() {
    if (!selectedPromptContext) {
        clearPromptPreview();
        return;
    }

    // If we have the initial content, show it immediately
    if (selectedPromptContext.content) {
        updatePromptPreview(selectedPromptContext.content);
    }

    // Request prompt rendering from extension with current variables
    vscode.postMessage({
        command: 'renderPromptWithVariables',
        promptId: selectedPromptContext.id,
        variables: promptVariables
    });
}

function updatePromptPreview(rendered) {
    if (!rendered) {
        clearPromptPreview();
        return;
    }

    const formattedContent = formatPreviewContent(rendered);

    // Update the full preview
    promptPreview.innerHTML = `
        <div class="preview-content">
            <h4>Rendered Prompt:</h4>
            <div class="preview-text">${formattedContent}</div>
        </div>
    `;
}

// Removed updateCollapsedPreview function - no longer needed

function formatPreviewContent(content) {
    // Basic markdown-to-HTML conversion for preview
    return content
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

function clearPromptPreview() {
    promptPreview.innerHTML = '<p class="no-preview">Select a prompt to see preview</p>';
}

// Utility Functions
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

function showError(errorMessage) {
    console.error('Agent panel error:', errorMessage);
    // You could also show a visual error notification here
}

// Phase 2: Execution tracking utility functions
function formatDuration(milliseconds) {
    if (milliseconds < 1000) {
        return `${milliseconds}ms`;
    } else if (milliseconds < 60000) {
        return `${Math.round(milliseconds / 1000)}s`;
    } else {
        const minutes = Math.floor(milliseconds / 60000);
        const seconds = Math.round((milliseconds % 60000) / 1000);
        return `${minutes}m ${seconds}s`;
    }
}

function getStatusIcon(status) {
    switch (status) {
        case 'success': return '✅';
        case 'partial': return '⚠️';
        case 'error': return '❌';
        case 'executing': return '⏳';
        case 'pending': return '🟡';
        case 'cancelled': return '⏹️';
        case 'completed': return '✅';
        case 'failed': return '❌';
        default: return '📝';
    }
}

function truncateText(text, maxLength = 50) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Existing functions (updated to work with prompt integration)
function updateAgentSelect() {
    agentSelect.innerHTML = '';

    if (agentCapabilities.length === 0) {
        agentSelect.innerHTML = '<option value="">No agents available</option>';
        return;
    }

    agentSelect.innerHTML = '<option value="">Select an agent</option>';
    agentCapabilities.forEach(capability => {
        const option = document.createElement('option');
        option.value = capability.name;
        option.textContent = `${capability.name} (v${capability.version})`;
        agentSelect.appendChild(option);
    });

    // Auto-select GitHub Copilot if available
    const copilotAgent = agentCapabilities.find(c => c.name === 'github-copilot');
    if (copilotAgent) {
        agentSelect.value = 'github-copilot';
        updateMethodSelect();
    }
}

function updateMethodSelect() {
    const selectedAgent = agentSelect.value;
    methodSelect.innerHTML = '';

    if (!selectedAgent) {
        methodSelect.innerHTML = '<option value="">Select an agent first</option>';
        methodSelect.disabled = true;
        agentTooltip.textContent = 'Select an agent to see its capabilities';
        updatePlaceholder();
        return;
    }

    methodSelect.disabled = false;
    const capability = agentCapabilities.find(c => c.name === selectedAgent);
    if (!capability) {
        methodSelect.innerHTML = '<option value="">Agent not found</option>';
        return;
    }

    // Update tooltip with agent info
    agentTooltip.textContent = `${capability.description || 'No description'} | Methods: ${capability.methods.join(', ')}`;

    // Populate methods
    methodSelect.innerHTML = '<option value="">Select a method</option>';
    capability.methods.forEach(method => {
        const option = document.createElement('option');
        option.value = method;
        option.textContent = method;
        methodSelect.appendChild(option);
    });

    // Auto-select openAgent method for GitHub Copilot
    if (selectedAgent === 'github-copilot') {
        const openAgentOption = Array.from(methodSelect.options).find(option => option.value === 'openAgent');
        if (openAgentOption) {
            methodSelect.value = 'openAgent';
        }
    }

    updatePlaceholder();
}

function handleKeyDown(event) {
    // Check for Ctrl+Enter (or Cmd+Enter on Mac)
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        sendAgentRequest();
        return;
    }

    // Handle arrow key navigation for input history
    if (event.key === 'ArrowUp') {
        event.preventDefault();
        navigateInputHistory('up');
        return;
    }

    if (event.key === 'ArrowDown') {
        event.preventDefault();
        navigateInputHistory('down');
        return;
    }

    // Reset history navigation when user starts typing
    if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown' && historyIndex !== -1) {
        // If user was navigating history and starts typing, save the current state
        if (historyIndex === inputHistory.length) {
            // User was at the "current input" position, update it
            currentInput = paramsInput.value;
        }
        historyIndex = -1;
        hideHistoryIndicator();
    }
}

function navigateInputHistory(direction) {
    if (inputHistory.length === 0) {
        return;
    }

    // Initialize navigation if not already started
    if (historyIndex === -1) {
        // Save current input before starting navigation
        currentInput = paramsInput.value;

        if (direction === 'up') {
            historyIndex = inputHistory.length - 1;
        } else {
            historyIndex = inputHistory.length; // Start at "current input" position
        }
    } else {
        // Navigate through history
        if (direction === 'up') {
            historyIndex = Math.max(0, historyIndex - 1);
        } else {
            historyIndex = Math.min(inputHistory.length, historyIndex + 1);
        }
    }

    // Update the input field
    if (historyIndex === inputHistory.length) {
        // Show current input (what user was typing before navigation)
        paramsInput.value = currentInput;
    } else {
        // Show historical input
        paramsInput.value = inputHistory[historyIndex];
    }

    // Show history indicator
    updateHistoryIndicator();

    // Move cursor to end of input
    setTimeout(() => {
        paramsInput.setSelectionRange(paramsInput.value.length, paramsInput.value.length);
    }, 0);
}

function addToInputHistory(input) {
    if (!input || input.trim() === '') {
        return;
    }

    const trimmedInput = input.trim();

    // Remove duplicate if it already exists
    const existingIndex = inputHistory.indexOf(trimmedInput);
    if (existingIndex !== -1) {
        inputHistory.splice(existingIndex, 1);
    }

    // Add to end of history
    inputHistory.push(trimmedInput);

    // Keep only last 50 entries
    if (inputHistory.length > 50) {
        inputHistory.shift();
    }

    // Save to localStorage for persistence
    saveInputHistoryToStorage();
}

function saveInputHistoryToStorage() {
    try {
        localStorage.setItem('wu-wei-input-history', JSON.stringify(inputHistory));
    } catch (error) {
        console.warn('Failed to save input history to localStorage:', error);
    }
}

function loadInputHistoryFromStorage() {
    try {
        const stored = localStorage.getItem('wu-wei-input-history');
        if (stored) {
            inputHistory = JSON.parse(stored);
            // Ensure it's an array and limit size
            if (!Array.isArray(inputHistory)) {
                inputHistory = [];
            } else if (inputHistory.length > 50) {
                inputHistory = inputHistory.slice(-50);
                saveInputHistoryToStorage();
            }
        }
    } catch (error) {
        console.warn('Failed to load input history from localStorage:', error);
        inputHistory = [];
    }
}

function updateHistoryIndicator() {
    if (!historyIndicator || historyIndex === -1) {
        return;
    }

    const totalEntries = inputHistory.length + 1; // +1 for current input
    const currentPosition = historyIndex + 1;

    if (historyIndex === inputHistory.length) {
        historyIndicator.textContent = `Current`;
    } else {
        historyIndicator.textContent = `${currentPosition}/${totalEntries - 1}`;
    }

    historyIndicator.classList.add('show');
}

function hideHistoryIndicator() {
    if (historyIndicator) {
        historyIndicator.classList.remove('show');
    }
}

function handleInputClick() {
    // If user clicks in input while navigating history, stop navigation
    if (historyIndex !== -1) {
        historyIndex = -1;
        hideHistoryIndicator();
    }
}

function handleInputFocus() {
    // Optional: Could show some indication that history navigation is available
    // For now, just ensure any existing navigation state is cleared if needed
}

function updatePlaceholder() {
    // Placeholder is managed by combined mode settings
    // Always use the combined mode placeholder set by updateInputLabelsAndPlaceholders()
    return;
}

function sendAgentRequest() {
    const agentName = agentSelect.value;
    const method = methodSelect.value;
    const paramsText = paramsInput.value.trim();

    if (!agentName) {
        alert('Please select an agent');
        return;
    }

    if (!method) {
        alert('Please select a method');
        return;
    }

    // Check if we have either a prompt template or a message
    if (!selectedPromptContext && !paramsText.trim()) {
        alert('Please either select a prompt template or enter a message');
        return;
    }

    // If prompt is selected, validate required variables
    if (selectedPromptContext) {
        const validationErrors = validatePromptVariables();
        if (validationErrors.length > 0) {
            alert(`Please fill in required fields:\n${validationErrors.join('\n')}`);
            return;
        }
    }

    // Add input to history before sending
    addToInputHistory(paramsText);

    // Generate a unique message ID for tracking
    const messageId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Track this message as processing
    processingMessages.set(messageId, {
        agentName,
        method,
        startTime: new Date(),
        status: 'processing'
    });

    // Send request with optional prompt context and message ID
    vscode.postMessage({
        command: 'sendAgentRequestWithPrompt',
        messageId,
        agentName,
        method,
        params: parseParams(paramsText),
        promptContext: selectedPromptContext ? {
            promptId: selectedPromptContext.id,
            variables: promptVariables,
            mode: promptMode
        } : null
    });

    // Clear input after sending and reset navigation state
    paramsInput.value = '';
    historyIndex = -1;
    currentInput = '';
    hideHistoryIndicator();

    // Refresh message history to show the processing indicator
    updateMessageHistory();
}

function parseParams(paramsText) {
    if (!paramsText) {
        return {};
    }

    // Try to parse as JSON first
    if (paramsText.startsWith('{') || paramsText.startsWith('[')) {
        try {
            return JSON.parse(paramsText);
        } catch (error) {
            alert('Invalid JSON format. Please check your syntax or use plain text.');
            return null;
        }
    } else {
        // Treat as raw string and convert to appropriate parameter format
        const method = methodSelect.value;
        if (method === 'ask') {
            return { question: paramsText };
        } else if (method === 'openAgent') {
            return { query: paramsText };
        } else if (method === 'echo') {
            return { message: paramsText };
        } else {
            // Generic fallback - use 'message' as the key
            return { message: paramsText };
        }
    }
}

function validatePromptVariables() {
    const errors = [];

    if (!selectedPromptContext || !selectedPromptContext.parameters) {
        return errors;
    }

    selectedPromptContext.parameters.forEach(param => {
        if (param.required) {
            const value = promptVariables[param.name];
            if (value === undefined || value === '' || value === null) {
                errors.push(`${param.name} is required`);
            }
        }
    });

    return errors;
}

function clearHistory() {
    // Clear processing messages tracking
    processingMessages.clear();
    messageExecutionMap.clear();

    // Clear the processing duration interval if active
    if (window.messageProcessingInterval) {
        clearInterval(window.messageProcessingInterval);
        window.messageProcessingInterval = null;
    }

    vscode.postMessage({ command: 'clearHistory' });
}

// Handle message processing completion
function handleMessageProcessingComplete(messageId, success) {
    if (processingMessages.has(messageId)) {
        processingMessages.delete(messageId);
        messageExecutionMap.delete(messageId); // Clean up the execution mapping
        updateMessageHistory(); // Refresh to remove the progress indicator
    }
}

// Phase 2: Execution tracking functions
function handleExecutionStatusUpdate(message) {
    const { executionId, status, details } = message;

    // Update the pending execution status in real-time
    const execution = pendingExecutions.find(e => e.executionId === executionId);
    if (execution) {
        execution.status = status;
        if (details) {
            execution.details = details;
        }
    }

    // Refresh the pending executions display
    updatePendingExecutionsDisplay();

    // Show visual feedback for status changes
    if (status === 'completed' || status === 'failed' || status === 'cancelled') {
        showExecutionStatusNotification(status, details);
    }
}

function updatePendingExecutionsDisplay() {
    const container = document.getElementById('pendingExecutionsContainer');
    if (!container) {
        // Create the pending executions container if it doesn't exist
        createPendingExecutionsSection();
        return;
    }

    const list = container.querySelector('.pending-executions-list');
    if (!list) return;

    if (pendingExecutions.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⏳</div>
                <h4>No running executions</h4>
                <p>All agent executions are complete.</p>
            </div>
        `;
        container.style.display = 'none';

        // Clear the duration update interval when no executions are pending
        if (durationUpdateInterval) {
            clearInterval(durationUpdateInterval);
            durationUpdateInterval = null;
        }
        return;
    }

    container.style.display = 'block';

    // Start duration update interval if not already running
    if (!durationUpdateInterval) {
        durationUpdateInterval = setInterval(() => {
            updateExecutionDurations();
        }, 1000); // Update every second
    }

    renderPendingExecutions(list);
}

function renderPendingExecutions(list) {
    list.innerHTML = pendingExecutions.map(execution => {
        const statusIcon = getStatusIcon(execution.status);
        const currentTime = new Date().getTime();
        const startTime = new Date(execution.startTime).getTime();
        const duration = formatDuration(currentTime - startTime);
        const startTimeFormatted = new Date(execution.startTime).toLocaleTimeString();

        return `
            <div class="execution-item ${execution.status}" data-execution-id="${execution.executionId}">
                <div class="execution-header">
                    <span class="execution-status">${statusIcon} ${execution.status}</span>
                    <span class="execution-duration" data-start-time="${execution.startTime}">${duration}</span>
                </div>
                <div class="execution-details">
                    <div class="execution-agent">${execution.agentName}.${execution.method}</div>
                    <div class="execution-task">${truncateText(execution.taskDescription)}</div>
                    <div class="execution-time">Started: ${startTimeFormatted}</div>
                </div>
                <div class="execution-actions">
                    <button class="btn-cancel" onclick="cancelExecution('${execution.executionId}')" 
                            ${execution.status !== 'executing' ? 'disabled' : ''}>
                        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                            <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
                        </svg>
                        Cancel
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function updateExecutionDurations() {
    // Update duration displays for running executions
    const durationElements = document.querySelectorAll('.execution-duration[data-start-time]');
    const currentTime = new Date().getTime();

    durationElements.forEach(element => {
        const startTime = new Date(element.getAttribute('data-start-time')).getTime();
        const duration = formatDuration(currentTime - startTime);
        element.textContent = duration;
    });
}

function updateExecutionHistoryDisplay(stats) {
    // This function can be implemented later for execution history display
    console.log('Execution history updated:', executionHistory.length, 'entries');
    console.log('Stats:', stats);
}

function showExecutionStatusNotification(status, details) {
    // Create a temporary notification element
    const notification = document.createElement('div');
    notification.className = `execution-notification ${status}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-icon">${getStatusIcon(status)}</span>
            <span class="notification-text">Execution ${status}</span>
        </div>
    `;

    // Add to the page temporarily
    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);

    // Remove after delay
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => document.body.removeChild(notification), 300);
    }, 2000);
}

function cancelExecution(executionId) {
    vscode.postMessage({
        command: 'cancelExecution',
        executionId: executionId
    });
}

function cancelMessageExecution(messageId) {
    vscode.postMessage({
        command: 'cancelMessageExecution',
        messageId: messageId
    });
}

function createPendingExecutionsSection() {
    // Find the input section to insert the pending executions section after it
    const inputSection = document.querySelector('.input-section');
    if (!inputSection) return;

    const pendingSection = document.createElement('div');
    pendingSection.className = 'section pending-executions-section';
    pendingSection.id = 'pendingExecutionsContainer';
    pendingSection.style.display = 'none'; // Initially hidden

    pendingSection.innerHTML = `
        <div class="section-header">
            <div class="section-title">
                <span class="icon">⏳</span>
                <span>Running Executions</span>
                <button class="collapse-toggle" id="pendingToggle" onclick="togglePendingCollapse()"
                        title="Toggle pending executions visibility">
                    <svg class="collapse-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708z"/>
                    </svg>
                </button>
            </div>
            <div class="section-subtitle">Real-time status of agent executions</div>
        </div>
        <div class="collapsible-content" id="pendingContent">
            <div class="pending-executions-list">
                <!-- Pending executions will be populated here -->
            </div>
        </div>
    `;

    // Insert after the input section
    inputSection.parentNode.insertBefore(pendingSection, inputSection.nextSibling);
}

function togglePendingCollapse() {
    const pendingSection = document.querySelector('.pending-executions-section');

    if (!pendingSection) {
        console.error('Pending executions section not found');
        return;
    }

    const isCollapsed = pendingSection.classList.contains('collapsed');

    if (isCollapsed) {
        pendingSection.classList.remove('collapsed');
        localStorage.setItem('pendingCollapsed', 'false');
        console.log('Expanded pending executions section');
    } else {
        pendingSection.classList.add('collapsed');
        localStorage.setItem('pendingCollapsed', 'true');
        console.log('Collapsed pending executions section');
    }
}

function updateMessageHistory() {
    // Check if we have processing messages or regular messages
    const hasProcessingMessages = processingMessages.size > 0;
    const hasMessages = messageHistory.length > 0;

    if (!hasMessages && !hasProcessingMessages) {
        messageList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">💬</div>
                <h3>No messages yet</h3>
                <p>Send your first agent request to see the conversation history here.</p>
            </div>
        `;
        return;
    }

    let messagesHtml = '';

    // Build tree structure from messages grouped by session/request
    if (hasMessages) {
        const sessionTree = buildSessionTree(messageHistory);
        messagesHtml += renderSessionTree(sessionTree);
    }

    // Add processing messages at the end
    if (hasProcessingMessages) {
        messagesHtml += renderProcessingMessages();
    }

    messageList.innerHTML = messagesHtml;

    // Start/stop duration updates for processing messages
    if (hasProcessingMessages && !window.messageProcessingInterval) {
        window.messageProcessingInterval = setInterval(updateProcessingMessageDurations, 1000);
    } else if (!hasProcessingMessages && window.messageProcessingInterval) {
        clearInterval(window.messageProcessingInterval);
        window.messageProcessingInterval = null;
    }

    // Scroll to bottom with smooth animation
    setTimeout(() => {
        messageList.scrollTo({
            top: messageList.scrollHeight,
            behavior: 'smooth'
        });
    }, 100);
}

// Build a tree structure from messages grouped by session/request
function buildSessionTree(messages) {
    const sessions = [];
    let currentSession = null;

    for (let i = 0; i < messages.length; i++) {
        const message = messages[i];

        if (message.type === 'request') {
            // Start a new session
            currentSession = {
                id: `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                request: message,
                responses: [],
                timestamp: message.timestamp,
                summary: generateRequestSummary(message),
                executionId: message.params?.executionId || null,
                expanded: false // Default to collapsed
            };
            sessions.push(currentSession);
        } else if (currentSession) {
            // Add response to current session
            currentSession.responses.push(message);
        }
    }

    return sessions;
}

// Generate a short summary for a request (first 10 words or method name)
function generateRequestSummary(request) {
    // Try to extract meaningful text from parameters
    let text = '';

    if (request.params?.message) {
        text = request.params.message;
    } else if (request.params?.query) {
        text = request.params.query;
    } else if (request.params?.input) {
        text = request.params.input;
    } else if (request.method) {
        text = `${request.method} request`;
    } else {
        text = 'Agent request';
    }

    // Clean and truncate to first 10 words
    const words = text.replace(/\n/g, ' ').split(' ').filter(word => word.trim());
    const summary = words.slice(0, 10).join(' ');

    return summary.length > 60 ? summary.substring(0, 57) + '...' : summary;
}

// Render the session tree structure
function renderSessionTree(sessions) {
    if (!sessions.length) return '';

    return `
        <div class="session-tree">
            ${sessions.map(session => renderSessionNode(session)).join('')}
        </div>
    `;
}

// Render a single session node (request + responses)
function renderSessionNode(session) {
    const timestamp = new Date(session.timestamp).toLocaleString();
    const responseCount = session.responses.length;
    const hasResponses = responseCount > 0;
    const isExpanded = session.expanded;

    // Determine session status based on responses
    let sessionStatus = 'pending';
    let statusIcon = '⏳';
    let statusText = 'Pending';

    if (hasResponses) {
        const hasCompletionSignal = session.responses.some(r =>
            r.result?.type === 'completion-signal' || r.result?.type === 'standalone-completion-signal'
        );
        const hasErrors = session.responses.some(r => r.error || r.type === 'error');

        if (hasCompletionSignal) {
            const completionResponse = session.responses.find(r =>
                r.result?.type === 'completion-signal' || r.result?.type === 'standalone-completion-signal'
            );
            const status = completionResponse?.result?.status || 'success';
            sessionStatus = status;
            statusIcon = getStatusIcon(status);
            statusText = status.charAt(0).toUpperCase() + status.slice(1);
        } else if (hasErrors) {
            sessionStatus = 'error';
            statusIcon = '❌';
            statusText = 'Error';
        } else {
            sessionStatus = 'processing';
            statusIcon = '🔄';
            statusText = 'Processing';
        }
    }

    return `
        <div class="session-node ${sessionStatus}" data-session-id="${session.id}">
            <div class="session-header">
                <div class="session-expand-icon ${isExpanded ? 'expanded' : ''}" data-action="toggle" data-session-id="${session.id}" title="${isExpanded ? 'Collapse' : 'Expand'}">
                    <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M6 12L10 8L6 4" />
                    </svg>
                </div>
                <div class="session-info" data-action="open-editor" data-session-id="${session.id}">
                    <div class="session-summary">${session.summary}</div>
                    <div class="session-meta">
                        <span class="session-timestamp">${timestamp}</span>
                        <span class="session-status ${sessionStatus}">
                            <span class="status-icon">${statusIcon}</span>
                            ${statusText}
                        </span>
                        ${hasResponses ? `<span class="response-count">${responseCount} response${responseCount > 1 ? 's' : ''}</span>` : ''}
                    </div>
                </div>
            </div>
            
            ${isExpanded ? `
                <div class="session-content">
                    <div class="request-details">
                        ${formatRequestDetails(session.request)}
                    </div>
                    ${hasResponses ? `
                        <div class="responses-list">
                            ${session.responses.map(response => formatResponseDetails(response)).join('')}
                        </div>
                    ` : ''}
                </div>
            ` : ''}
        </div>
    `;
}

// Open session details in main editor
function openSessionInEditor(sessionId) {
    console.log('openSessionInEditor called with sessionId:', sessionId);

    // Check if vscode API is available
    if (typeof vscode === 'undefined') {
        console.error('vscode API is not available');
        return;
    }

    // Find the session data
    const sessions = buildSessionTree(messageHistory);
    console.log('Available sessions:', sessions);
    const session = sessions.find(s => s.id === sessionId);

    if (!session) {
        console.error('Session not found:', sessionId, 'Available sessions:', sessions.map(s => s.id));
        return;
    }

    console.log('Found session:', session);

    try {
        // Send message to backend to open detailed view
        vscode.postMessage({
            command: 'openSessionDetails',
            sessionId: sessionId,
            session: {
                id: session.id,
                summary: session.summary,
                timestamp: session.timestamp,
                executionId: session.executionId,
                request: session.request,
                responses: session.responses
            }
        });

        console.log('Sent openSessionDetails message to backend');
    } catch (error) {
        console.error('Error sending message to backend:', error);
    }
}

// Make sure the function is globally accessible
window.openSessionInEditor = openSessionInEditor;
window.toggleSession = toggleSession;

// Format request details for expanded view
function formatRequestDetails(request) {
    const displayParams = { ...request.params };
    delete displayParams.executionId; // Hide internal fields

    return `
        <div class="detail-item request-detail">
            <div class="detail-header">
                <span class="detail-type request">📤 Request</span>
                <span class="detail-method">${request.method}</span>
            </div>
            <div class="detail-content">
                <div class="params-block">
                    <div class="params-label">Parameters:</div>
                    <pre class="params-code">${JSON.stringify(displayParams, null, 2)}</pre>
                </div>
            </div>
        </div>
    `;
}

// Format response details for expanded view
function formatResponseDetails(response) {
    let responseType = 'response';
    let typeIcon = '✅';
    let typeLabel = 'Response';
    let content = '';

    if (response.error || response.type === 'error') {
        responseType = 'error';
        typeIcon = '❌';
        typeLabel = 'Error';
        const error = response.error || { message: 'Unknown error', code: 'N/A' };
        content = `
            <div class="error-block">
                <div class="error-message"><strong>Error:</strong> ${error.message}</div>
                <div class="error-code"><strong>Code:</strong> ${error.code}</div>
                ${error.data ? `<div class="error-data"><strong>Details:</strong></div><pre class="error-data-code">${JSON.stringify(error.data, null, 2)}</pre>` : ''}
            </div>
        `;
    } else if (response.result?.type === 'completion-signal') {
        responseType = 'completion';
        const status = response.result.status;
        typeIcon = getStatusIcon(status);
        typeLabel = 'Task Completion';

        content = `
            <div class="completion-block">
                <div class="completion-status"><strong>Status:</strong> ${status}</div>
                <div class="completion-task"><strong>Task:</strong> ${response.result.taskDescription}</div>
                <div class="completion-summary-text"><strong>Summary:</strong> ${response.result.summary}</div>
                ${response.result.duration ? `<div class="completion-duration"><strong>Duration:</strong> ${formatDuration(response.result.duration)}</div>` : ''}
                ${response.result.agentName ? `<div class="completion-agent"><strong>Agent:</strong> ${response.result.agentName}</div>` : ''}
            </div>
        `;
    } else if (response.result?.type === 'standalone-completion-signal') {
        responseType = 'standalone-completion';
        const status = response.result.status;
        typeIcon = getStatusIcon(status);
        typeLabel = 'Standalone Completion';

        content = `
            <div class="completion-block standalone">
                <div class="completion-status"><strong>Status:</strong> ${status}</div>
                <div class="completion-task"><strong>Task:</strong> ${response.result.taskDescription}</div>
                <div class="completion-summary-text"><strong>Summary:</strong> ${response.result.summary}</div>
                <div class="standalone-note"><em>Note: This completion could not be correlated with a specific request.</em></div>
            </div>
        `;
    } else {
        // Regular response (acknowledgment)
        responseType = 'acknowledgment';
        typeIcon = '✅';
        typeLabel = 'Agent Acknowledgment';

        content = `
            <div class="response-block">
                <pre class="response-code">${JSON.stringify(response.result, null, 2)}</pre>
                <div class="response-note"><em>Initial response - waiting for task completion...</em></div>
            </div>
        `;
    }

    const timestamp = new Date(response.timestamp).toLocaleString();

    return `
        <div class="detail-item response-detail ${responseType}">
            <div class="detail-header">
                <span class="detail-type ${responseType}">${typeIcon} ${typeLabel}</span>
                <span class="detail-timestamp">${timestamp}</span>
            </div>
            <div class="detail-content">
                ${content}
            </div>
        </div>
    `;
}

// Render processing messages
function renderProcessingMessages() {
    if (processingMessages.size === 0) return '';

    let html = '<div class="processing-sessions">';

    processingMessages.forEach((processingInfo, messageId) => {
        const timestamp = new Date(processingInfo.startTime).toLocaleString();
        const duration = formatDuration(new Date().getTime() - processingInfo.startTime.getTime());
        const hasExecutionId = messageExecutionMap.has(messageId);

        // Generate summary for processing request
        const summary = `${processingInfo.method} request`;

        html += `
            <div class="session-node processing" data-message-id="${messageId}">
                <div class="session-header processing">
                    <div class="session-info">
                        <div class="session-summary">${summary}</div>
                        <div class="session-meta">
                            <span class="session-timestamp">${timestamp}</span>
                            <span class="session-status processing">
                                <span class="status-icon processing-spinner-small">🔄</span>
                                Processing
                            </span>
                            <span class="processing-duration">${duration}</span>
                        </div>
                    </div>
                    ${hasExecutionId ? `
                        <button class="btn-cancel-session" onclick="cancelMessageExecution('${messageId}')" title="Cancel execution">
                            <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M2.146 2.854a.5.5 0 1 1 .708-.708L8 7.293l5.146-5.147a.5.5 0 0 1 .708.708L8.707 8l5.147 5.146a.5.5 0 0 1-.708.708L8 8.707l-5.146 5.147a.5.5 0 0 1-.708-.708L7.293 8 2.146 2.854Z"/>
                            </svg>
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    });

    html += '</div>';
    return html;
}

// Toggle session expansion state
function toggleSession(sessionId) {
    const sessionNode = document.querySelector(`[data-session-id="${sessionId}"]`);
    if (!sessionNode) return;

    const expandIcon = sessionNode.querySelector('.session-expand-icon');
    const isCurrentlyExpanded = expandIcon.classList.contains('expanded');

    // Toggle the expanded state
    if (isCurrentlyExpanded) {
        expandIcon.classList.remove('expanded');
        sessionNode.classList.remove('expanded');
        // Remove content
        const content = sessionNode.querySelector('.session-content');
        if (content) {
            content.remove();
        }
    } else {
        expandIcon.classList.add('expanded');
        sessionNode.classList.add('expanded');

        // Find the session data and render content
        const sessions = buildSessionTree(messageHistory);
        const session = sessions.find(s => s.id === sessionId);
        if (session) {
            session.expanded = true;
            const contentHtml = `
                <div class="session-content">
                    <div class="request-details">
                        ${formatRequestDetails(session.request)}
                    </div>
                    ${session.responses.length ? `
                        <div class="responses-list">
                            ${session.responses.map(response => formatResponseDetails(response)).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
            sessionNode.insertAdjacentHTML('beforeend', contentHtml);
        }
    }
}

// Update duration displays for processing messages
function updateProcessingMessageDurations() {
    const currentTime = new Date().getTime();

    processingMessages.forEach((processingInfo, messageId) => {
        const messageElement = document.querySelector(`[data-message-id="${messageId}"] .processing-duration`);
        if (messageElement) {
            const duration = formatDuration(currentTime - processingInfo.startTime.getTime());
            messageElement.textContent = duration;
        }
    });

    // If there are no more processing messages, clear the interval
    if (processingMessages.size === 0 && window.messageProcessingInterval) {
        clearInterval(window.messageProcessingInterval);
        window.messageProcessingInterval = null;
    }
}

// Initialize the panel
document.addEventListener('DOMContentLoaded', function () {
    initializeCollapseState();
    updateInputLabelsAndPlaceholders();
    updateUIForCombinedMode();

    // Load input history from storage
    loadInputHistoryFromStorage();

    // Create pending executions section
    createPendingExecutionsSection();

    // Add event delegation for session clicks
    setupSessionEventHandlers();

    // Initialize pending executions collapse state after a short delay
    // to ensure the section is fully created
    setTimeout(() => {
        const savedPendingState = localStorage.getItem('pendingCollapsed');
        const pendingSection = document.querySelector('.pending-executions-section');
        const isPendingCollapsed = savedPendingState === 'true';

        if (isPendingCollapsed && pendingSection) {
            pendingSection.classList.add('collapsed');
        }
    }, 100);
});

// Global reference to prevent duplicate event handlers
let sessionClickHandler = null;

// Setup event delegation for session interactions
function setupSessionEventHandlers() {
    // Remove existing handler if it exists to prevent duplicates
    if (sessionClickHandler) {
        document.removeEventListener('click', sessionClickHandler);
    }

    // Create new handler
    sessionClickHandler = function (event) {
        const target = event.target.closest('[data-action]');

        if (!target) {
            return;
        }

        const action = target.getAttribute('data-action');
        const sessionId = target.getAttribute('data-session-id');

        if (!sessionId) {
            console.error('No session ID found for action:', action);
            return;
        }

        // Prevent default behavior and stop propagation
        event.preventDefault();
        event.stopPropagation();

        switch (action) {
            case 'toggle':
                toggleSession(sessionId);
                break;
            case 'open-editor':
                openSessionInEditor(sessionId);
                break;
            default:
                console.warn('Unknown session action:', action);
        }
    };

    // Add the new handler
    document.addEventListener('click', sessionClickHandler);
}

// Request initial data
vscode.postMessage({ command: 'getAgentCapabilities' });
vscode.postMessage({ command: 'getAvailablePrompts' });
vscode.postMessage({ command: 'getPendingExecutions' });
vscode.postMessage({ command: 'getExecutionHistory' });

// Cleanup on page unload
window.addEventListener('beforeunload', function () {
    if (durationUpdateInterval) {
        clearInterval(durationUpdateInterval);
    }
    if (window.messageProcessingInterval) {
        clearInterval(window.messageProcessingInterval);
    }
});
