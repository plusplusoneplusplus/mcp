import * as vscode from 'vscode';
import { logger } from '../../logger';
import { PromptTemplate, ToolCallContext, ToolSelectionResult } from './types';

/**
 * Generates context-aware prompts for tool usage
 */
export class PromptTemplateEngine {
    private templates: Map<string, PromptTemplate> = new Map();

    constructor() {
        this.initializeDefaultTemplates();
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

        return this.interpolateTemplate(template, {
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

        return this.interpolateTemplate(template, {
            roundNumber: roundNumber.toString(),
            resultsSummary,
            userIntent: context.userIntent,
            contextInfo: this.summarizeContext(context)
        });
    }

    /**
     * Generate error recovery prompts
     */
    generateErrorRecoveryPrompt(
        failedToolName: string,
        error: string,
        context: ToolCallContext
    ): string {
        const template = this.templates.get('error-recovery');

        if (!template) {
            return `The tool "${failedToolName}" encountered an error: ${error}. Please try an alternative approach or explain what information you need to help the user.`;
        }

        return this.interpolateTemplate(template, {
            failedToolName,
            error,
            userIntent: context.userIntent,
            alternativeTools: this.suggestAlternativeTools(failedToolName, context).join(', ')
        });
    }

    /**
     * Add or update a custom template
     */
    addTemplate(template: PromptTemplate): void {
        this.templates.set(template.id, template);
        logger.debug(`PromptTemplateEngine: Added template ${template.id}`, {
            templateName: template.name,
            toolSpecific: template.toolSpecific
        });
    }

    /**
     * Get all available templates
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
            },
            {
                id: 'multi-round-context',
                name: 'Multi-round Context',
                template: `This is round {{roundNumber}} of tool execution.

Previous results summary:
{{resultsSummary}}

Continue working on: {{userIntent}}

{{contextInfo}}`,
                variables: ['roundNumber', 'resultsSummary', 'userIntent', 'contextInfo']
            },
            {
                id: 'error-recovery',
                name: 'Error Recovery',
                template: `The tool "{{failedToolName}}" failed with error: {{error}}

For the user's request about "{{userIntent}}", consider these alternatives:
{{alternativeTools}}

Please try a different approach or explain what information you need.`,
                variables: ['failedToolName', 'error', 'userIntent', 'alternativeTools']
            }
        ];

        for (const template of defaultTemplates) {
            this.templates.set(template.id, template);
        }

        logger.debug(`PromptTemplateEngine: Initialized ${defaultTemplates.length} default templates`);
    }

    /**
     * Generate tool guidance based on available tools and context
     */
    private generateToolGuidance(
        availableTools: vscode.LanguageModelToolInformation[],
        context: ToolCallContext
    ): string {
        if (availableTools.length === 0) {
            return 'Currently no tools are available.';
        }

        const toolCategories = this.categorizeTools(availableTools);
        const relevantTools = this.identifyRelevantTools(context.userIntent, availableTools);

        let guidance = `Here are your available tools:\n`;

        // Add categorized tool information
        for (const [category, tools] of Object.entries(toolCategories)) {
            if (tools.length > 0) {
                guidance += `\n**${category}**: ${tools.map(t => t.name).join(', ')}`;
            }
        }

        // Add specific recommendations
        if (relevantTools.length > 0) {
            guidance += `\n\n**Recommended for this request**: ${relevantTools.map(t => t.name).join(', ')}`;
        }

        return guidance;
    }

    /**
     * Generate contextual guidance based on the current context
     */
    private generateContextualGuidance(context: ToolCallContext): string {
        let guidance = '';

        if (context.roundNumber > 1) {
            guidance += `\n## Context: This is round ${context.roundNumber} of our conversation.`;

            if (Object.keys(context.previousResults).length > 0) {
                guidance += ` You have previous tool results to build upon.`;
            }
        }

        if (context.userIntent) {
            guidance += `\n## User's Goal: ${context.userIntent}`;
        }

        return guidance;
    }

    /**
     * Get tool-specific template if available
     */
    private getToolSpecificTemplate(toolName: string): PromptTemplate | undefined {
        return Array.from(this.templates.values()).find(
            t => t.toolSpecific && t.targetTool === toolName
        );
    }

    /**
     * Generate generic tool prompt
     */
    private generateGenericToolPrompt(
        toolName: string,
        userIntent: string,
        context: ToolCallContext
    ): string {
        return `Use the "${toolName}" tool to help with: ${userIntent}

Context: ${this.summarizeContext(context)}

Please use this tool effectively and explain the results clearly.`;
    }

    /**
     * Interpolate template variables
     */
    private interpolateTemplate(template: PromptTemplate, variables: Record<string, string>): string {
        let result = template.template;

        for (const [key, value] of Object.entries(variables)) {
            const placeholder = `{{${key}}}`;
            result = result.replace(new RegExp(placeholder, 'g'), value || '');
        }

        return result;
    }

    /**
     * Summarize context for prompt inclusion
     */
    private summarizeContext(context: ToolCallContext): string {
        const parts: string[] = [];

        if (context.availableTools.length > 0) {
            parts.push(`${context.availableTools.length} tools available`);
        }

        if (context.conversationHistory.length > 0) {
            parts.push(`${context.conversationHistory.length} previous messages`);
        }

        if (Object.keys(context.previousResults).length > 0) {
            parts.push(`${Object.keys(context.previousResults).length} previous tool results`);
        }

        return parts.length > 0 ? parts.join(', ') : 'No additional context';
    }

    /**
     * Extract user intent from prompt
     */
    private extractUserIntent(userPrompt: string): string {
        // Simplified intent extraction - in a production system, this could use NLP
        const prompt = userPrompt.toLowerCase();

        if (prompt.includes('analyze') || prompt.includes('review')) {
            return 'analysis';
        }
        if (prompt.includes('find') || prompt.includes('search')) {
            return 'search';
        }
        if (prompt.includes('create') || prompt.includes('generate')) {
            return 'creation';
        }
        if (prompt.includes('fix') || prompt.includes('debug')) {
            return 'debugging';
        }
        if (prompt.includes('explain') || prompt.includes('understand')) {
            return 'explanation';
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
        // Simplified tool matching - in production, this could be more sophisticated
        const intentKeywords: Record<string, string[]> = {
            'analysis': ['analyze', 'review', 'inspect', 'examine'],
            'search': ['find', 'search', 'locate', 'query'],
            'creation': ['create', 'generate', 'build', 'make'],
            'debugging': ['debug', 'fix', 'diagnose', 'troubleshoot'],
            'explanation': ['explain', 'describe', 'detail', 'clarify']
        };

        const keywords = intentKeywords[intent] || [];

        return availableTools.filter(tool => {
            const toolDesc = (tool.description || '').toLowerCase();
            const toolName = tool.name.toLowerCase();

            return keywords.some(keyword =>
                toolDesc.includes(keyword) || toolName.includes(keyword)
            );
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
        if (intent === 'general') return 0.3;

        // Higher confidence for specific intents with matching tools
        return Math.min(0.9, 0.5 + (relevantTools.length * 0.1));
    }

    /**
     * Generate reasoning for tool selection
     */
    private generateSelectionReasoning(
        intent: string,
        relevantTools: vscode.LanguageModelToolInformation[]
    ): string {
        if (relevantTools.length === 0) {
            return `No tools specifically match the intent "${intent}"`;
        }

        return `Selected ${relevantTools.length} tools that match the intent "${intent}": ${relevantTools.map(t => t.name).join(', ')}`;
    }

    /**
     * Categorize tools by type/purpose
     */
    private categorizeTools(
        tools: vscode.LanguageModelToolInformation[]
    ): Record<string, vscode.LanguageModelToolInformation[]> {
        const categories: Record<string, vscode.LanguageModelToolInformation[]> = {
            'File Operations': [],
            'Code Analysis': [],
            'Search & Query': [],
            'Development': [],
            'Other': []
        };

        for (const tool of tools) {
            const name = tool.name.toLowerCase();
            const desc = (tool.description || '').toLowerCase();

            if (name.includes('file') || desc.includes('file')) {
                categories['File Operations'].push(tool);
            } else if (name.includes('code') || desc.includes('analyze')) {
                categories['Code Analysis'].push(tool);
            } else if (name.includes('search') || name.includes('find')) {
                categories['Search & Query'].push(tool);
            } else if (name.includes('git') || name.includes('debug')) {
                categories['Development'].push(tool);
            } else {
                categories['Other'].push(tool);
            }
        }

        return categories;
    }

    /**
     * Identify relevant tools for user intent
     */
    private identifyRelevantTools(
        userIntent: string,
        availableTools: vscode.LanguageModelToolInformation[]
    ): vscode.LanguageModelToolInformation[] {
        const intent = this.extractUserIntent(userIntent);
        return this.matchToolsToIntent(intent, availableTools);
    }

    /**
     * Summarize previous tool results
     */
    private summarizePreviousResults(results: Record<string, vscode.LanguageModelToolResult>): string {
        if (Object.keys(results).length === 0) {
            return 'No previous results';
        }

        const summaries: string[] = [];
        for (const [callId, result] of Object.entries(results)) {
            try {
                const summary = String(result).substring(0, 100);
                summaries.push(`${callId}: ${summary}${String(result).length > 100 ? '...' : ''}`);
            } catch (error) {
                summaries.push(`${callId}: [Result processing failed]`);
            }
        }

        return summaries.join('\n');
    }

    /**
     * Generate generic multi-round prompt
     */
    private generateGenericMultiRoundPrompt(
        roundNumber: number,
        resultsSummary: string,
        context: ToolCallContext
    ): string {
        return `This is round ${roundNumber} of tool execution.

Previous results:
${resultsSummary}

Continue working on: ${context.userIntent}

Use the available tools to build upon the previous results and provide a comprehensive response.`;
    }

    /**
     * Suggest alternative tools when one fails
     */
    private suggestAlternativeTools(failedToolName: string, context: ToolCallContext): string[] {
        // Simple alternative suggestion based on tool categories
        const alternatives = context.availableTools
            .filter(tool => tool.name !== failedToolName)
            .slice(0, 3) // Limit to 3 alternatives
            .map(tool => tool.name);

        return alternatives;
    }
} 