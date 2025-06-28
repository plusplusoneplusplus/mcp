/**
 * Prompt Store Provider - Webview provider for the prompt store UI
 * Following wu wei principles: simple, natural interface that flows with user needs
 * Phase 3: Migrated to use shared PromptService interface
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { PromptService, PromptUsageContext } from '../shared/promptManager/types';
import { PromptServiceFactory } from '../shared/promptManager/PromptServiceFactory';
import { FileOperationManager } from './FileOperationManager';
import { Prompt, WebviewMessage, WebviewResponse, SearchFilter } from './types';
import { UI_CONFIG } from './constants';
import { WuWeiLogger } from '../logger';
import { BaseWebviewProvider } from '../providers/BaseWebviewProvider';

// Enhanced message types for Phase 3
interface EnhancedWebviewMessage {
    type: 'webviewReady' | 'configureDirectory' | 'openPrompt' | 'createNewPrompt' |
    'refreshStore' | 'getPrompts' | 'searchPrompts' | 'selectPrompt' |
    'refreshPrompts' | 'updateConfig' | 'deletePrompt' | 'renamePrompt' |
    'duplicatePrompt' | 'selectPromptForUse' | 'renderPromptWithVariables';
    payload?: any;
    path?: string;
    newName?: string;
    promptId?: string;
    variables?: Record<string, any>;
}

interface EnhancedWebviewResponse {
    type: 'updatePrompts' | 'updateConfig' | 'showLoading' | 'hideLoading' |
    'showError' | 'promptsLoaded' | 'promptSelected' | 'error' |
    'configUpdated' | 'promptUsageContext' | 'promptRendered';
    payload?: any;
    prompts?: Prompt[];
    config?: any;
    error?: string;
    usageContext?: PromptUsageContext;
    renderedContent?: string;
}

export class PromptStoreProvider extends BaseWebviewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'wu-wei.promptStore';

    private logger: WuWeiLogger;
    private promptService: PromptService;
    private fileOperationManager: FileOperationManager;
    private webview?: vscode.Webview;

    // Performance optimization: cache for recent operations
    private promptCache: Map<string, Prompt> = new Map();
    private lastRefreshTime: number = 0;
    private readonly CACHE_DURATION = 30000; // 30 seconds

    constructor(
        private readonly extensionUri: vscode.Uri,
        context: vscode.ExtensionContext
    ) {
        super(context);
        this.logger = WuWeiLogger.getInstance();

        // Create configuration manager first
        const { ConfigurationManager } = require('./ConfigurationManager');
        const configManager = new ConfigurationManager(context);

        // Get initial configuration from ConfigurationManager
        const configManagerConfig = configManager.getConfig();

        // Convert to PromptManager-compatible config format
        const initialConfig = {
            rootDirectory: configManagerConfig.rootDirectory,
            watchPaths: configManagerConfig.rootDirectory ? [configManagerConfig.rootDirectory] : [],
            filePatterns: ['**/*.md', '**/*.txt'],
            excludePatterns: ['**/node_modules/**', '**/.git/**', '**/dist/**', '**/build/**'],
            autoRefresh: configManagerConfig.autoRefresh,
            refreshInterval: 1000,
            enableCache: true,
            maxCacheSize: 1000,
            sortBy: 'name' as const,
            sortOrder: 'asc' as const,
            showCategories: true,
            showTags: true,
            enableSearch: true
        };

        // Create legacy PromptManager for FileOperationManager compatibility with proper config
        const { PromptManager } = require('./PromptManager');
        const promptManager = new PromptManager(initialConfig);

        this.fileOperationManager = new FileOperationManager(
            promptManager,
            configManager
        );

        // Use shared service factory after ensuring PromptManager is properly configured
        this.promptService = PromptServiceFactory.createService(context, initialConfig);

        // Initialize services sequentially to avoid race conditions
        this.initializeServicesSequentially(promptManager, configManager);

        // Set up event listeners for the shared service
        this.setupServiceEventHandlers();
    }

    /**
     * Initialize services in the correct order to avoid race conditions
     */
    private async initializeServicesSequentially(promptManager: any, configManager: any): Promise<void> {
        try {
            // First ensure configuration is properly loaded
            const config = configManager.getConfig();
            this.logger.info('📋 Configuration loaded:', {
                rootDirectory: config.rootDirectory,
                autoRefresh: config.autoRefresh
            });

            // Initialize the legacy PromptManager first
            await promptManager.initialize();
            this.logger.info('✅ Legacy PromptManager initialized successfully');

            // Then initialize the shared service
            await this.promptService.initialize();
            this.logger.info('✅ PromptService initialized successfully');

        } catch (error) {
            this.logger.error('❌ Failed to initialize services', error);
            // Don't throw - let the extension continue to work even if initialization fails
        }
    }

    /**
     * Set up event handlers for the shared service
     */
    private setupServiceEventHandlers(): void {
        // Replace direct PromptManager event handlers with service events
        this.promptService.onPromptsChanged(this.handlePromptsChanged.bind(this));
        this.promptService.onConfigChanged(this.handleConfigChanged.bind(this));
        this.promptService.onPromptSelected(this.handlePromptSelected.bind(this));
    }

    /**
     * Handle prompts changed event from service
     */
    private async handlePromptsChanged(prompts: Prompt[]): Promise<void> {
        // Update cache
        this.promptCache.clear();
        prompts.forEach(prompt => this.promptCache.set(prompt.id, prompt));
        this.lastRefreshTime = Date.now();

        // Send to webview
        if (this.webview) {
            this.sendToWebview({
                type: 'updatePrompts',
                prompts
            });
        }
    }

    /**
     * Handle config changed event from service
     */
    private async handleConfigChanged(config: any): Promise<void> {
        if (this.webview) {
            this.sendToWebview({
                type: 'configUpdated',
                payload: config
            });
        }
    }

    /**
     * Handle prompt selected event from service (for future agent integration)
     */
    private async handlePromptSelected(context: PromptUsageContext): Promise<void> {
        this.logger.info(`Prompt selected for use: ${context.prompt.metadata.title}`);

        if (this.webview) {
            this.sendToWebview({
                type: 'promptUsageContext',
                usageContext: context
            });
        }
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

        webviewView.webview.html = this.getWebviewContent(
            webviewView.webview,
            'promptStore/index.html',
            ['shared/base.css', 'shared/components.css', 'promptStore/style.css'],
            ['shared/utils.js', 'promptStore/main.js']
        );

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
    }

    /**
     * Refresh the webview (called by VS Code's refresh button)
     * Implementation of abstract method from BaseWebviewProvider
     */
    public refresh(): void {
        this.logger.info('🔄 PromptStoreProvider.refresh() called');

        if (this._view && this.webview) {
            this.logger.info('🖼️ Regenerating webview HTML content');
            // Regenerate the HTML content
            this._view.webview.html = this.getWebviewContent(
                this._view.webview,
                'promptStore/index.html',
                ['shared/base.css', 'shared/components.css', 'promptStore/style.css'],
                ['shared/utils.js', 'promptStore/main.js']
            );

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
     * Handle messages from the webview with enhanced functionality
     */
    private async handleWebviewMessage(message: EnhancedWebviewMessage): Promise<void> {
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

                case 'getPrompts':
                    await this.handleGetPrompts();
                    break;

                case 'searchPrompts':
                    await this.handleSearchPrompts(message.payload);
                    break;

                case 'selectPrompt':
                    await this.handleSelectPrompt(message.payload);
                    break;

                // New enhanced handlers for Phase 3
                case 'selectPromptForUse':
                    if (message.promptId) {
                        await this.handleSelectPromptForUse(message.promptId);
                    } else {
                        this.sendToWebview({
                            type: 'showError',
                            error: 'No prompt ID provided for selection'
                        });
                    }
                    break;

                case 'renderPromptWithVariables':
                    if (message.promptId && message.variables) {
                        await this.handleRenderPromptWithVariables(message.promptId, message.variables);
                    } else {
                        this.sendToWebview({
                            type: 'showError',
                            error: 'Missing prompt ID or variables for rendering'
                        });
                    }
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

    // ===== Enhanced Handler Methods for Phase 3 =====

    /**
     * Handle get prompts request with caching
     */
    private async handleGetPrompts(): Promise<void> {
        try {
            const prompts = await this.getPromptsWithCache();
            this.sendToWebview({
                type: 'updatePrompts',
                prompts
            });
        } catch (error) {
            this.handleError('Failed to load prompts', error);
        }
    }

    /**
     * Handle search prompts request with async service
     */
    private async handleSearchPrompts(filter: SearchFilter): Promise<void> {
        try {
            const query = filter.query || '';
            const prompts = await this.promptService.searchPrompts(query, filter);
            this.sendToWebview({
                type: 'updatePrompts',
                prompts
            });
        } catch (error) {
            this.handleError('Search failed', error);
        }
    }

    /**
     * Handle select prompt request (existing behavior)
     */
    private async handleSelectPrompt(promptId: string): Promise<void> {
        try {
            const prompt = await this.promptService.getPrompt(promptId);
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
        } catch (error) {
            this.handleError('Failed to select prompt', error);
        }
    }

    /**
     * Handle select prompt for use (new enhanced functionality)
     */
    private async handleSelectPromptForUse(promptId: string): Promise<void> {
        try {
            const usageContext = await this.promptService.selectPromptForUse(promptId);

            this.sendToWebview({
                type: 'promptUsageContext',
                usageContext
            });
        } catch (error) {
            this.handleError('Failed to select prompt for use', error);
        }
    }

    /**
     * Handle render prompt with variables (new functionality)
     */
    private async handleRenderPromptWithVariables(
        promptId: string,
        variables: Record<string, any>
    ): Promise<void> {
        try {
            const renderedContent = await this.promptService.renderPromptWithVariables(
                promptId,
                variables
            );

            this.sendToWebview({
                type: 'promptRendered',
                renderedContent
            });
        } catch (error) {
            this.handleError('Failed to render prompt', error);
        }
    }

    /**
     * Handle refresh prompts request
     */
    private async handleRefreshPrompts(): Promise<void> {
        try {
            await this.invalidateCache();
            // Prompts will be sent via the onPromptsChanged event
        } catch (error) {
            this.handleError('Failed to refresh prompts', error);
        }
    }

    /**
     * Handle update configuration request
     */
    private async handleUpdateConfig(config: any): Promise<void> {
        try {
            await this.promptService.updateConfig(config);
            // Config update will be sent via the onConfigChanged event
        } catch (error) {
            this.handleError('Failed to update configuration', error);
        }
    }

    // ===== Performance Optimization Methods =====

    /**
     * Get prompts with caching for better performance
     */
    private async getPromptsWithCache(): Promise<Prompt[]> {
        const now = Date.now();

        // Use cache if recent
        if (now - this.lastRefreshTime < this.CACHE_DURATION && this.promptCache.size > 0) {
            return Array.from(this.promptCache.values());
        }

        // Refresh from service
        const prompts = await this.promptService.getAllPrompts();

        // Update cache
        this.promptCache.clear();
        prompts.forEach(prompt => this.promptCache.set(prompt.id, prompt));
        this.lastRefreshTime = now;

        return prompts;
    }

    /**
     * Invalidate cache and refresh
     */
    private async invalidateCache(): Promise<void> {
        this.promptCache.clear();
        this.lastRefreshTime = 0;
        await this.loadAndDisplayPrompts();
    }

    /**
     * Load and display prompts with loading states
     */
    private async loadAndDisplayPrompts(): Promise<void> {
        try {
            this.sendToWebview({ type: 'showLoading' });
            const prompts = await this.promptService.getAllPrompts();
            this.sendToWebview({
                type: 'updatePrompts',
                prompts
            });
        } catch (error) {
            this.handleError('Failed to load prompts', error);
        } finally {
            this.sendToWebview({ type: 'hideLoading' });
        }
    }

    // ===== Utility Methods =====

    /**
     * Handle errors with consistent logging and user feedback
     */
    private handleError(message: string, error: any): void {
        const errorMessage = error instanceof Error ? error.message : String(error);
        this.logger.error(message, { error: errorMessage });

        this.sendToWebview({
            type: 'showError',
            error: `${message}: ${errorMessage}`
        });
    }

    /**
     * Send message to webview
     */
    private sendToWebview(response: EnhancedWebviewResponse): void {
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
     * Send initial data to webview when it's ready
     */
    private async sendInitialData(): Promise<void> {
        this.logger.info('📤 sendInitialData() called');

        try {
            // Ensure service is initialized before using it
            if (!this.promptService) {
                throw new Error('PromptService not available');
            }

            // Initialize service if not already done
            await this.promptService.initialize();

            const config = await this.promptService.getConfig();

            // Check if root directory is configured
            if (!config.rootDirectory) {
                this.logger.info('📁 No root directory configured, sending empty state with config');

                // Send empty prompts list and config
                this.sendToWebview({
                    type: 'updatePrompts',
                    prompts: []
                });

                this.sendToWebview({
                    type: 'updateConfig',
                    config
                });

                this.sendToWebview({
                    type: 'hideLoading'
                });

                this.logger.info('✅ Initial data sent (no directory configured)');
                return;
            }

            const prompts = await this.getPromptsWithCache();

            this.logger.info('📊 Sending prompts to webview:', {
                count: prompts.length,
                configExists: !!config,
                rootDirectory: config.rootDirectory,
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
        try {
            const options: vscode.OpenDialogOptions = {
                canSelectFiles: false,
                canSelectFolders: true,
                canSelectMany: false,
                openLabel: 'Select Prompt Directory'
            };

            this.logger.info('📁 Opening directory selection dialog');
            const folderUri = await vscode.window.showOpenDialog(options);

            if (folderUri && folderUri[0]) {
                const selectedPath = folderUri[0].fsPath;
                this.logger.info('📁 Directory selected:', { path: selectedPath });

                // Update VS Code configuration
                const configuration = vscode.workspace.getConfiguration('wu-wei.promptStore');
                await configuration.update('rootDirectory', selectedPath, vscode.ConfigurationTarget.Workspace);

                // Update both prompt services with new directory
                await this.promptService.updateConfig({ rootDirectory: selectedPath });
                await this.promptService.refreshPrompts();

                // Show success message
                vscode.window.showInformationMessage(`Prompt store directory set to: ${selectedPath}`);

                // Send updated configuration and prompts to webview
                setTimeout(async () => {
                    await this.sendInitialData();
                }, 500); // Give time for the config to propagate

                this.logger.info('✅ Directory configuration completed successfully');
            } else {
                this.logger.info('📁 Directory selection cancelled by user');
            }
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('❌ Failed to configure directory', { error: errorMessage });

            vscode.window.showErrorMessage(`Failed to configure directory: ${errorMessage}`);

            this.sendToWebview({
                type: 'showError',
                error: `Failed to configure directory: ${errorMessage}`
            });
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
        const config = await this.promptService.getConfig();
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
            await this.promptService.refreshPrompts();
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
            await this.invalidateCache();
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
                await this.promptService.refreshPrompts();
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
                await this.promptService.refreshPrompts();

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
