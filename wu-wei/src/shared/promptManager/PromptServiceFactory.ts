import * as vscode from 'vscode';
import { PromptService } from './types';
import { PromptManager, PromptManagerServiceAdapter } from '../../promptStore/index';

export class PromptServiceFactory {
    private static instance: PromptService | null = null;
    private static context: vscode.ExtensionContext | null = null;

    /**
     * Create or get the singleton PromptService instance
     */
    static createService(context: vscode.ExtensionContext, config?: any): PromptService {
        if (!this.instance) {
            this.context = context;

            // If no config provided, get it from VS Code settings
            if (!config) {
                const { ConfigurationManager } = require('../../promptStore/ConfigurationManager');
                const configManager = new ConfigurationManager(context);
                config = configManager.getConfig();
            }

            const promptManager = new PromptManager(config);
            this.instance = new PromptManagerServiceAdapter(promptManager);
        }
        return this.instance;
    }

    /**
     * Get the existing PromptService instance
     */
    static getInstance(): PromptService | null {
        return this.instance;
    }

    /**
     * Initialize the service if it exists
     */
    static async initialize(): Promise<void> {
        if (this.instance) {
            await this.instance.initialize();
        }
    }

    /**
     * Dispose of the service instance
     */
    static dispose(): void {
        if (this.instance) {
            this.instance.dispose();
            this.instance = null;
            this.context = null;
        }
    }

    /**
     * Check if service is initialized
     */
    static isInitialized(): boolean {
        return this.instance !== null;
    }

    /**
     * Get the VS Code extension context
     */
    static getContext(): vscode.ExtensionContext | null {
        return this.context;
    }

    /**
     * Force recreation of the service (useful for testing)
     */
    static reset(context?: vscode.ExtensionContext): void {
        this.dispose();
        if (context) {
            this.createService(context);
        }
    }
} 