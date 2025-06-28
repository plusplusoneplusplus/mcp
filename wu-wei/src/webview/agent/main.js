// Wu Wei Agent Panel JavaScript

const vscode = acquireVsCodeApi();
let agentCapabilities = [];
let messageHistory = [];

// Prompt integration state
let availablePrompts = [];
let selectedPromptContext = null;
let promptVariables = {};
let promptMode = 'custom';

// DOM elements
const agentSelect = document.getElementById('agentSelect');
const methodSelect = document.getElementById('methodSelect');
const paramsInput = document.getElementById('paramsInput');
const agentTooltip = document.getElementById('agentTooltip');
const messageList = document.getElementById('messageList');

// DOM elements - new prompt integration
const promptModeSelector = document.getElementById('promptModeSelector');
const promptSelectorContainer = document.getElementById('promptSelectorContainer');
const promptSearch = document.getElementById('promptSearch');
const promptSelector = document.getElementById('promptSelector');
const variableEditorContainer = document.getElementById('variableEditorContainer');
const variableEditor = document.getElementById('variableEditor');
const promptPreviewContainer = document.getElementById('promptPreviewContainer');
const promptPreview = document.getElementById('promptPreview');
const parameterSubtitle = document.getElementById('parameterSubtitle');
const parametersLabel = document.getElementById('parametersLabel');

// Event listeners
agentSelect.addEventListener('change', updateMethodSelect);
methodSelect.addEventListener('change', updatePlaceholder);
paramsInput.addEventListener('keydown', handleKeyDown);

// Event listeners - new prompt integration
promptModeSelector.addEventListener('change', handlePromptModeChange);
promptSearch.addEventListener('input', debounce(handlePromptSearch, 300));
promptSelector.addEventListener('change', handlePromptSelection);

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
    }
});

// Initialize collapse state from localStorage
function initializeCollapseState() {
    // Initialize history section collapse state
    const savedHistoryState = localStorage.getItem('historyCollapsed');
    const historySection = document.querySelector('.history-section');

    // Default to collapsed if no saved state exists, otherwise use saved state
    const isHistoryCollapsed = savedHistoryState === null ? true : savedHistoryState === 'true';

    if (isHistoryCollapsed) {
        historySection.classList.add('collapsed');
    }

    // Initialize agent selection collapse state
    const savedAgentState = localStorage.getItem('agentCollapsed');
    const agentSection = document.querySelector('.agent-selection');

    // Default to expanded for agent selection (false means not collapsed)
    const isAgentCollapsed = savedAgentState === 'true';

    if (isAgentCollapsed) {
        agentSection.classList.add('collapsed');
    }
}

// Toggle history collapse state
function toggleHistoryCollapse() {
    const historySection = document.querySelector('.history-section');
    const isCollapsed = historySection.classList.contains('collapsed');

    if (isCollapsed) {
        historySection.classList.remove('collapsed');
        localStorage.setItem('historyCollapsed', 'false');
    } else {
        historySection.classList.add('collapsed');
        localStorage.setItem('historyCollapsed', 'true');
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

// Prompt Mode Management
function handlePromptModeChange() {
    promptMode = promptModeSelector.value;
    updateUIForPromptMode();
    updateInputLabelsAndPlaceholders();
}

function updateUIForPromptMode() {
    switch (promptMode) {
        case 'custom':
            promptSelectorContainer.style.display = 'none';
            variableEditorContainer.style.display = 'none';
            promptPreviewContainer.style.display = 'none';
            break;
        case 'prompt':
            promptSelectorContainer.style.display = 'block';
            // Only show variable editor if prompt has variables
            const hasVariablesPrompt = selectedPromptContext?.parameters?.length > 0;
            variableEditorContainer.style.display = selectedPromptContext && hasVariablesPrompt ? 'block' : 'none';
            promptPreviewContainer.style.display = selectedPromptContext ? 'block' : 'none';
            break;
        case 'combined':
            promptSelectorContainer.style.display = 'block';
            // Only show variable editor if prompt has variables
            const hasVariables = selectedPromptContext?.parameters?.length > 0;
            variableEditorContainer.style.display = selectedPromptContext && hasVariables ? 'block' : 'none';
            promptPreviewContainer.style.display = selectedPromptContext ? 'block' : 'none';
            break;
    }
}

function updateInputLabelsAndPlaceholders() {
    switch (promptMode) {
        case 'custom':
            parameterSubtitle.textContent = 'Enter your message or JSON parameters';
            parametersLabel.textContent = 'Message/Parameters';
            paramsInput.placeholder = 'Enter your message or JSON parameters...';
            break;
        case 'prompt':
            parameterSubtitle.textContent = 'Use selected prompt template only';
            parametersLabel.textContent = 'Additional Parameters (Optional)';
            paramsInput.placeholder = 'Enter additional JSON parameters if needed...';
            break;
        case 'combined':
            parameterSubtitle.textContent = 'Add custom message to combine with prompt';
            parametersLabel.textContent = 'Additional Message';
            paramsInput.placeholder = 'Enter additional message to combine with prompt...';
            break;
    }
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

    promptSelector.innerHTML = '<option value="">Select a prompt...</option>';
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
        updateUIForPromptMode();
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

    // Update prompt preview
    renderPromptPreview();

    // Show appropriate containers
    updateUIForPromptMode();
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
    if (!selectedPromptContext || promptMode === 'custom') {
        clearPromptPreview();
        return;
    }

    // Request prompt rendering from extension
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

    promptPreview.innerHTML = `
        <div class="preview-content">
            <h4>Rendered Prompt:</h4>
            <div class="preview-text">${formatPreviewContent(rendered)}</div>
        </div>
    `;
}

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
    }
}

function updatePlaceholder() {
    if (promptMode !== 'custom') {
        return; // Placeholder is managed by prompt mode
    }

    const selectedAgent = agentSelect.value;
    const selectedMethod = methodSelect.value;

    if (!selectedAgent || !selectedMethod) {
        paramsInput.placeholder = 'Select an agent and method first';
        return;
    }

    // Update placeholder based on agent and method
    if (selectedAgent === 'github-copilot') {
        if (selectedMethod === 'ask') {
            paramsInput.placeholder = 'Ask a question about your code or project...';
        } else if (selectedMethod === 'openAgent') {
            paramsInput.placeholder = 'Describe what you want to do or ask about...';
        }
    } else if (selectedAgent === 'wu-wei-example') {
        if (selectedMethod === 'echo') {
            paramsInput.placeholder = 'Enter a message to echo back...';
        } else if (selectedMethod === 'status') {
            paramsInput.placeholder = 'No parameters needed (leave empty)';
        } else if (selectedMethod === 'execute') {
            paramsInput.placeholder = 'Describe what to execute or use JSON: {"action": "test"}';
        }
    }
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

    // Handle different prompt modes
    if (promptMode === 'combined') {
        if (!selectedPromptContext) {
            alert('Please select a prompt for this input mode');
            return;
        }

        if (!paramsText.trim()) {
            alert('Please enter a custom message to combine with the prompt');
            return;
        }

        // Validate required variables
        const validationErrors = validatePromptVariables();
        if (validationErrors.length > 0) {
            alert(`Please fill in required fields:\n${validationErrors.join('\n')}`);
            return;
        }

        // Send request with prompt context
        vscode.postMessage({
            command: 'sendAgentRequestWithPrompt',
            agentName,
            method,
            params: parseParams(paramsText),
            promptContext: {
                promptId: selectedPromptContext.id,
                variables: promptVariables,
                mode: promptMode
            }
        });
    } else {
        // Standard request without prompt
        vscode.postMessage({
            command: 'sendAgentRequest',
            agentName,
            method,
            params: parseParams(paramsText)
        });
    }

    // Clear input after sending (only for custom mode or combined additional message)
    if (promptMode === 'custom' || promptMode === 'combined') {
        paramsInput.value = '';
    }
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
    vscode.postMessage({ command: 'clearHistory' });
}

function updateMessageHistory() {
    if (messageHistory.length === 0) {
        messageList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">💬</div>
                <h3>No messages yet</h3>
                <p>Send your first agent request to see the conversation history here.</p>
            </div>
        `;
        return;
    }

    messageList.innerHTML = messageHistory.map(message => {
        const timestamp = new Date(message.timestamp).toLocaleString();

        let content = '';
        let typeClass = message.type;

        if (message.type === 'request') {
            content = `Method: ${message.method}\nParams: ${JSON.stringify(message.params, null, 2)}`;
        } else if (message.type === 'response') {
            if (message.error) {
                content = `Error: ${message.error.message}\nCode: ${message.error.code}`;
                if (message.error.data) {
                    content += `\nData: ${JSON.stringify(message.error.data, null, 2)}`;
                }
                typeClass = 'error';
            } else {
                content = `Result: ${JSON.stringify(message.result, null, 2)}`;
            }
        } else if (message.type === 'error') {
            content = `Error: ${message.error?.message || 'Unknown error'}\nCode: ${message.error?.code || 'N/A'}`;
        }

        return `
            <div class="message-item ${typeClass}">
                <div class="message-header">
                    <span class="message-type ${typeClass}">${message.type}</span>
                    <span class="message-timestamp">${timestamp}</span>
                </div>
                <div class="message-content">${content}</div>
            </div>
        `;
    }).join('');

    // Scroll to bottom with smooth animation
    setTimeout(() => {
        messageList.scrollTo({
            top: messageList.scrollHeight,
            behavior: 'smooth'
        });
    }, 100);
}

// Initialize the panel
document.addEventListener('DOMContentLoaded', function () {
    initializeCollapseState();
    updateInputLabelsAndPlaceholders();
});

// Request initial data
vscode.postMessage({ command: 'getAgentCapabilities' });
vscode.postMessage({ command: 'getAvailablePrompts' });
