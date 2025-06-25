/**
 * Prompt Store Provider - Webview provider for the prompt store UI
 * Following wu wei principles: simple, natural interface that flows with user needs
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { PromptManager } from './PromptManager';
import { Prompt, WebviewMessage, WebviewResponse, SearchFilter } from './types';
import { UI_CONFIG } from './constants';
import { WuWeiLogger } from '../logger';

export class PromptStoreProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'wu-wei.promptStore';

    private logger: WuWeiLogger;
    private promptManager: PromptManager;
    private webview?: vscode.Webview;

    constructor(
        private readonly extensionUri: vscode.Uri,
        promptManager: PromptManager
    ) {
        this.logger = WuWeiLogger.getInstance();
        this.promptManager = promptManager;

        // Listen to prompt changes
        this.promptManager.onPromptsChanged(this.handlePromptsChanged.bind(this));
    }

    /**
     * Resolve the webview view
     */
    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        token: vscode.CancellationToken
    ): void {
        this.webview = webviewView.webview;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [
                this.extensionUri
            ]
        };

        webviewView.webview.html = this.getHtmlForWebview(webviewView.webview);

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(
            this.handleWebviewMessage.bind(this),
            undefined,
            []
        );

        this.logger.info('Prompt Store webview resolved');
    }

    /**
     * Handle messages from the webview
     */
    private async handleWebviewMessage(message: WebviewMessage): Promise<void> {
        try {
            switch (message.type) {
                case 'getPrompts':
                    await this.handleGetPrompts();
                    break;

                case 'searchPrompts':
                    await this.handleSearchPrompts(message.payload);
                    break;

                case 'selectPrompt':
                    await this.handleSelectPrompt(message.payload);
                    break;

                case 'refreshPrompts':
                    await this.handleRefreshPrompts();
                    break;

                case 'updateConfig':
                    await this.handleUpdateConfig(message.payload);
                    break;

                default:
                    this.logger.warn('Unknown webview message type', { type: message.type });
            }
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Error handling webview message', {
                type: message.type,
                error: errorMessage
            });

            this.sendToWebview({
                type: 'error',
                error: errorMessage
            });
        }
    }

    /**
     * Handle get prompts request
     */
    private async handleGetPrompts(): Promise<void> {
        const prompts = this.promptManager.getAllPrompts();
        this.sendToWebview({
            type: 'promptsLoaded',
            payload: prompts
        });
    }

    /**
     * Handle search prompts request
     */
    private async handleSearchPrompts(filter: SearchFilter): Promise<void> {
        const prompts = this.promptManager.searchPrompts(filter);
        this.sendToWebview({
            type: 'promptsLoaded',
            payload: prompts
        });
    }

    /**
     * Handle select prompt request
     */
    private async handleSelectPrompt(promptId: string): Promise<void> {
        const prompt = this.promptManager.getPrompt(promptId);
        if (prompt) {
            // Insert prompt into active editor or show in new document
            await this.insertPromptIntoEditor(prompt);

            this.sendToWebview({
                type: 'promptSelected',
                payload: { id: promptId, success: true }
            });
        } else {
            this.sendToWebview({
                type: 'error',
                error: 'Prompt not found'
            });
        }
    }

    /**
     * Handle refresh prompts request
     */
    private async handleRefreshPrompts(): Promise<void> {
        await this.promptManager.refreshPrompts();
        // Prompts will be sent via the onPromptsChanged event
    }

    /**
     * Handle update configuration request
     */
    private async handleUpdateConfig(config: any): Promise<void> {
        this.promptManager.updateConfig(config);
        this.sendToWebview({
            type: 'configUpdated',
            payload: this.promptManager.getConfig()
        });
    }

    /**
     * Handle prompts changed event
     */
    private handlePromptsChanged(prompts: Prompt[]): void {
        if (this.webview) {
            this.sendToWebview({
                type: 'promptsLoaded',
                payload: prompts
            });
        }
    }

    /**
     * Send message to webview
     */
    private sendToWebview(response: WebviewResponse): void {
        if (this.webview) {
            this.webview.postMessage(response);
        }
    }

    /**
     * Insert prompt content into the active editor
     */
    private async insertPromptIntoEditor(prompt: Prompt): Promise<void> {
        const activeEditor = vscode.window.activeTextEditor;

        if (activeEditor) {
            // Insert at cursor position
            const position = activeEditor.selection.active;
            await activeEditor.edit(editBuilder => {
                editBuilder.insert(position, prompt.content);
            });

            this.logger.info('Prompt inserted into active editor', {
                promptId: prompt.id,
                title: prompt.metadata.title
            });
        } else {
            // Create new document
            const document = await vscode.workspace.openTextDocument({
                content: prompt.content,
                language: 'markdown'
            });

            await vscode.window.showTextDocument(document);

            this.logger.info('Prompt opened in new document', {
                promptId: prompt.id,
                title: prompt.metadata.title
            });
        }
    }

    /**
     * Generate HTML for the webview
     */
    private getHtmlForWebview(webview: vscode.Webview): string {
        // Get resource URIs
        const scriptUri = webview.asWebviewUri(
            vscode.Uri.joinPath(this.extensionUri, 'src', 'webview', 'promptStore', 'main.js')
        );
        const styleUri = webview.asWebviewUri(
            vscode.Uri.joinPath(this.extensionUri, 'src', 'webview', 'promptStore', 'style.css')
        );

        // Use a nonce to only allow specific scripts to be run
        const nonce = this.getNonce();

        return `
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource}; script-src 'nonce-${nonce}';">
                <link href="${styleUri}" rel="stylesheet">
                <title>Wu Wei - Prompt Store</title>
            </head>
            <body>
                <div id="app">
                    <div class="header">
                        <h2>Prompt Store</h2>
                        <div class="actions">
                            <button id="refresh-btn" class="btn btn-secondary" title="Refresh prompts">
                                <span class="codicon codicon-refresh"></span>
                            </button>
                        </div>
                    </div>
                    
                    <div class="search-container">
                        <input type="text" id="search-input" placeholder="Search prompts..." class="search-input">
                    </div>
                    
                    <div class="filters">
                        <select id="category-filter" class="filter-select">
                            <option value="">All Categories</option>
                        </select>
                        <select id="sort-filter" class="filter-select">
                            <option value="name">Sort by Name</option>
                            <option value="modified">Sort by Modified</option>
                            <option value="category">Sort by Category</option>
                            <option value="author">Sort by Author</option>
                        </select>
                    </div>
                    
                    <div id="prompts-container" class="prompts-container">
                        <div class="loading">Loading prompts...</div>
                    </div>
                </div>
                
                <script nonce="${nonce}" src="${scriptUri}"></script>
            </body>
            </html>
        `;
    }

    /**
     * Generate a nonce for script security
     */
    private getNonce(): string {
        let text = '';
        const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        for (let i = 0; i < 32; i++) {
            text += possible.charAt(Math.floor(Math.random() * possible.length));
        }
        return text;
    }
}
