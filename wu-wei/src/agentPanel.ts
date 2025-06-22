import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
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
        try {
            // Read HTML template from file
            const htmlPath = path.join(this.context.extensionPath, 'src', 'templates', 'agentPanel.html');
            let html = fs.readFileSync(htmlPath, 'utf8');

            // Replace template variables with actual values
            html = html.replace('{{VERSION}}', this.getExtensionVersion());
            html = html.replace('{{VSCODE_VERSION}}', vscode.version);

            return html;
        } catch (error) {
            logger.error('Failed to load agent panel HTML template', error);

            // Fallback HTML if template loading fails
            return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Wu Wei Agent Panel - Error</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            padding: 20px; 
            background: var(--vscode-sideBar-background); 
            color: var(--vscode-sideBar-foreground); 
        }
        .error { color: var(--vscode-errorForeground); }
    </style>
</head>
<body>
    <h2>Wu Wei Agent Panel</h2>
    <p class="error">⚠️ Failed to load agent panel template.</p>
    <p>Please check the extension installation and try again.</p>
    <p><strong>Error:</strong> ${error instanceof Error ? error.message : 'Unknown error'}</p>
</body>
</html>`;
        }
    }

    private getExtensionVersion(): string {
        try {
            const packageJsonPath = path.join(this.context.extensionPath, 'package.json');
            const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
            return packageJson.version || '0.1.0';
        } catch (error) {
            logger.debug('Failed to read extension version from package.json', error);
            return '0.1.0'; // Fallback version
        }
    }
}
