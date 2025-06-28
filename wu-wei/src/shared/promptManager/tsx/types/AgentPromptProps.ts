import { BasePromptElementProps } from '@vscode/prompt-tsx';

/**
 * Chat message interface for conversation history
 */
export interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp?: Date;
    id?: string;
}

/**
 * Props for the main AgentPrompt component
 */
export interface AgentPromptProps extends BasePromptElementProps {
    systemPrompt: string;
    userInput: string;
    conversationHistory?: ChatMessage[];
    contextData?: string;
    maxTokens?: number;
    priorityStrategy?: PriorityStrategy;
}

/**
 * Props for SystemInstructionMessage component
 */
export interface SystemInstructionMessageProps extends BasePromptElementProps {
    children: string;
    priority?: number;
    enforced?: boolean; // If true, this message cannot be pruned
}

/**
 * Props for UserQueryMessage component
 */
export interface UserQueryMessageProps extends BasePromptElementProps {
    children: string;
    priority?: number;
    timestamp?: Date;
}

/**
 * Props for ConversationHistoryMessages component
 */
export interface ConversationHistoryMessagesProps extends BasePromptElementProps {
    history: ChatMessage[];
    priority?: number;
    maxMessages?: number;
    includeTimestamps?: boolean;
}

/**
 * Props for ContextDataMessage component
 */
export interface ContextDataMessageProps extends BasePromptElementProps {
    children: string;
    priority?: number;
    flexGrow?: number;
    label?: string;
    maxTokens?: number;
}

/**
 * Priority strategy configuration
 */
export interface PriorityStrategy {
    systemInstructions: number;
    userQuery: number;
    conversationHistory: number;
    contextData: number;
}

/**
 * Default priority values as specified in the issue
 */
export const DEFAULT_PRIORITIES: PriorityStrategy = {
    systemInstructions: 100, // Always included
    userQuery: 90,          // High importance
    conversationHistory: 80, // Medium importance
    contextData: 70         // Flexible, can be pruned
};

/**
 * Token budget configuration for flexible content management
 */
export interface TokenBudget {
    total: number;
    reserved: number;
    flexible: number;
} 