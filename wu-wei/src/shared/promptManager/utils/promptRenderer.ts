import { VariableResolver } from './variableResolver';
import { VariableResolutionOptions, ValidationError } from '../types';

export class PromptRenderer {
    private variableResolver: VariableResolver;

    constructor() {
        this.variableResolver = new VariableResolver();
    }

    async render(
        content: string,
        variables: Record<string, any>,
        options: VariableResolutionOptions = {}
    ): Promise<string> {
        try {
            // Start performance timing
            const startTime = performance.now();

            // Resolve variables in the content
            const renderedContent = this.variableResolver.resolve(content, variables, options);

            // Check performance requirement (<10ms for typical prompts)
            const endTime = performance.now();
            const duration = endTime - startTime;

            if (duration > 10) {
                console.warn(`Prompt rendering took ${duration.toFixed(2)}ms, exceeding 10ms target`);
            }

            return renderedContent;
        } catch (error) {
            throw new Error(`Failed to render prompt: ${error instanceof Error ? error.message : String(error)}`);
        }
    }

    async renderWithValidation(
        content: string,
        variables: Record<string, any>,
        parameters: import('../types').PromptParameter[] = [],
        options: VariableResolutionOptions = {}
    ): Promise<{ content: string; errors: ValidationError[] }> {
        // Validate variables first
        const errors = this.variableResolver.validateVariables(content, variables, parameters);

        // If there are critical errors, don't render
        const criticalErrors = errors.filter(e => e.severity === 'error');
        if (criticalErrors.length > 0 && options.strictMode) {
            return {
                content: '',
                errors
            };
        }

        try {
            const renderedContent = await this.render(content, variables, options);
            return {
                content: renderedContent,
                errors
            };
        } catch (error) {
            errors.push({
                field: 'rendering',
                message: error instanceof Error ? error.message : String(error),
                severity: 'error'
            });

            return {
                content: '',
                errors
            };
        }
    }

    extractVariables(content: string): string[] {
        return this.variableResolver.extractVariables(content);
    }

    previewRender(
        content: string,
        variables: Record<string, any>,
        options: VariableResolutionOptions = {}
    ): { preview: string; missingVariables: string[] } {
        const extractedVars = this.extractVariables(content);
        const missingVariables = extractedVars.filter(varName => !variables.hasOwnProperty(varName));

        // Create preview with placeholder for missing variables
        const previewOptions: VariableResolutionOptions = {
            ...options,
            allowUndefined: true,
            resolver: (variable: string) => {
                if (missingVariables.includes(variable)) {
                    return `[${variable}]`;
                }
                return options.resolver?.(variable);
            }
        };

        const preview = this.variableResolver.resolve(content, variables, previewOptions);

        return {
            preview,
            missingVariables
        };
    }

    /**
     * Batch render multiple prompts efficiently
     */
    async batchRender(
        prompts: Array<{ content: string; variables: Record<string, any> }>,
        options: VariableResolutionOptions = {}
    ): Promise<string[]> {
        const startTime = performance.now();

        const results = await Promise.all(
            prompts.map(async ({ content, variables }) => {
                try {
                    return await this.render(content, variables, options);
                } catch (error) {
                    console.error('Failed to render prompt in batch:', error);
                    return '';
                }
            })
        );

        const endTime = performance.now();
        const duration = endTime - startTime;
        const avgTime = duration / prompts.length;

        if (avgTime > 10) {
            console.warn(`Batch rendering averaged ${avgTime.toFixed(2)}ms per prompt, exceeding 10ms target`);
        }

        return results;
    }
} 