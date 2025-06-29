import * as vscode from 'vscode';
import { logger } from '../logger';
import { PromptTemplateLoader } from './PromptTemplateLoader';
import { ToolManager } from './ToolManager';
import { MessageBuilder } from './MessageBuilder';
import { RequestRouter } from './RequestRouter';
import { RequestHandlers } from './RequestHandlers';
import { WorkspaceAnalyzer } from './WorkspaceAnalyzer';
import { ConversationOrchestrator } from './ConversationOrchestrator';
import { WuWeiToolMetadata } from './types';
import { EnhancedToolParticipant, DEFAULT_TOOL_PARTICIPANT_CONFIG } from './enhanced';

// Re-export types for backward compatibility
export { WuWeiToolMetadata, ToolCallsMetadata, ToolCallRound, isWuWeiToolMetadata } from './types';

/**
 * Wu Wei Chat Participant - Coding-Focused Assistant with Tools Support
 * 
 * A powerful coding assistant that helps with development tasks using VS Code tools.
 * Focuses on practical coding assistance, debugging, and development workflow optimization.
 * 
 * This class now uses a modular architecture with separate components for:
 * - Tool management and invocation
 * - Message building and metadata handling
 * - Request routing and analysis
 * - Workspace analysis and context gathering
 * - Conversation orchestration with tools
 */
export class WuWeiChatParticipant {
    private participant: vscode.ChatParticipant;
    private toolManager: ToolManager;
    private messageBuilder: MessageBuilder;
    private requestRouter: RequestRouter;
    private requestHandlers: RequestHandlers;
    private workspaceAnalyzer: WorkspaceAnalyzer;
    private conversationOrchestrator: ConversationOrchestrator;
    private enhancedToolParticipant?: EnhancedToolParticipant;
    private useEnhancedMode: boolean;

    constructor(context: vscode.ExtensionContext) {
        // Initialize modular components
        this.toolManager = new ToolManager();
        this.messageBuilder = new MessageBuilder();
        this.requestRouter = new RequestRouter();
        this.workspaceAnalyzer = new WorkspaceAnalyzer();
        this.requestHandlers = new RequestHandlers(this.toolManager, this.workspaceAnalyzer);
        this.conversationOrchestrator = new ConversationOrchestrator(this.toolManager, this.messageBuilder);

        // Initialize enhanced tool participant
        const config = vscode.workspace.getConfiguration('wu-wei');
        this.useEnhancedMode = config.get<boolean>('enhancedToolCalling', true);

        if (this.useEnhancedMode) {
            this.enhancedToolParticipant = new EnhancedToolParticipant({
                ...DEFAULT_TOOL_PARTICIPANT_CONFIG,
                debugMode: config.get<boolean>('debugMode', false),
                maxToolRounds: config.get<number>('maxToolRounds', 5),
                enableCaching: config.get<boolean>('enableToolCaching', true),
                enableParallelExecution: config.get<boolean>('enableParallelToolExecution', true)
            });
        }

        // Register the chat participant
        this.participant = vscode.chat.createChatParticipant(
            'wu-wei.assistant',
            this.handleChatRequest.bind(this)
        );

        // Set participant properties
        this.participant.iconPath = new vscode.ThemeIcon('code');

        logger.info(`Wu Wei Coding Assistant initialized in ${this.useEnhancedMode ? 'ENHANCED' : 'STANDARD'} MODE with modular architecture - ready to autonomously assist with development tasks 🤖`);

        // Log available tools on initialization
        this.toolManager.logAvailableTools();
    }

    private async handleChatRequest(
        request: vscode.ChatRequest,
        context: vscode.ChatContext,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<vscode.ChatResult | void> {
        try {
            logger.info(`Wu Wei Coding Assistant request: "${request.prompt}"`);

            // Handle special commands
            const requestType = this.requestRouter.getRequestType(request.prompt);

            // For special requests, handle them directly
            switch (requestType) {
                case 'tools':
                    await this.requestHandlers.handleToolsRequest(stream);
                    return;
                case 'workspace':
                    await this.requestHandlers.handleWorkspaceRequest(stream);
                    return;
                case 'code-analysis':
                    await this.requestHandlers.handleCodeAnalysisRequest(stream, request);
                    // Continue to normal processing
                    break;
                case 'debugging':
                    await this.requestHandlers.handleDebuggingRequest(stream);
                    // Continue to normal processing
                    break;
            }

            // Get language model
            let models = await vscode.lm.selectChatModels();
            if (models.length === 0) {
                stream.markdown(PromptTemplateLoader.getNoModelsTemplate());
                return;
            }

            // Use a non-o1 model if o1 is selected (o1 models don't support tools yet)
            let model = request.model || models[0];
            if (model.vendor === 'copilot' && model.family.startsWith('o1')) {
                const alternativeModels = await vscode.lm.selectChatModels({
                    vendor: 'copilot',
                    family: 'gpt-4o'
                });
                if (alternativeModels.length > 0) {
                    model = alternativeModels[0];
                    logger.info('Wu Wei Coding Assistant: Switched from o1 to gpt-4o for tool support');
                }
            }

            // Get available tools
            const tools = this.toolManager.getAvailableTools();

            // Log tool availability for this request
            logger.info(`Wu Wei Coding Assistant: Tool setup for request`, {
                toolsAvailable: tools.length,
                toolNames: tools.map(t => t.name).slice(0, 10),
                hasTools: tools.length > 0,
                enhancedMode: this.useEnhancedMode
            });

            // Use enhanced tool participant if enabled and tools are available
            if (this.useEnhancedMode && this.enhancedToolParticipant && tools.length > 0) {
                logger.info('Wu Wei Coding Assistant: Using enhanced tool calling mode');
                return await this.enhancedToolParticipant.handleChatRequest(
                    request,
                    context,
                    stream,
                    token,
                    model,
                    tools
                );
            }

            // Fall back to standard mode
            logger.info('Wu Wei Coding Assistant: Using standard tool calling mode');

            // Set up options for the language model
            const options: vscode.LanguageModelChatRequestOptions = {
                justification: 'To provide coding assistance and development support with natural tool usage',
                tools: tools.length > 0 ? tools : undefined
            };

            // Get enhanced system prompt with tool awareness
            const config = vscode.workspace.getConfiguration('wu-wei');
            const basePrompt = config.get<string>('systemPrompt', PromptTemplateLoader.getBaseSystemPrompt());
            const systemPrompt = this.messageBuilder.getEnhancedSystemPrompt(basePrompt, tools.length > 0);

            // Check if this prompt should trigger tool usage
            const toolAnalysis = this.requestRouter.shouldUseTool(request.prompt);
            logger.info(`Wu Wei Coding Assistant: Prompt analysis`, {
                shouldUseTool: toolAnalysis.shouldUse,
                reason: toolAnalysis.reason,
                suggestedTools: toolAnalysis.suggestedTools,
                prompt: request.prompt.substring(0, 100)
            });

            // Prepare chat history with previous tool calls if any
            const previousMetadata = this.messageBuilder.extractToolMetadata(context);

            // Enhance system prompt with specific guidance for this request
            let enhancedSystemPrompt = systemPrompt;
            if (toolAnalysis.shouldUse && toolAnalysis.suggestedTools.length > 0) {
                enhancedSystemPrompt += `\n\n**FOR THIS SPECIFIC REQUEST:** The user is asking "${request.prompt}". ${toolAnalysis.reason}. You MUST start by using one or more of these tools: ${toolAnalysis.suggestedTools.join(', ')}. Do not provide a generic response - examine the actual codebase first.`;
            }

            const messages = this.messageBuilder.buildMessages(enhancedSystemPrompt, request, context, previousMetadata);

            // Execute the conversation with tools
            const result = await this.conversationOrchestrator.runWithTools(model, messages, options, stream, token, previousMetadata, request);

            return result;

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            logger.error('Wu Wei Coding Assistant request failed', { error: errorMessage });

            stream.markdown(PromptTemplateLoader.getErrorTemplate(errorMessage));
        }
    }

    public dispose(): void {
        this.participant?.dispose();
        logger.info('Wu Wei Coding Assistant disposed 🔧');
    }

    /**
     * Toggle enhanced tool calling mode
     */
    public toggleEnhancedMode(enabled: boolean): void {
        const wasEnabled = this.useEnhancedMode;
        this.useEnhancedMode = enabled;

        if (enabled && !this.enhancedToolParticipant) {
            // Initialize enhanced participant if not already done
            const config = vscode.workspace.getConfiguration('wu-wei');
            this.enhancedToolParticipant = new EnhancedToolParticipant({
                ...DEFAULT_TOOL_PARTICIPANT_CONFIG,
                debugMode: config.get<boolean>('debugMode', false),
                maxToolRounds: config.get<number>('maxToolRounds', 5),
                enableCaching: config.get<boolean>('enableToolCaching', true),
                enableParallelExecution: config.get<boolean>('enableParallelToolExecution', true)
            });
        }

        logger.info(`Wu Wei Coding Assistant: Enhanced mode ${enabled ? 'enabled' : 'disabled'}`, {
            previousState: wasEnabled,
            newState: enabled
        });
    }

    /**
     * Get enhanced tool participant statistics
     */
    public getEnhancedModeStats(): any {
        if (this.useEnhancedMode && this.enhancedToolParticipant) {
            return {
                enabled: this.useEnhancedMode,
                cacheStats: this.enhancedToolParticipant.getCacheStatistics(),
                config: this.enhancedToolParticipant.getConfig()
            };
        }
        return {
            enabled: false,
            cacheStats: null,
            config: null
        };
    }

    /**
     * Clear enhanced mode cache
     */
    public clearEnhancedCache(): void {
        if (this.enhancedToolParticipant) {
            this.enhancedToolParticipant.clearCache();
            logger.info('Wu Wei Coding Assistant: Enhanced mode cache cleared');
        }
    }

    /**
     * Update enhanced mode configuration
     */
    public updateEnhancedConfig(config: any): void {
        if (this.enhancedToolParticipant) {
            this.enhancedToolParticipant.updateConfig(config);
            logger.info('Wu Wei Coding Assistant: Enhanced mode configuration updated', { config });
        }
    }
}
