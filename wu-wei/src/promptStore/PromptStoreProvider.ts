/**
 * Prompt Store Provider - Webview provider for the prompt store UI
 * Following wu wei principles: simple, natural interface that flows with user needs
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { PromptManager } from './PromptManager';
import { FileOperationManager } from './FileOperationManager';
import { Prompt, WebviewMessage, WebviewResponse, SearchFilter } from './types';
import { UI_CONFIG } from './constants';
import { WuWeiLogger } from '../logger';

export class PromptStoreProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'wu-wei.promptStore';

    private logger: WuWeiLogger;
    private promptManager: PromptManager;
    private fileOperationManager: FileOperationManager;
    private webview?: vscode.Webview;
    private _view?: vscode.WebviewView;

    constructor(
        private readonly extensionUri: vscode.Uri,
        promptManager: PromptManager,
        fileOperationManager: FileOperationManager
    ) {
        this.logger = WuWeiLogger.getInstance();
        this.promptManager = promptManager;
        this.fileOperationManager = fileOperationManager;

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
        this._view = webviewView;
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

        // Handle webview disposal
        webviewView.onDidDispose(() => {
            this.webview = undefined;
            this._view = undefined;
        });

        // Handle webview becoming visible/hidden
        webviewView.onDidChangeVisibility(() => {
            if (webviewView.visible && this.webview) {
                // Refresh data when view becomes visible after being hidden
                this.sendInitialData();
            }
        });

        this.logger.info('Prompt Store webview resolved');
    }    /**
     * Refresh the webview (called by VS Code's refresh button)
     */
    public refresh(): void {
        this.logger.info('🔄 PromptStoreProvider.refresh() called');

        if (this._view && this.webview) {
            this.logger.info('🖼️ Regenerating webview HTML content');
            // Regenerate the HTML content
            this._view.webview.html = this.getHtmlForWebview(this._view.webview);

            this.logger.info('⏰ Scheduling initial data send after 100ms delay');
            // Send initial data after a short delay to ensure webview is ready
            setTimeout(() => {
                this.logger.info('📤 Sending initial data after refresh delay');
                this.sendInitialData();
            }, 100);

            this.logger.info('✅ Prompt Store webview refreshed');
        } else {
            this.logger.warn('⚠️ Cannot refresh: view or webview not available', {
                hasView: !!this._view,
                hasWebview: !!this.webview
            });
        }
    }

    /**
     * Handle messages from the webview
     */
    private async handleWebviewMessage(message: WebviewMessage): Promise<void> {
        this.logger.info('📨 Received webview message:', { type: message.type, hasPayload: !!message.payload });

        try {
            switch (message.type) {
                case 'webviewReady':
                    this.logger.info('🚀 Webview ready, sending initial data');
                    await this.sendInitialData();
                    break;

                case 'configureDirectory':
                    this.logger.info('📁 Configure directory requested');
                    await this.configureDirectory();
                    break;

                case 'openPrompt':
                    this.logger.info('📄 Open prompt requested:', { path: message.path });
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
                    this.logger.info('➕ Create new prompt requested');
                    await this.createNewPrompt();
                    break;

                case 'refreshStore':
                    this.logger.info('🔄 Refresh store requested from webview');
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

                case 'deletePrompt':
                    if (message.path) {
                        await this.handleDeletePrompt(message.path);
                    } else {
                        this.sendToWebview({
                            type: 'showError',
                            error: 'No prompt path provided for deletion'
                        });
                    }
                    break;

                case 'renamePrompt':
                    if (message.path && message.newName) {
                        await this.handleRenamePrompt(message.path, message.newName);
                    } else {
                        this.sendToWebview({
                            type: 'showError',
                            error: 'Missing path or new name for rename operation'
                        });
                    }
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
            this.logger.info('📤 Sending message to webview:', { type: response.type });
            this.webview.postMessage(response);
        } else {
            this.logger.warn('⚠️ Cannot send message to webview: webview not available', { messageType: response.type });
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
    }    /**
     * Send initial data to webview when it's ready
     */
    private async sendInitialData(): Promise<void> {
        this.logger.info('📤 sendInitialData() called');

        try {
            const prompts = this.promptManager.getAllPrompts();
            const config = this.promptManager.getConfig();

            this.logger.info('📊 Sending prompts to webview:', {
                count: prompts.length,
                configExists: !!config,
                samplePrompts: prompts.slice(0, 2).map(p => ({
                    id: p.id,
                    title: p.metadata?.title,
                    fileName: p.fileName
                }))
            });

            this.logger.info('📤 Sending updatePrompts message');
            this.sendToWebview({
                type: 'updatePrompts',
                prompts
            });

            this.logger.info('📤 Sending updateConfig message');
            this.sendToWebview({
                type: 'updateConfig',
                config
            });

            this.logger.info('📤 Sending hideLoading message');
            // Hide loading state after initial data is sent
            this.sendToWebview({
                type: 'hideLoading'
            });

            this.logger.info('✅ Initial data sent successfully');
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('❌ Failed to send initial data to webview', { error: errorMessage });

            this.sendToWebview({
                type: 'showError',
                error: `Failed to load prompts: ${errorMessage}`
            });

            this.sendToWebview({
                type: 'hideLoading'
            });
        }
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

    /**
     * Handle delete prompt request
     */
    private async handleDeletePrompt(promptPath: string): Promise<void> {
        try {
            const result = await this.fileOperationManager.deletePrompt(promptPath);

            if (result.success) {
                this.sendToWebview({
                    type: 'showError', // Will be renamed to showMessage in the future
                    error: 'Prompt deleted successfully'
                });

                // Refresh the prompt store
                await this.promptManager.refreshPrompts();
            } else if (result.error !== 'Deletion cancelled') {
                this.sendToWebview({
                    type: 'showError',
                    error: result.error || 'Failed to delete prompt'
                });
            }
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to delete prompt', { path: promptPath, error: errorMessage });

            this.sendToWebview({
                type: 'showError',
                error: `Failed to delete prompt: ${errorMessage}`
            });
        }
    }

    /**
     * Handle rename prompt request
     */
    private async handleRenamePrompt(promptPath: string, newName: string): Promise<void> {
        try {
            const result = await this.fileOperationManager.renamePrompt(promptPath, newName);

            if (result.success) {
                this.sendToWebview({
                    type: 'showError', // Will be renamed to showMessage in the future
                    error: `Prompt renamed to: ${newName}`
                });

                // Refresh the prompt store
                await this.promptManager.refreshPrompts();

                // Open the renamed file
                if (result.filePath) {
                    await this.openPrompt(result.filePath);
                }
            } else {
                this.sendToWebview({
                    type: 'showError',
                    error: result.error || 'Failed to rename prompt'
                });
            }
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to rename prompt', { path: promptPath, newName, error: errorMessage });

            this.sendToWebview({
                type: 'showError',
                error: `Failed to rename prompt: ${errorMessage}`
            });
        }
    }
}
