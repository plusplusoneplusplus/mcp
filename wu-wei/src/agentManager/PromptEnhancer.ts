/**
 * Utility for enhancing user prompts with execution context
 * 
 * This module provides functions to inject execution tracking information
 * into user prompts in a way that instructs GitHub Copilot to call the
 * completion signal tool with the appropriate execution context.
 */

export interface ExecutionContext {
    executionId: string;
    taskDescription: string;
    agentName: string;
    startTime: Date;
}

export class PromptEnhancer {
    /**
     * Inject execution context into a user prompt
     * 
     * This adds hidden execution metadata and explicit instructions for
     * Copilot to call the completion signal tool when finished.
     */
    static enhancePromptWithExecutionContext(
        originalPrompt: string,
        context: ExecutionContext
    ): string {
        const executionInstructions = this.generateExecutionInstructions(context);

        // If the original prompt is empty, just use the execution instructions
        if (!originalPrompt.trim()) {
            return executionInstructions;
        }

        // Combine original prompt with execution context
        return `${originalPrompt}\n\n${executionInstructions}`;
    }

    /**
     * Generate execution tracking instructions for Copilot
     */
    private static generateExecutionInstructions(context: ExecutionContext): string {
        return `
==============
**IMPORTANT**: When you have completed this request, please call the \`@wu-wei_copilot_completion_signal\` tool with executionId="${context.executionId}".`;
    }

    /**
     * Generate execution context for prompt enhancement
     */
    static createExecutionContext(
        executionId: string,
        taskDescription: string,
        agentName: string,
        startTime: Date = new Date()
    ): ExecutionContext {
        return {
            executionId,
            taskDescription,
            agentName,
            startTime
        };
    }

    /**
     * Extract task description from agent parameters
     */
    static extractTaskDescription(params: any, promptContext?: any): string {
        // Try to find a meaningful task description from various parameter fields
        if (params.message) {
            return this.truncateTaskDescription(params.message);
        }
        if (params.query) {
            return this.truncateTaskDescription(params.query);
        }
        if (params.input) {
            return this.truncateTaskDescription(params.input);
        }
        if (params.question) {
            return this.truncateTaskDescription(params.question);
        }
        if (params.prompt) {
            return this.truncateTaskDescription(params.prompt);
        }

        // Try prompt context if available
        if (promptContext?.promptId) {
            return `Using prompt: ${promptContext.promptId}`;
        }

        // Fallback to a generic description
        return 'Agent execution request';
    }

    /**
     * Truncate task description to a reasonable length
     */
    private static truncateTaskDescription(description: string): string {
        if (!description || typeof description !== 'string') {
            return 'Agent execution request';
        }

        // Clean up the description
        const cleaned = description.trim().replace(/\s+/g, ' ');

        // Truncate if too long
        const maxLength = 100;
        if (cleaned.length <= maxLength) {
            return cleaned;
        }

        // Try to truncate at word boundary
        const truncated = cleaned.substring(0, maxLength);
        const lastSpace = truncated.lastIndexOf(' ');

        if (lastSpace > maxLength * 0.7) {
            return truncated.substring(0, lastSpace) + '...';
        }

        return truncated + '...';
    }

    /**
     * Check if a prompt already contains execution tracking instructions
     */
    static hasExecutionTracking(prompt: string): boolean {
        return prompt.includes('WU_WEI_TRACKING: enabled') ||
            prompt.includes('@wu-wei_copilot_completion_signal');
    }

    /**
     * Extract execution ID from a prompt if it exists
     */
    static extractExecutionIdFromPrompt(prompt: string): string | null {
        const match = prompt.match(/EXECUTION_ID:\s*([^\s\n]+)/);
        return match ? match[1] : null;
    }

    /**
     * Clean execution tracking instructions from a prompt (for display purposes)
     */
    static cleanPromptForDisplay(prompt: string): string {
        // Remove HTML comments with execution context
        const withoutComments = prompt.replace(/<!--[\s\S]*?-->/g, '');

        // Remove the execution instructions section
        const lines = withoutComments.split('\n');
        const importantIndex = lines.findIndex(line =>
            line.includes('**IMPORTANT**') && line.includes('wu-wei_copilot_completion_signal')
        );

        if (importantIndex >= 0) {
            // Find the end of the instructions (usually ends with description about Wu Wei)
            const endIndex = lines.findIndex((line, index) =>
                index > importantIndex &&
                (line.includes('Wu Wei') || line.trim() === '' && lines[index + 1]?.trim() === '')
            );

            if (endIndex >= 0) {
                lines.splice(importantIndex, endIndex - importantIndex + 1);
            } else {
                // Remove from IMPORTANT to end
                lines.splice(importantIndex);
            }
        }

        return lines.join('\n').replace(/\n{3,}/g, '\n\n').trim();
    }

    /**
     * Generate a fallback execution context when correlation fails
     */
    static generateFallbackContext(
        taskDescription: string,
        agentName: string = 'unknown',
        timestamp: Date = new Date()
    ): ExecutionContext {
        const executionId = `wu-wei-fallback-${timestamp.getTime()}-${Math.random().toString(36).substr(2, 9)}`;

        return {
            executionId,
            taskDescription,
            agentName,
            startTime: timestamp
        };
    }
}
