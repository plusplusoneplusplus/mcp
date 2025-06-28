import * as vscode from 'vscode';
import { BasePromptElementProps, TsxRenderOptions, TsxRenderResult, PromptElement } from '../types';

/**
 * TSX Rendering Engine - Handles TSX component rendering with token budget management
 * and priority-based composition for VS Code language model integration
 */
export class TsxRenderer {
    private static instance: TsxRenderer | null = null;

    /**
     * Get singleton instance
     */
    static getInstance(): TsxRenderer {
        if (!this.instance) {
            this.instance = new TsxRenderer();
        }
        return this.instance;
    }

    /**
     * Render a TSX prompt component with token budget management
     */
    async renderTsxPrompt<T extends BasePromptElementProps>(
        promptComponent: new (props: T) => PromptElement<T>,
        props: T,
        options: TsxRenderOptions = {}
    ): Promise<TsxRenderResult> {
        try {
            // Create component instance
            const component = new promptComponent(props);

            // For now, create a simple text-based rendering
            // This will be enhanced when the full @vscode/prompt-tsx integration is available
            const rendered = component.render();
            const content = this.extractContentFromComponent(rendered);

            // Create messages from the rendered content
            const messages: vscode.LanguageModelChatMessage[] = [{
                role: vscode.LanguageModelChatMessageRole.User,
                content: [{ value: content, text: content } as vscode.LanguageModelTextPart],
                name: 'tsx-rendered'
            }];

            // Calculate token count
            const tokenCount = this.estimateTokenCount(messages);

            // Extract rendering metadata
            const renderingMetadata = {
                totalElements: this.countElements(rendered),
                includedElements: messages.length,
                priorityLevels: this.extractPriorityLevels(rendered)
            };

            return {
                messages,
                tokenCount,
                prunedElements: [], // Will be populated when full TSX integration is available
                renderingMetadata
            };

        } catch (error) {
            throw new Error(`TSX rendering failed: ${error instanceof Error ? error.message : String(error)}`);
        }
    }

    /**
     * Render a TSX component with token budget constraints
     */
    async renderWithTokenBudget<T extends BasePromptElementProps>(
        promptComponent: new (props: T) => PromptElement<T>,
        props: T,
        tokenBudget: number,
        model?: vscode.LanguageModelChat
    ): Promise<vscode.LanguageModelChatMessage[]> {
        const result = await this.renderTsxPrompt(promptComponent, props, {
            tokenBudget,
            model,
            enablePrioritization: true
        });

        // Apply token budget by truncating if necessary
        return this.applyTokenBudget(result.messages, tokenBudget);
    }

    /**
     * Validate a TSX component without full rendering
     */
    async validateTsxComponent<T extends BasePromptElementProps>(
        promptComponent: new (props: T) => PromptElement<T>,
        props: T
    ): Promise<{ isValid: boolean; errors: string[] }> {
        try {
            // Create component instance
            const component = new promptComponent(props);

            // Try to render to check for errors
            const rendered = component.render();

            // Basic validation checks
            const errors: string[] = [];

            if (!rendered) {
                errors.push('Component render() method returned null or undefined');
            }

            // Check for required props
            if (props.priority !== undefined && (props.priority < 0 || props.priority > 100)) {
                errors.push('Priority must be between 0 and 100');
            }

            if (props.maxTokens !== undefined && props.maxTokens <= 0) {
                errors.push('maxTokens must be positive');
            }

            return {
                isValid: errors.length === 0,
                errors
            };

        } catch (error) {
            return {
                isValid: false,
                errors: [`Component validation failed: ${error instanceof Error ? error.message : String(error)}`]
            };
        }
    }

    /**
     * Extract text content from a component render result
     */
    private extractContentFromComponent(rendered: any): string {
        if (typeof rendered === 'string') {
            return rendered;
        }

        if (Array.isArray(rendered)) {
            return rendered.map(item => this.extractContentFromComponent(item)).join('\n');
        }

        if (rendered && typeof rendered === 'object') {
            if (rendered.props && rendered.props.children) {
                return this.extractContentFromComponent(rendered.props.children);
            }
            if (rendered.content) {
                return rendered.content;
            }
        }

        return String(rendered || '');
    }

    /**
     * Apply token budget by truncating messages if necessary
     */
    private applyTokenBudget(messages: vscode.LanguageModelChatMessage[], tokenBudget: number): vscode.LanguageModelChatMessage[] {
        const result: vscode.LanguageModelChatMessage[] = [];
        let currentTokens = 0;

        for (const message of messages) {
            const messageTokens = this.estimateTokenCount([message]);

            if (currentTokens + messageTokens <= tokenBudget) {
                result.push(message);
                currentTokens += messageTokens;
            } else {
                // Truncate the message content to fit
                const availableTokens = tokenBudget - currentTokens;
                if (availableTokens > 0) {
                    const truncatedContent = this.truncateToTokenLimit(
                        typeof message.content === 'string' ? message.content :
                            message.content.map(part => this.extractTextFromPart(part)).join(''),
                        availableTokens
                    );

                    result.push({
                        ...message,
                        content: [{ value: truncatedContent, text: truncatedContent } as vscode.LanguageModelTextPart]
                    });
                }
                break;
            }
        }

        return result;
    }

    /**
     * Extract text from a language model content part
     */
    private extractTextFromPart(part: vscode.LanguageModelTextPart | vscode.LanguageModelToolResultPart | vscode.LanguageModelToolCallPart): string {
        if ('text' in part && typeof part.text === 'string') {
            return part.text;
        }
        if ('value' in part && typeof part.value === 'string') {
            return part.value;
        }
        if ('content' in part) {
            return typeof part.content === 'string' ? part.content : String(part.content);
        }
        return '';
    }

    /**
     * Truncate text to fit within token limit
     */
    private truncateToTokenLimit(text: string, tokenLimit: number): string {
        const estimatedCharLimit = tokenLimit * 4; // Rough estimation: 4 chars per token
        if (text.length <= estimatedCharLimit) {
            return text;
        }
        return text.substring(0, estimatedCharLimit) + '...';
    }

    /**
     * Estimate token count for an array of messages
     */
    private estimateTokenCount(messages: vscode.LanguageModelChatMessage[]): number {
        let totalTokens = 0;

        for (const message of messages) {
            // Simple token estimation: ~4 characters per token
            const content = typeof message.content === 'string' ? message.content :
                message.content.map(part => this.extractTextFromPart(part)).join('');
            totalTokens += Math.ceil(content.length / 4);
        }

        return totalTokens;
    }

    /**
     * Count elements in a rendered component
     */
    private countElements(rendered: any): number {
        if (!rendered) return 0;
        if (Array.isArray(rendered)) return rendered.length;
        if (typeof rendered === 'object' && rendered.props && rendered.props.children) {
            return Array.isArray(rendered.props.children) ? rendered.props.children.length : 1;
        }
        return 1;
    }

    /**
     * Extract priority levels from rendered component
     */
    private extractPriorityLevels(rendered: any): number[] {
        const priorities: number[] = [];

        const extractFromElement = (element: any) => {
            if (!element) return;

            if (element.props && typeof element.props.priority === 'number') {
                priorities.push(element.props.priority);
            }

            if (element.props && element.props.children) {
                if (Array.isArray(element.props.children)) {
                    element.props.children.forEach(extractFromElement);
                } else {
                    extractFromElement(element.props.children);
                }
            }
        };

        extractFromElement(rendered);
        return [...new Set(priorities)].sort((a, b) => b - a); // Unique priorities, highest first
    }

    /**
     * Create a simple text-based fallback when TSX rendering fails
     */
    createFallbackMessages(content: string, role: vscode.LanguageModelChatMessageRole = vscode.LanguageModelChatMessageRole.User): vscode.LanguageModelChatMessage[] {
        return [{
            role,
            content: [{ value: content, text: content } as vscode.LanguageModelTextPart],
            name: 'fallback'
        }];
    }
}

export default TsxRenderer; 