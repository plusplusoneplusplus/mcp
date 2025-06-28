import * as vscode from 'vscode';
import { BaseWebviewProvider, WebviewResourceConfig } from './BaseWebviewProvider';
import { logger } from '../logger';
import {
    AbstractAgent,
    AgentRequest,
    AgentResponse,
    AgentRegistry,
    WuWeiExampleAgent,
    GitHubCopilotAgent,
    AgentMessage
} from '../interfaces/agentInterface';
import { PromptService, PromptUsageContext, TsxRenderOptions, TsxRenderResult } from '../shared/promptManager/types';
import { PromptServiceFactory } from '../shared/promptManager/PromptServiceFactory';
import { AgentPrompt } from '../shared/promptManager/tsx/components/AgentPrompt';
import { ChatMessage, DEFAULT_PRIORITIES } from '../shared/promptManager/tsx/types';

/**
 * Configuration interface for agent prompt handling
 */
interface AgentPromptConfig {
    maxTokens: number;
    historyMessageCount: number;
    enablePrioritization: boolean;
    fallbackToStringConcatenation: boolean;
}

/**
 * Wu Wei Agent Panel Provider (Enhanced with Prompt Integration)
 * Provides a panel for triggering agents with messages using separated HTML, CSS, and JavaScript files
 * Phase 4: Added prompt selection and integration capabilities
 * Phase 5: Enhanced with TSX-based prompt composition (Issue #378)
 */
export class AgentPanelProvider extends BaseWebviewProvider implements vscode.WebviewViewProvider {
    private _agentRegistry: AgentRegistry;
    private _messageHistory: AgentMessage[] = [];
    private _promptService: PromptService;
    private _selectedPromptContext?: PromptUsageContext;
    private _agentPromptConfig: AgentPromptConfig = {
        maxTokens: 4096,
        historyMessageCount: 4,
        enablePrioritization: true,
        fallbackToStringConcatenation: true
    };

    constructor(context: vscode.ExtensionContext) {
        super(context);
        logger.debug('Wu Wei Agent Panel Provider initialized with prompt integration and TSX support');

        // Initialize prompt service
        this._promptService = PromptServiceFactory.createService(context);
        this.setupPromptEventHandlers();

        // Initialize prompt service asynchronously
        this.initializePromptService();

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
        }).catch((error: any) => {
            logger.error('Failed to activate example agent', error);
        });

        // Activate the GitHub Copilot agent
        copilotAgent.activate().then(() => {
            logger.info('GitHub Copilot agent activated');
        }).catch((error: any) => {
            logger.error('Failed to activate GitHub Copilot agent', error);
        });
    }

    private setupPromptEventHandlers(): void {
        this._promptService.onPromptsChanged(this.handlePromptsChanged.bind(this));
        this._promptService.onPromptSelected(this.handlePromptSelected.bind(this));
    }

    private async handlePromptsChanged(prompts: any[]): Promise<void> {
        if (this._view) {
            this._view.webview.postMessage({
                command: 'updateAvailablePrompts',
                prompts: prompts.map(p => ({
                    id: p.id,
                    title: p.metadata.title,
                    category: p.metadata.category,
                    description: p.metadata.description,
                    tags: p.metadata.tags
                }))
            });
        }
    }

    private async handlePromptSelected(context: PromptUsageContext): Promise<void> {
        this._selectedPromptContext = context;

        if (this._view) {
            this._view.webview.postMessage({
                command: 'promptSelected',
                promptContext: {
                    id: context.prompt.id,
                    title: context.prompt.metadata.title,
                    content: context.prompt.content,
                    parameters: context.metadata.parameters || [],
                    usageInstructions: context.metadata.usageInstructions
                }
            });
        }
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

        // Load HTML with named resource mapping
        webviewView.webview.html = this.getWebviewContent(webviewView.webview, this.getAgentPanelConfig());

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async message => {
            logger.debug('Received message from agent panel webview:', message);
            await this.handleMessage(message);
        });

        // Send initial data
        this.sendAgentCapabilities();
        this.sendMessageHistory();
        this.sendAvailablePrompts();

        logger.debug('Wu Wei Agent Panel webview resolved with prompt integration');
    }

    protected async handleMessage(message: any): Promise<void> {
        switch (message.command) {
            case 'sendAgentRequestWithPrompt':
                await this.handleAgentRequestWithPrompt(
                    message.agentName,
                    message.method,
                    message.params,
                    message.promptContext
                );
                break;
            case 'selectPrompt':
                await this.handleSelectPrompt(message.promptId);
                break;
            case 'renderPromptWithVariables':
                await this.handleRenderPrompt(message.promptId, message.variables);
                break;
            case 'getAvailablePrompts':
                await this.sendAvailablePrompts();
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
    }

    private async handleSelectPrompt(promptId: string): Promise<void> {
        try {
            const context = await this._promptService.selectPromptForUse(promptId);
            this._selectedPromptContext = context;

            this._view?.webview.postMessage({
                command: 'promptSelected',
                promptContext: {
                    id: context.prompt.id,
                    title: context.prompt.metadata.title,
                    content: context.prompt.content,
                    parameters: context.metadata.parameters || [],
                    usageInstructions: context.metadata.usageInstructions
                }
            });
        } catch (error) {
            this._view?.webview.postMessage({
                command: 'error',
                error: `Failed to select prompt: ${error instanceof Error ? error.message : String(error)}`
            });
        }
    }

    private async handleRenderPrompt(promptId: string, variables: Record<string, any>): Promise<void> {
        try {
            const rendered = await this._promptService.renderPromptWithVariables(promptId, variables);

            this._view?.webview.postMessage({
                command: 'promptRendered',
                rendered
            });
        } catch (error) {
            this._view?.webview.postMessage({
                command: 'error',
                error: `Failed to render prompt: ${error instanceof Error ? error.message : String(error)}`
            });
        }
    }

    private async handleAgentRequestWithPrompt(
        agentName: string,
        method: string,
        params: any,
        promptContext?: any
    ): Promise<void> {
        try {
            logger.info(`Processing agent request with prompt: ${agentName}.${method}`, { params, promptContext });

            const agent = this._agentRegistry.getAgent(agentName);
            if (!agent) {
                throw new Error(`Agent '${agentName}' not found`);
            }

            // Enhance parameters with prompt context
            const enhancedParams = await this.enhanceParamsWithPrompt(params, promptContext, agent);

            // Process the request
            const request: AgentRequest = {
                id: this.generateMessageId(),
                method,
                params: enhancedParams,
                timestamp: new Date()
            };

            const response = await agent.processRequest(request);

            // Add to message history
            this.addMessageToHistory({
                id: request.id,
                timestamp: request.timestamp,
                type: 'request',
                method: request.method,
                params: request.params
            });

            this.addMessageToHistory({
                id: response.id,
                timestamp: response.timestamp,
                type: 'response',
                result: response.result,
                error: response.error
            });

        } catch (error) {
            this.addMessageToHistory({
                id: this.generateMessageId(),
                timestamp: new Date(),
                type: 'error',
                error: {
                    code: -32603,
                    message: 'Request failed',
                    data: error instanceof Error ? error.message : String(error)
                }
            });
        }
    }

    private async enhanceParamsWithPrompt(
        params: any,
        promptContext: any,
        agent: AbstractAgent
    ): Promise<any> {
        if (!promptContext) {
            return params;
        }

        // Try TSX-based rendering first if enabled
        if (this._agentPromptConfig.enablePrioritization) {
            try {
                return await this.enhanceParamsWithTsxPrompt(params, promptContext, agent);
            } catch (error) {
                logger.warn('TSX prompt rendering failed, falling back to string concatenation', error);

                // If fallback is disabled, re-throw the error
                if (!this._agentPromptConfig.fallbackToStringConcatenation) {
                    throw error;
                }
            }
        }

        // Original string concatenation logic (fallback)
        const capabilities = agent.getCapabilities();
        const promptSupport = capabilities.metadata?.promptSupport;

        if (promptSupport?.supportsPrompts) {
            const promptParam = promptSupport.promptParameterName || 'prompt';

            // Render the prompt with variables
            const rendered = await this._promptService.renderPromptWithVariables(
                promptContext.promptId,
                promptContext.variables
            );

            const enhancedParams = {
                ...params,
                [promptParam]: rendered
            };

            if (promptSupport.variableResolution) {
                enhancedParams.variables = promptContext.variables;
            }

            // Always use combined mode - check for user input
            const userInput = params.message || params.question || params.query || params.input;
            if (!userInput) {
                throw new Error('Please provide a custom message to combine with the prompt template');
            }
            enhancedParams.additionalMessage = userInput;

            return enhancedParams;
        }

        // Fallback: add prompt as message parameter
        if (promptContext.promptId) {
            const rendered = await this._promptService.renderPromptWithVariables(
                promptContext.promptId,
                promptContext.variables
            );

            // Always use combined mode - require both prompt and custom message
            const userInput = params.message || params.question || params.query || params.input;
            if (!userInput) {
                throw new Error('Please provide a custom message to combine with the prompt template');
            }

            // Combine prompt and custom message
            return {
                ...params,
                message: `${rendered}\n\n${userInput}`
            };
        }

        return params;
    }

    /**
     * Enhanced TSX-based prompt parameter enhancement
     * Replaces string concatenation with intelligent TSX composition
     */
    private async enhanceParamsWithTsxPrompt(
        params: any,
        promptContext: any,
        agent: AbstractAgent
    ): Promise<any> {
        if (!promptContext) {
            return params;
        }

        const userInput = params.message || params.question || params.query || params.input;
        if (!userInput) {
            throw new Error('Please provide a custom message to combine with the prompt template');
        }

        // Render the prompt with variables
        const rendered = await this._promptService.renderPromptWithVariables(
            promptContext.promptId,
            promptContext.variables
        );

        // Convert message history to ChatMessage format
        const conversationHistory: ChatMessage[] = this._messageHistory
            .filter(msg => msg.type === 'request' || msg.type === 'response')
            .slice(-this._agentPromptConfig.historyMessageCount)
            .map(msg => ({
                role: msg.type === 'request' ? 'user' : 'assistant',
                content: this.extractMessageContent(msg),
                timestamp: msg.timestamp,
                id: msg.id
            }));

        // Prepare TSX rendering options
        const tsxOptions: TsxRenderOptions = {
            modelMaxPromptTokens: this._agentPromptConfig.maxTokens,
            enablePrioritization: this._agentPromptConfig.enablePrioritization,
            tokenBudget: this._agentPromptConfig.maxTokens
        };

        // Render TSX prompt with intelligent composition
        const tsxResult: TsxRenderResult = await this._promptService.renderTsxPrompt(
            AgentPrompt,
            {
                systemPrompt: rendered,
                userInput: userInput,
                conversationHistory: conversationHistory,
                contextData: params.context || '',
                maxTokens: this._agentPromptConfig.maxTokens,
                priorityStrategy: DEFAULT_PRIORITIES
            },
            tsxOptions
        );

        // Check agent capabilities for TSX support
        const capabilities = agent.getCapabilities();
        const promptSupport = capabilities.metadata?.promptSupport;

        if (promptSupport?.supportsPrompts && promptSupport.supportsTsxMessages) {
            // Agent supports TSX messages directly
            return {
                ...params,
                messages: tsxResult.messages,
                tokenCount: tsxResult.tokenCount,
                renderingMetadata: tsxResult.renderingMetadata
            };
        } else {
            // Convert TSX messages back to string format for compatibility
            const combinedMessage = this.convertTsxMessagesToString(tsxResult.messages);

            return {
                ...params,
                message: combinedMessage,
                tokenCount: tsxResult.tokenCount,
                renderingMetadata: tsxResult.renderingMetadata
            };
        }
    }

    /**
     * Extract content from AgentMessage for conversation history
     */
    private extractMessageContent(message: AgentMessage): string {
        if (message.type === 'request') {
            return message.params?.message || message.params?.query || message.params?.input || 'Request';
        } else if (message.type === 'response') {
            return message.result?.message || message.result?.content || JSON.stringify(message.result || {});
        }
        return 'Unknown message';
    }

    /**
     * Convert TSX messages to string format for agents that don't support TSX
     */
    private convertTsxMessagesToString(messages: vscode.LanguageModelChatMessage[]): string {
        return messages.map(msg => {
            // Map roles to string labels
            let role = 'USER';
            if (msg.role === vscode.LanguageModelChatMessageRole.User) {
                role = 'USER';
            } else {
                // For any other role (system, assistant, etc.), use generic labels
                role = 'ASSISTANT';
            }

            // Extract text content from message
            const content = Array.isArray(msg.content)
                ? msg.content.map(part => {
                    if (typeof part === 'string') {
                        return part;
                    } else if (part && typeof part === 'object' && 'text' in part) {
                        return part.text;
                    } else if (part && typeof part === 'object' && 'value' in part) {
                        return String(part.value);
                    }
                    return JSON.stringify(part);
                }).join(' ')
                : String(msg.content);

            return `${role}: ${content}`;
        }).join('\n\n');
    }

    /**
     * Update agent prompt configuration
     */
    public updateAgentPromptConfig(config: Partial<AgentPromptConfig>): void {
        this._agentPromptConfig = { ...this._agentPromptConfig, ...config };
        logger.info('Agent prompt configuration updated', this._agentPromptConfig);
    }

    /**
     * Get current agent prompt configuration
     */
    public getAgentPromptConfig(): AgentPromptConfig {
        return { ...this._agentPromptConfig };
    }

    private async sendAvailablePrompts(): Promise<void> {
        try {
            const prompts = await this._promptService.getAllPrompts();

            if (this._view) {
                this._view.webview.postMessage({
                    command: 'updateAvailablePrompts',
                    prompts: prompts.map(p => ({
                        id: p.id,
                        title: p.metadata.title,
                        category: p.metadata.category,
                        description: p.metadata.description,
                        tags: p.metadata.tags
                    }))
                });
            }
        } catch (error) {
            logger.error('Failed to load available prompts', error);
            if (this._view) {
                this._view.webview.postMessage({
                    command: 'updateAvailablePrompts',
                    prompts: []
                });
            }
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
        if (!this._view) {
            return;
        }

        const capabilities = this._agentRegistry.getAgentCapabilities();
        this._view.webview.postMessage({
            command: 'updateAgentCapabilities',
            capabilities
        });
    }

    private sendMessageHistory(): void {
        if (!this._view) {
            return;
        }

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

    /**
     * Refresh the webview content
     */
    public refresh(): void {
        if (this._view) {
            this._view.webview.html = this.getWebviewContent(this._view.webview, this.getAgentPanelConfig());

            // Re-send initial data after refresh
            setTimeout(() => {
                this.sendAgentCapabilities();
                this.sendMessageHistory();
                this.sendAvailablePrompts();
            }, 100);
        }
    }

    private generateMessageId(): string {
        return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Get the webview resource configuration for the agent panel
     * @returns WebviewResourceConfig for the agent panel
     */
    private getAgentPanelConfig(): WebviewResourceConfig {
        return {
            htmlFile: 'agent/index.html',
            cssResources: {
                'BASE_CSS_URI': 'shared/base.css',
                'COMPONENTS_CSS_URI': 'shared/components.css',
                'AGENT_CSS_URI': 'agent/style.css'
            },
            jsResources: {
                'UTILS_JS_URI': 'shared/utils.js',
                'AGENT_JS_URI': 'agent/main.js'
            }
        };
    }

    private async initializePromptService(): Promise<void> {
        try {
            await this._promptService.initialize();
            logger.info('Prompt service initialized for agent panel');
        } catch (error) {
            logger.error('Failed to initialize prompt service for agent panel', error);
        }
    }
}
