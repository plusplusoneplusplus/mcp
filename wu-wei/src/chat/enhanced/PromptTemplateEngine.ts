import * as vscode from 'vscode';
import { logger } from '../../logger';
import { PromptTemplate, ToolCallContext, ToolSelectionResult } from './types';
import { PromptTemplateLoader } from '../PromptTemplateLoader';

/**
 * Generates context-aware prompts for tool usage
 */
export class PromptTemplateEngine {
    private templates: Map<string, PromptTemplate> = new Map();

    constructor() {
        this.initializeDefaultTemplates();
        this.initializeFileBasedTemplates();
    }

    /**
     * Get a template by name, supporting both file-based and in-memory templates
     */
    getTemplate(templateName: string, variables?: Record<string, string>): string {
        try {
            // First try to load from PromptTemplateLoader for file-based templates
            if (templateName === 'workspace-analysis-template.md' && variables) {
                return PromptTemplateLoader.getWorkspaceAnalysisTemplate({
                    projectStructure: variables.projectStructure || '',
                    totalFiles: variables.totalFiles || '0',
                    languagesDetected: variables.languagesDetected || '',
                    currentContext: variables.currentContext || '',
                    availableTools: variables.availableTools || ''
                });
            }

            if (templateName === 'code-analysis-template.md' && variables) {
                return PromptTemplateLoader.getCodeAnalysisTemplate({
                    analysisContext: variables.analysisContext || '',
                    requestPrompt: variables.requestPrompt || ''
                });
            }

            // Try in-memory templates
            const template = this.templates.get(templateName);
            if (template) {
                return variables ? this.interpolateTemplate(template.template, variables) : template.template;
            }

            // If template not found, return error message
            return `Template ${templateName} not found`;
        } catch (error) {
            logger.error('PromptTemplateEngine: Failed to get template', { templateName, error });
            return `Template ${templateName} not found`;
        }
    }

    /**
     * Generate a system prompt enhanced with tool awareness
     */
    generateToolAwareSystemPrompt(
        basePrompt: string,
        availableTools: vscode.LanguageModelToolInformation[],
        context: ToolCallContext
    ): string {
        try {
            const toolGuidance = this.generateToolGuidance(availableTools, context);
            const contextualGuidance = this.generateContextualGuidance(context);

            return `${basePrompt}

## Tool Usage Guidelines

You have access to ${availableTools.length} powerful tools that can help you provide accurate, real-time information. ${toolGuidance}

${contextualGuidance}

## Important Tool Usage Rules

1. **Always use tools when they can provide better information** than your training data
2. **Use multiple tools when needed** to gather comprehensive information
3. **Explain your tool choices** briefly to help users understand your process
4. **Summarize tool results** in a clear, actionable way
5. **If a tool fails**, try alternative approaches or explain the limitation

Remember: Your goal is to provide the most helpful and accurate response possible by leveraging these tools effectively.`;

        } catch (error) {
            logger.warn('PromptTemplateEngine: Failed to generate tool-aware system prompt', { error });
            return basePrompt; // Fallback to base prompt
        }
    }

    /**
     * Generate tool-specific guidance based on user intent
     */
    generateToolSpecificPrompt(
        toolName: string,
        userIntent: string,
        context: ToolCallContext
    ): string {
        const template = this.getToolSpecificTemplate(toolName);

        if (!template) {
            return this.generateGenericToolPrompt(toolName, userIntent, context);
        }

        return this.interpolateTemplate(template.template, {
            userIntent,
            toolName,
            contextInfo: this.summarizeContext(context)
        });
    }

    /**
     * Analyze user intent and suggest appropriate tools
     */
    analyzeUserIntentForTools(
        userPrompt: string,
        availableTools: vscode.LanguageModelToolInformation[]
    ): ToolSelectionResult {
        try {
            const intent = this.extractUserIntent(userPrompt);
            const relevantTools = this.matchToolsToIntent(intent, availableTools);

            return {
                selectedTools: relevantTools.map(t => t.name),
                confidence: this.calculateConfidence(intent, relevantTools),
                reasoning: this.generateSelectionReasoning(intent, relevantTools)
            };
        } catch (error) {
            logger.warn('PromptTemplateEngine: Failed to analyze user intent', { error });
            return {
                selectedTools: [],
                confidence: 0,
                reasoning: 'Intent analysis failed'
            };
        }
    }

    /**
     * Generate prompts for multi-round tool execution
     */
    generateMultiRoundPrompt(
        roundNumber: number,
        previousResults: Record<string, vscode.LanguageModelToolResult>,
        context: ToolCallContext
    ): string {
        const resultsSummary = this.summarizePreviousResults(previousResults);

        const template = this.templates.get('multi-round-context');
        if (!template) {
            return this.generateGenericMultiRoundPrompt(roundNumber, resultsSummary, context);
        }

        return this.interpolateTemplate(template.template, {
            roundNumber: roundNumber.toString(),
            resultsSummary,
            userIntent: context.userIntent,
            contextInfo: this.summarizeContext(context)
        });
    }

    /**
     * Generate error recovery prompt for failed tool execution
     */
    generateErrorRecoveryPrompt(
        error: any,
        classification: any,
        context: ToolCallContext,
        recoverySuggestions: string[]
    ): string {
        try {
            const template = this.templates.get('error-recovery');
            if (!template) {
                return this.generateBasicErrorRecoveryPrompt(error, recoverySuggestions);
            }

            // Build template variables
            const variables = {
                TOOL_NAME: error.toolName,
                ERROR_MESSAGE: error.error,
                ERROR_TYPE: classification.type,
                ERROR_SEVERITY: classification.severity,
                RECOVERABLE: classification.recoverable ? 'Yes' : 'No',
                RECOVERY_CONFIDENCE: Math.round(classification.confidence * 100),
                ERROR_DESCRIPTION: recoverySuggestions[0] || 'Tool execution failed',
                RECOVERY_STRATEGY_DESCRIPTION: this.getRecoveryStrategyDescription(classification.suggestedStrategy),
                ALTERNATIVE_TOOLS: context.availableTools
                    .filter(tool => tool.name !== error.toolName)
                    .slice(0, 3), // Show top 3 alternatives
                RECOVERY_INSTRUCTIONS: this.getRecoveryInstructions(classification.suggestedStrategy)
            };

            return this.interpolateTemplate(template.template, variables);

        } catch (templateError) {
            logger.warn('PromptTemplateEngine: Failed to generate error recovery prompt', { templateError });
            return this.generateBasicErrorRecoveryPrompt(error, recoverySuggestions);
        }
    }

    /**
     * Generate brief error recovery message for user display
     */
    generateBriefErrorRecoveryMessage(
        error: any,
        recoveryResult: any
    ): string {
        try {
            const template = this.templates.get('error-recovery-brief');
            if (!template) {
                return `⚠️ ${error.toolName} encountered an issue - continuing with alternative approach.`;
            }

            const variables = {
                TOOL_NAME: error.toolName,
                ERROR_TYPE: error.errorType || 'unknown',
                RECOVERY_SUCCESS: recoveryResult.success,
                RECOVERY_ACTION_DESCRIPTION: recoveryResult.action?.description || 'Alternative approach selected',
                ALTERNATIVE_APPROACH: recoveryResult.alternativeApproach || 'Continuing without this tool',
                USER_ACTION_REQUIRED: recoveryResult.action?.strategy === 'user_intervention',
                USER_ACTION_MESSAGE: recoveryResult.userMessage || ''
            };

            return this.interpolateTemplate(template.template, variables);

        } catch (templateError) {
            logger.warn('PromptTemplateEngine: Failed to generate brief error recovery message', { templateError });
            return `⚠️ ${error.toolName} encountered an issue - continuing with alternative approach.`;
        }
    }

    /**
     * Generate troubleshooting guide for users
     */
    generateTroubleshootingGuide(): string {
        try {
            const template = this.templates.get('error-troubleshooting-guide');
            return template ? template.template : this.getBasicTroubleshootingGuide();
        } catch (error) {
            logger.warn('PromptTemplateEngine: Failed to generate troubleshooting guide', { error });
            return this.getBasicTroubleshootingGuide();
        }
    }

    /**
     * Generate tool guidance based on available tools and context
     */
    private generateToolGuidance(
        availableTools: vscode.LanguageModelToolInformation[],
        context: ToolCallContext
    ): string {
        if (availableTools.length === 0) {
            return "No tools are currently available.";
        }

        const toolList = availableTools
            .map(tool => `- **${tool.name}**: ${tool.description}`)
            .join('\n');

        return `Available tools:\n${toolList}`;
    }

    /**
     * Generate contextual guidance based on the current context
     */
    private generateContextualGuidance(context: ToolCallContext): string {
        let guidance = '';

        if (context.roundNumber > 1) {
            guidance += `This is round ${context.roundNumber} of our conversation. `;
        }

        if (Object.keys(context.previousResults).length > 0) {
            guidance += `You have ${Object.keys(context.previousResults).length} previous tool results to consider. `;
        }

        return guidance;
    }

    /**
     * Get tool-specific template
     */
    private getToolSpecificTemplate(toolName: string): PromptTemplate | null {
        const template = this.templates.get(`tool-${toolName}`);
        return template || null;
    }

    /**
     * Generate generic tool prompt
     */
    private generateGenericToolPrompt(
        toolName: string,
        userIntent: string,
        context: ToolCallContext
    ): string {
        return `Using tool "${toolName}" for: ${userIntent}
        
Context: ${this.summarizeContext(context)}`;
    }

    /**
     * Interpolate template with variables
     */
    private interpolateTemplate(template: string, variables: Record<string, any>): string {
        let result = template;

        for (const [key, value] of Object.entries(variables)) {
            const placeholder = `{{${key}}}`;
            result = result.replace(new RegExp(placeholder, 'g'), String(value));
        }

        return result;
    }

    /**
     * Summarize context for template usage
     */
    private summarizeContext(context: ToolCallContext): string {
        const parts = [];

        if (context.userIntent) {
            parts.push(`Intent: ${context.userIntent}`);
        }

        if (context.roundNumber > 1) {
            parts.push(`Round: ${context.roundNumber}`);
        }

        if (Object.keys(context.previousResults).length > 0) {
            parts.push(`Previous results: ${Object.keys(context.previousResults).length}`);
        }

        return parts.join(', ');
    }

    /**
     * Extract user intent from prompt
     */
    private extractUserIntent(userPrompt: string): string {
        // Simple intent extraction - could be enhanced with NLP
        const prompt = userPrompt.toLowerCase();

        if (prompt.includes('analyze') || prompt.includes('analysis')) {
            return 'analysis';
        } else if (prompt.includes('debug') || prompt.includes('error')) {
            return 'debugging';
        } else if (prompt.includes('refactor')) {
            return 'refactoring';
        } else if (prompt.includes('test')) {
            return 'testing';
        } else if (prompt.includes('search') || prompt.includes('find')) {
            return 'search';
        }

        return 'general';
    }

    /**
     * Match tools to user intent
     */
    private matchToolsToIntent(
        intent: string,
        availableTools: vscode.LanguageModelToolInformation[]
    ): vscode.LanguageModelToolInformation[] {
        const intentKeywords: Record<string, string[]> = {
            analysis: ['analyze', 'inspect', 'review', 'examine'],
            debugging: ['debug', 'error', 'troubleshoot', 'diagnose'],
            refactoring: ['refactor', 'restructure', 'reorganize'],
            testing: ['test', 'verify', 'validate', 'check'],
            search: ['search', 'find', 'locate', 'grep']
        };

        const keywords = intentKeywords[intent] || [];

        return availableTools.filter(tool => {
            const toolText = `${tool.name} ${tool.description}`.toLowerCase();
            return keywords.some(keyword => toolText.includes(keyword));
        });
    }

    /**
     * Calculate confidence score for tool selection
     */
    private calculateConfidence(
        intent: string,
        relevantTools: vscode.LanguageModelToolInformation[]
    ): number {
        if (relevantTools.length === 0) return 0;
        if (relevantTools.length >= 3) return 0.9;
        if (relevantTools.length >= 2) return 0.7;
        return 0.5;
    }

    /**
     * Generate reasoning for tool selection
     */
    private generateSelectionReasoning(
        intent: string,
        relevantTools: vscode.LanguageModelToolInformation[]
    ): string {
        if (relevantTools.length === 0) {
            return `No specific tools found for ${intent} tasks.`;
        }

        const toolNames = relevantTools.map(t => t.name).join(', ');
        return `Selected ${relevantTools.length} tools for ${intent}: ${toolNames}`;
    }

    /**
     * Summarize previous results
     */
    private summarizePreviousResults(
        previousResults: Record<string, vscode.LanguageModelToolResult>
    ): string {
        const resultCount = Object.keys(previousResults).length;
        if (resultCount === 0) {
            return 'No previous results.';
        }

        return `${resultCount} previous tool results available.`;
    }

    /**
     * Generate generic multi-round prompt
     */
    private generateGenericMultiRoundPrompt(
        roundNumber: number,
        resultsSummary: string,
        context: ToolCallContext
    ): string {
        return `This is round ${roundNumber} of our conversation.
        
${resultsSummary}

Continue building on the previous results to provide a comprehensive response.`;
    }

    /**
     * Generate basic error recovery prompt
     */
    private generateBasicErrorRecoveryPrompt(
        error: any,
        recoverySuggestions: string[]
    ): string {
        return `⚠️ Tool Error: ${error.toolName} failed with: ${error.error}

Recovery suggestions:
${recoverySuggestions.map(s => `• ${s}`).join('\n')}

I'll continue with an alternative approach.`;
    }

    /**
     * Get recovery strategy description
     */
    private getRecoveryStrategyDescription(strategy: string): string {
        const descriptions: Record<string, string> = {
            retry: 'Retry the operation after a brief delay',
            fallback_tool: 'Use an alternative tool with similar capabilities',
            parameter_correction: 'Correct the parameters and retry',
            graceful_degradation: 'Continue without this specific tool',
            user_intervention: 'Requires user action to resolve',
            abort: 'Cannot recover from this error'
        };

        return descriptions[strategy] || 'Unknown recovery strategy';
    }

    /**
     * Get recovery instructions
     */
    private getRecoveryInstructions(strategy: string): string {
        const instructions: Record<string, string> = {
            retry: 'I will automatically retry this operation.',
            fallback_tool: 'I will try using a similar tool instead.',
            parameter_correction: 'I will adjust the parameters and try again.',
            graceful_degradation: 'I will continue and provide the best response possible without this tool.',
            user_intervention: 'Please check the tool configuration and try again.',
            abort: 'This operation cannot be completed due to the error.'
        };

        return instructions[strategy] || 'No specific instructions available.';
    }

    /**
     * Get basic troubleshooting guide
     */
    private getBasicTroubleshootingGuide(): string {
        return `## Common Tool Issues

**Permission Errors**: Check VS Code workspace trust and file permissions
**Tool Not Found**: Install required extensions and restart VS Code
**Timeout Issues**: Try smaller operations or check network connectivity
**Parameter Errors**: Verify parameter names, types, and formats

The Wu Wei assistant adapts to work around tool limitations while still helping you achieve your goals.`;
    }

    /**
     * Add a custom template
     */
    addTemplate(template: PromptTemplate): void {
        this.templates.set(template.id, template);
    }

    /**
     * Get available templates
     */
    getAvailableTemplates(): PromptTemplate[] {
        return Array.from(this.templates.values());
    }

    /**
     * Initialize default prompt templates
     */
    private initializeDefaultTemplates(): void {
        const defaultTemplates: PromptTemplate[] = [
            {
                id: 'system-prompt-with-tools',
                name: 'System Prompt with Tools',
                template: `You are an AI assistant with access to powerful tools. Use them wisely to provide accurate, helpful responses.

Available tools: {{toolList}}
User intent: {{userIntent}}

Guidelines:
- Use tools when they provide better information than your knowledge
- Explain your tool usage briefly
- Summarize results clearly`,
                variables: ['toolList', 'userIntent']
            },
            {
                id: 'tool-usage-guidance',
                name: 'Tool Usage Guidance',
                template: `For this request about "{{userIntent}}", consider using these tools:
{{suggestedTools}}

This will help you provide accurate, up-to-date information rather than relying on potentially outdated training data.`,
                variables: ['userIntent', 'suggestedTools']
            }
        ];

        // Register templates
        for (const template of defaultTemplates) {
            this.templates.set(template.id, template);
        }
    }

    /**
     * Initialize file-based templates integration
     */
    private initializeFileBasedTemplates(): void {
        // Register commonly used file-based templates
        const fileBasedTemplates = [
            'workspace-analysis-template.md',
            'code-analysis-template.md',
            'debug-assistant-template.md',
            'error-template.md'
        ];

        for (const templateName of fileBasedTemplates) {
            this.templates.set(templateName, {
                id: templateName,
                name: templateName,
                template: '', // Will be loaded dynamically via PromptTemplateLoader
                variables: []
            });
        }
    }
}