/**
 * Wu Wei Agent Manager
 * Centralized orchestration and execution tracking for worker agents
 */

// Agent interfaces and implementations
export * from './agentInterface';

// Execution tracking and management
export * from './ExecutionRegistry';
export * from './PromptEnhancer';

// Agent panel provider for UI integration
export * from './agentPanelProvider';

// Re-export commonly used types for convenience
export type {
    AgentMessage,
    AgentError,
    AgentRequest,
    AgentResponse,
    AgentCapabilities
} from './agentInterface';

export type {
    ActiveExecution
} from './ExecutionRegistry';

export type {
    ExecutionContext
} from './PromptEnhancer';
