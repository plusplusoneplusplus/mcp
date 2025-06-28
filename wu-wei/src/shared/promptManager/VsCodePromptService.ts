import * as vscode from 'vscode';
import {
    PromptService,
    PromptUsageContext,
    VariableResolutionOptions,
    PromptParameter,
    BasePromptElementProps,
    TsxRenderOptions,
    TsxRenderResult,
    ValidationResult,
    PromptElement
} from './types';
import { Prompt, PromptStoreConfig, SearchFilter } from '../../promptStore/types';
import { PromptManager } from '../../promptStore/PromptManager';
import { VariableResolver } from './utils/variableResolver';
import { PromptRenderer } from './utils/promptRenderer';
import { PromptValidators } from './utils/validators';
import { TsxRenderer } from './utils/tsxRenderer';
import { TsxValidation } from './utils/tsxValidation';

export class VsCodePromptService implements PromptService {
    private context: vscode.ExtensionContext;
    private promptManager: PromptManager;
    private variableResolver: VariableResolver;
    private promptRenderer: PromptRenderer;
    private tsxRenderer: TsxRenderer;
    private tsxValidation: TsxValidation;
    private disposables: vscode.Disposable[] = [];

    // Event emitters
    private _onPromptsChanged = new vscode.EventEmitter<Prompt[]>();
    private _onPromptSelected = new vscode.EventEmitter<PromptUsageContext>();
    private _onConfigChanged = new vscode.EventEmitter<PromptStoreConfig>();

    // Public events
    public readonly onPromptsChanged: vscode.Event<Prompt[]> = this._onPromptsChanged.event;
    public readonly onPromptSelected: vscode.Event<PromptUsageContext> = this._onPromptSelected.event;
    public readonly onConfigChanged: vscode.Event<PromptStoreConfig> = this._onConfigChanged.event;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.variableResolver = new VariableResolver();
        this.promptRenderer = new PromptRenderer();
        this.tsxRenderer = new TsxRenderer();
        this.tsxValidation = new TsxValidation();

        // Initialize PromptManager with default config
        this.promptManager = new PromptManager();

        this.setupEventHandlers();
    }

    async initialize(): Promise<void> {
        try {
            await this.promptManager.initialize();

            // Fire initial prompts changed event
            const prompts = await this.getAllPrompts();
            this._onPromptsChanged.fire(prompts);

        } catch (error) {
            console.error('Failed to initialize VsCodePromptService:', error);
            throw error;
        }
    }

    async getAllPrompts(): Promise<Prompt[]> {
        return this.promptManager.getAllPrompts();
    }

    async getPrompt(id: string): Promise<Prompt | null> {
        const prompt = this.promptManager.getPrompt(id);
        return prompt || null;
    }

    async searchPrompts(query: string, filters?: SearchFilter): Promise<Prompt[]> {
        const searchFilter: SearchFilter = {
            query,
            ...filters
        };
        return this.promptManager.searchPrompts(searchFilter);
    }

    async refreshPrompts(): Promise<void> {
        await this.promptManager.refreshPrompts();
    }

    async selectPromptForUse(promptId: string): Promise<PromptUsageContext> {
        const prompt = await this.getPrompt(promptId);
        if (!prompt) {
            throw new Error(`Prompt not found: ${promptId}`);
        }

        // Extract parameters from prompt metadata
        const parameters = this.extractParameters(prompt);

        // Create usage context
        const usageContext: PromptUsageContext = {
            prompt,
            renderedContent: prompt.content,
            variables: {},
            metadata: {
                ...prompt.metadata,
                parameters,
                usageInstructions: this.generateUsageInstructions(parameters),
                category: prompt.metadata.category,
                tags: prompt.metadata.tags
            }
        };

        // Fire prompt selected event
        this._onPromptSelected.fire(usageContext);

        return usageContext;
    }

    async renderPromptWithVariables(
        promptId: string,
        variables: Record<string, any>
    ): Promise<string> {
        const prompt = await this.getPrompt(promptId);
        if (!prompt) {
            throw new Error(`Prompt not found: ${promptId}`);
        }

        return this.promptRenderer.render(prompt.content, variables);
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

        // Render the prompt with variables
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

    async getConfig(): Promise<PromptStoreConfig> {
        return this.promptManager.getConfig();
    }

    async updateConfig(config: Partial<PromptStoreConfig>): Promise<void> {
        this.promptManager.updateConfig(config);

        // Fire config changed event
        const newConfig = await this.getConfig();
        this._onConfigChanged.fire(newConfig);
    }

    dispose(): void {
        // Dispose of all event emitters
        this._onPromptsChanged.dispose();
        this._onPromptSelected.dispose();
        this._onConfigChanged.dispose();

        // Dispose of all disposables
        this.disposables.forEach(disposable => disposable.dispose());
        this.disposables = [];

        // Dispose of prompt manager
        this.promptManager.dispose();
    }

    /**
     * Enhanced methods for better prompt usage
     */

    async renderPromptWithValidation(
        promptId: string,
        variables: Record<string, any>,
        options: VariableResolutionOptions = {}
    ): Promise<{ content: string; errors: import('./types').ValidationError[] }> {
        const prompt = await this.getPrompt(promptId);
        if (!prompt) {
            throw new Error(`Prompt not found: ${promptId}`);
        }

        const parameters = this.extractParameters(prompt);
        return this.promptRenderer.renderWithValidation(
            prompt.content,
            variables,
            parameters,
            options
        );
    }

    async validatePrompt(promptId: string): Promise<import('./types').ValidationError[]> {
        const prompt = await this.getPrompt(promptId);
        if (!prompt) {
            throw new Error(`Prompt not found: ${promptId}`);
        }

        const parameters = this.extractParameters(prompt);
        return PromptValidators.validatePrompt(prompt.content, parameters);
    }

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

    getPromptVariables(promptId: string): Promise<string[]> {
        return this.getPrompt(promptId).then(prompt => {
            if (!prompt) {
                throw new Error(`Prompt not found: ${promptId}`);
            }
            return this.variableResolver.extractVariables(prompt.content);
        });
    }

    /**
     * Private helper methods
     */

    private setupEventHandlers(): void {
        // Listen to prompt manager events
        this.disposables.push(
            this.promptManager.onPromptsChanged((prompts) => {
                this._onPromptsChanged.fire(prompts);
            })
        );

        // Listen to configuration changes
        this.disposables.push(
            vscode.workspace.onDidChangeConfiguration((e) => {
                if (e.affectsConfiguration('wuwei.prompts')) {
                    this.handleConfigurationChange();
                }
            })
        );
    }

    private async handleConfigurationChange(): Promise<void> {
        try {
            await this.refreshPrompts();
            const newConfig = await this.getConfig();
            this._onConfigChanged.fire(newConfig);
        } catch (error) {
            console.error('Failed to handle configuration change:', error);
        }
    }

    private extractParameters(prompt: Prompt): PromptParameter[] {
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
} 