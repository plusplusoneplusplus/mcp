import * as vscode from 'vscode';
import { BaseWebviewProvider } from './BaseWebviewProvider';
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
import { PromptService, PromptUsageContext } from '../shared/promptManager/types';
import { PromptServiceFactory } from '../shared/promptManager/PromptServiceFactory';

/**
 * Wu Wei Agent Panel Provider (Enhanced with Prompt Integration)
 * Provides a panel for triggering agents with messages using separated HTML, CSS, and JavaScript files
 * Phase 4: Added prompt selection and integration capabilities
 */
export class AgentPanelProvider extends BaseWebviewProvider implements vscode.WebviewViewProvider {
    private _agentRegistry: AgentRegistry;
    private _messageHistory: AgentMessage[] = [];
    private _promptService: PromptService;
    private _selectedPromptContext?: PromptUsageContext;

    constructor(context: vscode.ExtensionContext) {
        super(context);
        logger.debug('Wu Wei Agent Panel Provider initialized with prompt integration');

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

        // Load HTML with separated CSS and JS files
        webviewView.webview.html = this.getWebviewContent(
            webviewView.webview,
            'agent/index.html',
            ['shared/base.css', 'shared/components.css', 'agent/style.css'],
            ['shared/utils.js', 'agent/main.js']
        );

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
            case 'sendAgentRequest':
                await this.handleAgentRequest(message.agentName, message.method, message.params);
                break;
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

            // Handle different prompt modes
            if (promptContext.mode === 'combined') {
                // Check for user input in various possible parameter names
                const userInput = params.message || params.question || params.query || params.input;
                if (!userInput) {
                    throw new Error('Please provide a custom message to combine with the prompt template');
                }
                enhancedParams.additionalMessage = userInput;
            }

            return enhancedParams;
        }

        // Fallback: add prompt as message parameter
        if (promptContext.promptId) {
            const rendered = await this._promptService.renderPromptWithVariables(
                promptContext.promptId,
                promptContext.variables
            );

            if (promptContext.mode === 'combined') {
                // For combined mode, always require both prompt and custom message
                // Check for user input in various possible parameter names
                const userInput = params.message || params.question || params.query || params.input;
                if (!userInput) {
                    throw new Error('Please provide a custom message to combine with the prompt template');
                }

                // Combine prompt and custom message
                return {
                    ...params,
                    message: `${rendered}\n\n${userInput}`
                };
            } else {
                // For custom mode, use prompt as main message
                return {
                    ...params,
                    message: rendered,
                    prompt: rendered // Also include as explicit prompt parameter
                };
            }
        }

        return params;
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
            this._view.webview.html = this.getWebviewContent(
                this._view.webview,
                'agent/index.html',
                ['shared/base.css', 'shared/components.css', 'agent/style.css'],
                ['shared/utils.js', 'agent/main.js']
            );

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

    private async initializePromptService(): Promise<void> {
        try {
            await this._promptService.initialize();
            logger.info('Prompt service initialized for agent panel');
        } catch (error) {
            logger.error('Failed to initialize prompt service for agent panel', error);
        }
    }
}
