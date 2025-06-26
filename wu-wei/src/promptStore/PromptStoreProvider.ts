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
                case 'webviewReady':
                    await this.sendInitialData();
                    break;

                case 'configureDirectory':
                    await this.configureDirectory();
                    break;

                case 'openPrompt':
                    if (message.path) {
                        await this.openPrompt(message.path);
                    } else {
                        this.sendToWebview({
                            type: 'showError',
                            error: 'No prompt path provided'
                        });
                    }
                    break;

                case 'createNewPrompt':
                    await this.createNewPrompt();
                    break;

                case 'refreshStore':
                    await this.refreshStore();
                    break;

                // Legacy support
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
                type: 'showError',
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
            type: 'updatePrompts',
            prompts
        });
    }

    /**
     * Handle search prompts request
     */
    private async handleSearchPrompts(filter: SearchFilter): Promise<void> {
        const prompts = this.promptManager.searchPrompts(filter);
        this.sendToWebview({
            type: 'updatePrompts',
            prompts
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
                type: 'updatePrompts',
                prompts
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
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource}; script-src 'nonce-${nonce}';">
                <link href="${styleUri}" rel="stylesheet">
                <title>Wu Wei Prompt Store</title>
            </head>
            <body>
                <div class="prompt-store-container">
                    <header class="store-header">
                        <h2>Wu Wei Prompt Store</h2>
                    </header>
                    
                    <div class="search-section">
                        <input type="text" id="search-input" placeholder="🔍 Search prompts..." />
                        <div class="search-filters">
                            <select id="category-filter">
                                <option value="">All Categories</option>
                            </select>
                            <select id="tag-filter">
                                <option value="">All Tags</option>
                            </select>
                        </div>
                    </div>
                    
                    <main class="prompt-list-container">
                        <div id="prompt-tree" class="prompt-tree">
                            <!-- Prompt tree will be populated dynamically -->
                        </div>
                        
                        <div id="empty-state" class="empty-state" style="display: none;">
                            <div class="empty-content">
                                <h3>No Prompt Directory Configured</h3>
                                <p>Configure a directory to start managing your prompts</p>
                                <button id="configure-directory-empty" class="primary-button">
                                    📁 Select Directory
                                </button>
                            </div>
                        </div>
                        
                        <div id="loading-state" class="loading-state" style="display: none;">
                            <div class="loading-spinner"></div>
                            <p>Loading prompts...</p>
                        </div>
                    </main>
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

    /**
     * Send initial data to webview when it's ready
     */
    private async sendInitialData(): Promise<void> {
        const prompts = this.promptManager.getAllPrompts();
        const config = this.promptManager.getConfig();

        this.logger.info('Sending prompts to webview:', { count: prompts.length, prompts: prompts.slice(0, 2) }); // Debug log

        this.sendToWebview({
            type: 'updatePrompts',
            prompts
        });

        this.sendToWebview({
            type: 'updateConfig',
            config
        });

        // Hide loading state after initial data is sent
        this.sendToWebview({
            type: 'hideLoading'
        });
    }

    /**
     * Configure prompt store directory
     */
    private async configureDirectory(): Promise<void> {
        const options: vscode.OpenDialogOptions = {
            canSelectFiles: false,
            canSelectFolders: true,
            canSelectMany: false,
            openLabel: 'Select Prompt Directory'
        };

        const folderUri = await vscode.window.showOpenDialog(options);
        if (folderUri && folderUri[0]) {
            const configuration = vscode.workspace.getConfiguration('wu-wei.promptStore');
            await configuration.update('rootDirectory', folderUri[0].fsPath, vscode.ConfigurationTarget.Workspace);

            // Update prompt manager with new directory
            this.promptManager.updateConfig({ rootDirectory: folderUri[0].fsPath });
            await this.promptManager.refreshPrompts();

            vscode.window.showInformationMessage(`Prompt store directory set to: ${folderUri[0].fsPath}`);
        }
    }

    /**
     * Open a prompt file in the editor
     */
    private async openPrompt(promptPath: string): Promise<void> {
        try {
            const uri = vscode.Uri.file(promptPath);
            const document = await vscode.workspace.openTextDocument(uri);
            await vscode.window.showTextDocument(document);
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to open prompt file', { path: promptPath, error: errorMessage });

            this.sendToWebview({
                type: 'showError',
                error: `Failed to open prompt: ${errorMessage}`
            });
        }
    }

    /**
     * Create a new prompt file
     */
    private async createNewPrompt(): Promise<void> {
        const config = this.promptManager.getConfig();
        if (!config.rootDirectory) {
            vscode.window.showWarningMessage('Please configure a prompt directory first');
            await this.configureDirectory();
            return;
        }

        const promptName = await vscode.window.showInputBox({
            prompt: 'Enter prompt name',
            placeHolder: 'my-new-prompt'
        });

        if (!promptName) {
            return;
        }

        const fileName = promptName.endsWith('.md') ? promptName : `${promptName}.md`;
        const filePath = vscode.Uri.file(`${config.rootDirectory}/${fileName}`);

        const template = `---
title: ${promptName}
description: A new prompt
category: general
tags: []
author: ${process.env.USER || 'Unknown'}
version: 1.0.0
---

# ${promptName}

Your prompt content goes here...
`;

        try {
            await vscode.workspace.fs.writeFile(filePath, Buffer.from(template, 'utf8'));
            const document = await vscode.workspace.openTextDocument(filePath);
            await vscode.window.showTextDocument(document);

            // Refresh the prompt store
            await this.promptManager.refreshPrompts();
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to create new prompt', { path: filePath.fsPath, error: errorMessage });
            vscode.window.showErrorMessage(`Failed to create prompt: ${errorMessage}`);
        }
    }

    /**
     * Refresh the prompt store
     */
    private async refreshStore(): Promise<void> {
        this.sendToWebview({ type: 'showLoading' });

        try {
            await this.promptManager.refreshPrompts();
            // Prompts will be sent via the onPromptsChanged event
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to refresh prompt store', { error: errorMessage });

            this.sendToWebview({
                type: 'showError',
                error: `Failed to refresh: ${errorMessage}`
            });
        } finally {
            this.sendToWebview({ type: 'hideLoading' });
        }
    }
}
