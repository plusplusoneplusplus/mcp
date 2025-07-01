import * as vscode from 'vscode';
import { EnhancedToolParticipant, DEFAULT_TOOL_PARTICIPANT_CONFIG } from './index';
import { logger } from '../../logger';

/**
 * Example integration of Enhanced Tool Calling with Wu Wei Chat Participant
 * 
 * This example shows how to integrate the enhanced tool calling framework
 * with the existing chat participant architecture.
 */
export class EnhancedWuWeiIntegration {
    private enhancedParticipant: EnhancedToolParticipant;

    constructor() {
        // Initialize with custom configuration
        this.enhancedParticipant = new EnhancedToolParticipant({
            ...DEFAULT_TOOL_PARTICIPANT_CONFIG,
            maxToolRounds: 3, // Limit to 3 rounds for demo
            debugMode: true,  // Enable debug output
            enableCaching: true,
            enableParallelExecution: true
        });

        logger.info('EnhancedWuWeiIntegration: Initialized enhanced tool calling integration');
    }

    /**
     * Example method showing how to handle enhanced chat requests
     */
    async handleEnhancedChatRequest(
        request: vscode.ChatRequest,
        context: vscode.ChatContext,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<vscode.ChatResult | void> {
        try {
            // Get available language models
            const models = await vscode.lm.selectChatModels();
            if (models.length === 0) {
                stream.markdown('❌ No language models available for enhanced tool calling.');
                return;
            }

            // Use first available model (with tool support)
            let model = models[0];

            // Prefer non-o1 models for tool support
            if (model.vendor === 'copilot' && model.family.startsWith('o1')) {
                const alternativeModels = await vscode.lm.selectChatModels({
                    vendor: 'copilot',
                    family: 'gpt-4o'
                });
                if (alternativeModels.length > 0) {
                    model = alternativeModels[0];
                    logger.info('EnhancedWuWeiIntegration: Switched to gpt-4o for tool support');
                }
            }

            // Get available tools
            const availableTools = this.getAvailableTools();

            stream.markdown(`🚀 **Enhanced Wu Wei Mode Activated**\n\n`);
            stream.markdown(`Tools available: ${availableTools.length}\n\n`);

            // Use the enhanced participant to handle the request
            const result = await this.enhancedParticipant.handleChatRequest(
                request,
                context,
                stream,
                token,
                model,
                availableTools
            );

            return result;

        } catch (error) {
            logger.error('EnhancedWuWeiIntegration: Enhanced request failed', { error });
            stream.markdown(`❌ Enhanced processing failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
            return;
        }
    }

    /**
     * Get available VS Code tools
     */
    private getAvailableTools(): vscode.LanguageModelToolInformation[] {
        try {
            if (vscode.lm && vscode.lm.tools) {
                return Array.from(vscode.lm.tools).map(tool => ({
                    name: tool.name,
                    description: tool.description,
                    inputSchema: tool.inputSchema || {},
                    tags: []
                }));
            }
        } catch (error) {
            logger.debug('EnhancedWuWeiIntegration: Error accessing tools API:', error);
        }

        return [];
    }

    /**
     * Get cache statistics for monitoring
     */
    getCacheStats() {
        return this.enhancedParticipant.getCacheStatistics();
    }

    /**
     * Clear cache
     */
    clearCache() {
        this.enhancedParticipant.clearCache();
    }

    /**
     * Update configuration
     */
    updateConfig(config: any) {
        this.enhancedParticipant.updateConfig(config);
    }
}

/**
 * Factory function to create an enhanced integration instance
 */
export function createEnhancedWuWeiIntegration(): EnhancedWuWeiIntegration {
    return new EnhancedWuWeiIntegration();
} 