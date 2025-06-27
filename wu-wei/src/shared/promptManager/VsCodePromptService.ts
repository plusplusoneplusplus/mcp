import * as vscode from 'vscode';
import { PromptService, PromptUsageContext, VariableResolutionOptions, PromptParameter } from './types';
import { Prompt, PromptStoreConfig, SearchFilter } from '../../promptStore/types';
import { PromptManager } from '../../promptStore/PromptManager';
import { VariableResolver } from './utils/variableResolver';
import { PromptRenderer } from './utils/promptRenderer';
import { PromptValidators } from './utils/validators';

export class VsCodePromptService implements PromptService {
    private context: vscode.ExtensionContext;
    private promptManager: PromptManager;
    private variableResolver: VariableResolver;
    private promptRenderer: PromptRenderer;
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
            vscode.workspace.onDidChangeConfiguration((event) => {
                if (event.affectsConfiguration('wu-wei.promptStore')) {
                    this.handleConfigurationChange();
                }
            })
        );
    }

    private async handleConfigurationChange(): Promise<void> {
        try {
            // Refresh prompts after configuration change
            await this.promptManager.refreshPrompts();

            // Fire config changed event
            const config = await this.getConfig();
            this._onConfigChanged.fire(config);
        } catch (error) {
            console.error('Failed to handle configuration change:', error);
        }
    }

    private extractParameters(prompt: Prompt): PromptParameter[] {
        const parameters: PromptParameter[] = [];

        // Extract variables from content
        const variables = this.variableResolver.extractVariables(prompt.content);

        // Check if prompt metadata has parameter definitions
        const metadataParams = (prompt.metadata as any).parameters as PromptParameter[] | undefined;

        if (metadataParams && Array.isArray(metadataParams)) {
            // Use defined parameters
            return metadataParams;
        }

        // Generate basic parameters from variables
        for (const variable of variables) {
            parameters.push({
                name: variable,
                type: 'string',
                description: `Variable: ${variable}`,
                required: true
            });
        }

        return parameters;
    }

    private generateUsageInstructions(parameters: PromptParameter[]): string {
        if (parameters.length === 0) {
            return 'This prompt has no variables and can be used directly.';
        }

        const instructions = [
            'This prompt requires the following variables:',
            ...parameters.map(param => {
                const required = param.required ? ' (required)' : ' (optional)';
                const type = param.type !== 'string' ? ` [${param.type}]` : '';
                const description = param.description ? `: ${param.description}` : '';
                return `• {{${param.name}}}${type}${required}${description}`;
            })
        ];

        return instructions.join('\n');
    }
} 