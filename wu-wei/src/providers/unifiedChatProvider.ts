import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { logger } from '../logger';
import { BaseWebviewProvider } from './BaseWebviewProvider';

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
export class UnifiedChatProvider extends BaseWebviewProvider implements vscode.WebviewViewProvider {
    private chatSessions: ChatSession[] = [];
    private currentSessionId?: string;
    private availableModels: vscode.LanguageModelChat[] = [];
    private isLoadingModels: boolean = false;
    private modelsLoaded: boolean = false;
    private modelChangeListener: vscode.Disposable | undefined;
    private debounceTimer: NodeJS.Timeout | undefined;

    constructor(context: vscode.ExtensionContext) {
        super(context);
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

        webviewView.webview.html = this.getWebviewContent(
            webviewView.webview,
            'chat/index.html',
            ['chat/style.css'],
            ['chat/main.js']
        );

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
                case 'showModelDetails':
                    this.showDetailedModelInfo();
                    break;
            }
        });

        webviewView.onDidChangeVisibility(() => {
            if (webviewView.visible) {
                // Refresh state when view becomes visible
                this.updateWebviewState();
                this.loadAvailableModels();
            }
        });

        // Initial load
        this.loadAvailableModels();
        this.updateWebviewState();
    }

    private createNewChat() {
        const newSession: ChatSession = {
            id: Date.now().toString(),
            title: `Chat ${this.chatSessions.length + 1}`,
            timestamp: new Date(),
            chatHistory: []
        };

        this.chatSessions.unshift(newSession);
        this.currentSessionId = newSession.id;
        this.saveChatSessions();
        this.updateWebviewState();

        logger.info(`Created new chat session: ${newSession.id}`);
    }

    private selectSession(sessionId: string) {
        const session = this.chatSessions.find(s => s.id === sessionId);
        if (session) {
            this.currentSessionId = sessionId;
            this.updateWebviewState();
            logger.info(`Selected chat session: ${sessionId}`);
        }
    }

    private deleteSession(sessionId: string) {
        const index = this.chatSessions.findIndex(s => s.id === sessionId);
        if (index !== -1) {
            this.chatSessions.splice(index, 1);

            if (this.currentSessionId === sessionId) {
                this.currentSessionId = this.chatSessions.length > 0 ? this.chatSessions[0].id : undefined;
            }

            this.saveChatSessions();
            this.updateWebviewState();
            logger.info(`Deleted chat session: ${sessionId}`);
        }
    }

    private renameSession(sessionId: string, newName: string) {
        const session = this.chatSessions.find(s => s.id === sessionId);
        if (session) {
            session.title = newName;
            this.saveChatSessions();
            this.updateWebviewState();
            logger.info(`Renamed chat session ${sessionId} to: ${newName}`);
        }
    }

    private async handleUserMessage(text: string) {
        if (!this.currentSessionId) {
            this.createNewChat();
        }

        const currentSession = this.chatSessions.find(s => s.id === this.currentSessionId);
        if (!currentSession) {
            logger.error('No current session found');
            return;
        }

        // Add user message to session
        const userMessage: ChatMessage = {
            role: 'user',
            content: text,
            timestamp: new Date()
        };

        currentSession.chatHistory.push(userMessage);
        currentSession.lastMessage = text.length > 50 ? text.substring(0, 50) + '...' : text;
        currentSession.timestamp = new Date();

        // Update session title if it's the first message
        if (currentSession.chatHistory.length === 1) {
            currentSession.title = text.length > 30 ? text.substring(0, 30) + '...' : text;
        }

        this.saveChatSessions();
        this.updateWebviewState();

        // Show thinking indicator
        this._view?.webview.postMessage({ command: 'showThinking' });

        try {
            // Get selected model
            const selectedModel = this.getSelectedModel();
            if (!selectedModel) {
                throw new Error('No model selected');
            }

            // Prepare messages for the model
            const messages = currentSession.chatHistory.map(msg =>
                msg.role === 'user'
                    ? vscode.LanguageModelChatMessage.User(msg.content)
                    : vscode.LanguageModelChatMessage.Assistant(msg.content)
            );

            // Request completion from language model
            const request = await selectedModel.sendRequest(messages, {}, new vscode.CancellationTokenSource().token);

            let response = '';
            for await (const fragment of request.text) {
                response += fragment;
            }

            // Add assistant response
            const assistantMessage: ChatMessage = {
                role: 'assistant',
                content: response,
                timestamp: new Date()
            };

            currentSession.chatHistory.push(assistantMessage);
            currentSession.lastMessage = response.length > 50 ? response.substring(0, 50) + '...' : response;
            currentSession.timestamp = new Date();

            this.saveChatSessions();
            this.updateWebviewState();

            // Send message to webview
            this._view?.webview.postMessage({
                command: 'addMessage',
                message: response,
                isUser: false
            });

        } catch (error) {
            logger.error('Error getting AI response', error);

            const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
            this._view?.webview.postMessage({
                command: 'addMessage',
                message: `Error: ${errorMessage}`,
                isUser: false
            });
        } finally {
            // Hide thinking indicator
            this._view?.webview.postMessage({ command: 'hideThinking' });
        }
    }

    private handleModelSelection(modelFamily: string) {
        if (this.currentSessionId) {
            const session = this.chatSessions.find(s => s.id === this.currentSessionId);
            if (session) {
                session.selectedModel = modelFamily;
                this.saveChatSessions();
                logger.info(`Selected model for session ${this.currentSessionId}: ${modelFamily}`);
            }
        }
    }

    private getSelectedModel(): vscode.LanguageModelChat | undefined {
        if (!this.currentSessionId) return undefined;

        const session = this.chatSessions.find(s => s.id === this.currentSessionId);
        const selectedFamily = session?.selectedModel;

        if (selectedFamily) {
            return this.availableModels.find(model => model.family === selectedFamily);
        }

        // Return first available model if no selection
        return this.availableModels.length > 0 ? this.availableModels[0] : undefined;
    }

    private async loadAvailableModels() {
        if (this.isLoadingModels) {
            logger.info('Already loading models, skipping duplicate request');
            return;
        }

        this.isLoadingModels = true; logger.info('Loading available language models...');
        logger.info(`VS Code Language Model API available: ${!!vscode.lm}`);

        if (vscode.lm) {
            logger.info('Language Model API capabilities:');
            logger.info(`  - selectChatModels: ${typeof vscode.lm.selectChatModels}`);
            logger.info(`  - onDidChangeChatModels: ${typeof vscode.lm.onDidChangeChatModels}`);
        }

        // Check what language model extensions are installed
        logger.info('Checking installed extensions that might provide language models...');
        const extensions = vscode.extensions.all;
        const potentialLMExtensions = extensions.filter(ext => {
            const id = ext.id.toLowerCase();
            const displayName = ext.packageJSON?.displayName?.toLowerCase() || '';
            const description = ext.packageJSON?.description?.toLowerCase() || '';

            return (
                id.includes('copilot') ||
                id.includes('openai') ||
                id.includes('claude') ||
                id.includes('anthropic') ||
                id.includes('gemini') ||
                id.includes('gpt') ||
                displayName.includes('copilot') ||
                displayName.includes('ai') ||
                description.includes('language model') ||
                ext.packageJSON?.contributes?.languageModels
            );
        });

        logger.info(`Found ${potentialLMExtensions.length} potential language model extensions:`);
        potentialLMExtensions.forEach(ext => {
            logger.info(`  - ${ext.id} (${ext.packageJSON?.displayName || 'Unknown'}) - ${ext.isActive ? 'Active' : 'Inactive'}`);
            if (ext.packageJSON?.contributes?.languageModels) {
                logger.info(`    Contributes language models: ${JSON.stringify(ext.packageJSON.contributes.languageModels)}`);
            }
        });

        // Set loading state
        this._view?.webview.postMessage({ command: 'setLoadingState', loading: true }); try {
            logger.info('Attempting to load all available chat models...');
            logger.info('Calling vscode.lm.selectChatModels() with no criteria to get all models');

            // Get all available models first
            const allModels = await vscode.lm.selectChatModels();
            logger.info(`Found ${allModels.length} total available models`);

            if (allModels.length > 0) {
                logger.info('='.repeat(80));
                logger.info('DETAILED MODEL INFORMATION');
                logger.info('='.repeat(80));

                allModels.forEach((model, index) => {
                    logger.info(`\n📋 MODEL ${index + 1}:`);
                    logger.info(`   🆔 ID: ${model.id}`);
                    logger.info(`   👨‍💼 Family: ${model.family}`);
                    logger.info(`   🏢 Vendor: ${model.vendor}`);
                    logger.info(`   📝 Name: ${model.name}`);
                    logger.info(`   🎯 Max Input Tokens: ${model.maxInputTokens?.toLocaleString() || 'Unknown'}`);
                    logger.info(`   📊 Version: ${model.version || 'N/A'}`);

                    // Additional properties that might be available
                    logger.info(`   🔧 All Properties:`);
                    const modelObj = model as any;
                    Object.keys(modelObj).forEach(key => {
                        if (!['id', 'family', 'vendor', 'name', 'maxInputTokens', 'version'].includes(key)) {
                            logger.info(`      ${key}: ${JSON.stringify(modelObj[key])}`);
                        }
                    });

                    // Test if we can get more detailed info
                    try {
                        logger.info(`   📋 Model Object Type: ${typeof model}`);
                        logger.info(`   📋 Model Constructor: ${model.constructor.name}`);
                        logger.info(`   📋 Model Prototype Keys: ${Object.getOwnPropertyNames(Object.getPrototypeOf(model))}`);
                    } catch (e) {
                        logger.info(`   ⚠️  Could not get additional model metadata: ${e}`);
                    }
                });

                this.availableModels = allModels;

                // Also try specific vendor filtering for comparison
                logger.info('Also checking Copilot models specifically...');
                try {
                    const copilotModels = await vscode.lm.selectChatModels({ vendor: 'copilot' });
                    logger.info(`Found ${copilotModels.length} Copilot models`);
                    copilotModels.forEach((model, index) => {
                        logger.info(`  Copilot ${index + 1}. ${model.family} - ${model.name}`);
                    });
                } catch (copilotError) {
                    logger.warn('Failed to get Copilot-specific models:', copilotError);
                }

            } else {
                logger.warn('No models found! Checking if specific models are available...');

                // Fallback: try specific model criteria
                logger.info('Attempting to select chat models with criteria: vendor=copilot, family=gpt-4o');
                const specificModels = await vscode.lm.selectChatModels({
                    vendor: 'copilot',
                    family: 'gpt-4o'
                });

                logger.info(`Found ${specificModels.length} models matching specific criteria`);

                if (specificModels.length > 0) {
                    logger.info('Specific model details:');
                    specificModels.forEach((model, index) => {
                        logger.info(`  ${index + 1}. ID: ${model.id}`);
                        logger.info(`     Family: ${model.family}`);
                        logger.info(`     Vendor: ${model.vendor}`);
                        logger.info(`     Name: ${model.name}`);
                        logger.info(`     Max Input Tokens: ${model.maxInputTokens}`);
                        logger.info(`     Version: ${model.version || 'N/A'}`);
                    });
                    this.availableModels = specificModels;
                } else {
                    logger.error('No language models found at all');
                    this.availableModels = [];
                }
            }

            this.modelsLoaded = true;
            logger.info(`Final loaded models count: ${this.availableModels.length}`);

            const modelData = this.availableModels.map(model => ({
                id: model.id,
                family: model.family,
                vendor: model.vendor,
                name: model.name
            }));

            const currentModel = this.getSelectedModel()?.family;

            logger.info(`Sending ${modelData.length} models to webview:`);
            modelData.forEach((model, index) => {
                logger.info(`  ${index + 1}. ${model.family} (${model.vendor}) - ${model.name}`);
            });
            logger.info(`Current selected model: ${currentModel || 'none'}`);

            // Send models to webview
            this._view?.webview.postMessage({
                command: 'updateModels',
                models: modelData,
                currentModel: currentModel,
                loading: false,
                error: null
            });

        } catch (error) {
            logger.error('Failed to load language models', error);

            const errorInfo = {
                message: error instanceof Error ? error.message : 'Failed to load models',
                details: 'Please check your GitHub Copilot subscription and try again.',
                actionable: true
            };

            this._view?.webview.postMessage({
                command: 'updateModels',
                models: [],
                currentModel: null,
                loading: false,
                error: errorInfo
            });
        } finally {
            this.isLoadingModels = false;
            this._view?.webview.postMessage({ command: 'setLoadingState', loading: false });
        }
    }

    /**
     * Public method to force reload models (for debugging)
     */
    public async forceReloadModels(): Promise<void> {
        this.isLoadingModels = false; // Reset the flag
        this.modelsLoaded = false; await this.loadAvailableModels();
    }

    /**
     * Show detailed information about all available models
     */
    public async showDetailedModelInfo(): Promise<void> {
        logger.show();
        logger.info('='.repeat(80));
        logger.info('DETAILED MODEL INFORMATION REPORT');
        logger.info('='.repeat(80));

        if (this.availableModels.length === 0) {
            logger.info('⚠️  No models currently loaded. Loading models first...');
            await this.forceReloadModels();
        }

        if (this.availableModels.length === 0) {
            logger.error('❌ No models available');
            return;
        }

        logger.info(`📊 Total Models Available: ${this.availableModels.length}`);
        logger.info('');

        // Group by vendor
        const modelsByVendor = this.availableModels.reduce((acc, model) => {
            if (!acc[model.vendor]) {
                acc[model.vendor] = [];
            }
            acc[model.vendor].push(model);
            return acc;
        }, {} as Record<string, vscode.LanguageModelChat[]>);

        Object.entries(modelsByVendor).forEach(([vendor, models]) => {
            logger.info(`🏢 VENDOR: ${vendor.toUpperCase()}`);
            logger.info('─'.repeat(60));

            models.forEach((model, index) => {
                logger.info(`\n  📋 Model ${index + 1}:`);
                logger.info(`     🆔 ID: ${model.id}`);
                logger.info(`     👨‍💼 Family: ${model.family}`);
                logger.info(`     📝 Name: ${model.name}`);
                logger.info(`     🎯 Context Window: ${model.maxInputTokens?.toLocaleString() || 'Unknown'} tokens`);
                logger.info(`     📊 Version: ${model.version || 'N/A'}`);

                // Calculate approximate context in different units
                if (model.maxInputTokens) {
                    const approxWords = Math.round(model.maxInputTokens * 0.75); // ~0.75 words per token
                    const approxPages = Math.round(approxWords / 250); // ~250 words per page
                    logger.info(`     📖 Approximate Capacity:`);
                    logger.info(`        - ${approxWords.toLocaleString()} words`);
                    logger.info(`        - ${approxPages.toLocaleString()} pages (250 words/page)`);
                }

                // Try to get additional model properties
                try {
                    const modelObj = model as any;
                    const additionalProps = Object.keys(modelObj).filter(key =>
                        !['id', 'family', 'vendor', 'name', 'maxInputTokens', 'version', 'sendRequest'].includes(key)
                    );

                    if (additionalProps.length > 0) {
                        logger.info(`     🔧 Additional Properties:`);
                        additionalProps.forEach(prop => {
                            const value = modelObj[prop];
                            if (typeof value !== 'function') {
                                logger.info(`        ${prop}: ${JSON.stringify(value)}`);
                            }
                        });
                    }
                } catch (e) {
                    // Ignore errors when inspecting model object
                }
            });
            logger.info('');
        });

        // Summary statistics
        logger.info('📈 SUMMARY STATISTICS:');
        logger.info('─'.repeat(40));

        const totalTokens = this.availableModels.reduce((sum, model) => sum + (model.maxInputTokens || 0), 0);
        const maxTokens = Math.max(...this.availableModels.map(m => m.maxInputTokens || 0));
        const minTokens = Math.min(...this.availableModels.map(m => m.maxInputTokens || 0));
        const avgTokens = Math.round(totalTokens / this.availableModels.length);

        logger.info(`  📊 Total Models: ${this.availableModels.length}`);
        logger.info(`  🏢 Unique Vendors: ${Object.keys(modelsByVendor).length}`);
        logger.info(`  👨‍💼 Unique Families: ${[...new Set(this.availableModels.map(m => m.family))].length}`);
        logger.info(`  🎯 Context Window Stats:`);
        logger.info(`     - Largest: ${maxTokens.toLocaleString()} tokens`);
        logger.info(`     - Smallest: ${minTokens.toLocaleString()} tokens`);
        logger.info(`     - Average: ${avgTokens.toLocaleString()} tokens`);
        logger.info(`     - Total: ${totalTokens.toLocaleString()} tokens`);

        logger.info('='.repeat(80));
        logger.info('MODEL INFORMATION REPORT COMPLETE');
        logger.info('='.repeat(80));

        vscode.window.showInformationMessage(
            `Model details logged. Found ${this.availableModels.length} models with ${avgTokens.toLocaleString()} avg context window.`
        );
    }

    private updateWebviewState() {
        if (!this._view) return;

        const currentSession = this.currentSessionId ?
            this.chatSessions.find(s => s.id === this.currentSessionId) : undefined;

        const sessionData = this.chatSessions.map(session => ({
            id: session.id,
            title: session.title,
            lastMessage: session.lastMessage,
            timestamp: session.timestamp
        }));

        const messageData = currentSession ? currentSession.chatHistory : [];

        this._view.webview.postMessage({
            command: 'updateState',
            currentSessionId: this.currentSessionId,
            sessions: sessionData,
            messages: messageData
        });
    }

    private loadChatSessions() {
        try {
            const sessionsFile = path.join(this.context.globalStorageUri.fsPath, 'chatSessions.json');

            if (fs.existsSync(sessionsFile)) {
                const data = fs.readFileSync(sessionsFile, 'utf8');
                const parsed = JSON.parse(data);

                this.chatSessions = parsed.sessions || [];
                this.currentSessionId = parsed.currentSessionId;

                // Convert timestamp strings back to Date objects
                this.chatSessions.forEach(session => {
                    session.timestamp = new Date(session.timestamp);
                    session.chatHistory.forEach(message => {
                        message.timestamp = new Date(message.timestamp);
                    });
                });

                logger.info(`Loaded ${this.chatSessions.length} chat sessions from storage`);
            }
        } catch (error) {
            logger.error('Failed to load chat sessions', error);
            this.chatSessions = [];
        }
    }

    private saveChatSessions() {
        try {
            // Ensure storage directory exists
            if (!fs.existsSync(this.context.globalStorageUri.fsPath)) {
                fs.mkdirSync(this.context.globalStorageUri.fsPath, { recursive: true });
            }

            const sessionsFile = path.join(this.context.globalStorageUri.fsPath, 'chatSessions.json');
            const data = {
                sessions: this.chatSessions,
                currentSessionId: this.currentSessionId
            };

            fs.writeFileSync(sessionsFile, JSON.stringify(data, null, 2));
            logger.info('Saved chat sessions to storage');
        } catch (error) {
            logger.error('Failed to save chat sessions', error);
        }
    }

    protected replaceTemplateVariables(html: string): string {
        // No template variables to replace for chat panel currently
        return html;
    }

    public refresh(): void {
        if (this._view) {
            this._view.webview.html = this.getWebviewContent(
                this._view.webview,
                'chat/index.html',
                ['chat/style.css'],
                ['chat/main.js']
            );
            this.updateWebviewState();
            this.loadAvailableModels();
        }
    }
}
