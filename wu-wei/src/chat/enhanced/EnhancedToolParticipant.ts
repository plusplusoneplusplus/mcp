import * as vscode from 'vscode';
import { logger } from '../../logger';
import {
    ToolWorkflowResult,
    ToolParticipantConfig,
    DEFAULT_TOOL_PARTICIPANT_CONFIG,
    ToolCallContext
} from './types';
import { ToolCallOrchestrator } from './ToolCallOrchestrator';
import { ToolResultManager } from './ToolResultManager';
import { PromptTemplateEngine } from './PromptTemplateEngine';

/**
 * Enhanced Tool Participant - Main orchestrator for tool-enabled conversations
 * 
 * This class provides sophisticated tool calling capabilities including:
 * - Multi-round tool execution loops
 * - Intelligent tool selection based on user intent
 * - Context-aware prompt generation
 * - Tool result integration and summarization
 */
export class EnhancedToolParticipant {
    private config: ToolParticipantConfig;
    private toolCallOrchestrator: ToolCallOrchestrator;
    private toolResultManager: ToolResultManager;
    private promptTemplateEngine: PromptTemplateEngine;

    constructor(config: Partial<ToolParticipantConfig> = {}) {
        this.config = { ...DEFAULT_TOOL_PARTICIPANT_CONFIG, ...config };

        // Initialize components
        this.toolResultManager = new ToolResultManager(this.config.enableCaching);
        this.promptTemplateEngine = new PromptTemplateEngine();
        this.toolCallOrchestrator = new ToolCallOrchestrator(
            this.config,
            this.toolResultManager,
            this.promptTemplateEngine
        );

        logger.info('EnhancedToolParticipant: Initialized with enhanced tool calling capabilities', {
            maxRounds: this.config.maxToolRounds,
            cachingEnabled: this.config.enableCaching,
            parallelExecution: this.config.enableParallelExecution,
            debugMode: this.config.debugMode
        });
    }

    /**
     * Handle a chat request with enhanced tool calling capabilities
     */
    async handleChatRequest(
        request: vscode.ChatRequest,
        context: vscode.ChatContext,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken,
        model: vscode.LanguageModelChat,
        availableTools: vscode.LanguageModelToolInformation[]
    ): Promise<vscode.ChatResult | void> {
        const startTime = Date.now();

        try {
            logger.info('EnhancedToolParticipant: Processing enhanced chat request', {
                prompt: request.prompt.substring(0, 100),
                toolsAvailable: availableTools.length,
                historyLength: context.history.length
            });

            // Analyze user intent and suggest tools
            const intentAnalysis = this.promptTemplateEngine.analyzeUserIntentForTools(
                request.prompt,
                availableTools
            );

            if (this.config.debugMode) {
                stream.markdown(`🔍 **Intent Analysis**: ${intentAnalysis.reasoning} (confidence: ${Math.round(intentAnalysis.confidence * 100)}%)\n\n`);
            }

            // Prepare enhanced system prompt
            const baseSystemPrompt = this.getBaseSystemPrompt();
            const toolCallContext: ToolCallContext = {
                userIntent: request.prompt,
                availableTools,
                conversationHistory: this.buildConversationHistory(context),
                previousResults: {},
                roundNumber: 1
            };

            const enhancedSystemPrompt = this.promptTemplateEngine.generateToolAwareSystemPrompt(
                baseSystemPrompt,
                availableTools,
                toolCallContext
            );

            // Build messages with enhanced context
            const messages = this.buildEnhancedMessages(
                enhancedSystemPrompt,
                request,
                context,
                intentAnalysis
            );

            // Set up language model options
            const options: vscode.LanguageModelChatRequestOptions = {
                justification: 'Enhanced Wu Wei assistant providing comprehensive development support with intelligent tool usage',
                tools: availableTools.length > 0 ? availableTools : undefined
            };

            // Execute the enhanced workflow
            const workflowResult = await this.toolCallOrchestrator.executeWorkflow(
                model,
                messages,
                options,
                stream,
                token,
                request.prompt
            );

            // Display workflow summary if debug mode is enabled
            if (this.config.debugMode) {
                this.displayWorkflowSummary(stream, workflowResult);
            }

            // Log completion metrics
            this.logCompletionMetrics(workflowResult, startTime);

            // Return enhanced metadata
            return {
                metadata: {
                    enhancedToolWorkflow: workflowResult,
                    intentAnalysis,
                    executionTime: Date.now() - startTime,
                    toolsUsed: workflowResult.metadata.toolsUsed,
                    cacheHits: workflowResult.metadata.cacheHits
                }
            };

        } catch (error) {
            logger.error('EnhancedToolParticipant: Request processing failed', {
                error: error instanceof Error ? error.message : 'Unknown error',
                executionTime: Date.now() - startTime
            });

            stream.markdown(`❌ **Enhanced tool processing failed**: ${error instanceof Error ? error.message : 'Unknown error'}\n\nFalling back to basic response mode.`);

            return {
                metadata: {
                    error: error instanceof Error ? error.message : 'Unknown error',
                    executionTime: Date.now() - startTime
                }
            };
        }
    }

    /**
     * Get cache statistics for monitoring
     */
    getCacheStatistics(): { size: number; hitRate: number; oldestEntry: number | null } {
        return this.toolResultManager.getCacheStats();
    }

    /**
     * Clear all cached results
     */
    clearCache(): void {
        this.toolResultManager.clearCache();
        logger.info('EnhancedToolParticipant: Cache cleared');
    }

    /**
     * Update configuration
     */
    updateConfig(newConfig: Partial<ToolParticipantConfig>): void {
        this.config = { ...this.config, ...newConfig };
        logger.info('EnhancedToolParticipant: Configuration updated', { newConfig });
    }

    /**
     * Get current configuration
     */
    getConfig(): ToolParticipantConfig {
        return { ...this.config };
    }

    /**
     * Add custom prompt template
     */
    addPromptTemplate(template: any): void {
        this.promptTemplateEngine.addTemplate(template);
        logger.debug('EnhancedToolParticipant: Custom template added', { templateId: template.id });
    }

    /**
     * Get available prompt templates
     */
    getAvailableTemplates(): any[] {
        return this.promptTemplateEngine.getAvailableTemplates();
    }

    /**
     * Get base system prompt from configuration or default
     */
    private getBaseSystemPrompt(): string {
        const config = vscode.workspace.getConfiguration('wu-wei');
        const basePrompt = config.get<string>('systemPrompt', '');

        if (basePrompt) {
            return basePrompt;
        }

        // Default enhanced system prompt
        return `You are Wu Wei, an advanced AI coding assistant that embodies the philosophy of 无为而治 (wu wei) - effortless action that flows naturally like water.

You have access to powerful tools that allow you to provide accurate, real-time information about codebases, files, and development environments. Use these tools wisely to provide comprehensive, helpful responses.

Your approach:
- Flow naturally with the user's needs
- Use tools when they provide better information than your training data
- Provide thoughtful, actionable guidance
- Maintain harmony between efficiency and thoroughness
- Explain your reasoning clearly but concisely

Remember: Your goal is to provide the most helpful response possible by combining your knowledge with real-time tool insights.`;
    }

    /**
     * Build conversation history from context
     */
    private buildConversationHistory(context: vscode.ChatContext): vscode.LanguageModelChatMessage[] {
        const messages: vscode.LanguageModelChatMessage[] = [];

        for (const turn of context.history) {
            if (turn instanceof vscode.ChatRequestTurn) {
                messages.push(vscode.LanguageModelChatMessage.User(turn.prompt));
            } else if (turn instanceof vscode.ChatResponseTurn) {
                // Extract response text from the turn
                const responseText = this.extractResponseText(turn);
                if (responseText) {
                    messages.push(vscode.LanguageModelChatMessage.Assistant(responseText));
                }
            }
        }

        return messages;
    }

    /**
     * Extract response text from a chat response turn
     */
    private extractResponseText(turn: vscode.ChatResponseTurn): string {
        try {
            // This is a simplified extraction - in practice, you might need to handle
            // different response formats based on the VS Code API
            return turn.response.map(part => {
                if (part instanceof vscode.ChatResponseMarkdownPart) {
                    return part.value.value;
                }
                return '';
            }).join('');
        } catch (error) {
            logger.debug('EnhancedToolParticipant: Failed to extract response text', { error });
            return '';
        }
    }

    /**
     * Build enhanced messages with intent analysis
     */
    private buildEnhancedMessages(
        systemPrompt: string,
        request: vscode.ChatRequest,
        context: vscode.ChatContext,
        intentAnalysis: any
    ): vscode.LanguageModelChatMessage[] {
        const messages: vscode.LanguageModelChatMessage[] = [];

        // Add enhanced system prompt
        messages.push(vscode.LanguageModelChatMessage.User(systemPrompt));

        // Add conversation history
        const history = this.buildConversationHistory(context);
        messages.push(...history);

        // Add enhanced user prompt with intent context
        let enhancedUserPrompt = request.prompt;

        if (intentAnalysis.selectedTools.length > 0) {
            enhancedUserPrompt += `\n\n[Assistant: Based on this request, consider using these tools: ${intentAnalysis.selectedTools.join(', ')}. ${intentAnalysis.reasoning}]`;
        }

        messages.push(vscode.LanguageModelChatMessage.User(enhancedUserPrompt));

        return messages;
    }

    /**
     * Display workflow summary in debug mode
     */
    private displayWorkflowSummary(stream: vscode.ChatResponseStream, result: ToolWorkflowResult): void {
        stream.markdown(`\n---\n**🔧 Workflow Summary**\n`);
        stream.markdown(`- **Rounds executed**: ${result.metadata.totalRounds}\n`);
        stream.markdown(`- **Tools used**: ${result.metadata.toolsUsed.join(', ') || 'None'}\n`);
        stream.markdown(`- **Execution time**: ${result.metadata.executionTime}ms\n`);
        stream.markdown(`- **Cache hits**: ${result.metadata.cacheHits}\n`);

        if (result.metadata.errors.length > 0) {
            stream.markdown(`- **Errors**: ${result.metadata.errors.length}\n`);
        }

        stream.markdown(`\n${result.conversationSummary}\n---\n\n`);
    }

    /**
     * Log completion metrics for monitoring
     */
    private logCompletionMetrics(result: ToolWorkflowResult, startTime: number): void {
        logger.info('EnhancedToolParticipant: Request completed', {
            totalExecutionTime: Date.now() - startTime,
            workflowExecutionTime: result.metadata.executionTime,
            toolRounds: result.metadata.totalRounds,
            toolsUsed: result.metadata.toolsUsed,
            toolCallsExecuted: Object.keys(result.toolCallResults).length,
            cacheHits: result.metadata.cacheHits,
            errors: result.metadata.errors.length,
            success: result.metadata.errors.length === 0
        });
    }
} 