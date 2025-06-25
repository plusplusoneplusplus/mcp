// Wu Wei Chat JavaScript
const vscode = acquireVsCodeApi();

let sessions = [];
let currentSessionId = null;
let messages = [];
let availableModels = [];

// Auto-resize textarea
document.getElementById('messageInput').addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 80) + 'px';
});

// Send on Enter
document.getElementById('messageInput').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Model selector
document.getElementById('modelSelector').addEventListener('change', function () {
    if (this.value) {
        vscode.postMessage({
            command: 'selectModel',
            modelFamily: this.value
        });
    }
});

function newChat() {
    vscode.postMessage({ command: 'newChat' });
}

function selectSession(sessionId) {
    vscode.postMessage({
        command: 'selectSession',
        sessionId: sessionId
    });
}

function deleteSession(sessionId, event) {
    event.stopPropagation();
    vscode.postMessage({
        command: 'deleteSession',
        sessionId: sessionId
    });
}

function renameSession(sessionId, event) {
    event.stopPropagation();
    const newName = prompt('Enter new name:');
    if (newName && newName.trim()) {
        vscode.postMessage({
            command: 'renameSession',
            sessionId: sessionId,
            newName: newName.trim()
        });
    }
}

document.getElementById('errorActionBtn').addEventListener('click', () => {
    // Error action removed - diagnostics functionality removed
});

function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    if (!message) return;

    // Add user message immediately
    addMessage(message, true);
    input.value = '';
    input.style.height = 'auto';

    vscode.postMessage({
        command: 'sendMessage',
        text: message
    });
}

function addMessage(text, isUser) {
    const container = document.getElementById('messagesContainer');
    const emptyState = document.getElementById('emptyState');

    if (emptyState.style.display !== 'none') {
        emptyState.style.display = 'none';
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
    messageDiv.textContent = text;

    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

function updateSessions(sessionData) {
    sessions = sessionData;
    const sessionsList = document.getElementById('sessionsList');
    sessionsList.innerHTML = '';

    sessions.forEach(session => {
        const sessionDiv = document.createElement('div');
        sessionDiv.className = `session-item ${session.id === currentSessionId ? 'active' : ''}`;
        sessionDiv.onclick = () => selectSession(session.id);

        sessionDiv.innerHTML = `
            <div class="session-info">
                <div class="session-title">${session.title}</div>
                <div class="session-preview">${session.lastMessage || 'No messages'}</div>
            </div>
            <div class="session-actions">
                <button class="action-btn" onclick="renameSession('${session.id}', event)" title="Rename">✏️</button>
                <button class="action-btn" onclick="deleteSession('${session.id}', event)" title="Delete">🗑️</button>
            </div>
        `;

        sessionsList.appendChild(sessionDiv);
    });
}

function updateMessages(messageData) {
    messages = messageData;
    const container = document.getElementById('messagesContainer');
    const emptyState = document.getElementById('emptyState');
    const thinkingIndicator = document.getElementById('thinkingIndicator');

    // Clear existing messages (except empty state and thinking indicator)
    const messagesToRemove = container.querySelectorAll('.message');
    messagesToRemove.forEach(msg => msg.remove());

    if (messages.length === 0) {
        emptyState.style.display = 'flex';
    } else {
        emptyState.style.display = 'none';
        messages.forEach(msg => {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${msg.role === 'user' ? 'user' : 'assistant'}`;
            messageDiv.textContent = msg.content;
            container.insertBefore(messageDiv, thinkingIndicator);
        });
    }

    container.scrollTop = container.scrollHeight;
}

function updateModels(modelData, currentModel, loading, error) {
    console.log('updateModels called:', { modelData, currentModel, loading, error });
    console.log('Models received in webview:', modelData);

    availableModels = modelData;
    const selector = document.getElementById('modelSelector');
    selector.innerHTML = '';

    // Handle loading state
    const input = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');

    if (loading === false) {
        console.log('Clearing loading state - enabling input');
        input.disabled = false;
        sendBtn.disabled = false;
        input.placeholder = 'Type your message...';
    }

    // Show error if any
    const errorContainer = document.getElementById('errorMessage');
    const errorTitle = document.getElementById('errorTitle');
    const errorDetails = document.getElementById('errorDetails');
    const errorActionBtn = document.getElementById('errorActionBtn');

    if (error) {
        console.log('Model loading error:', error);
        errorTitle.textContent = error.message || 'An error occurred.';
        errorDetails.textContent = error.details || '';
        if (error.actionable) {
            errorActionBtn.style.display = 'inline-block';
        } else {
            errorActionBtn.style.display = 'none';
        }
        errorContainer.style.display = 'block';
    } else {
        errorContainer.style.display = 'none';
    }

    if (modelData.length === 0) {
        console.log('No models available, showing default option');
        selector.innerHTML = '<option value="">No models available</option>';
        return;
    }

    console.log('Adding models to selector:');
    modelData.forEach((model, index) => {
        console.log(`  ${index + 1}. ${model.family} (${model.vendor}) - ${model.name}`);
        const option = document.createElement('option');
        option.value = model.family;
        option.textContent = `${model.family} (${model.vendor})`;
        if (model.family === currentModel) {
            option.selected = true;
            console.log(`Selected model: ${model.family}`);
        }
        selector.appendChild(option);
    });

    console.log(`Total options added to selector: ${selector.options.length}`);
}

// Debug functions
function showModelDetails() {
    console.log('Requesting detailed model information...');
    vscode.postMessage({ command: 'showModelDetails' });
}

// Handle messages from extension
window.addEventListener('message', event => {
    const message = event.data;

    switch (message.command) {
        case 'updateState':
            currentSessionId = message.currentSessionId;
            updateSessions(message.sessions);
            updateMessages(message.messages);
            break;
        case 'addMessage':
            addMessage(message.message, message.isUser);
            break;
        case 'showThinking':
            document.getElementById('thinkingIndicator').style.display = 'flex';
            document.getElementById('messagesContainer').scrollTop = document.getElementById('messagesContainer').scrollHeight;
            break;
        case 'hideThinking':
            document.getElementById('thinkingIndicator').style.display = 'none';
            break;
        case 'updateModels':
            updateModels(message.models, message.currentModel, message.loading, message.error);
            break;
        case 'setLoadingState':
            console.log('setLoadingState called:', message.loading);
            const input = document.getElementById('messageInput');
            const sendBtn = document.getElementById('sendBtn');
            if (message.loading) {
                console.log('Setting loading state - disabling input');
                input.disabled = true;
                sendBtn.disabled = true;
                input.placeholder = 'Loading...';
            } else {
                console.log('Clearing loading state - enabling input');
                input.disabled = false;
                sendBtn.disabled = false;
                input.placeholder = 'Type your message...';
            }
            break;
    }
});

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    // Ensure thinking indicator is hidden initially
    const thinkingIndicator = document.getElementById('thinkingIndicator');
    if (thinkingIndicator) {
        thinkingIndicator.style.display = 'none';
    }

    // Request initial state
    vscode.postMessage({ command: 'requestModels' });
});

// Fallback in case DOMContentLoaded has already fired
if (document.readyState === 'loading') {
    // Document is still loading, wait for DOMContentLoaded
} else {
    // Document is already loaded
    const thinkingIndicator = document.getElementById('thinkingIndicator');
    if (thinkingIndicator) {
        thinkingIndicator.style.display = 'none';
    }
    vscode.postMessage({ command: 'requestModels' });
}
