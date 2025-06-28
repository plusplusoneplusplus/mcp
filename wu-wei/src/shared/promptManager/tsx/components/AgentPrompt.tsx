import { PromptElement } from '@vscode/prompt-tsx';
import { AgentPromptProps, DEFAULT_PRIORITIES } from '../types';
import { PromptHelpers } from '../utils';
// import { SystemInstructionMessage } from './SystemInstructionMessage';
// import { UserQueryMessage } from './UserQueryMessage';
// import { ConversationHistoryMessages } from './ConversationHistoryMessages';
// import { ContextDataMessage } from './ContextDataMessage';

/**
 * AgentPrompt - Main prompt composition component with priority-based message composition
 * This component orchestrates all message types and handles token budgeting and prioritization
 */
export class AgentPrompt extends PromptElement<AgentPromptProps> {
    render() {
        const {
            systemPrompt,
            userInput,
            conversationHistory = [],
            contextData,
            maxTokens = 4000,
            priorityStrategy = DEFAULT_PRIORITIES,
            ...rest
        } = this.props;

        // Validate required props
        const errors = PromptHelpers.validatePromptProps(this.props, ['systemPrompt', 'userInput']);
        if (errors.length > 0) {
            throw new Error(`AgentPrompt validation failed: ${errors.join(', ')}`);
        }

        // For now, return a simple structure while we resolve typing issues
        return (
            <>
                {/* TODO: Implement full component composition once typing issues are resolved */}
                {systemPrompt}
                {userInput}
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
} 