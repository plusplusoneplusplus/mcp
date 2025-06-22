import * as vscode from 'vscode';
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
    selectedModel?: string;
}

/**
 * Unified Wu Wei Chat Provider
 * Combines session management and chat interface in a single webview
 */
export class UnifiedWuWeiChatProvider implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;
    private chatSessions: ChatSession[] = [];
    private currentSessionId?: string;
    private availableModels: vscode.LanguageModelChat[] = [];
    private isLoadingModels: boolean = false;
    private modelsLoaded: boolean = false;
    private modelChangeListener: vscode.Disposable | undefined;
    private debounceTimer: NodeJS.Timeout | undefined;

    constructor(private readonly context: vscode.ExtensionContext) {
        this.loadChatSessions();
        logger.info(`Unified Chat Provider: Loaded ${this.chatSessions.length} chat sessions`);

        // Listen for changes in available language models
        if (vscode.lm) {
            this.modelChangeListener = vscode.lm.onDidChangeChatModels(() => {
                logger.info('Language models changed event received.');

                // Debounce the reload request
                if (this.debounceTimer) {
                    clearTimeout(this.debounceTimer);
                }

                this.debounceTimer = setTimeout(() => {
                    logger.info('Debounced model reload triggered.');
                    if (this._view?.visible) {
                        this.loadAvailableModels();
                    }
                }, 500); // 500ms debounce interval
            });
        }
    }

    public dispose() {
        this.modelChangeListener?.dispose();
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.context.extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from webview
        webviewView.webview.onDidReceiveMessage(data => {
            switch (data.command) {
                case 'newChat':
                    this.createNewChat();
                    break;
                case 'selectSession':
                    this.selectSession(data.sessionId);
                    break;
                case 'deleteSession':
                    this.deleteSession(data.sessionId);
                    break;
                case 'renameSession':
                    this.renameSession(data.sessionId, data.newName);
                    break;
                case 'sendMessage':
                    this.handleUserMessage(data.text);
                    break;
                case 'selectModel':
                    this.handleModelSelection(data.modelFamily);
                    break;
                case 'requestModels':
                    this.loadAvailableModels();
                    break;
                case 'clearChat':
                    this.clearCurrentChat();
                    break;
                case 'runDiagnostics':
                    this.runDiagnostics();
                    break;
            }
        });

        // Load models immediately, and the event listener will catch any later changes.
        this.loadAvailableModels();

        // Update webview with current state
        this.updateWebview();
    }

    private createNewChat(): void {
        const sessionId = this.generateSessionId();
        const timestamp = new Date();
        const title = `Chat ${this.chatSessions.length + 1}`;

        const newSession: ChatSession = {
            id: sessionId,
            title,
            timestamp,
            lastMessage: undefined,
            chatHistory: []
        };

        this.chatSessions.unshift(newSession);
        this.saveChatSessions();

        // Switch to the new session
        this.currentSessionId = sessionId;
        this.updateWebview();

        logger.chat('New chat session created', sessionId, { title });
    }

    private selectSession(sessionId: string): void {
        if (this.currentSessionId !== sessionId) {
            this.currentSessionId = sessionId;
            this.updateWebview();
            logger.chat('Selected session', sessionId);
        }
    }

    private deleteSession(sessionId: string): void {
        const sessionIndex = this.chatSessions.findIndex(s => s.id === sessionId);
        if (sessionIndex >= 0) {
            const session = this.chatSessions[sessionIndex];
            this.chatSessions.splice(sessionIndex, 1);
            this.saveChatSessions();

            // If we deleted the current session, clear it
            if (this.currentSessionId === sessionId) {
                this.currentSessionId = undefined;
            }

            this.updateWebview();
            logger.chat('Session deleted', sessionId, { title: session.title });
        }
    }

    private async renameSession(sessionId: string, newName: string): Promise<void> {
        const session = this.chatSessions.find(s => s.id === sessionId);
        if (session && newName.trim()) {
            session.title = newName.trim();
            this.saveChatSessions();
            this.updateWebview();
            logger.chat('Session renamed', sessionId, { newTitle: session.title });
        }
    }

    private async handleUserMessage(message: string): Promise<void> {
        if (!this.currentSessionId) {
            // Create a new session if none exists
            this.createNewChat();
        }

        const session = this.chatSessions.find(s => s.id === this.currentSessionId);
        if (!session) return;

        // Add user message
        const userMessage: ChatMessage = {
            role: 'user',
            content: message,
            timestamp: new Date()
        };

        session.chatHistory.push(userMessage);
        session.lastMessage = message.substring(0, 50) + (message.length > 50 ? '...' : '');
        this.saveChatSessions();

        // Update UI
        this.updateWebview();
        this.postMessageToWebview({ command: 'showThinking' });

        try {
            const response = await this.generateAIResponse(message, session);

            const assistantMessage: ChatMessage = {
                role: 'assistant',
                content: response,
                timestamp: new Date()
            };

            session.chatHistory.push(assistantMessage);
            this.saveChatSessions();

            this.postMessageToWebview({
                command: 'addMessage',
                message: response,
                isUser: false
            });
        } catch (error) {
            const fallbackResponse = this.generateWuWeiResponse(message);

            const assistantMessage: ChatMessage = {
                role: 'assistant',
                content: fallbackResponse,
                timestamp: new Date()
            };

            session.chatHistory.push(assistantMessage);
            this.saveChatSessions();

            this.postMessageToWebview({
                command: 'addMessage',
                message: fallbackResponse,
                isUser: false
            });
        } finally {
            this.postMessageToWebview({ command: 'hideThinking' });
        }
    }

    private async generateAIResponse(userMessage: string, session: ChatSession): Promise<string> {
        try {
            // Get preferred model
            const config = vscode.workspace.getConfiguration('wu-wei');
            const preferredModel = session.selectedModel || config.get<string>('preferredModel', 'gpt-4o');

            // Access language models
            let models = await vscode.lm.selectChatModels({ family: preferredModel });
            if (models.length === 0) {
                models = await vscode.lm.selectChatModels();
            }

            if (models.length === 0) {
                throw new Error('No language models available');
            }

            // Prepare messages
            const systemPrompt = config.get<string>('systemPrompt',
                'You are Wu Wei, an AI assistant that embodies the philosophy of 无为而治 (wu wei) - effortless action that flows naturally like water. You provide thoughtful, gentle guidance while maintaining harmony and balance. Your responses are wise, concise, and flow naturally without forcing solutions.'
            );

            const messages: vscode.LanguageModelChatMessage[] = [
                vscode.LanguageModelChatMessage.User(systemPrompt),
                ...session.chatHistory.slice(-10).map(msg =>
                    msg.role === 'user'
                        ? vscode.LanguageModelChatMessage.User(msg.content)
                        : vscode.LanguageModelChatMessage.Assistant(msg.content)
                )
            ];

            const chatRequest = await models[0].sendRequest(messages, {}, new vscode.CancellationTokenSource().token);

            let response = '';
            for await (const fragment of chatRequest.text) {
                response += fragment;
            }

            return response.trim() || this.generateWuWeiResponse(userMessage);
        } catch (error) {
            logger.error('AI response generation failed', error);
            throw error;
        }
    }

    private generateWuWeiResponse(userMessage: string): string {
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

    private async handleModelSelection(modelFamily: string): Promise<void> {
        if (this.currentSessionId) {
            const session = this.chatSessions.find(s => s.id === this.currentSessionId);
            if (session) {
                session.selectedModel = modelFamily;
                this.saveChatSessions();
            }
        } else {
            const config = vscode.workspace.getConfiguration('wu-wei');
            await config.update('preferredModel', modelFamily, vscode.ConfigurationTarget.Global);
        }

        logger.info(`Model changed to ${modelFamily}`);
    }

    private async loadAvailableModels(): Promise<void> {
        if (this.isLoadingModels) return;

        this.isLoadingModels = true;
        this.postMessageToWebview({ command: 'setLoadingState', loading: true });

        try {
            logger.info('Starting to load language models...');

            // Check if the API is available
            if (!vscode.lm) {
                throw new Error('VS Code Language Model API is not available. Please ensure you have VS Code 1.90+ and the required extensions.');
            }

            logger.info('Language Model API is available, attempting to select models...');

            // Add timeout to the model selection
            const timeoutPromise = new Promise<never>((_, reject) => {
                setTimeout(() => reject(new Error('Model loading timed out after 10 seconds')), 10000);
            });

            const modelsPromise = vscode.lm.selectChatModels();

            this.availableModels = await Promise.race([modelsPromise, timeoutPromise]);
            this.modelsLoaded = true;

            logger.info(`Successfully loaded ${this.availableModels.length} language models`);

            const modelData = this.availableModels.map(model => ({
                family: model.family,
                vendor: model.vendor,
                name: model.name,
                maxInputTokens: model.maxInputTokens
            }));

            const config = vscode.workspace.getConfiguration('wu-wei');
            const currentModel = config.get<string>('preferredModel', 'gpt-4o');

            if (this.availableModels.length === 0) {
                logger.warn('No language models found. You may need to install GitHub Copilot or another language model extension.');
                this.postMessageToWebview({
                    command: 'updateModels',
                    models: [],
                    currentModel: currentModel,
                    loading: false,
                    error: {
                        message: 'No language models available.',
                        details: 'Please install and enable a compatible extension like GitHub Copilot, and ensure you are signed in. You may also need to restart VS Code after installing the extension.',
                        actionable: true
                    }
                });
            } else {
                this.postMessageToWebview({
                    command: 'updateModels',
                    models: modelData,
                    currentModel: currentModel,
                    loading: false
                });
            }

            logger.info(`Model loading completed successfully`);
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error loading models';
            logger.error('Failed to load models:', errorMessage);

            let userFriendlyMessage = 'Failed to load language models.';
            let details = errorMessage;

            // Provide specific guidance based on error type
            if (errorMessage.includes('timed out')) {
                userFriendlyMessage = 'Model loading timed out.';
                details = 'This may indicate a network issue or that language model extensions are not properly configured. Try restarting VS Code and ensuring you\'re signed in to your language model service.';
            } else if (errorMessage.includes('not available')) {
                userFriendlyMessage = 'Language Model API not available.';
                details = 'Please ensure you have VS Code 1.90+ installed. If you have the correct version, try restarting VS Code.';
            } else if (errorMessage.includes('ENOTFOUND') || errorMessage.includes('network')) {
                userFriendlyMessage = 'Network error while loading models.';
                details = 'Check your internet connection and try again. If using a corporate network, you may need to configure proxy settings.';
            }

            this.postMessageToWebview({
                command: 'updateModels',
                models: [],
                currentModel: 'gpt-4o',
                loading: false,
                error: {
                    message: userFriendlyMessage,
                    details: details,
                    actionable: true
                }
            });
        } finally {
            this.isLoadingModels = false;
        }
    }

    private clearCurrentChat(): void {
        if (this.currentSessionId) {
            const session = this.chatSessions.find(s => s.id === this.currentSessionId);
            if (session) {
                session.chatHistory = [];
                session.lastMessage = undefined;
                this.saveChatSessions();
                this.updateWebview();
            }
        }
    }

    private updateWebview(): void {
        if (this._view) {
            const currentSession = this.currentSessionId ?
                this.chatSessions.find(s => s.id === this.currentSessionId) : undefined;

            this.postMessageToWebview({
                command: 'updateState',
                sessions: this.chatSessions.map(s => ({
                    id: s.id,
                    title: s.title,
                    lastMessage: s.lastMessage,
                    timestamp: s.timestamp.toISOString(),
                    messageCount: s.chatHistory.length
                })),
                currentSessionId: this.currentSessionId,
                messages: currentSession?.chatHistory || []
            });
        }
    }

    private postMessageToWebview(message: any): void {
        if (this._view) {
            this._view.webview.postMessage(message);
        }
    }

    private generateSessionId(): string {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    private loadChatSessions(): void {
        try {
            const storedSessions = this.context.globalState.get<ChatSession[]>('wu-wei.chatSessions', []);
            this.chatSessions = storedSessions.map(session => ({
                ...session,
                timestamp: new Date(session.timestamp)
            }));
        } catch (error) {
            logger.error('Failed to load chat sessions', error);
            this.chatSessions = [];
        }
    }

    private saveChatSessions(): void {
        try {
            this.context.globalState.update('wu-wei.chatSessions', this.chatSessions);
        } catch (error) {
            logger.error('Failed to save chat sessions', error);
        }
    }

    /**
     * Public method to force reload models (for debugging)
     */
    public async forceReloadModels(): Promise<void> {
        this.isLoadingModels = false; // Reset the flag
        this.modelsLoaded = false;
        await this.loadAvailableModels();
    }

    /**
     * Get current model loading state (for debugging)
     */
    public getModelState() {
        return {
            isLoadingModels: this.isLoadingModels,
            modelsLoaded: this.modelsLoaded,
            availableModelsCount: this.availableModels.length,
            models: this.availableModels.map(m => ({ family: m.family, vendor: m.vendor }))
        };
    }

    /**
     * Comprehensive troubleshooting method to help users diagnose issues
     */
    public async runDiagnostics(): Promise<void> {
        logger.show();
        logger.info('='.repeat(80));
        logger.info('WU WEI COMPREHENSIVE DIAGNOSTICS');
        logger.info('='.repeat(80));

        try {
            // 1. Check VS Code version
            const vscodeVersion = vscode.version;
            logger.info(`VS Code Version: ${vscodeVersion}`);

            const versionParts = vscodeVersion.split('.');
            const majorVersion = parseInt(versionParts[0]);
            const minorVersion = parseInt(versionParts[1]);

            if (majorVersion < 1 || (majorVersion === 1 && minorVersion < 90)) {
                logger.error(`❌ VS Code version ${vscodeVersion} is too old. Language Model API requires 1.90+`);
            } else {
                logger.info(`✅ VS Code version ${vscodeVersion} supports Language Model API`);
            }

            // 2. Check Language Model API availability
            logger.info(`Language Model API Available: ${!!vscode.lm ? '✅ Yes' : '❌ No'}`);

            if (!vscode.lm) {
                logger.error('❌ Language Model API is not available');
                logger.info('Possible causes:');
                logger.info('  - VS Code version is too old (need 1.90+)');
                logger.info('  - Extension is not running in proper context');
                return;
            }

            // 3. Check installed extensions
            const extensions = vscode.extensions.all;
            const languageModelExtensions = extensions.filter(ext =>
                ext.id.toLowerCase().includes('copilot') ||
                ext.id.toLowerCase().includes('github.copilot') ||
                ext.id.toLowerCase().includes('claude') ||
                ext.id.toLowerCase().includes('openai') ||
                ext.packageJSON?.contributes?.languageModels
            );

            logger.info(`Total Extensions: ${extensions.length}`);
            logger.info(`Language Model Extensions Found: ${languageModelExtensions.length}`);

            if (languageModelExtensions.length === 0) {
                logger.error('❌ No language model extensions found');
                logger.info('Install one of these extensions:');
                logger.info('  - GitHub Copilot (github.copilot)');
                logger.info('  - GitHub Copilot Chat (github.copilot-chat)');
            } else {
                logger.info('✅ Language model extensions found:');
                languageModelExtensions.forEach(ext => {
                    const status = ext.isActive ? '✅ Active' : '⚠️  Inactive';
                    logger.info(`  - ${ext.id} (${ext.packageJSON?.displayName || 'Unknown'}) - ${status}`);
                });
            }

            // 4. Try to load models with detailed error reporting
            logger.info('Attempting to load language models...');
            const startTime = Date.now();

            try {
                const models = await Promise.race([
                    vscode.lm.selectChatModels(),
                    new Promise<never>((_, reject) =>
                        setTimeout(() => reject(new Error('Timeout after 15 seconds')), 15000)
                    )
                ]);

                const endTime = Date.now();
                logger.info(`✅ Models loaded successfully in ${endTime - startTime}ms`);
                logger.info(`Found ${models.length} models:`);

                if (models.length === 0) {
                    logger.error('❌ No models available');
                    logger.info('Possible causes:');
                    logger.info('  - Language model extension not signed in');
                    logger.info('  - Extension needs activation (try using it first)');
                    logger.info('  - Network connectivity issues');
                    logger.info('  - Extension configuration problems');
                } else {
                    models.forEach((model, index) => {
                        logger.info(`  ${index + 1}. ${model.family} (${model.vendor})`);
                        logger.info(`     - Name: ${model.name}`);
                        logger.info(`     - Max Input: ${model.maxInputTokens} tokens`);
                    });
                }

            } catch (modelError) {
                const endTime = Date.now();
                logger.error(`❌ Model loading failed after ${endTime - startTime}ms`);
                logger.error(`Error: ${modelError instanceof Error ? modelError.message : String(modelError)}`);

                // Provide specific guidance
                const errorStr = String(modelError);
                if (errorStr.includes('Timeout')) {
                    logger.info('💡 Troubleshooting timeout issues:');
                    logger.info('  1. Check internet connection');
                    logger.info('  2. Sign in to GitHub Copilot if using it');
                    logger.info('  3. Try restarting VS Code');
                    logger.info('  4. Check corporate firewall/proxy settings');
                } else if (errorStr.includes('not authorized') || errorStr.includes('authentication')) {
                    logger.info('💡 Authentication issue detected:');
                    logger.info('  1. Sign in to your language model service');
                    logger.info('  2. Check your subscription status');
                    logger.info('  3. Try signing out and back in');
                }
            }

            // 5. Check Wu Wei configuration
            const config = vscode.workspace.getConfiguration('wu-wei');
            const preferredModel = config.get<string>('preferredModel', 'gpt-4o');
            const automationEnabled = config.get<boolean>('enableAutomation', true);

            logger.info('Wu Wei Configuration:');
            logger.info(`  - Preferred Model: ${preferredModel}`);
            logger.info(`  - Automation Enabled: ${automationEnabled}`);

            // 6. Check extension state
            const modelState = this.getModelState();
            logger.info('Extension State:');
            logger.info(`  - Is Loading Models: ${modelState.isLoadingModels}`);
            logger.info(`  - Models Loaded: ${modelState.modelsLoaded}`);
            logger.info(`  - Available Models Count: ${modelState.availableModelsCount}`);
            logger.info(`  - Chat Sessions: ${this.chatSessions.length}`);

            logger.info('='.repeat(80));
            logger.info('DIAGNOSTICS COMPLETED');
            logger.info('='.repeat(80));

        } catch (error) {
            logger.error('❌ Diagnostics failed:', error);
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            background: var(--vscode-sideBar-background);
            color: var(--vscode-sideBar-foreground);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            padding: 8px 16px;
            border-bottom: 1px solid var(--vscode-panel-border);
            background: var(--vscode-sideBarSectionHeader-background);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h3 {
            font-size: 13px;
            font-weight: 600;
            margin: 0;
        }
        
        .new-chat-btn {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: 3px;
            padding: 4px 8px;
            font-size: 11px;
            cursor: pointer;
        }
        
        .new-chat-btn:hover {
            background: var(--vscode-button-hoverBackground);
        }
        
        .sessions-container {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }
        
        .sessions-list {
            border-bottom: 1px solid var(--vscode-panel-border);
            max-height: 40vh;
            overflow-y: auto;
        }
        
        .session-item {
            padding: 8px 16px;
            cursor: pointer;
            border-bottom: 1px solid var(--vscode-panel-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .session-item:hover {
            background: var(--vscode-list-hoverBackground);
        }
        
        .session-item.active {
            background: var(--vscode-list-activeSelectionBackground);
            color: var(--vscode-list-activeSelectionForeground);
        }
        
        .session-info {
            flex: 1;
            min-width: 0;
        }
        
        .session-title {
            font-size: 12px;
            font-weight: 500;
            margin-bottom: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .session-preview {
            font-size: 10px;
            opacity: 0.7;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .session-actions {
            display: flex;
            gap: 4px;
            opacity: 0;
            transition: opacity 0.2s;
        }
        
        .session-item:hover .session-actions {
            opacity: 1;
        }
        
        .action-btn {
            background: none;
            border: none;
            color: var(--vscode-icon-foreground);
            cursor: pointer;
            padding: 2px;
            border-radius: 2px;
            font-size: 12px;
        }
        
        .action-btn:hover {
            background: var(--vscode-toolbar-hoverBackground);
        }
        
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }
        
        .model-selector-container {
            padding: 8px 16px;
            border-bottom: 1px solid var(--vscode-panel-border);
            background: var(--vscode-sideBarSectionHeader-background);
        }
        
        .model-selector {
            width: 100%;
            background: var(--vscode-dropdown-background);
            color: var(--vscode-dropdown-foreground);
            border: 1px solid var(--vscode-dropdown-border);
            border-radius: 3px;
            padding: 4px 6px;
            font-size: 11px;
        }
        
        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .message {
            padding: 8px 12px;
            border-radius: 8px;
            max-width: 90%;
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
        
        .thinking-indicator {
            align-self: flex-start;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            padding: 8px 12px;
            border-radius: 8px;
            display: none;
            align-items: center;
            gap: 8px;
            font-style: italic;
        }
        
        .thinking-dots {
            display: flex;
            gap: 2px;
        }
        
        .thinking-dot {
            width: 4px;
            height: 4px;
            border-radius: 50%;
            background: currentColor;
            opacity: 0.4;
            animation: thinking 1.4s ease-in-out infinite both;
        }
        
        .thinking-dot:nth-child(1) { animation-delay: -0.32s; }
        .thinking-dot:nth-child(2) { animation-delay: -0.16s; }
        .thinking-dot:nth-child(3) { animation-delay: 0s; }
        
        @keyframes thinking {
            0%, 80%, 100% { opacity: 0.4; }
            40% { opacity: 1; }
        }
        
        .input-container {
            padding: 8px 16px;
            border-top: 1px solid var(--vscode-panel-border);
            display: flex;
            gap: 8px;
        }
        
        .message-input {
            flex: 1;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            border-radius: 3px;
            padding: 6px 8px;
            font-size: 12px;
            resize: none;
            min-height: 20px;
            max-height: 80px;
        }
        
        .send-btn {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: 3px;
            padding: 6px 12px;
            cursor: pointer;
            font-size: 11px;
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
            align-items: center;
            justify-content: center;
            text-align: center;
            color: var(--vscode-descriptionForeground);
            gap: 8px;
            padding: 16px;
        }
        
        .empty-icon {
            font-size: 32px;
            opacity: 0.6;
        }
        
        .empty-text {
            font-size: 12px;
            font-weight: 500;
        }
        
        .empty-subtitle {
            font-size: 11px;
            opacity: 0.8;
        }

        .error-container {
            padding: 12px 16px;
            background-color: var(--vscode-errorForeground);
            color: var(--vscode-input-foreground);
            opacity: 0.8;
        }

        .error-title {
            font-weight: bold;
            margin-bottom: 4px;
        }

        .error-details {
            font-size: 0.9em;
            margin-bottom: 8px;
        }

        .error-action-btn {
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            border: 1px solid var(--vscode-button-border);
            padding: 4px 8px;
            cursor: pointer;
            border-radius: 3px;
            font-size: 0.9em;
        }

        .error-action-btn:hover {
            background: var(--vscode-button-secondaryHoverBackground);
        }
    </style>
</head>
<body>
    <div class="header">
        <h3>Chat</h3>
        <button class="new-chat-btn" onclick="newChat()">+ New</button>
    </div>
    
    <div class="sessions-container">
        <div class="sessions-list" id="sessionsList">
            <!-- Sessions will be populated here -->
        </div>
        
        <div class="chat-area">
            <div class="model-selector-container">
                <select class="model-selector" id="modelSelector">
                    <option value="">Loading models...</option>
                </select>
            </div>
            
            <div class="error-message" id="errorMessage" style="display: none; color: var(--vscode-errorForeground); background: var(--vscode-inputValidation-errorBackground); border: 1px solid var(--vscode-inputValidation-errorBorder); padding: 8px; margin: 8px 16px; border-radius: 4px; font-size: 12px;">
                <div class="error-title" id="errorTitle">Error</div>
                <div class="error-details" id="errorDetails">Error details</div>
                <button class="error-action-btn" id="errorActionBtn" style="display: none;">Run Diagnostics</button>
            </div>
            
            <div id="messagesContainer" class="messages-container">
                <div id="emptyState" class="empty-state">
                    <div class="empty-icon">🌊</div>
                    <div class="empty-text">Select or create a chat</div>
                    <div class="empty-subtitle">Wu wei - effortless conversation</div>
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
                <textarea class="message-input" id="messageInput" placeholder="Loading..." rows="1" disabled></textarea>
                <button class="send-btn" id="sendBtn" onclick="sendMessage()" disabled>Send</button>
            </div>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        
        let sessions = [];
        let currentSessionId = null;
        let messages = [];
        let availableModels = [];
        
        // Auto-resize textarea
        document.getElementById('messageInput').addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 80) + 'px';
        });
        
        // Send on Enter
        document.getElementById('messageInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Model selector
        document.getElementById('modelSelector').addEventListener('change', function() {
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
            vscode.postMessage({ command: 'runDiagnostics' });
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
            messageDiv.className = \`message \${isUser ? 'user' : 'assistant'}\`;
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
                sessionDiv.className = \`session-item \${session.id === currentSessionId ? 'active' : ''}\`;
                sessionDiv.onclick = () => selectSession(session.id);
                
                sessionDiv.innerHTML = \`
                    <div class="session-info">
                        <div class="session-title">\${session.title}</div>
                        <div class="session-preview">\${session.lastMessage || 'No messages'}</div>
                    </div>
                    <div class="session-actions">
                        <button class="action-btn" onclick="renameSession('\${session.id}', event)" title="Rename">✏️</button>
                        <button class="action-btn" onclick="deleteSession('\${session.id}', event)" title="Delete">🗑️</button>
                    </div>
                \`;
                
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
                    messageDiv.className = \`message \${msg.role === 'user' ? 'user' : 'assistant'}\`;
                    messageDiv.textContent = msg.content;
                    container.insertBefore(messageDiv, thinkingIndicator);
                });
            }
            
            container.scrollTop = container.scrollHeight;
        }
        
        function updateModels(modelData, currentModel, loading, error) {
            console.log('updateModels called:', { modelData, currentModel, loading, error });
            
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
                selector.innerHTML = '<option value="">No models available</option>';
                return;
            }
            
            modelData.forEach(model => {
                const option = document.createElement('option');
                option.value = model.family;
                option.textContent = \`\${model.family} (\${model.vendor})\`;
                if (model.family === currentModel) {
                    option.selected = true;
                }
                selector.appendChild(option);
            });
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
        
        // Request initial state
        vscode.postMessage({ command: 'requestModels' });
    </script>
</body>
</html>`;
    }
}
