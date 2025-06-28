/**
 * PromptManager Service Adapter - Bridge between legacy PromptManager and PromptService interface
 * Following wu wei principles: seamless adaptation without disruption
 */

import * as vscode from 'vscode';
import { BasePromptElementProps, PromptElement } from '@vscode/prompt-tsx';
import { PromptManager } from './PromptManager';
import { Prompt, PromptStoreConfig, SearchFilter } from './types';
import {
    PromptService,
    PromptUsageContext,
    PromptParameter,
    ValidationError,
    VariableResolutionOptions,
    TsxRenderOptions,
    TsxRenderResult,
    ValidationResult
} from '../shared/promptManager/types';
import { VariableResolver } from '../shared/promptManager/utils/variableResolver';
import { PromptRenderer } from '../shared/promptManager/utils/promptRenderer';
import { TsxRenderer } from '../shared/promptManager/utils/tsxRenderer';
import { TsxValidation } from '../shared/promptManager/utils/tsxValidation';

export class PromptManagerServiceAdapter implements PromptService {
    private promptManager: PromptManager;
    private variableResolver: VariableResolver;
    private promptRenderer: PromptRenderer;
    private tsxRenderer: TsxRenderer;
    private tsxValidation: TsxValidation;
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
        this.tsxRenderer = new TsxRenderer();
        this.tsxValidation = new TsxValidation();
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
     * Refresh prompts (async wrapper over sync method)
     */
    async refreshPrompts(): Promise<void> {
        await this.promptManager.refreshPrompts();
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

    // ===== New TSX Methods =====

    /**
     * Render a TSX prompt component
     */
    async renderTsxPrompt<T extends BasePromptElementProps>(
        promptComponent: new (props: T) => PromptElement<T>,
        props: T,
        options?: TsxRenderOptions
    ): Promise<TsxRenderResult> {
        try {
            return await this.tsxRenderer.renderTsxPrompt(promptComponent, props, options);
        } catch (error) {
            throw new Error(`TSX prompt rendering failed: ${error instanceof Error ? error.message : String(error)}`);
        }
    }

    /**
     * Render a prompt with token budget management
     */
    async renderPromptWithTokenBudget(
        promptId: string,
        variables: Record<string, any>,
        tokenBudget: number,
        model?: vscode.LanguageModelChat
    ): Promise<vscode.LanguageModelChatMessage[]> {
        const prompt = await this.getPrompt(promptId);
        if (!prompt) {
            throw new Error(`Prompt not found: ${promptId}`);
        }

        // For now, render as string and convert to messages
        const renderedContent = await this.renderPromptWithVariables(promptId, variables);

        // Create a simple message array
        const messages: vscode.LanguageModelChatMessage[] = [{
            role: vscode.LanguageModelChatMessageRole.User,
            content: [{ value: renderedContent, text: renderedContent } as vscode.LanguageModelTextPart],
            name: `prompt-${promptId}`
        }];

        // Check token budget (simplified implementation)
        const tokenCount = Math.ceil(renderedContent.length / 4); // Rough estimate
        if (tokenCount > tokenBudget) {
            throw new Error(`Rendered prompt exceeds token budget: ${tokenCount} > ${tokenBudget}`);
        }

        return messages;
    }

    /**
     * Validate a TSX prompt component
     */
    async validateTsxPrompt<T extends BasePromptElementProps>(
        component: new (props: T) => PromptElement<T>,
        props: T
    ): Promise<ValidationResult> {
        try {
            return await this.tsxRenderer.validateTsxPrompt(component, props);
        } catch (error) {
            return {
                isValid: false,
                errors: [{
                    field: 'validation',
                    message: `TSX validation failed: ${error instanceof Error ? error.message : String(error)}`,
                    severity: 'error'
                }],
                warnings: []
            };
        }
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
     * Get variables used in a prompt
     */
    async getPromptVariables(promptId: string): Promise<string[]> {
        const prompt = await this.getPrompt(promptId);
        if (!prompt) {
            throw new Error(`Prompt not found: ${promptId}`);
        }

        return this.variableResolver.extractVariables(prompt.content);
    }

    // ===== Private Helper Methods =====

    private setupEventBridge(): void {
        // Bridge events from PromptManager to PromptService interface
        this.promptManager.onPromptsChanged((prompts) => {
            // Event is already bridged via public property
        });
    }

    private extractPromptParameters(prompt: Prompt): PromptParameter[] {
        // Extract variables from prompt content
        const variables = this.variableResolver.extractVariables(prompt.content);

        return variables.map(variable => ({
            name: variable,
            type: 'string' as const,
            description: `Variable: ${variable}`,
            required: true,
            defaultValue: undefined
        }));
    }

    private generateUsageInstructions(parameters: PromptParameter[]): string {
        if (parameters.length === 0) {
            return 'This prompt has no variables and can be used as-is.';
        }

        const variableList = parameters.map(p => `- ${p.name}: ${p.description || 'No description'}`).join('\n');
        return `This prompt requires the following variables:\n${variableList}`;
    }

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