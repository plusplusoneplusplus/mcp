import { PromptElement, UserMessage } from '@vscode/prompt-tsx';
import { ContextDataMessageProps, DEFAULT_PRIORITIES } from '../types';
import { PromptHelpers } from '../utils';

/**
 * ContextDataMessage component for flexible context with token allocation
 * These messages provide additional context and can be pruned or truncated as needed
 */
export class ContextDataMessage extends PromptElement<ContextDataMessageProps> {
    render() {
        const {
            children,
            priority = DEFAULT_PRIORITIES.contextData,
            flexGrow = 1,
            label,
            maxTokens,
            ...rest
        } = this.props;

        // Validate required props
        const errors = PromptHelpers.validatePromptProps(this.props, ['children']);
        if (errors.length > 0) {
            throw new Error(`ContextDataMessage validation failed: ${errors.join(', ')}`);
        }

        // Sanitize content
        let sanitizedContent = PromptHelpers.sanitizeContent(children);

        // Apply token limit if specified
        if (maxTokens && maxTokens > 0) {
            sanitizedContent = PromptHelpers.truncateToTokenLimit(sanitizedContent, maxTokens);
        }

        // Add label if provided
        const contentWithLabel = label
            ? `${label}:\n${sanitizedContent}`
            : sanitizedContent;

        return (
            <UserMessage
                priority={priority}
                flexGrow={flexGrow}
                {...rest}
            >
                {contentWithLabel}
            </UserMessage>
        );
    }
} 