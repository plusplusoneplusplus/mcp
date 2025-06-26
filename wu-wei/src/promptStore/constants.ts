/**
 * Configuration constants for the Prompt Store
 * Following wu wei principles: simple defaults that flow naturally
 */

import { PromptStoreConfig, PromptMetadata } from './types';

/**
 * Default configuration for the Prompt Store
 */
export const DEFAULT_CONFIG: PromptStoreConfig = {
    rootDirectory: '',
    watchPaths: ['${workspaceFolder}/prompts', '${workspaceFolder}/.prompts'],
    filePatterns: ['**/*.md', '**/*.txt'],
    excludePatterns: ['**/node_modules/**', '**/.git/**', '**/dist/**', '**/build/**'],
    autoRefresh: true,
    refreshInterval: 1000, // 1 second
    enableCache: true,
    maxCacheSize: 1000,
    sortBy: 'name',
    sortOrder: 'asc',
    showCategories: true,
    showTags: true,
    enableSearch: true
};

/**
 * File patterns for detecting markdown files with prompts
 */
export const FILE_PATTERNS = {
    MARKDOWN: ['**/*.md', '**/*.markdown'],
    TEXT: ['**/*.txt'],
    ALL_SUPPORTED: ['**/*.md', '**/*.markdown', '**/*.txt']
};

/**
 * YAML frontmatter delimiters
 */
export const FRONTMATTER_DELIMITERS = {
    START: '---',
    END: '---'
};

/**
 * Default metadata schema for validation
 */
export const DEFAULT_METADATA_SCHEMA: Partial<PromptMetadata> = {
    title: 'Untitled Prompt',
    description: '',
    category: 'General',
    tags: []
};

/**
 * Validation rules and patterns
 */
export const VALIDATION_RULES = {
    TITLE: {
        MIN_LENGTH: 1,
        MAX_LENGTH: 200,
        PATTERN: /^[a-zA-Z0-9\s\-_.,!?()[\]{}]+$/
    },
    DESCRIPTION: {
        MAX_LENGTH: 2000
    },
    CATEGORY: {
        PATTERN: /^[a-zA-Z0-9\s\-_]+$/,
        MAX_LENGTH: 50
    },
    TAG: {
        PATTERN: /^[a-zA-Z0-9\-_]+$/,
        MAX_LENGTH: 30,
        MAX_COUNT: 20
    }
};

/**
 * UI configuration defaults
 */
export const UI_CONFIG = {
    WEBVIEW: {
        TITLE: 'Wu Wei - Prompt Store',
        ICON: '$(book)',
        RETAIN_CONTEXT_WHEN_HIDDEN: true
    },
    SEARCH: {
        DEBOUNCE_DELAY: 300,
        MIN_QUERY_LENGTH: 2,
        MAX_RESULTS: 100
    },
    PAGINATION: {
        DEFAULT_PAGE_SIZE: 25,
        MAX_PAGE_SIZE: 100
    },
    REFRESH: {
        SHOW_PROGRESS: true,
        PROGRESS_TITLE: 'Refreshing prompts...'
    }
};

/**
 * File watcher configuration
 */
export const WATCHER_CONFIG = {
    IGNORED: [
        /(^|[\/\\])\../, // Hidden files
        /\.tmp$/, /\.swp$/, /~$/, // Temp files
        /node_modules/, // Common directories
        /(^|[\/\\])\.git([\/\\]|$)/,
        /(^|[\/\\])dist([\/\\]|$)/,
        /(^|[\/\\])build([\/\\]|$)/,
        /(^|[\/\\])\.vscode([\/\\]|$)/
    ],
    POLL_INTERVAL: 1000,
    USE_POLLING: false,
    ATOMIC_WRITES: true,
    DEBOUNCE_MS: 500,
    MAX_DEPTH: 10,
    FOLLOW_SYMLINKS: false,
    AWAIT_WRITE_FINISH: {
        stabilityThreshold: 500,
        pollInterval: 100
    }
};

/**
 * Cache configuration
 */
export const CACHE_CONFIG = {
    TTL: 300000, // 5 minutes
    CHECK_INTERVAL: 60000, // 1 minute
    MAX_SIZE: 1000,
    ENABLE_COMPRESSION: false
};

/**
 * Logging categories for the prompt store
 */
export const LOG_CATEGORIES = {
    CORE: 'PromptStore',
    WATCHER: 'PromptStore.Watcher',
    PARSER: 'PromptStore.Parser',
    PROVIDER: 'PromptStore.Provider',
    CACHE: 'PromptStore.Cache',
    WEBVIEW: 'PromptStore.Webview'
};

/**
 * Error messages
 */
export const ERROR_MESSAGES = {
    FILE_NOT_FOUND: 'Prompt file not found',
    INVALID_FRONTMATTER: 'Invalid YAML frontmatter',
    MISSING_TITLE: 'Prompt title is required',
    INVALID_METADATA: 'Invalid metadata format',
    WATCHER_INIT_FAILED: 'Failed to initialize file watcher',
    CACHE_ERROR: 'Cache operation failed',
    WEBVIEW_ERROR: 'Webview communication error'
};

/**
 * Success messages
 */
export const SUCCESS_MESSAGES = {
    PROMPTS_LOADED: 'Prompts loaded successfully',
    WATCHER_STARTED: 'File watcher started',
    CACHE_CLEARED: 'Cache cleared successfully',
    EXPORT_COMPLETE: 'Export completed successfully'
};
