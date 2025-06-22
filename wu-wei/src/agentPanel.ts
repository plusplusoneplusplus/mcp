import * as vscode from 'vscode';
import { logger } from './logger';
import {
    AbstractAgent,
    AgentRequest,
    AgentResponse,
    AgentRegistry,
    WuWeiExampleAgent,
    GitHubCopilotAgent,
    AgentMessage
} from './agentInterface';

/**
 * Wu Wei Agent Panel Provider
 * Provides a panel for triggering agents with messages
 */
export class WuWeiAgentPanelProvider implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;
    private _agentRegistry: AgentRegistry;
    private _messageHistory: AgentMessage[] = [];

    constructor(private context: vscode.ExtensionContext) {
        logger.debug('Wu Wei Agent Panel Provider initialized');

        // Initialize agent registry
        this._agentRegistry = new AgentRegistry();

        // Register example agent
        const exampleAgent = new WuWeiExampleAgent();
        this._agentRegistry.registerAgent(exampleAgent);

        // Register GitHub Copilot agent
        const copilotAgent = new GitHubCopilotAgent();
        this._agentRegistry.registerAgent(copilotAgent);

        // Activate the example agent
        exampleAgent.activate().then(() => {
            logger.info('Example agent activated');
        }).catch(error => {
            logger.error('Failed to activate example agent', error);
        });

        // Activate the GitHub Copilot agent
        copilotAgent.activate().then(() => {
            logger.info('GitHub Copilot agent activated');
        }).catch(error => {
            logger.error('Failed to activate GitHub Copilot agent', error);
        });
    }

    resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        token: vscode.CancellationToken
    ): void {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.context.extensionUri]
        };

        webviewView.webview.html = this.getAgentHtml();

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async message => {
            logger.debug('Received message from agent panel webview:', message);

            switch (message.command) {
                case 'sendAgentRequest':
                    await this.handleAgentRequest(message.agentName, message.method, message.params);
                    break;
                case 'clearHistory':
                    this.clearMessageHistory();
                    break;
                case 'getAgentCapabilities':
                    this.sendAgentCapabilities();
                    break;
                default:
                    logger.warn('Unknown command received from agent panel:', message.command);
            }
        });

        // Send initial data
        this.sendAgentCapabilities();
        this.sendMessageHistory();
    }

    private async handleAgentRequest(agentName: string, method: string, params: any): Promise<void> {
        try {
            logger.info(`Processing agent request: ${agentName}.${method}`, params);

            const agent = this._agentRegistry.getAgent(agentName);

            if (!agent) {
                const errorMessage = `Agent '${agentName}' not found`;
                logger.error(errorMessage);
                this.addMessageToHistory({
                    id: this.generateMessageId(),
                    timestamp: new Date(),
                    type: 'error',
                    error: {
                        code: -32000,
                        message: errorMessage
                    }
                });
                return;
            }

            // Create request
            const request: AgentRequest = {
                id: this.generateMessageId(),
                method,
                params,
                timestamp: new Date()
            };

            // Add request to history
            this.addMessageToHistory({
                id: request.id,
                timestamp: request.timestamp,
                type: 'request',
                method: request.method,
                params: request.params
            });

            // Process request
            const response = await agent.processRequest(request);

            // Add response to history
            this.addMessageToHistory({
                id: response.id,
                timestamp: response.timestamp,
                type: 'response',
                result: response.result,
                error: response.error
            });

            logger.info(`Agent request completed: ${agentName}.${method}`, response);

        } catch (error) {
            logger.error('Error handling agent request', error);

            this.addMessageToHistory({
                id: this.generateMessageId(),
                timestamp: new Date(),
                type: 'error',
                error: {
                    code: -32603,
                    message: 'Internal error processing request',
                    data: error instanceof Error ? error.message : String(error)
                }
            });
        }
    }

    private addMessageToHistory(message: AgentMessage): void {
        this._messageHistory.push(message);

        // Keep only last 100 messages
        if (this._messageHistory.length > 100) {
            this._messageHistory = this._messageHistory.slice(-100);
        }

        this.sendMessageHistory();
    }

    private sendAgentCapabilities(): void {
        if (!this._view) return;

        const capabilities = this._agentRegistry.getAgentCapabilities();
        this._view.webview.postMessage({
            command: 'updateAgentCapabilities',
            capabilities
        });
    }

    private sendMessageHistory(): void {
        if (!this._view) return;

        this._view.webview.postMessage({
            command: 'updateMessageHistory',
            messages: this._messageHistory
        });
    }

    private clearMessageHistory(): void {
        logger.info('Clearing agent message history');
        this._messageHistory = [];
        this.sendMessageHistory();
        vscode.window.showInformationMessage('Wu Wei: Message history cleared');
    }

    private generateMessageId(): string {
        return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    private getAgentHtml(): string {
        return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wu Wei Agent Panel</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            font-weight: var(--vscode-font-weight);
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }

        .header {
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--vscode-panel-border);
        }

        .header h2 {
            margin: 0 0 5px 0;
            color: var(--vscode-foreground);
        }

        .header p {
            margin: 0;
            color: var(--vscode-descriptionForeground);
            font-size: 0.9em;
        }

        .agent-form {
            margin-bottom: 20px;
            padding: 15px;
            background-color: var(--vscode-editor-inactiveSelectionBackground);
            border-radius: 6px;
            border: 1px solid var(--vscode-panel-border);
        }

        .form-group {
            margin-bottom: 15px;
        }

        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: var(--vscode-foreground);
        }

        .form-group select,
        .form-group input,
        .form-group textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid var(--vscode-input-border);
            border-radius: 4px;
            background-color: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            font-family: inherit;
            font-size: inherit;
            box-sizing: border-box;
        }

        .form-group textarea {
            min-height: 80px;
            resize: vertical;
            font-family: var(--vscode-editor-font-family);
        }

        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }

        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 500;
            transition: background-color 0.2s ease;
        }

        .btn-primary {
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
        }

        .btn-primary:hover {
            background-color: var(--vscode-button-hoverBackground);
        }

        .btn-secondary {
            background-color: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
        }

        .btn-secondary:hover {
            background-color: var(--vscode-button-secondaryHoverBackground);
        }

        .message-history {
            margin-top: 20px;
        }

        .message-history h3 {
            margin: 0 0 15px 0;
            color: var(--vscode-foreground);
        }

        .message-list {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid var(--vscode-panel-border);
            border-radius: 6px;
            background-color: var(--vscode-editor-background);
        }

        .message-item {
            padding: 12px;
            border-bottom: 1px solid var(--vscode-panel-border);
            font-family: var(--vscode-editor-font-family);
            font-size: 0.85em;
        }

        .message-item:last-child {
            border-bottom: none;
        }

        .message-item.request {
            background-color: var(--vscode-textCodeBlock-background);
        }

        .message-item.response {
            background-color: var(--vscode-editor-inactiveSelectionBackground);
        }

        .message-item.error {
            background-color: var(--vscode-inputValidation-errorBackground);
            border-left: 3px solid var(--vscode-inputValidation-errorBorder);
        }

        .message-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            font-weight: 600;
        }

        .message-type {
            text-transform: uppercase;
            font-size: 0.75em;
            padding: 2px 6px;
            border-radius: 3px;
        }

        .message-type.request {
            background-color: var(--vscode-charts-blue);
            color: white;
        }

        .message-type.response {
            background-color: var(--vscode-charts-green);
            color: white;
        }

        .message-type.error {
            background-color: var(--vscode-charts-red);
            color: white;
        }

        .message-timestamp {
            color: var(--vscode-descriptionForeground);
            font-size: 0.8em;
            font-weight: normal;
        }

        .message-content {
            color: var(--vscode-foreground);
            white-space: pre-wrap;
            word-break: break-word;
        }

        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--vscode-descriptionForeground);
        }

        .empty-state p {
            margin: 0;
            font-style: italic;
        }

        .capability-info {
            margin-bottom: 10px;
            padding: 8px;
            background-color: var(--vscode-textCodeBlock-background);
            border-radius: 4px;
            font-size: 0.85em;
            color: var(--vscode-descriptionForeground);
        }
    </style>
</head>
<body>
    <div class="header">
        <h2>🤖 Wu Wei Agent Panel</h2>
        <p>Trigger agents with messages using MCP/A2A interface patterns</p>
    </div>

    <div class="agent-form">
        <div class="form-group">
            <label for="agentSelect">Select Agent:</label>
            <select id="agentSelect">
                <option value="">Loading agents...</option>
            </select>
            <div id="capabilityInfo" class="capability-info" style="display: none;"></div>
        </div>

        <div class="form-group">
            <label for="methodSelect">Method:</label>
            <select id="methodSelect">
                <option value="">Select an agent first</option>
            </select>
        </div>

        <div class="form-group">
            <label for="paramsInput">Parameters:</label>
            <textarea id="paramsInput" placeholder='Hello, agent! How can you help me?'></textarea>
            <small style="color: var(--vscode-descriptionForeground); font-size: 0.8em; margin-top: 4px; display: block;">
                Enter your message or question as plain text. For advanced usage, you can use JSON format. Press Ctrl+Enter to send.
            </small>
        </div>

        <div class="button-group">
            <button class="btn btn-primary" id="sendRequestBtn">Send Request</button>
            <button class="btn btn-secondary" id="clearHistoryBtn">Clear History</button>
        </div>
    </div>

    <div class="message-history">
        <h3>Message History</h3>
        <div class="message-list" id="messageList">
            <div class="empty-state">
                <p>No messages yet. Send your first agent request!</p>
            </div>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        let agentCapabilities = [];
        let messageHistory = [];

        // DOM elements
        const agentSelect = document.getElementById('agentSelect');
        const methodSelect = document.getElementById('methodSelect');
        const paramsInput = document.getElementById('paramsInput');
        const capabilityInfo = document.getElementById('capabilityInfo');
        const messageList = document.getElementById('messageList');
        const sendRequestBtn = document.getElementById('sendRequestBtn');
        const clearHistoryBtn = document.getElementById('clearHistoryBtn');

        // Event listeners
        agentSelect.addEventListener('change', updateMethodSelect);
        methodSelect.addEventListener('change', updatePlaceholder);
        paramsInput.addEventListener('keydown', handleKeyDown);
        sendRequestBtn.addEventListener('click', sendAgentRequest);
        clearHistoryBtn.addEventListener('click', () => vscode.postMessage({ command: 'clearHistory' }));

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
                option.textContent = \`\${capability.name} (v\${capability.version})\`;
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
            capabilityInfo.style.display = 'none';

            if (!selectedAgent) {
                methodSelect.innerHTML = '<option value="">Select an agent first</option>';
                paramsInput.placeholder = 'Select an agent and method first';
                return;
            }

            const capability = agentCapabilities.find(c => c.name === selectedAgent);
            if (!capability) {
                methodSelect.innerHTML = '<option value="">Agent not found</option>';
                return;
            }

            // Show capability info
            capabilityInfo.innerHTML = \`
                <strong>\${capability.name}</strong> - \${capability.description || 'No description'}
                <br>Methods: \${capability.methods.join(', ')}
            \`;
            capabilityInfo.style.display = 'block';

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
        }

        function updateMessageHistory() {
            if (messageHistory.length === 0) {
                messageList.innerHTML = '<div class="empty-state"><p>No messages yet. Send your first agent request!</p></div>';
                return;
            }

            messageList.innerHTML = messageHistory.map(message => {
                const timestamp = new Date(message.timestamp).toLocaleString();
                
                let content = '';
                let typeClass = message.type;
                
                if (message.type === 'request') {
                    content = \`Method: \${message.method}\\nParams: \${JSON.stringify(message.params, null, 2)}\`;
                } else if (message.type === 'response') {
                    if (message.error) {
                        content = \`Error: \${message.error.message}\\nCode: \${message.error.code}\`;
                        if (message.error.data) {
                            content += \`\\nData: \${JSON.stringify(message.error.data, null, 2)}\`;
                        }
                        typeClass = 'error';
                    } else {
                        content = \`Result: \${JSON.stringify(message.result, null, 2)}\`;
                    }
                } else if (message.type === 'error') {
                    content = \`Error: \${message.error?.message || 'Unknown error'}\\nCode: \${message.error?.code || 'N/A'}\`;
                }

                return \`
                    <div class="message-item \${typeClass}">
                        <div class="message-header">
                            <span class="message-type \${typeClass}">\${message.type}</span>
                            <span class="message-timestamp">\${timestamp}</span>
                        </div>
                        <div class="message-content">\${content}</div>
                    </div>
                \`;
            }).join('');
        }

        // Request initial data
        vscode.postMessage({ command: 'getAgentCapabilities' });
    </script>
</body>
</html>
        `;
    }
}
