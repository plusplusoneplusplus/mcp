/**
 * Configuration Manager for Wu Wei Prompt Store
 * Handles VS Code settings, validation, and persistence
 * Following wu wei principles: simple, reliable, naturally flowing configuration
 */

import * as vscode from 'vscode';
import * as fs from 'fs/promises';
import * as path from 'path';
import { logger } from '../logger';

export interface PromptStoreConfig {
    rootDirectory: string;
    autoRefresh: boolean;
    showMetadataTooltips: boolean;
    enableTemplates: boolean;
    metadataSchema: MetadataSchemaConfig;
    fileWatcher: FileWatcherConfig;
}

export interface MetadataSchemaConfig {
    requireTitle: boolean;
    requireDescription: boolean;
    allowCustomFields: boolean;
}

export interface FileWatcherConfig {
    enabled: boolean;
    debounceMs: number;
    maxDepth: number;
    ignorePatterns: string[];
    usePolling: boolean;
    pollingInterval: number;
}

export interface ValidationResult {
    isValid: boolean;
    errors: string[];
    warnings: string[];
}

export interface ConfigError {
    type: 'DIRECTORY_NOT_FOUND' | 'PERMISSION_DENIED' | 'NETWORK_ERROR' | 'INVALID_CONFIG' | 'UNKNOWN_ERROR';
    message: string;
    details?: any;
}

/**
 * Manages configuration for the Prompt Store
 */
export class ConfigurationManager {
    private context: vscode.ExtensionContext;
    private disposables: vscode.Disposable[] = [];
    private readonly CONFIG_PREFIX = 'wu-wei.promptStore';

    // Event emitters for configuration changes
    private readonly _onConfigurationChanged = new vscode.EventEmitter<PromptStoreConfig>();
    public readonly onConfigurationChanged = this._onConfigurationChanged.event;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.setupConfigurationWatcher();
        logger.info('ConfigurationManager initialized');
    }

    /**
     * Get the current configuration
     */
    getConfig(): PromptStoreConfig {
        const config = vscode.workspace.getConfiguration(this.CONFIG_PREFIX);

        const rootDirectory = this.resolveRootDirectory(config.get('rootDirectory', ''));

        return {
            rootDirectory,
            autoRefresh: config.get('autoRefresh', true),
            showMetadataTooltips: config.get('showMetadataTooltips', true),
            enableTemplates: config.get('enableTemplates', true),
            metadataSchema: this.getMetadataSchemaConfig(),
            fileWatcher: this.getFileWatcherConfig(config)
        };
    }

    /**
     * Update configuration with new values
     */
    async updateConfig(updates: Partial<PromptStoreConfig>): Promise<void> {
        try {
            const config = vscode.workspace.getConfiguration(this.CONFIG_PREFIX);

            for (const [key, value] of Object.entries(updates)) {
                if (key === 'metadataSchema' || key === 'fileWatcher') {
                    // Handle nested objects
                    if (key === 'fileWatcher' && value) {
                        const fileWatcher = value as FileWatcherConfig;
                        await config.update('fileWatcher.enabled', fileWatcher.enabled);
                        await config.update('fileWatcher.debounceMs', fileWatcher.debounceMs);
                        await config.update('fileWatcher.maxDepth', fileWatcher.maxDepth);
                        await config.update('fileWatcher.ignorePatterns', fileWatcher.ignorePatterns);
                        await config.update('fileWatcher.usePolling', fileWatcher.usePolling);
                        await config.update('fileWatcher.pollingInterval', fileWatcher.pollingInterval);
                    }
                } else {
                    await config.update(key, value);
                }
            }

            logger.info('Configuration updated', { updates });
        } catch (error) {
            logger.error('Failed to update configuration', error);
            throw error;
        }
    }

    /**
     * Reset configuration to defaults
     */
    async resetToDefaults(): Promise<void> {
        try {
            const config = vscode.workspace.getConfiguration(this.CONFIG_PREFIX);

            // Reset all settings to undefined to use defaults
            await config.update('rootDirectory', undefined);
            await config.update('autoRefresh', undefined);
            await config.update('showMetadataTooltips', undefined);
            await config.update('enableTemplates', undefined);
            await config.update('fileWatcher.enabled', undefined);
            await config.update('fileWatcher.debounceMs', undefined);
            await config.update('fileWatcher.maxDepth', undefined);
            await config.update('fileWatcher.ignorePatterns', undefined);
            await config.update('fileWatcher.usePolling', undefined);
            await config.update('fileWatcher.pollingInterval', undefined);

            logger.info('Configuration reset to defaults');
        } catch (error) {
            logger.error('Failed to reset configuration', error);
            throw error;
        }
    }

    /**
     * Validate the current configuration
     */
    async validateConfig(config?: PromptStoreConfig): Promise<ValidationResult> {
        const currentConfig = config || this.getConfig();
        const errors: string[] = [];
        const warnings: string[] = [];

        // Validate root directory
        if (currentConfig.rootDirectory) {
            try {
                const dirValidation = await this.validateDirectory(currentConfig.rootDirectory);
                if (!dirValidation.isValid) {
                    errors.push(...dirValidation.errors);
                }
                warnings.push(...dirValidation.warnings);
            } catch (error) {
                errors.push(`Failed to validate directory: ${error}`);
            }
        } else {
            warnings.push('No root directory configured for prompt store');
        }

        // Validate file watcher settings
        if (currentConfig.fileWatcher.debounceMs < 100 || currentConfig.fileWatcher.debounceMs > 5000) {
            errors.push('File watcher debounce must be between 100 and 5000 milliseconds');
        }

        if (currentConfig.fileWatcher.maxDepth < 1 || currentConfig.fileWatcher.maxDepth > 50) {
            errors.push('File watcher max depth must be between 1 and 50');
        }

        if (currentConfig.fileWatcher.usePolling &&
            (currentConfig.fileWatcher.pollingInterval < 100 || currentConfig.fileWatcher.pollingInterval > 10000)) {
            errors.push('Polling interval must be between 100 and 10000 milliseconds');
        }

        return {
            isValid: errors.length === 0,
            errors,
            warnings
        };
    }

    /**
     * Select a directory using the native OS dialog
     */
    async selectDirectory(): Promise<string | undefined> {
        try {
            const result = await vscode.window.showOpenDialog({
                canSelectFiles: false,
                canSelectFolders: true,
                canSelectMany: false,
                title: 'Select Prompt Store Directory',
                openLabel: 'Select Directory'
            });

            if (result && result[0]) {
                const selectedPath = result[0].fsPath;
                logger.info('Directory selected', { path: selectedPath });

                // Validate directory
                const validation = await this.validateDirectory(selectedPath);
                if (!validation.isValid) {
                    const errorMessage = `Invalid directory: ${validation.errors.join(', ')}`;
                    vscode.window.showErrorMessage(errorMessage);
                    return undefined;
                }

                return selectedPath;
            }

            return undefined;
        } catch (error) {
            logger.error('Failed to select directory', error);
            const errorMessage = this.getConfigErrorMessage({
                type: 'UNKNOWN_ERROR',
                message: `Failed to select directory: ${error}`
            });
            vscode.window.showErrorMessage(errorMessage);
            return undefined;
        }
    }

    /**
     * Set the root directory and update configuration
     */
    async setRootDirectory(directory: string): Promise<void> {
        try {
            const validation = await this.validateDirectory(directory);
            if (!validation.isValid) {
                throw new Error(`Invalid directory: ${validation.errors.join(', ')}`);
            }

            await this.updateConfig({ rootDirectory: directory });
            logger.info('Root directory updated', { directory });
        } catch (error) {
            logger.error('Failed to set root directory', { directory, error });
            throw error;
        }
    }

    /**
     * Validate a directory path
     */
    private async validateDirectory(dirPath: string): Promise<ValidationResult> {
        const errors: string[] = [];
        const warnings: string[] = [];

        try {
            const stats = await fs.stat(dirPath);

            if (!stats.isDirectory()) {
                errors.push('Path is not a directory');
                return { isValid: false, errors, warnings };
            }

            // Test read permissions
            try {
                await fs.access(dirPath, fs.constants.R_OK);
            } catch {
                errors.push('Directory is not readable');
            }

            // Test write permissions
            try {
                await fs.access(dirPath, fs.constants.W_OK);
            } catch {
                warnings.push('Directory is not writable - you will not be able to create new prompts');
            }

            // Check if directory contains prompt files
            try {
                const files = await fs.readdir(dirPath);
                const promptFiles = files.filter(file =>
                    file.endsWith('.md') || file.endsWith('.txt') || file.endsWith('.prompt')
                );

                if (promptFiles.length === 0) {
                    warnings.push('Directory does not contain any prompt files');
                }
            } catch {
                warnings.push('Unable to read directory contents');
            }

        } catch (error: any) {
            if (error.code === 'ENOENT') {
                errors.push('Directory does not exist');
            } else if (error.code === 'EACCES') {
                errors.push('Insufficient permissions to access directory');
            } else if (error.code === 'ENOTDIR') {
                errors.push('Path is not a directory');
            } else {
                errors.push(`Access error: ${error.message}`);
            }
        }

        return {
            isValid: errors.length === 0,
            errors,
            warnings
        };
    }

    /**
     * Get metadata schema configuration with defaults
     */
    private getMetadataSchemaConfig(): MetadataSchemaConfig {
        return {
            requireTitle: true,
            requireDescription: false,
            allowCustomFields: true
        };
    }

    /**
     * Get file watcher configuration from VS Code settings
     */
    private getFileWatcherConfig(config: vscode.WorkspaceConfiguration): FileWatcherConfig {
        return {
            enabled: config.get('fileWatcher.enabled', true),
            debounceMs: config.get('fileWatcher.debounceMs', 500),
            maxDepth: config.get('fileWatcher.maxDepth', 10),
            ignorePatterns: config.get('fileWatcher.ignorePatterns', ['*.tmp', '*.swp', '*~', '.git/**']),
            usePolling: config.get('fileWatcher.usePolling', false),
            pollingInterval: config.get('fileWatcher.pollingInterval', 1000)
        };
    }

    /**
     * Resolve root directory path, handling relative paths and workspace folders
     */
    private resolveRootDirectory(rootDir: string): string {
        if (!rootDir) {
            return '';
        }

        // If it's already an absolute path, return as-is
        if (path.isAbsolute(rootDir)) {
            return rootDir;
        }

        // If we have a workspace folder, resolve relative to it
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (workspaceFolder) {
            return path.resolve(workspaceFolder.uri.fsPath, rootDir);
        }

        // Otherwise, return as-is (might be relative to home or current directory)
        return rootDir;
    }

    /**
     * Set up configuration change watcher
     */
    private setupConfigurationWatcher(): void {
        const disposable = vscode.workspace.onDidChangeConfiguration((event) => {
            if (event.affectsConfiguration(this.CONFIG_PREFIX)) {
                logger.info('Configuration changed, notifying listeners');
                const newConfig = this.getConfig();
                this._onConfigurationChanged.fire(newConfig);
            }
        });

        this.disposables.push(disposable);
    }

    /**
     * Get user-friendly error messages for configuration errors
     */
    private getConfigErrorMessage(error: ConfigError): string {
        switch (error.type) {
            case 'DIRECTORY_NOT_FOUND':
                return 'The selected directory no longer exists. Please choose a new directory.';
            case 'PERMISSION_DENIED':
                return 'Cannot access the directory. Please check permissions or select a different directory.';
            case 'NETWORK_ERROR':
                return 'Network drive is not accessible. Please ensure the drive is connected.';
            case 'INVALID_CONFIG':
                return `Invalid configuration: ${error.message}`;
            default:
                return `Configuration error: ${error.message}`;
        }
    }

    /**
     * Dispose of resources
     */
    dispose(): void {
        this.disposables.forEach(d => d.dispose());
        this._onConfigurationChanged.dispose();
        logger.info('ConfigurationManager disposed');
    }
}
