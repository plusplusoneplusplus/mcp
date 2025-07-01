/**
 * Utility for enhancing user prompts with execution context
 * 
 * This module provides functions to inject execution tracking information
 * into user prompts in a way that instructs GitHub Copilot to call the
 * completion signal tool with the appropriate execution context.
 */

import { PromptService } from '../shared/promptManager/types';
import { AbstractAgent } from './agentInterface';

export interface ExecutionContext {
    executionId: string;
    taskDescription: string;
    agentName: string;
    startTime: Date;
}

/**
 * Interface for prompt enhancement configuration
 */
export interface PromptEnhancementConfig {
    promptService: PromptService;
    promptContext?: any;
    agent: AbstractAgent;
    userParams: any;
}

export class PromptEnhancer {
    /**
     * Comprehensive method to enhance parameters with prompts and user input
     * 
     * This consolidates all prompt stitching logic from AgentPanelProvider
     * and provides a unified approach to combining prompts with user input.
     */
    static async enhanceParamsWithPrompt(config: PromptEnhancementConfig): Promise<any> {
        const { promptService, promptContext, agent, userParams } = config;

        if (!promptContext) {
            return userParams;
        }

        // If no promptId is provided, this is message-only mode
        if (!promptContext.promptId) {
            return userParams;
        }

        // Check if both prompt and user input are empty - do nothing in this case
        const userInput = this.extractUserInput(userParams);
        if (!promptContext.promptId && !userInput) {
            throw new Error('Please provide either a prompt template or a message');
        }

        // Get agent capabilities for prompt support detection
        const capabilities = agent.getCapabilities();
        const promptSupport = capabilities.metadata?.promptSupport;

        if (promptSupport?.supportsPrompts) {
            return await this.enhanceWithNativePromptSupport(
                promptService,
                promptContext,
                userParams,
                promptSupport
            );
        }

        // Fallback: add prompt as message parameter for agents without native support
        return await this.enhanceWithFallbackStitching(
            promptService,
            promptContext,
            userParams
        );
    }

    /**
     * Enhance parameters for agents with native prompt support
     */
    private static async enhanceWithNativePromptSupport(
        promptService: PromptService,
        promptContext: any,
        userParams: any,
        promptSupport: any
    ): Promise<any> {
        const promptParam = promptSupport.promptParameterName || 'prompt';

        // Check if the prompt has variables that need rendering
        const hasVariables = promptContext.variables && Object.keys(promptContext.variables).length > 0;

        let rendered: string;
        if (hasVariables) {
            // Render the prompt with variables
            rendered = await promptService.renderPromptWithVariables(
                promptContext.promptId,
                promptContext.variables
            );
        } else {
            // Get the prompt file path for direct reference
            const promptData = await promptService.getPrompt(promptContext.promptId);
            if (!promptData) {
                throw new Error(`Prompt with id '${promptContext.promptId}' not found`);
            }
            rendered = promptData.filePath ? `#${promptData.filePath}` : promptData.content;
        }

        const enhancedParams = {
            ...userParams,
            [promptParam]: rendered
        };

        if (promptSupport.variableResolution) {
            enhancedParams.variables = promptContext.variables;
        }

        // Support optional user input - can use prompt alone or combined with user message
        const userInput = this.extractUserInput(userParams);
        if (userInput) {
            enhancedParams.additionalMessage = userInput;
        }

        return enhancedParams;
    }

    /**
     * Enhance parameters using fallback string concatenation for agents without native prompt support
     */
    private static async enhanceWithFallbackStitching(
        promptService: PromptService,
        promptContext: any,
        userParams: any
    ): Promise<any> {
        if (!promptContext.promptId) {
            return userParams;
        }

        // Check if the prompt has variables that need rendering
        const hasVariables = promptContext.variables && Object.keys(promptContext.variables).length > 0;

        let promptContent: string;
        if (hasVariables) {
            // Render the prompt with variables
            const rendered = await promptService.renderPromptWithVariables(
                promptContext.promptId,
                promptContext.variables
            );
            promptContent = "System Instructions:\n" + rendered;
        } else {
            // Get the prompt file path for direct reference
            const promptData = await promptService.getPrompt(promptContext.promptId);
            if (!promptData) {
                throw new Error(`Prompt with id '${promptContext.promptId}' not found`);
            }
            promptContent = promptData.filePath
                ? `Follow Instructions in ${promptData.filePath}`
                : "System Instructions:\n" + promptData.content;
        }

        // Support optional user input - can use prompt alone or combined with user message
        const userInput = this.extractUserInput(userParams);

        if (userInput) {
            // Combine prompt with user input
            return {
                ...userParams,
                message: `${promptContent}\n\nUser Request:\n${userInput}`
            };
        } else {
            // Use prompt alone
            return {
                ...userParams,
                message: promptContent
            };
        }
    }

    /**
     * Extract user input from various parameter fields
     * 
     * This standardizes the extraction of user input across different parameter formats
     */
    static extractUserInput(params: any): string | null {
        // Try each field in priority order, but only accept string values
        const candidates = [params.message, params.question, params.query, params.input];

        for (const candidate of candidates) {
            if (candidate && typeof candidate === 'string') {
                const trimmed = candidate.trim();
                if (trimmed.length > 0) {
                    return trimmed;
                }
            }
        }

        return null;
    }

    /**
     * Create a comprehensive prompt combination with execution context
     * 
     * This method combines prompt content, user input, and execution tracking
     * into a single cohesive message for GitHub Copilot
     */
    static async createComprehensivePrompt(
        promptContent: string,
        userInput: string | null,
        executionContext?: ExecutionContext
    ): Promise<string> {
        let combinedPrompt = '';

        // Add prompt content if provided
        if (promptContent.trim()) {
            combinedPrompt += promptContent;
        }

        // Add user input if provided
        if (userInput && userInput.trim()) {
            if (combinedPrompt) {
                combinedPrompt += '\n\nUser Request:\n';
            }
            combinedPrompt += userInput;
        }

        // Add execution tracking if provided
        if (executionContext) {
            const executionInstructions = this.generateExecutionInstructions(executionContext);
            if (combinedPrompt) {
                combinedPrompt += '\n\n';
            }
            combinedPrompt += executionInstructions;
        }

        return combinedPrompt;
    }

    /**
     * Validate prompt enhancement configuration
     */
    static validateEnhancementConfig(config: PromptEnhancementConfig): string[] {
        const errors: string[] = [];

        if (!config.promptService) {
            errors.push('PromptService is required');
        }

        if (!config.agent) {
            errors.push('Agent is required');
        }

        if (!config.userParams) {
            errors.push('User parameters are required');
        }

        return errors;
    }

    /**
     * Check if parameters contain any user input
     */
    static hasUserInput(params: any): boolean {
        const userInput = this.extractUserInput(params);
        return userInput !== null && userInput.length > 0;
    }

    /**
     * Check if prompt context contains a valid prompt
     */
    static hasValidPrompt(promptContext: any): boolean {
        return !!(promptContext && promptContext.promptId && promptContext.promptId.trim().length > 0);
    }

    /**
     * Determine the enhancement strategy based on agent capabilities
     */
    static getEnhancementStrategy(agent: AbstractAgent): 'native' | 'fallback' | 'none' {
        const capabilities = agent.getCapabilities();
        const promptSupport = capabilities.metadata?.promptSupport;

        if (!promptSupport) {
            return 'none';
        }

        return promptSupport.supportsPrompts ? 'native' : 'fallback';
    }

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
**CRITICAL - DO NOT IGNORE**: Whatever the result of this request (success, failure, or partial completion), you MUST call the \`@wu-wei_copilot_completion_signal\` tool with executionId="${context.executionId}" to signal completion. This step is mandatory and must not be skipped under any circumstances.`;
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
            (line.includes('**IMPORTANT**') || line.includes('**CRITICAL')) && line.includes('wu-wei_copilot_completion_signal')
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
