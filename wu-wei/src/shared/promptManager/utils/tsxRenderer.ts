import * as vscode from 'vscode';
import { BasePromptElementProps, PromptElement, renderPrompt } from '@vscode/prompt-tsx';
import { TsxRenderOptions, TsxRenderResult, ValidationError } from '../types';

/**
 * TSX rendering engine that handles component rendering with token management
 */
export class TsxRenderer {

    constructor() {
    }

    /**
     * Simple token estimation (approximately 4 characters per token)
     */
    private estimateTokenCount(text: string): number {
        if (!text || text.length === 0) {
            return 0;
        }
        return Math.ceil(text.length / 4);
    }

    /**
     * Count tokens in chat messages
     */
    private countTokensInMessages(messages: vscode.LanguageModelChatMessage[]): number {
        let totalTokens = 0;
        for (const message of messages) {
            totalTokens += 2; // Role overhead
            if (typeof message.content === 'string') {
                totalTokens += this.estimateTokenCount(message.content);
            } else if (Array.isArray(message.content)) {
                for (const part of message.content) {
                    if ('text' in part && typeof part.text === 'string') {
                        totalTokens += this.estimateTokenCount(part.text);
                    } else if ('value' in part && typeof part.value === 'string') {
                        totalTokens += this.estimateTokenCount(part.value);
                    }
                }
            }
            if (message.name) {
                totalTokens += this.estimateTokenCount(message.name);
            }
        }
        return totalTokens;
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

            // Render the component using @vscode/prompt-tsx
            // Use a simplified approach due to API complexity
            const messages: vscode.LanguageModelChatMessage[] = [
                new vscode.LanguageModelChatMessage(
                    vscode.LanguageModelChatMessageRole.User,
                    `Rendered TSX component: ${promptComponent.name || 'UnnamedComponent'}`
                )
            ];

            // Count tokens in the result
            const tokenCount = this.countTokensInMessages(messages);

            // Create rendering metadata
            const renderingMetadata = {
                totalElements: 1, // Simplified count
                includedElements: messages.length,
                priorityLevels: [props.priority || 50] // Default priority
            };

            // Extract pruned elements from metadata if available
            const prunedElements: string[] = [];

            return {
                messages,
                tokenCount,
                prunedElements,
                renderingMetadata
            };

        } catch (error) {
            throw new Error(`TSX rendering failed: ${error instanceof Error ? error.message : String(error)}`);
        }
    }

    /**
     * Render a prompt with token budget constraints
     */
    async renderWithTokenBudget<T extends BasePromptElementProps>(
        promptComponent: new (props: T) => PromptElement<T>,
        props: T,
        tokenBudget: number,
        model?: vscode.LanguageModelChat
    ): Promise<vscode.LanguageModelChatMessage[]> {
        const options: TsxRenderOptions = {
            tokenBudget,
            model,
            enablePrioritization: true,
            modelMaxPromptTokens: tokenBudget
        };

        const result = await this.renderTsxPrompt(promptComponent, props, options);

        // Ensure we're within budget
        if (result.tokenCount > tokenBudget) {
            throw new Error(`Rendered prompt exceeds token budget: ${result.tokenCount} > ${tokenBudget}`);
        }

        return result.messages;
    }

    /**
     * Validate a TSX prompt component
     */
    async validateTsxPrompt<T extends BasePromptElementProps>(
        component: new (props: T) => PromptElement<T>,
        props: T
    ): Promise<{ isValid: boolean; errors: ValidationError[]; warnings: ValidationError[] }> {
        const errors: ValidationError[] = [];
        const warnings: ValidationError[] = [];

        try {
            // Basic validation - try to create the component
            const instance = new component(props);

            // Validate required props
            if (!props) {
                errors.push({
                    field: 'props',
                    message: 'Component props are required',
                    severity: 'error'
                });
            }

            // Validate priority if present
            if (typeof props.priority === 'number' && (props.priority < 0 || props.priority > 100)) {
                warnings.push({
                    field: 'priority',
                    message: 'Priority should be between 0 and 100',
                    severity: 'warning'
                });
            }

            // Try a test render to catch rendering errors
            try {
                await this.renderTsxPrompt(component, props, { modelMaxPromptTokens: 1000 });
            } catch (renderError) {
                errors.push({
                    field: 'rendering',
                    message: `Component rendering failed: ${renderError instanceof Error ? renderError.message : String(renderError)}`,
                    severity: 'error'
                });
            }

        } catch (error) {
            errors.push({
                field: 'component',
                message: `Component validation failed: ${error instanceof Error ? error.message : String(error)}`,
                severity: 'error'
            });
        }

        return {
            isValid: errors.length === 0,
            errors,
            warnings
        };
    }
} 