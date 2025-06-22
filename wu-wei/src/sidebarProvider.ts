import * as vscode from 'vscode';
import { WuWeiChatPanel } from './chatPanel';
import { logger } from './logger';

interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
}

interface ChatSession {
    id: string;
    title: string;
    timestamp: Date;
    lastMessage?: string;
    chatHistory: ChatMessage[];
}

/**
 * Wu Wei Sidebar Provider
 * Provides a tree view in the sidebar for managing chat sessions
 */
export class WuWeiSidebarProvider implements vscode.TreeDataProvider<ChatSessionItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<ChatSessionItem | undefined | null | void> = new vscode.EventEmitter<ChatSessionItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<ChatSessionItem | undefined | null | void> = this._onDidChangeTreeData.event;

    private chatSessions: ChatSession[] = [];
    private context: vscode.ExtensionContext;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        logger.info('Initializing Wu Wei Sidebar Provider');
        this.loadChatSessions();
        logger.info(`Loaded ${this.chatSessions.length} chat sessions`);
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: ChatSessionItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: ChatSessionItem): Thenable<ChatSessionItem[]> {
        if (!element) {
            // Root level - show chat sessions
            if (this.chatSessions.length === 0) {
                return Promise.resolve([]);
            }

            return Promise.resolve(
                this.chatSessions.map(session => new ChatSessionItem(
                    session.title,
                    session.id,
                    session.lastMessage || 'No messages yet',
                    session.timestamp,
                    vscode.TreeItemCollapsibleState.None
                ))
            );
        }

        return Promise.resolve([]);
    }

    /**
     * Create a new chat session
     */
    createNewChat(): void {
        const sessionId = this.generateSessionId();
        const timestamp = new Date();
        const title = `Chat ${this.chatSessions.length + 1}`;

        logger.chat('Creating new chat session', sessionId, { title, sessionCount: this.chatSessions.length });

        const newSession: ChatSession = {
            id: sessionId,
            title,
            timestamp,
            lastMessage: undefined,
            chatHistory: []
        };

        this.chatSessions.unshift(newSession); // Add to beginning
        this.saveChatSessions();
        this.refresh();

        // Open the new chat with the specific session ID to switch to it
        WuWeiChatPanel.createOrShow(this.context.extensionUri, sessionId);

        logger.chat('New chat session created successfully', sessionId, { title });
        vscode.window.showInformationMessage(`Wu Wei: New chat session "${title}" created 🌊`);
    }

    /**
     * Delete a chat session
     */
    deleteChat(sessionId: string): void {
        logger.chat('Attempting to delete session', sessionId);
        logger.debug('Current sessions', this.chatSessions.map(s => ({ id: s.id, title: s.title })));

        const sessionIndex = this.chatSessions.findIndex(s => s.id === sessionId);
        logger.debug(`Found session at index: ${sessionIndex}`);

        if (sessionIndex >= 0) {
            const session = this.chatSessions[sessionIndex];
            logger.chat('Deleting session', sessionId, { title: session.title, messageCount: session.chatHistory.length });

            this.chatSessions.splice(sessionIndex, 1);
            this.saveChatSessions();
            this.refresh();

            vscode.window.showInformationMessage(`Wu Wei: Chat session "${session.title}" deleted`);
            logger.chat('Session deleted successfully', sessionId, { title: session.title });
        } else {
            logger.error(`Could not find session with ID: ${sessionId}`);
            vscode.window.showErrorMessage(`Wu Wei: Could not find session to delete`);
        }
    }

    /**
     * Rename a chat session
     */
    async renameChat(sessionId: string): Promise<void> {
        const session = this.chatSessions.find(s => s.id === sessionId);
        if (!session) {
            logger.warn('Rename chat: session not found', { sessionId });
            return;
        }

        logger.chat('Starting chat rename', sessionId, { currentTitle: session.title });

        const newTitle = await vscode.window.showInputBox({
            prompt: 'Enter new chat title',
            value: session.title,
            validateInput: (value) => {
                if (!value || value.trim().length === 0) {
                    return 'Title cannot be empty';
                }
                if (value.length > 50) {
                    return 'Title must be 50 characters or less';
                }
                return null;
            }
        });

        if (newTitle && newTitle.trim() !== session.title) {
            const oldTitle = session.title;
            session.title = newTitle.trim();
            this.saveChatSessions();
            this.refresh();

            logger.chat('Chat renamed successfully', sessionId, {
                oldTitle,
                newTitle: session.title
            });
            vscode.window.showInformationMessage(`Wu Wei: Chat renamed to "${session.title}"`);
        } else {
            logger.chat('Chat rename cancelled or unchanged', sessionId);
        }
    }

    /**
     * Open a chat session
     */
    openChat(sessionId: string): void {
        try {
            // Validate sessionId
            if (!sessionId || typeof sessionId !== 'string') {
                logger.error('Invalid sessionId provided to openChat', { sessionId });
                vscode.window.showErrorMessage('Wu Wei: Invalid chat session ID');
                return;
            }

            const session = this.chatSessions.find(s => s.id === sessionId);
            if (session) {
                logger.chat('Opening chat session', sessionId, { title: session.title });
                WuWeiChatPanel.createOrShow(this.context.extensionUri, sessionId);
            } else {
                logger.warn('Open chat: session not found', { sessionId });
                vscode.window.showErrorMessage('Wu Wei: Chat session not found');
            }
        } catch (error) {
            logger.error('Error opening chat session', error);
            vscode.window.showErrorMessage('Wu Wei: Error opening chat session');
        }
    }

    /**
     * Get chat session by ID
     */
    getChatSession(sessionId: string): ChatSession | undefined {
        return this.chatSessions.find(s => s.id === sessionId);
    }

    /**
     * Add message to chat session
     */
    addMessageToSession(sessionId: string, message: ChatMessage): void {
        const session = this.chatSessions.find(s => s.id === sessionId);
        if (session) {
            session.chatHistory.push(message);
            session.lastMessage = message.content.length > 50 ? message.content.substring(0, 47) + '...' : message.content;
            session.timestamp = new Date();
            this.saveChatSessions();
            this.refresh();
            logger.chat('Message added to session', sessionId, {
                role: message.role,
                messageLength: message.content.length,
                totalMessages: session.chatHistory.length
            });
        } else {
            logger.warn('Add message: session not found', { sessionId });
        }
    }

    /**
     * Update entire chat history for a session (bulk operation)
     * This method avoids the recursive save issue during session switching
     */
    updateSessionChatHistory(sessionId: string, chatHistory: ChatMessage[]): void {
        const session = this.chatSessions.find(s => s.id === sessionId);
        if (session) {
            session.chatHistory = [...chatHistory]; // Create a copy to avoid reference issues

            // Update last message from the most recent message
            const lastMessage = chatHistory.length > 0 ? chatHistory[chatHistory.length - 1] : null;
            session.lastMessage = lastMessage
                ? (lastMessage.content.length > 50 ? lastMessage.content.substring(0, 47) + '...' : lastMessage.content)
                : undefined;

            session.timestamp = new Date();
            this.saveChatSessions();
            this.refresh();

            logger.chat('Chat history updated for session', sessionId, {
                messageCount: chatHistory.length,
                lastMessageRole: lastMessage?.role
            });
        } else {
            logger.warn('Update chat history: session not found', { sessionId });
        }
    }

    /**
     * Get chat history for a session
     */
    getChatHistory(sessionId: string): ChatMessage[] {
        const session = this.chatSessions.find(s => s.id === sessionId);
        const history = session ? session.chatHistory : [];
        logger.debug('Retrieved chat history', { sessionId, messageCount: history.length });
        return history;
    }

    /**
     * Clear chat history for a session
     */
    clearChatHistory(sessionId: string): void {
        const session = this.chatSessions.find(s => s.id === sessionId);
        if (session) {
            const previousMessageCount = session.chatHistory.length;
            session.chatHistory = [];
            session.lastMessage = undefined;
            session.timestamp = new Date();
            this.saveChatSessions();
            this.refresh();
            logger.chat('Chat history cleared', sessionId, {
                previousMessageCount,
                title: session.title
            });
        } else {
            logger.warn('Clear history: session not found', { sessionId });
        }
    }

    private generateSessionId(): string {
        return `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    private loadChatSessions(): void {
        try {
            const saved = this.context.globalState.get<ChatSession[]>('wuWeiChatSessions', []);
            this.chatSessions = saved.map(session => ({
                ...session,
                timestamp: new Date(session.timestamp),
                chatHistory: session.chatHistory || [] // Ensure chatHistory exists
            }));
            logger.debug('Chat sessions loaded successfully', { count: this.chatSessions.length });
        } catch (error) {
            logger.error('Error loading chat sessions', error);
            this.chatSessions = [];
        }
    }

    private saveChatSessions(): void {
        try {
            this.context.globalState.update('wuWeiChatSessions', this.chatSessions);
            logger.debug('Chat sessions saved successfully', { count: this.chatSessions.length });
        } catch (error) {
            logger.error('Error saving chat sessions', error);
        }
    }

    /**
     * Update the last message for a session
     */
    updateSessionLastMessage(sessionId: string, message: string): void {
        const session = this.chatSessions.find(s => s.id === sessionId);
        if (session) {
            session.lastMessage = message.length > 50 ? message.substring(0, 47) + '...' : message;
            session.timestamp = new Date();
            this.saveChatSessions();
            this.refresh();
        }
    }

    /**
     * Get current session count
     */
    getSessionCount(): number {
        return this.chatSessions.length;
    }
}

/**
 * Tree item for chat sessions
 */
export class ChatSessionItem extends vscode.TreeItem {
    constructor(
        public readonly title: string,
        public readonly sessionId: string,
        public readonly lastMessage: string,
        public readonly timestamp: Date,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState
    ) {
        super(title, collapsibleState);

        this.tooltip = this.getTooltip();
        this.description = this.getDescription();
        this.contextValue = 'chatSession';

        // Store sessionId as a property that can be accessed by context menu commands
        this.id = this.sessionId;

        // Set icon
        this.iconPath = new vscode.ThemeIcon('comment-discussion');

        // Command to open chat when clicked
        this.command = {
            command: 'wu-wei.openChatSession',
            title: 'Open Chat',
            arguments: [this.sessionId]
        };

        console.log(`Wu Wei: Created ChatSessionItem with ID: ${this.sessionId}, title: ${this.title}`);
    }

    private getTooltip(): string {
        const timeAgo = this.getTimeAgo();
        return `${this.title}\nLast activity: ${timeAgo}\nLast message: ${this.lastMessage}`;
    }

    private getDescription(): string {
        return this.getTimeAgo();
    }

    private getTimeAgo(): string {
        const now = new Date();
        const diff = now.getTime() - this.timestamp.getTime();
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (days > 0) {
            return `${days}d ago`;
        } else if (hours > 0) {
            return `${hours}h ago`;
        } else if (minutes > 0) {
            return `${minutes}m ago`;
        } else {
            return 'Just now';
        }
    }
}

/**
 * Actions view provider - fixed panel with action buttons
 */
export class WuWeiActionsViewProvider implements vscode.WebviewViewProvider {
    constructor(private context: vscode.ExtensionContext) { }

    resolveWebviewView(webviewView: vscode.WebviewView): void {
        webviewView.webview.options = {
            enableScripts: true
        };

        webviewView.webview.html = this.getActionsHtml();

        webviewView.webview.onDidReceiveMessage(message => {
            switch (message.command) {
                case 'newChat':
                    vscode.commands.executeCommand('wu-wei.newChat');
                    break;
                case 'openChat':
                    vscode.commands.executeCommand('wu-wei.openChat');
                    break;
                case 'refreshChats':
                    vscode.commands.executeCommand('wu-wei.refreshChats');
                    break;
                case 'showLogs':
                    vscode.commands.executeCommand('wu-wei.showLogs');
                    break;
                case 'clearLogs':
                    vscode.commands.executeCommand('wu-wei.clearLogs');
                    break;
            }
        });
    }

    private getActionsHtml(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wu Wei Actions</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 12px;
            background: var(--vscode-sideBar-background);
            color: var(--vscode-sideBar-foreground);
        }
        
        .actions-container {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .action-btn {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 10px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
            width: 100%;
            text-align: left;
            transition: background-color 0.1s ease;
        }
        
        .action-btn:hover {
            background: var(--vscode-button-hoverBackground);
        }
        
        .action-btn:active {
            background: var(--vscode-button-secondaryBackground);
        }
        
        .action-btn .icon {
            width: 16px;
            height: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }
        
        .primary-btn {
            background: var(--vscode-button-background);
            border: 1px solid var(--vscode-button-border, transparent);
        }
        
        .secondary-btn {
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
        }
        
        .secondary-btn:hover {
            background: var(--vscode-button-secondaryHoverBackground);
        }
        
        .divider {
            height: 1px;
            background: var(--vscode-panel-border);
            margin: 4px 0;
        }
        
        .philosophy {
            margin-top: 12px;
            padding: 8px;
            background: var(--vscode-textBlockQuote-background);
            border-left: 3px solid var(--vscode-textBlockQuote-border);
            border-radius: 3px;
            font-style: italic;
            color: var(--vscode-descriptionForeground);
            font-size: 11px;
            line-height: 1.3;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="actions-container">
        <button class="action-btn primary-btn" onclick="newChat()">
            <span class="icon">➕</span>
            <span>New Chat</span>
        </button>
        
        <button class="action-btn secondary-btn" onclick="openChat()">
            <span class="icon">💬</span>
            <span>Open Chat Panel</span>
        </button>
        
        <div class="divider"></div>
        
        <button class="action-btn secondary-btn" onclick="refreshChats()">
            <span class="icon">🔄</span>
            <span>Refresh Sessions</span>
        </button>
        
        <div class="divider"></div>
        
        <button class="action-btn secondary-btn" onclick="showLogs()">
            <span class="icon">📄</span>
            <span>Show Output Logs</span>
        </button>
        
        <button class="action-btn secondary-btn" onclick="clearLogs()">
            <span class="icon">🗑️</span>
            <span>Clear Logs</span>
        </button>
        
        <div class="philosophy">
            "Wu wei - effortless action"<br>
            无为而治
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        
        function newChat() {
            vscode.postMessage({ command: 'newChat' });
        }
        
        function openChat() {
            vscode.postMessage({ command: 'openChat' });
        }
        
        function refreshChats() {
            vscode.postMessage({ command: 'refreshChats' });
        }
        
        function showLogs() {
            vscode.postMessage({ command: 'showLogs' });
        }
        
        function clearLogs() {
            vscode.postMessage({ command: 'clearLogs' });
        }
    </script>
</body>
</html>`;
    }
}

// Keep the old welcome provider for backward compatibility
export class WuWeiWelcomeViewProvider extends WuWeiActionsViewProvider {
    // Inherit from actions provider
}
