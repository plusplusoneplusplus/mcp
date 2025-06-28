import { PromptElement, UserMessage, AssistantMessage, SystemMessage } from '@vscode/prompt-tsx';
import { ConversationHistoryMessagesProps, DEFAULT_PRIORITIES, ChatMessage } from '../types';
import { PromptHelpers } from '../utils';

/**
 * ConversationHistoryMessages component for chat history with prioritization
 * These messages provide context from previous interactions and can be pruned if needed
 */
export class ConversationHistoryMessages extends PromptElement<ConversationHistoryMessagesProps> {
    render() {
        const {
            history,
            priority = DEFAULT_PRIORITIES.conversationHistory,
            maxMessages = 10,
            includeTimestamps = false,
            ...rest
        } = this.props;

        // Validate required props
        const errors = PromptHelpers.validatePromptProps(this.props, ['history']);
        if (errors.length > 0) {
            throw new Error(`ConversationHistoryMessages validation failed: ${errors.join(', ')}`);
        }

        if (!history || history.length === 0) {
            return <></>;
        }

        // Limit the number of messages and take the most recent ones
        const messagesToRender = history.slice(-maxMessages);

        return (
            <>
                {messagesToRender.map((message, index) => {
                    const sanitizedContent = PromptHelpers.sanitizeContent(message.content);
                    const contentWithTimestamp = includeTimestamps && message.timestamp
                        ? `[${message.timestamp.toLocaleTimeString()}] ${sanitizedContent}`
                        : sanitizedContent;

                    const key = message.id || `${message.role}-${index}`;

                    switch (message.role) {
                        case 'user':
                            return (
                                <UserMessage priority={priority} {...rest}>
                                    {contentWithTimestamp}
                                </UserMessage>
                            );
                        case 'assistant':
                            return (
                                <AssistantMessage priority={priority} {...rest}>
                                    {contentWithTimestamp}
                                </AssistantMessage>
                            );
                        case 'system':
                            return (
                                <SystemMessage priority={priority} {...rest}>
                                    {contentWithTimestamp}
                                </SystemMessage>
                            );
                        default:
                            // Fallback to user message for unknown roles
                            return (
                                <UserMessage priority={priority} {...rest}>
                                    {contentWithTimestamp}
                                </UserMessage>
                            );
                    }
                })}
            </>
        );
    }
} 