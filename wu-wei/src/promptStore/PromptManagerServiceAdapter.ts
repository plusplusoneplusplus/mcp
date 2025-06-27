/**
 * PromptManager Service Adapter - Bridge between legacy PromptManager and PromptService interface
 * Following wu wei principles: seamless adaptation without disruption
 */

import * as vscode from 'vscode';
import { PromptManager } from './PromptManager';
import { Prompt, PromptStoreConfig, SearchFilter } from './types';
import {
    PromptService,
    PromptUsageContext,
    PromptParameter,
    ValidationError,
    VariableResolutionOptions
} from '../shared/promptManager/types';
import { VariableResolver } from '../shared/promptManager/utils/variableResolver';
import { PromptRenderer } from '../shared/promptManager/utils/promptRenderer';

export class PromptManagerServiceAdapter implements PromptService {
    private promptManager: PromptManager;
    private variableResolver: VariableResolver;
    private promptRenderer: PromptRenderer;
    private sharedEventEmitter: vscode.EventEmitter<any>;

    // Event emitters for PromptService interface
    private _onPromptSelected = new vscode.EventEmitter<PromptUsageContext>();
    private _onConfigChanged = new vscode.EventEmitter<PromptStoreConfig>();

    // Public events
    public readonly onPromptsChanged: vscode.Event<Prompt[]>;
    public readonly onPromptSelected: vscode.Event<PromptUsageContext>;
    public readonly onConfigChanged: vscode.Event<PromptStoreConfig>;

    constructor(promptManager: PromptManager) {
        this.promptManager = promptManager;
        this.variableResolver = new VariableResolver();
        this.promptRenderer = new PromptRenderer();
        this.sharedEventEmitter = new vscode.EventEmitter<any>();

        // Bridge events from PromptManager
        this.onPromptsChanged = this.promptManager.onPromptsChanged;
        this.onPromptSelected = this._onPromptSelected.event;
        this.onConfigChanged = this._onConfigChanged.event;

        this.setupEventBridge();
    }

    /**
     * Initialize the service (delegates to PromptManager)
     */
    async initialize(): Promise<void> {
        await this.promptManager.initialize();
    }

    /**
     * Get all prompts (async wrapper over sync method)
     */
    async getAllPrompts(): Promise<Prompt[]> {
        return Promise.resolve(this.promptManager.getAllPrompts());
    }

    /**
     * Get a prompt by ID (async wrapper over sync method)
     */
    async getPrompt(id: string): Promise<Prompt | null> {
        const prompt = this.promptManager.getPrompt(id);
        return Promise.resolve(prompt || null);
    }

    /**
     * Search prompts (enhanced version with async support)
     */
    async searchPrompts(query: string, filters?: SearchFilter): Promise<Prompt[]> {
        const searchFilter: SearchFilter = {
            query,
            ...filters
        };
        return Promise.resolve(this.promptManager.searchPrompts(searchFilter));
    }

    /**
     * Select prompt for use with enhanced context
     */
    async selectPromptForUse(promptId: string): Promise<PromptUsageContext> {
        const prompt = await this.getPrompt(promptId);
        if (!prompt) {
            throw new Error(`Prompt not found: ${promptId}`);
        }

        const parameters = this.extractPromptParameters(prompt);
        const usageContext: PromptUsageContext = {
            prompt,
            renderedContent: prompt.content,
            variables: {},
            metadata: {
                ...prompt.metadata,
                parameters,
                usageInstructions: this.generateUsageInstructions(parameters)
            }
        };

        this._onPromptSelected.fire(usageContext);
        return usageContext;
    }

    /**
     * Render prompt with variables
     */
    async renderPromptWithVariables(
        promptId: string,
        variables: Record<string, any>
    ): Promise<string> {
        const prompt = await this.getPrompt(promptId);
        if (!prompt) {
            throw new Error(`Prompt not found: ${promptId}`);
        }

        const parameters = this.extractPromptParameters(prompt);
        const validationErrors = this.variableResolver.validateVariables(
            prompt.content,
            variables,
            parameters
        );

        if (validationErrors.some(e => e.severity === 'error')) {
            throw new Error(`Variable validation failed: ${validationErrors.map(e => e.message).join(', ')}`);
        }

        return this.promptRenderer.render(prompt.content, variables, {
            defaultValues: this.getDefaultVariableValues(parameters)
        });
    }

    /**
     * Get configuration (async wrapper over sync method)
     */
    async getConfig(): Promise<PromptStoreConfig> {
        return Promise.resolve(this.promptManager.getConfig());
    }

    /**
     * Update configuration (async wrapper over sync method)
     */
    async updateConfig(config: Partial<PromptStoreConfig>): Promise<void> {
        this.promptManager.updateConfig(config);
        this._onConfigChanged.fire(this.promptManager.getConfig());
        return Promise.resolve();
    }

    /**
     * Dispose of resources
     */
    dispose(): void {
        this.promptManager.dispose();
        this._onPromptSelected.dispose();
        this._onConfigChanged.dispose();
        this.sharedEventEmitter.dispose();
    }

    // ===== Enhanced Methods for Better Prompt Usage =====

    /**
     * Render prompt with validation
     */
    async renderPromptWithValidation(
        promptId: string,
        variables: Record<string, any>,
        options: VariableResolutionOptions = {}
    ): Promise<{ content: string; errors: ValidationError[] }> {
        const prompt = await this.getPrompt(promptId);
        if (!prompt) {
            throw new Error(`Prompt not found: ${promptId}`);
        }

        const parameters = this.extractPromptParameters(prompt);
        return this.promptRenderer.renderWithValidation(
            prompt.content,
            variables,
            parameters,
            options
        );
    }

    /**
     * Preview prompt rendering
     */
    async previewPromptRender(
        promptId: string,
        variables: Record<string, any>
    ): Promise<{ preview: string; missingVariables: string[] }> {
        const prompt = await this.getPrompt(promptId);
        if (!prompt) {
            throw new Error(`Prompt not found: ${promptId}`);
        }

        return this.promptRenderer.previewRender(prompt.content, variables);
    }

    /**
     * Get prompt variables
     */
    async getPromptVariables(promptId: string): Promise<string[]> {
        const prompt = await this.getPrompt(promptId);
        if (!prompt) {
            throw new Error(`Prompt not found: ${promptId}`);
        }
        return this.variableResolver.extractVariables(prompt.content);
    }

    // ===== Private Helper Methods =====

    /**
     * Setup event bridge between PromptManager and PromptService
     */
    private setupEventBridge(): void {
        // Bridge existing events to new interface
        this.promptManager.onPromptsChanged(() => {
            // Events are already bridged through the public property
        });
    }

    /**
     * Extract prompt parameters from metadata or auto-detect from content
     */
    private extractPromptParameters(prompt: Prompt): PromptParameter[] {
        const parameters: PromptParameter[] = [];

        // Extract from metadata if defined
        const metadataParams = (prompt.metadata as any).parameters as PromptParameter[] | undefined;
        if (metadataParams && Array.isArray(metadataParams)) {
            return metadataParams;
        }

        // Auto-extract from content
        const variables = this.variableResolver.extractVariables(prompt.content);

        for (const variable of variables) {
            parameters.push({
                name: variable,
                type: 'string',
                required: true,
                description: `Parameter for ${variable}`,
                placeholder: `Enter value for ${variable}...`
            });
        }

        return parameters;
    }

    /**
     * Generate usage instructions for prompt parameters
     */
    private generateUsageInstructions(parameters: PromptParameter[]): string {
        if (parameters.length === 0) {
            return 'This prompt has no variables and can be used directly.';
        }

        const required = parameters.filter(p => p.required);
        const optional = parameters.filter(p => !p.required);

        let instructions = 'This prompt requires the following variables:\n\n';

        if (required.length > 0) {
            instructions += 'Required:\n';
            required.forEach(p => {
                instructions += `- ${p.name}: ${p.description || 'No description'}\n`;
            });
        }

        if (optional.length > 0) {
            instructions += '\nOptional:\n';
            optional.forEach(p => {
                instructions += `- ${p.name}: ${p.description || 'No description'}\n`;
            });
        }

        return instructions;
    }

    /**
     * Get default variable values from parameters
     */
    private getDefaultVariableValues(parameters: PromptParameter[]): Record<string, any> {
        const defaults: Record<string, any> = {};

        for (const param of parameters) {
            if (param.defaultValue !== undefined) {
                defaults[param.name] = param.defaultValue;
            }
        }

        return defaults;
    }
} 