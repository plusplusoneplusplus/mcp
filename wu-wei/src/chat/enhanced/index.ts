/**
 * Enhanced Tool Calling Framework for Wu Wei
 * 
 * This module provides sophisticated tool calling capabilities including:
 * - Multi-round tool execution workflows
 * - Intelligent tool selection and orchestration
 * - Result caching and context management
 * - Advanced prompt engineering for tool usage
 */

// Main orchestrator
export { EnhancedToolParticipant } from './EnhancedToolParticipant';

// Core components
export { ToolCallOrchestrator } from './ToolCallOrchestrator';
export { ToolResultManager } from './ToolResultManager';
export { PromptTemplateEngine } from './PromptTemplateEngine';
export { ErrorRecoveryEngine } from './ErrorRecoveryEngine';

// Types and interfaces
export * from './types';

// Re-export for convenience
export {
    DEFAULT_TOOL_PARTICIPANT_CONFIG
} from './types';