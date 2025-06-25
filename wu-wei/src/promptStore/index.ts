/**
 * Main exports for the Prompt Store module
 * Following wu wei principles: simple, clean exports that flow naturally
 */

// Core classes
export { PromptStoreProvider } from './PromptStoreProvider';
export { PromptManager } from './PromptManager';
export { PromptFileWatcher } from './PromptFileWatcher';
export { MetadataParser } from './MetadataParser';

// Types and interfaces
export * from './types';

// Constants and configuration
export * from './constants';

// Convenience function to initialize the prompt store
export function initializePromptStore() {
    // This will be implemented in future steps
    // For now, just a placeholder
    return {
        provider: null,
        manager: null,
        watcher: null
    };
}
