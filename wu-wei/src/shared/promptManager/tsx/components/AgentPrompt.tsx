import { PromptElement, SystemMessage, UserMessage } from '@vscode/prompt-tsx';
import { AgentPromptProps, DEFAULT_PRIORITIES } from '../types';
import { PromptHelpers } from '../utils';
import { ConversationHistoryMessages } from './ConversationHistoryMessages';

/**
 * AgentPrompt - Main prompt composition component with priority-based message composition
 * This component orchestrates all message types and handles token budgeting and prioritization
 * 
 * Replaces string concatenation in AgentPanelProvider with intelligent TSX-based composition
 */
export class AgentPrompt extends PromptElement<AgentPromptProps> {
    render() {
        const {
            systemPrompt,
            userInput,
            conversationHistory = [],
            contextData,
            maxTokens = 4096,
            priorityStrategy = DEFAULT_PRIORITIES,
            ...rest
        } = this.props;

        // Validate required props
        const errors = PromptHelpers.validatePromptProps(this.props, ['systemPrompt', 'userInput']);
        if (errors.length > 0) {
            throw new Error(`AgentPrompt validation failed: ${errors.join(', ')}`);
        }

        // Split conversation history for prioritization
        const recentHistory = conversationHistory.slice(-2); // Last 2 messages - high priority
        const olderHistory = conversationHistory.slice(0, -2); // Older messages - medium priority

        // Prepare context data with token limit
        const contextWithLabel = contextData
            ? `Additional Context:\n${PromptHelpers.truncateToTokenLimit(contextData, Math.floor(maxTokens * 0.2))}`
            : null;

        return (
            <>
                {/* System instructions - highest priority, never pruned */}
                <SystemMessage priority={priorityStrategy.systemInstructions}>
                    {systemPrompt}
                </SystemMessage>

                {/* Current user query - very high priority */}
                <UserMessage priority={priorityStrategy.userQuery}>
                    {userInput}
                </UserMessage>

                {/* Recent conversation history - high priority */}
                {recentHistory.length > 0 && (
                    <ConversationHistoryMessages
                        history={recentHistory}
                        priority={85}
                        maxMessages={2}
                        includeTimestamps={false}
                    />
                )}

                {/* Older conversation history - medium priority */}
                {olderHistory.length > 0 && (
                    <ConversationHistoryMessages
                        history={olderHistory}
                        priority={priorityStrategy.conversationHistory}
                        maxMessages={4}
                        includeTimestamps={false}
                    />
                )}

                {/* Additional context - flexible priority, can be pruned */}
                {contextWithLabel && (
                    <UserMessage priority={priorityStrategy.contextData}>
                        {contextWithLabel}
                    </UserMessage>
                )}
            </>
        );
    }

    /**
     * Calculate the maximum number of conversation history messages to include
     * based on available token budget
     */
    private calculateMaxHistoryMessages(
        history: import('../types').ChatMessage[],
        availableTokens: number
    ): number {
        if (!history || history.length === 0 || availableTokens <= 0) {
            return 0;
        }

        let tokenCount = 0;
        let messageCount = 0;

        // Start from the most recent messages and work backwards
        for (let i = history.length - 1; i >= 0; i--) {
            const messageTokens = PromptHelpers.estimateTokenCount(history[i].content);

            if (tokenCount + messageTokens <= availableTokens) {
                tokenCount += messageTokens;
                messageCount++;
            } else {
                break;
            }
        }

        return messageCount;
    }

    /**
     * Get token allocation strategy for different content types
     */
    private getTokenAllocation(maxTokens: number): {
        system: number;
        userQuery: number;
        recentHistory: number;
        olderHistory: number;
        context: number;
    } {
        return {
            system: Math.floor(maxTokens * 0.3), // 30% for system instructions
            userQuery: Math.floor(maxTokens * 0.2), // 20% for user query
            recentHistory: Math.floor(maxTokens * 0.2), // 20% for recent history
            olderHistory: Math.floor(maxTokens * 0.15), // 15% for older history
            context: Math.floor(maxTokens * 0.15) // 15% for context data
        };
    }
} 