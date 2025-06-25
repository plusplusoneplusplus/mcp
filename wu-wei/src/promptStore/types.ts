/**
 * TypeScript interfaces and types for the Prompt Store feature
 * Following wu wei principles: simple, clear, naturally flowing types
 */

/**
 * Represents a parameter definition in a prompt
 */
export interface ParameterDef {
    name: string;
    type: 'string' | 'number' | 'boolean' | 'array' | 'object';
    required: boolean;
    description?: string;
    defaultValue?: any;
    validation?: {
        pattern?: string;
        min?: number;
        max?: number;
        options?: string[];
    };
}

/**
 * Metadata extracted from prompt file frontmatter
 */
export interface PromptMetadata {
    title: string;
    description?: string;
    category?: string;
    tags?: string[];
    author?: string;
    version?: string;
    created?: Date;
    modified?: Date;
    parameters?: ParameterDef[];
    examples?: Array<{
        name: string;
        description?: string;
        input: Record<string, any>;
    }>;
    model?: {
        preferred?: string;
        temperature?: number;
        maxTokens?: number;
    };
}

/**
 * Represents a complete prompt with metadata and content
 */
export interface Prompt {
    id: string;
    filePath: string;
    fileName: string;
    metadata: PromptMetadata;
    content: string;
    lastModified: Date;
    isValid: boolean;
    validationErrors?: string[];
}

/**
 * Configuration for the Prompt Store
 */
export interface PromptStoreConfig {
    watchPaths: string[];
    filePatterns: string[];
    excludePatterns: string[];
    autoRefresh: boolean;
    refreshInterval: number;
    enableCache: boolean;
    maxCacheSize: number;
    sortBy: 'name' | 'modified' | 'category' | 'author';
    sortOrder: 'asc' | 'desc';
    showCategories: boolean;
    showTags: boolean;
    enableSearch: boolean;
}

/**
 * Events emitted by the file watcher
 */
export interface FileWatcherEvent {
    type: 'add' | 'change' | 'unlink' | 'error';
    filePath: string;
    timestamp: Date;
    details?: any;
}

/**
 * Search filter options
 */
export interface SearchFilter {
    query?: string;
    category?: string;
    tags?: string[];
    author?: string;
    hasParameters?: boolean;
    modifiedAfter?: Date;
    modifiedBefore?: Date;
}

/**
 * Prompt validation result
 */
export interface ValidationResult {
    isValid: boolean;
    errors: ValidationError[];
    warnings: ValidationWarning[];
}

export interface ValidationError {
    field: string;
    message: string;
    severity: 'error' | 'warning';
}

export interface ValidationWarning {
    field: string;
    message: string;
    suggestion?: string;
}

/**
 * Webview message types for communication between extension and webview
 */
export interface WebviewMessage {
    type: 'getPrompts' | 'searchPrompts' | 'selectPrompt' | 'refreshPrompts' | 'updateConfig';
    payload?: any;
}

export interface WebviewResponse {
    type: 'promptsLoaded' | 'promptSelected' | 'error' | 'configUpdated';
    payload?: any;
    error?: string;
}

/**
 * Export utilities for working with prompts
 */
export interface ExportOptions {
    format: 'json' | 'yaml' | 'markdown';
    includeMetadata: boolean;
    includeContent: boolean;
    filterOptions?: SearchFilter;
}
