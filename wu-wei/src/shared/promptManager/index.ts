// Main exports for shared prompt manager
export * from './types';
export { VsCodePromptService } from './VsCodePromptService';
export { PromptServiceFactory } from './PromptServiceFactory';

// Utility exports
export { VariableResolver } from './utils/variableResolver';
export { PromptRenderer } from './utils/promptRenderer';
export { PromptValidators } from './utils/validators';

// Re-export commonly used types from promptStore for convenience
export {
    Prompt,
    PromptMetadata,
    SearchFilter,
    PromptStoreConfig
} from '../../promptStore/types'; 