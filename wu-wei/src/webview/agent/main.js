// Wu Wei Agent Panel JavaScript

const vscode = acquireVsCodeApi();
let agentCapabilities = [];
let messageHistory = [];

// DOM elements
const agentSelect = document.getElementById('agentSelect');
const methodSelect = document.getElementById('methodSelect');
const paramsInput = document.getElementById('paramsInput');
const agentTooltip = document.getElementById('agentTooltip');
const messageList = document.getElementById('messageList');

// Event listeners
agentSelect.addEventListener('change', updateMethodSelect);
methodSelect.addEventListener('change', updatePlaceholder);
paramsInput.addEventListener('keydown', handleKeyDown);

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
    }
});

// Initialize collapse state from localStorage
function initializeCollapseState() {
    const savedState = localStorage.getItem('historyCollapsed');
    const historySection = document.querySelector('.history-section');

    // Default to collapsed if no saved state exists, otherwise use saved state
    const isCollapsed = savedState === null ? true : savedState === 'true';

    if (isCollapsed) {
        historySection.classList.add('collapsed');
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
        paramsInput.placeholder = 'Select an agent and method first';
        agentTooltip.textContent = 'Select an agent to see its capabilities';
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

    // Update placeholder based on selected agent
    if (selectedAgent === 'github-copilot') {
        paramsInput.placeholder = 'Ask a question or describe what you need help with...';

        // Auto-select openAgent method for GitHub Copilot
        const openAgentOption = Array.from(methodSelect.options).find(option => option.value === 'openAgent');
        if (openAgentOption) {
            methodSelect.value = 'openAgent';
            updatePlaceholder();
        }
    } else if (selectedAgent === 'wu-wei-example') {
        paramsInput.placeholder = 'Enter your message or use JSON: {"action": "test"}';
    } else {
        paramsInput.placeholder = 'Enter your message or question...';
    }
}

function handleKeyDown(event) {
    // Check for Ctrl+Enter (or Cmd+Enter on Mac)
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        sendAgentRequest();
    }
}

function updatePlaceholder() {
    const selectedAgent = agentSelect.value;
    const selectedMethod = methodSelect.value;

    if (!selectedAgent || !selectedMethod) {
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

    let params = {};
    if (paramsText) {
        // Try to parse as JSON first
        if (paramsText.startsWith('{') || paramsText.startsWith('[')) {
            try {
                params = JSON.parse(paramsText);
            } catch (error) {
                alert('Invalid JSON format. Please check your syntax or use plain text.');
                return;
            }
        } else {
            // Treat as raw string and convert to appropriate parameter format
            // For most common cases, treat it as a message or question
            if (method === 'ask') {
                params = { question: paramsText };
            } else if (method === 'openAgent') {
                params = { query: paramsText };
            } else if (method === 'echo') {
                params = { message: paramsText };
            } else {
                // Generic fallback - use 'message' as the key
                params = { message: paramsText };
            }
        }
    }

    vscode.postMessage({
        command: 'sendAgentRequest',
        agentName,
        method,
        params
    });

    // Clear input after sending
    paramsInput.value = '';
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

// Initialize the collapse state when the page loads
document.addEventListener('DOMContentLoaded', function () {
    initializeCollapseState();
});

// Request initial data
vscode.postMessage({ command: 'getAgentCapabilities' });
