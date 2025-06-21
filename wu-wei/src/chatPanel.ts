import * as vscode from 'vscode';

interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
}

/**
 * Wu Wei Chat Panel
 * A simple chat interface that follows wu wei principles - natural, flowing interaction
 */
export class WuWeiChatPanel {
    public static currentPanel: WuWeiChatPanel | undefined;
    public static readonly viewType = 'wuWeiChat';

    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];
    private _chatHistory: ChatMessage[] = [];

    public static createOrShow(extensionUri: vscode.Uri) {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        // If we already have a panel, show it
        if (WuWeiChatPanel.currentPanel) {
            WuWeiChatPanel.currentPanel._panel.reveal(column);
            return;
        }

        // Otherwise, create a new panel
        const panel = vscode.window.createWebviewPanel(
            WuWeiChatPanel.viewType,
            'Wu Wei Chat',
            column || vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
            }
        );

        WuWeiChatPanel.currentPanel = new WuWeiChatPanel(panel, extensionUri);
    }

    public static revive(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        WuWeiChatPanel.currentPanel = new WuWeiChatPanel(panel, extensionUri);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._extensionUri = extensionUri;

        // Set the webview's initial html content
        this._update();

        // Listen for when the panel is disposed
        // This happens when the user closes the panel or when the panel is closed programmatically
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        // Handle messages from the webview
        this._panel.webview.onDidReceiveMessage(
            message => {
                switch (message.command) {
                    case 'sendMessage':
                        this._handleUserMessage(message.text);
                        return;
                    case 'clearChat':
                        this._clearChat();
                        return;
                }
            },
            null,
            this._disposables
        );
    }

    public dispose() {
        WuWeiChatPanel.currentPanel = undefined;

        // Clean up our resources
        this._panel.dispose();

        while (this._disposables.length) {
            const disposable = this._disposables.pop();
            if (disposable) {
                disposable.dispose();
            }
        }
    }

    private async _handleUserMessage(message: string) {
        // Add user message to history
        this._chatHistory.push({
            role: 'user',
            content: message,
            timestamp: new Date()
        });

        // Show thinking indicator
        this._panel.webview.postMessage({
            command: 'showThinking'
        });

        try {
            const response = await this._generateAIResponse(message);

            // Add AI response to history
            this._chatHistory.push({
                role: 'assistant',
                content: response,
                timestamp: new Date()
            });

            this._panel.webview.postMessage({
                command: 'addMessage',
                message: response,
                isUser: false
            });
        } catch (error) {
            console.error('Wu Wei: Error generating AI response:', error);
            const fallbackResponse = this._generateWuWeiResponse(message);

            this._chatHistory.push({
                role: 'assistant',
                content: fallbackResponse,
                timestamp: new Date()
            });

            this._panel.webview.postMessage({
                command: 'addMessage',
                message: fallbackResponse,
                isUser: false
            });
        } finally {
            this._panel.webview.postMessage({
                command: 'hideThinking'
            });
        }
    }

    private async _generateAIResponse(userMessage: string): Promise<string> {
        try {
            // Get configuration
            const config = vscode.workspace.getConfiguration('wu-wei');
            const preferredModel = config.get<string>('preferredModel', 'gpt-4o');
            const systemPrompt = config.get<string>('systemPrompt',
                'You are Wu Wei, an AI assistant that embodies the philosophy of 无为而治 (wu wei) - effortless action that flows naturally like water. You provide thoughtful, gentle guidance while maintaining harmony and balance. Your responses are wise, concise, and flow naturally without forcing solutions.'
            );

            // Access language models
            const models = await vscode.lm.selectChatModels({
                vendor: 'copilot',
                family: preferredModel
            });

            if (models.length === 0) {
                throw new Error('No language models available');
            }

            // Prepare messages for the chat
            const messages: vscode.LanguageModelChatMessage[] = [
                vscode.LanguageModelChatMessage.User(systemPrompt),
                ...this._chatHistory.slice(-10).map(msg => // Keep last 10 messages for context
                    msg.role === 'user'
                        ? vscode.LanguageModelChatMessage.User(msg.content)
                        : vscode.LanguageModelChatMessage.Assistant(msg.content)
                )
            ];

            // Make the request
            const chatRequest = await models[0].sendRequest(messages, {}, new vscode.CancellationTokenSource().token);

            let response = '';
            for await (const fragment of chatRequest.text) {
                response += fragment;
            }

            return response.trim() || this._generateWuWeiResponse(userMessage);
        } catch (error) {
            console.error('Wu Wei: Language model request failed:', error);
            throw error;
        }
    }

    private _generateWuWeiResponse(userMessage: string): string {
        // Fallback responses following wu wei philosophy
        const responses = [
            "Like water, let the solution flow naturally... 🌊",
            "In effortless action, find the path forward. 🍃",
            "The way that can be spoken is not the eternal Way... Let me ponder this. 🤔",
            "Wu wei suggests: sometimes the best action is patient waiting. ⏳",
            "Nature doesn't hurry, yet everything is accomplished in its time. 🌱",
            "The wise find solutions by not forcing them. Let's explore this together. 💫"
        ];

        return responses[Math.floor(Math.random() * responses.length)];
    }

    private _clearChat() {
        this._chatHistory = [];
        this._panel.webview.postMessage({
            command: 'clearMessages'
        });
    }

    private _update() {
        const webview = this._panel.webview;
        this._panel.webview.html = this._getHtmlForWebview(webview);
    }

    private _getHtmlForWebview(webview: vscode.Webview) {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wu Wei Chat</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            height: 100vh;
            display: flex;
            flex-direction: column;
            background: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
        }
        
        .header {
            padding: 16px;
            border-bottom: 1px solid var(--vscode-panel-border);
            background: var(--vscode-sideBar-background);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 18px;
            font-weight: 600;
            color: var(--vscode-foreground);
        }
        
        .clear-btn {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }
        
        .clear-btn:hover {
            background: var(--vscode-button-hoverBackground);
        }
        
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .message {
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 12px;
            line-height: 1.4;
            word-wrap: break-word;
        }
        
        .message.user {
            align-self: flex-end;
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
        }
        
        .message.assistant {
            align-self: flex-start;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
        }
        
        .input-container {
            padding: 16px;
            border-top: 1px solid var(--vscode-panel-border);
            background: var(--vscode-sideBar-background);
            display: flex;
            gap: 8px;
        }
        
        .message-input {
            flex: 1;
            padding: 12px;
            border: 1px solid var(--vscode-input-border);
            border-radius: 6px;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            font-size: 14px;
            resize: none;
            min-height: 40px;
            max-height: 120px;
        }
        
        .message-input:focus {
            outline: none;
            border-color: var(--vscode-focusBorder);
        }
        
        .send-btn {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 12px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
        }
        
        .send-btn:hover:not(:disabled) {
            background: var(--vscode-button-hoverBackground);
        }
        
        .send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .empty-state {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            color: var(--vscode-descriptionForeground);
            gap: 8px;
        }
        
        .empty-state-icon {
            font-size: 48px;
            opacity: 0.6;
        }
        
        .empty-state-text {
            font-size: 16px;
            font-weight: 500;
        }
        
        .empty-state-subtitle {
            font-size: 14px;
            opacity: 0.8;
        }
        
        .thinking-indicator {
            align-self: flex-start;
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 12px;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            display: none;
            align-items: center;
            gap: 8px;
        }
        
        .thinking-dots {
            display: flex;
            gap: 4px;
        }
        
        .thinking-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--vscode-input-foreground);
            opacity: 0.4;
            animation: thinking 1.4s ease-in-out infinite both;
        }
        
        .thinking-dot:nth-child(1) { animation-delay: -0.32s; }
        .thinking-dot:nth-child(2) { animation-delay: -0.16s; }
        .thinking-dot:nth-child(3) { animation-delay: 0s; }
        
        @keyframes thinking {
            0%, 80%, 100% {
                opacity: 0.4;
                transform: scale(1);
            }
            40% {
                opacity: 1;
                transform: scale(1.2);
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Wu Wei Chat</h1>
        <button class="clear-btn" id="clearBtn">Clear Chat</button>
    </div>
    
    <div class="chat-container" id="chatContainer">
        <div class="empty-state" id="emptyState">
            <div class="empty-state-icon">🌊</div>
            <div class="empty-state-text">Welcome to Wu Wei Chat</div>
            <div class="empty-state-subtitle">Effortless conversation flows like water</div>
        </div>
        <div class="thinking-indicator" id="thinkingIndicator">
            <span>Wu Wei is contemplating...</span>
            <div class="thinking-dots">
                <div class="thinking-dot"></div>
                <div class="thinking-dot"></div>
                <div class="thinking-dot"></div>
            </div>
        </div>
    </div>
    
    <div class="input-container">
        <textarea 
            class="message-input" 
            id="messageInput" 
            placeholder="Enter your message... (Shift+Enter for new line)"
            rows="1"
        ></textarea>
        <button class="send-btn" id="sendBtn">Send</button>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        const chatContainer = document.getElementById('chatContainer');
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const clearBtn = document.getElementById('clearBtn');
        const emptyState = document.getElementById('emptyState');
        const thinkingIndicator = document.getElementById('thinkingIndicator');
        
        let messages = [];
        let isThinking = false;

        // Auto-resize textarea
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });

        // Send message on button click
        sendBtn.addEventListener('click', sendMessage);
        
        // Send message on Enter (but not Shift+Enter)
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Clear chat
        clearBtn.addEventListener('click', function() {
            vscode.postMessage({
                command: 'clearChat'
            });
        });

        function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;

            // Add user message
            addMessage(message, true);
            
            // Clear input
            messageInput.value = '';
            messageInput.style.height = 'auto';
            
            // Send to extension
            vscode.postMessage({
                command: 'sendMessage',
                text: message
            });
        }

        function addMessage(text, isUser) {
            messages.push({ text, isUser });
            
            // Hide empty state if this is the first message
            if (messages.length === 1) {
                emptyState.style.display = 'none';
            }
            
            const messageDiv = document.createElement('div');
            messageDiv.className = \`message \${isUser ? 'user' : 'assistant'}\`;
            messageDiv.textContent = text;
            
            chatContainer.appendChild(messageDiv);
            
            // Scroll to bottom
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function clearMessages() {
            messages = [];
            chatContainer.innerHTML = '';
            chatContainer.appendChild(emptyState);
            chatContainer.appendChild(thinkingIndicator);
            emptyState.style.display = 'flex';
            thinkingIndicator.style.display = 'none';
            isThinking = false;
        }

        function showThinking() {
            if (messages.length === 0) {
                emptyState.style.display = 'none';
            }
            thinkingIndicator.style.display = 'flex';
            isThinking = true;
            
            // Disable send button while thinking
            sendBtn.disabled = true;
            messageInput.disabled = true;
            
            // Scroll to bottom
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function hideThinking() {
            thinkingIndicator.style.display = 'none';
            isThinking = false;
            
            // Re-enable send button
            sendBtn.disabled = false;
            messageInput.disabled = false;
            messageInput.focus();
        }

        // Listen for messages from the extension
        window.addEventListener('message', event => {
            const message = event.data;
            
            switch (message.command) {
                case 'addMessage':
                    addMessage(message.message, message.isUser);
                    break;
                case 'clearMessages':
                    clearMessages();
                    break;
                case 'showThinking':
                    showThinking();
                    break;
                case 'hideThinking':
                    hideThinking();
                    break;
            }
        });
        
        // Focus input on load
        messageInput.focus();
    </script>
</body>
</html>`;
    }
}
