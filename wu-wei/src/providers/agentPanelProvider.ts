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

/**
 * Wu Wei Agent Panel Provider (Migrated Structure)
 * Provides a panel for triggering agents with messages using separated HTML, CSS, and JavaScript files
 */
export class AgentPanelProvider extends BaseWebviewProvider implements vscode.WebviewViewProvider {
    private _agentRegistry: AgentRegistry;
    private _messageHistory: AgentMessage[] = [];

    constructor(context: vscode.ExtensionContext) {
        super(context);
        logger.debug('Wu Wei Agent Panel Provider initialized (migrated structure)');

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

        logger.debug('Wu Wei Agent Panel webview resolved (migrated structure)');
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
            }, 100);
        }
    }

    private generateMessageId(): string {
        return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
}
