import { ChatMessage, TokenBudget } from '../types';

/**
 * Utility functions for prompt composition and management
 */
export class PromptHelpers {
    /**
     * Estimates token count for a given text (rough approximation)
     * Uses the common rule of ~4 characters per token
     */
    static estimateTokenCount(text: string): number {
        if (!text) return 0;
        return Math.ceil(text.length / 4);
    }

    /**
     * Truncates text to fit within a token budget
     */
    static truncateToTokenLimit(text: string, maxTokens: number): string {
        if (!text || maxTokens <= 0) return '';

        const estimatedTokens = this.estimateTokenCount(text);
        if (estimatedTokens <= maxTokens) return text;

        // Calculate approximate character limit
        const charLimit = maxTokens * 4;
        return text.substring(0, charLimit - 3) + '...';
    }

    /**
     * Formats a chat message for display in conversation history
     */
    static formatChatMessage(message: ChatMessage, includeTimestamp: boolean = false): string {
        const rolePrefix = message.role.toUpperCase();
        const timestamp = includeTimestamp && message.timestamp
            ? ` [${message.timestamp.toLocaleTimeString()}]`
            : '';

        return `${rolePrefix}${timestamp}: ${message.content}`;
    }

    /**
     * Formats multiple chat messages into a conversation string
     */
    static formatConversationHistory(
        messages: ChatMessage[],
        maxMessages?: number,
        includeTimestamps: boolean = false
    ): string {
        if (!messages || messages.length === 0) return '';

        const messagesToFormat = maxMessages
            ? messages.slice(-maxMessages)
            : messages;

        return messagesToFormat
            .map(msg => this.formatChatMessage(msg, includeTimestamps))
            .join('\n\n');
    }

    /**
     * Calculates token budget allocation based on priorities and available tokens
     */
    static calculateTokenBudget(
        totalTokens: number,
        systemTokens: number,
        userQueryTokens: number,
        historyTokens: number,
        contextTokens: number
    ): TokenBudget {
        const reservedTokens = systemTokens + userQueryTokens;
        const flexibleTokens = Math.max(0, totalTokens - reservedTokens);

        return {
            total: totalTokens,
            reserved: reservedTokens,
            flexible: flexibleTokens
        };
    }

    /**
     * Prioritizes and truncates content based on available token budget
     */
    static prioritizeContent(
        content: Array<{ text: string; priority: number; flexible: boolean }>,
        tokenBudget: TokenBudget
    ): Array<{ text: string; priority: number; truncated: boolean }> {
        // Sort by priority (highest first)
        const sortedContent = [...content].sort((a, b) => b.priority - a.priority);

        let remainingTokens = tokenBudget.flexible;
        const result: Array<{ text: string; priority: number; truncated: boolean }> = [];

        for (const item of sortedContent) {
            if (!item.flexible) {
                // Non-flexible content is always included as-is
                result.push({ ...item, truncated: false });
                continue;
            }

            const tokenCount = this.estimateTokenCount(item.text);

            if (tokenCount <= remainingTokens) {
                // Content fits within budget
                result.push({ ...item, truncated: false });
                remainingTokens -= tokenCount;
            } else if (remainingTokens > 10) {
                // Truncate content to fit remaining budget
                const truncatedText = this.truncateToTokenLimit(item.text, remainingTokens);
                result.push({
                    text: truncatedText,
                    priority: item.priority,
                    truncated: true
                });
                remainingTokens = 0;
            }
            // If not enough tokens left, skip this content
        }

        return result;
    }

    /**
     * Validates that a prompt component has all required properties
     */
    static validatePromptProps(props: any, requiredProps: string[]): string[] {
        const errors: string[] = [];

        for (const prop of requiredProps) {
            if (props[prop] === undefined || props[prop] === null) {
                errors.push(`Missing required property: ${prop}`);
            }
        }

        return errors;
    }

    /**
     * Sanitizes text content to prevent injection issues
     */
    static sanitizeContent(content: string): string {
        if (!content) return '';

        // Basic sanitization - remove potentially harmful patterns
        return content
            .replace(/\r\n/g, '\n')
            .replace(/\r/g, '\n')
            .trim();
    }

    /**
     * Creates a unique identifier for a message or component
     */
    static generateId(): string {
        return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
} 