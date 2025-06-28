import * as vscode from 'vscode';

// Re-export existing types from promptStore for compatibility
export { Prompt, PromptMetadata, SearchFilter, PromptStoreConfig } from '../../promptStore/types';

// Re-export TSX-related types for convenience
export * from './tsx/types';

export interface PromptParameter {
    name: string;
    type: 'string' | 'number' | 'boolean' | 'select' | 'multiline' | 'file';
    description?: string;
    required?: boolean;
    defaultValue?: any;
    options?: string[]; // for select type
    placeholder?: string;
    validation?: {
        pattern?: string;
        minLength?: number;
        maxLength?: number;
        min?: number;
        max?: number;
    };
}

export interface PromptUsageContext {
    prompt: import('../../promptStore/types').Prompt;
    renderedContent: string;
    variables: Record<string, any>;
    metadata: import('../../promptStore/types').PromptMetadata & {
        parameters?: PromptParameter[];
        usageInstructions?: string;
        category?: string;
        tags?: string[];
    };
    renderingErrors?: ValidationError[];
}

export interface ValidationError {
    field: string;
    message: string;
    severity: 'error' | 'warning' | 'info';
}

export interface VariableResolutionOptions {
    strictMode?: boolean;
    allowUndefined?: boolean;
    defaultValues?: Record<string, any>;
    resolver?: (variable: string) => any;
}

// TSX-related interfaces for PromptService integration
export interface BasePromptElementProps {
    priority?: number;
    flexGrow?: number;
    maxTokens?: number;
}

export interface TsxRenderOptions {
    modelMaxPromptTokens?: number;
    tokenBudget?: number;
    model?: vscode.LanguageModelChat;
    enablePrioritization?: boolean;
}

export interface TsxRenderResult {
    messages: vscode.LanguageModelChatMessage[];
    tokenCount: number;
    prunedElements: string[];
    renderingMetadata: {
        totalElements: number;
        includedElements: number;
        priorityLevels: number[];
    };
}

export interface ValidationResult {
    isValid: boolean;
    errors: ValidationError[];
    warnings: ValidationError[];
}

// Type for TSX prompt components
export interface PromptElement<T extends BasePromptElementProps> {
    render(): any;
}

export interface PromptService {
    // Core Operations
    getAllPrompts(): Promise<import('../../promptStore/types').Prompt[]>;
    getPrompt(id: string): Promise<import('../../promptStore/types').Prompt | null>;
    searchPrompts(query: string, filters?: import('../../promptStore/types').SearchFilter): Promise<import('../../promptStore/types').Prompt[]>;
    refreshPrompts(): Promise<void>;

    // Prompt Usage
    selectPromptForUse(promptId: string): Promise<PromptUsageContext>;
    renderPromptWithVariables(
        promptId: string,
        variables: Record<string, any>
    ): Promise<string>;

    // New TSX methods
    renderTsxPrompt<T extends BasePromptElementProps>(
        promptComponent: new (props: T) => PromptElement<T>,
        props: T,
        options?: TsxRenderOptions
    ): Promise<TsxRenderResult>;

    renderPromptWithTokenBudget(
        promptId: string,
        variables: Record<string, any>,
        tokenBudget: number,
        model?: vscode.LanguageModelChat
    ): Promise<vscode.LanguageModelChatMessage[]>;

    validateTsxPrompt<T extends BasePromptElementProps>(
        component: new (props: T) => PromptElement<T>,
        props: T
    ): Promise<ValidationResult>;

    // Configuration
    getConfig(): Promise<import('../../promptStore/types').PromptStoreConfig>;
    updateConfig(config: Partial<import('../../promptStore/types').PromptStoreConfig>): Promise<void>;

    // Events
    onPromptsChanged: vscode.Event<import('../../promptStore/types').Prompt[]>;
    onPromptSelected: vscode.Event<PromptUsageContext>;
    onConfigChanged: vscode.Event<import('../../promptStore/types').PromptStoreConfig>;

    // Lifecycle
    initialize(): Promise<void>;
    dispose(): void;
} 