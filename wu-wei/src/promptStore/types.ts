/**
 * TypeScript interfaces and types for the Prompt Store feature
 * Following wu wei principles: simple, clear, naturally flowing types
 */

/**
 * Metadata extracted from prompt file frontmatter
 */
export interface PromptMetadata {
    title: string;
    description?: string;
    category?: string;
    tags?: string[];
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
    rootDirectory: string;
    watchPaths: string[];
    filePatterns: string[];
    excludePatterns: string[];
    autoRefresh: boolean;
    refreshInterval: number;
    enableCache: boolean;
    maxCacheSize: number;
    sortBy: 'name' | 'modified' | 'category';
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
 * Configuration for the file watcher
 */
export interface FileWatcherConfig {
    enabled: boolean;
    debounceMs: number;
    maxDepth: number;
    followSymlinks: boolean;
    ignorePatterns: string[];
    usePolling: boolean;
    pollingInterval: number;
}

/**
 * File watcher event types
 */
export type FileWatcherEventType = 'fileAdded' | 'fileChanged' | 'fileDeleted' | 'directoryAdded' | 'directoryDeleted' | 'error';

/**
 * File watcher event callback type
 */
export type FileWatcherEventCallback = (filePath: string, details?: any) => void;

/**
 * Search filter options
 */
export interface SearchFilter {
    query?: string;
    category?: string;
    tags?: string[];
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
 * Result of parsing a prompt file
 */
export interface ParsedPrompt {
    success: boolean;
    prompt?: Prompt;
    metadata?: PromptMetadata;
    content?: string;
    errors: ValidationError[];
    warnings: ValidationWarning[];
}

/**
 * Validation rule definition
 */
export interface ValidationRule {
    field: string;
    type: 'string' | 'array' | 'object' | 'date' | 'boolean' | 'number';
    required?: boolean;
    validator?: (value: any) => boolean;
    message?: string;
}

/**
 * Cache entry for parsed metadata
 */
export interface MetadataCacheEntry {
    prompt: Prompt;
    metadata: PromptMetadata;
    content: string;
    lastModified: number;
    filePath: string;
    errors: ValidationError[];
    warnings: ValidationWarning[];
}

/**
 * Webview message types for communication between extension and webview
 */
export interface WebviewMessage {
    type: 'webviewReady' | 'configureDirectory' | 'openPrompt' | 'createNewPrompt' | 'refreshStore' |
    'getPrompts' | 'searchPrompts' | 'selectPrompt' | 'refreshPrompts' | 'updateConfig' |
    'deletePrompt' | 'renamePrompt' | 'duplicatePrompt';
    payload?: any;
    path?: string; // For openPrompt, deletePrompt, renamePrompt, duplicatePrompt messages
    newName?: string; // For renamePrompt and duplicatePrompt messages
}

export interface WebviewResponse {
    type: 'updatePrompts' | 'updateConfig' | 'showLoading' | 'hideLoading' | 'showError' |
    'promptsLoaded' | 'promptSelected' | 'error' | 'configUpdated';
    payload?: any;
    prompts?: Prompt[];
    config?: any;
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

/**
 * File operation result interface
 */
export interface FileOperationResult {
    success: boolean;
    filePath?: string;
    error?: string;
}

/**
 * Options for creating new prompts
 */
export interface NewPromptOptions {
    name: string;
    category?: string;
    template?: string;
    metadata?: Partial<PromptMetadata>;
}

/**
 * Batch operation result interface
 */
export interface BatchOperationResult {
    successful: string[];
    failed: Array<{ filePath: string; error: string }>;
}

/**
 * Prompt template interface
 */
export interface PromptTemplate {
    id: string;
    name: string;
    description: string;
    content: string;
    metadata: Partial<PromptMetadata>;
}
