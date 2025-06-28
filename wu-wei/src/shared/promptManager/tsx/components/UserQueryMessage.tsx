import { PromptElement, UserMessage } from '@vscode/prompt-tsx';
import { UserQueryMessageProps, DEFAULT_PRIORITIES } from '../types';
import { PromptHelpers } from '../utils';

/**
 * UserQueryMessage component for user input with high priority
 * These messages represent the current user query and should rarely be pruned
 */
export class UserQueryMessage extends PromptElement<UserQueryMessageProps> {
    render() {
        const {
            children,
            priority = DEFAULT_PRIORITIES.userQuery,
            timestamp,
            ...rest
        } = this.props;

        // Validate required props
        const errors = PromptHelpers.validatePromptProps(this.props, ['children']);
        if (errors.length > 0) {
            throw new Error(`UserQueryMessage validation failed: ${errors.join(', ')}`);
        }

        // Sanitize content
        const sanitizedContent = PromptHelpers.sanitizeContent(children);

        // Add timestamp if provided
        const contentWithTimestamp = timestamp
            ? `[${timestamp.toLocaleTimeString()}] ${sanitizedContent}`
            : sanitizedContent;

        return (
            <UserMessage priority={priority} {...rest}>
                {contentWithTimestamp}
            </UserMessage>
        );
    }
} 