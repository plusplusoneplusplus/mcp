import { PromptElement, SystemMessage } from '@vscode/prompt-tsx';
import { SystemInstructionMessageProps, DEFAULT_PRIORITIES } from '../types';
import { PromptHelpers } from '../utils';

/**
 * SystemInstructionMessage component for high-priority system prompts
 * These messages have the highest priority and cannot be pruned from the conversation
 */
export class SystemInstructionMessage extends PromptElement<SystemInstructionMessageProps> {
    render() {
        const {
            children,
            priority = DEFAULT_PRIORITIES.systemInstructions,
            enforced = true,
            ...rest
        } = this.props;

        // Validate required props
        const errors = PromptHelpers.validatePromptProps(this.props, ['children']);
        if (errors.length > 0) {
            throw new Error(`SystemInstructionMessage validation failed: ${errors.join(', ')}`);
        }

        // Sanitize content
        const sanitizedContent = PromptHelpers.sanitizeContent(children);

        return (
            <SystemMessage priority={priority} {...rest}>
                {sanitizedContent}
            </SystemMessage>
        );
    }
} 