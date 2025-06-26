import * as vscode from 'vscode';
import { logger } from '../logger';

/**
 * Wu Wei Chat Participant - MVP Implementation
 * 
 * Embodies the philosophy of 无为而治 (wu wei) - effortless action that flows naturally.
 * Provides a simple VS Code chat participant that responds to @wu-wei mentions.
 */
export class WuWeiChatParticipant {
    private participant: vscode.ChatParticipant;

    constructor(context: vscode.ExtensionContext) {
        // Register the chat participant
        this.participant = vscode.chat.createChatParticipant(
            'wu-wei.assistant',
            this.handleChatRequest.bind(this)
        );

        // Set participant properties
        this.participant.iconPath = new vscode.ThemeIcon('symbol-operator');

        // Add followup suggestions that embody Wu Wei philosophy
        this.participant.followupProvider = {
            provideFollowups: (result, context, token) => {
                return [
                    {
                        prompt: 'Tell me about Wu Wei philosophy',
                        label: '🧘 Wu Wei Philosophy'
                    },
                    {
                        prompt: 'Help me with my current workspace',
                        label: '🏗️ Workspace Help'
                    },
                    {
                        prompt: 'Show me the way of effortless coding',
                        label: '⚡ Effortless Coding'
                    },
                    {
                        prompt: 'How can I work more harmoniously?',
                        label: '☯️ Harmonious Work'
                    },
                    {
                        prompt: 'What tools are available?',
                        label: '🔧 Available Tools'
                    }
                ];
            }
        };

        logger.info('Wu Wei Chat Participant initialized - flowing like water 🌊');

        // Log available tools on initialization
        this.logAvailableTools();
    }

    private async logAvailableTools(): Promise<void> {
        try {
            // Log language models
            const models = await vscode.lm.selectChatModels();
            logger.info('Wu Wei: Available Language Models:', {
                count: models.length,
                models: models.map(m => ({
                    id: m.id,
                    vendor: m.vendor,
                    family: m.family,
                    version: m.version,
                    maxInputTokens: m.maxInputTokens
                }))
            });

            // Log available VS Code tools/commands
            const commands = await vscode.commands.getCommands(true);
            const wuWeiCommands = commands.filter(cmd => cmd.startsWith('wu-wei.'));
            logger.info('Wu Wei: Available Wu Wei Commands:', {
                count: wuWeiCommands.length,
                commands: wuWeiCommands
            });

            // Log workspace information
            const workspaceFolders = vscode.workspace.workspaceFolders;
            logger.info('Wu Wei: Workspace Context:', {
                hasWorkspace: !!workspaceFolders,
                folderCount: workspaceFolders?.length || 0,
                folders: workspaceFolders?.map(f => ({
                    name: f.name,
                    uri: f.uri.toString()
                }))
            });

            // Log available tools that could be used
            logger.info('Wu Wei: Tool Capabilities Available:', {
                languageModels: models.length > 0,
                workspace: !!workspaceFolders,
                fileSystem: true, // VS Code always has file system access
                commands: wuWeiCommands.length,
                chat: true // We have chat capability
            });

        } catch (error) {
            logger.error('Wu Wei: Failed to log available tools', { error });
        }
    }

    private async handleChatRequest(
        request: vscode.ChatRequest,
        context: vscode.ChatContext,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<void> {
        try {
            logger.info(`Wu Wei chat request received: "${request.prompt}"`);

            // Check for tool-related requests
            if (request.prompt.toLowerCase().includes('tools') || request.prompt.toLowerCase().includes('what can you do')) {
                await this.handleToolsRequest(stream);
                return;
            }

            // Check for workspace-related requests
            if (request.prompt.toLowerCase().includes('workspace') || request.prompt.toLowerCase().includes('current project')) {
                await this.handleWorkspaceRequest(stream);
                return;
            }

            // Get language model (reuse existing logic from UnifiedChatProvider)
            const models = await vscode.lm.selectChatModels();
            if (models.length === 0) {
                stream.markdown('❌ No language models available. Please install GitHub Copilot or another language model extension to experience the flow of Wu Wei.');
                return;
            }

            // Log request details
            logger.info('Wu Wei: Processing chat request with tools:', {
                prompt: request.prompt,
                modelCount: models.length,
                selectedModel: models[0].id
            });

            // Get the system prompt from configuration, with Wu Wei philosophy as default
            const config = vscode.workspace.getConfiguration('wu-wei');
            const systemPromptConfig = config.get<string>('systemPrompt',
                'You are Wu Wei, an AI assistant that embodies the philosophy of 无为而治 (wu wei) - effortless action that flows naturally like water. You provide thoughtful, gentle guidance while maintaining harmony and balance. Your responses are wise, concise, and flow naturally without forcing solutions.'
            );

            // Enhance system prompt with tool awareness
            const enhancedSystemPrompt = `${systemPromptConfig}

You have access to various tools and capabilities:
- Workspace information and file system access
- VS Code commands and functionality  
- Wu Wei-specific commands and features
- Current project context and structure

When users ask about tools, workspace, or capabilities, provide helpful information about what you can do.`;

            // Prepare system message with Wu Wei philosophy
            const systemMessage = vscode.LanguageModelChatMessage.User(enhancedSystemPrompt);

            // Prepare user message with context
            const contextualPrompt = await this.addContextToPrompt(request.prompt);
            const userMessage = vscode.LanguageModelChatMessage.User(contextualPrompt);

            // Send request to language model
            const chatResponse = await models[0].sendRequest(
                [systemMessage, userMessage],
                {},
                token
            );

            // Stream the response with Wu Wei grace
            let responseText = '';
            for await (const fragment of chatResponse.text) {
                responseText += fragment;
                stream.markdown(fragment);
            }

            logger.info(`Wu Wei chat response completed (${responseText.length} characters) - harmony achieved ☯️`);

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            logger.error('Wu Wei chat request failed - disruption in the flow', { error: errorMessage });

            // Provide a Wu Wei-style error message
            stream.markdown(`❌ **The flow has been disrupted**
            
Error: ${errorMessage}

*"In the midst of winter, I found there was, within me, an invincible summer."* - Albert Camus

The way of Wu Wei teaches us that obstacles are temporary. Please try again, and let the natural flow guide us.`);
        }
    }

    private async handleToolsRequest(stream: vscode.ChatResponseStream): Promise<void> {
        logger.info('Wu Wei: Handling tools request');

        const models = await vscode.lm.selectChatModels();
        const commands = await vscode.commands.getCommands(true);
        const wuWeiCommands = commands.filter(cmd => cmd.startsWith('wu-wei.'));
        const workspaceFolders = vscode.workspace.workspaceFolders;

        stream.markdown(`# 🔧 Wu Wei Tools & Capabilities

*Following the principle of 无为而治 - tools that work with natural flow*

## 🤖 Language Models Available
${models.length > 0 ?
                models.map(m => `- **${m.id}** (${m.vendor}/${m.family}) - ${m.maxInputTokens} tokens`).join('\n') :
                '- No language models currently available'
            }

## 🏗️ Workspace Tools
${workspaceFolders ?
                `- **Active Workspace**: ${workspaceFolders.map(f => f.name).join(', ')}
- **File System Access**: Available for reading/writing files
- **Project Structure**: Can analyze and navigate your codebase` :
                '- No workspace currently open'
            }

## ⚡ Wu Wei Commands Available
${wuWeiCommands.length > 0 ?
                wuWeiCommands.map(cmd => `- \`${cmd}\``).join('\n') :
                '- Wu Wei commands loading...'
            }

## 🌊 Natural Capabilities
- **Chat Integration**: Native VS Code chat participant
- **Configuration**: Respects your Wu Wei settings
- **Logging**: Detailed activity tracking
- **Philosophy**: Every interaction embodies effortless action

*Ask me about any of these capabilities, and I'll guide you through their harmonious use.*`);
    }

    private async handleWorkspaceRequest(stream: vscode.ChatResponseStream): Promise<void> {
        logger.info('Wu Wei: Handling workspace request');

        const workspaceFolders = vscode.workspace.workspaceFolders;
        const activeEditor = vscode.window.activeTextEditor;

        if (!workspaceFolders) {
            stream.markdown(`# 🏗️ Workspace Flow

No workspace is currently open. Like an empty meditation hall, we have infinite potential.

To begin the Wu Wei development flow:
1. Open a folder in VS Code
2. Let the natural structure emerge
3. Allow harmony between code and intention

*"The sage does not attempt anything very big, and thus achieves greatness."*`);
            return;
        }

        stream.markdown(`# 🏗️ Current Workspace Flow

*Observing the natural structure of your development environment*

## 📁 Workspace Structure
${workspaceFolders.map(folder => `- **${folder.name}**\n  \`${folder.uri.fsPath}\``).join('\n')}

## 📄 Current Context
${activeEditor ?
                `- **Active File**: \`${activeEditor.document.fileName}\`
- **Language**: ${activeEditor.document.languageId}
- **Lines**: ${activeEditor.document.lineCount}` :
                '- No file currently active'
            }

## 🌊 Wu Wei Recommendations
- **Flow with Structure**: Your workspace shows natural organization
- **Embrace Simplicity**: Focus on what truly matters
- **Maintain Harmony**: Balance between features and clarity

*How can I help you work more effortlessly with this workspace?*`);
    }

    private async addContextToPrompt(prompt: string): Promise<string> {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        const activeEditor = vscode.window.activeTextEditor;

        let context = prompt;

        if (workspaceFolders) {
            context += `\n\nWorkspace Context: Working in ${workspaceFolders.map(f => f.name).join(', ')}`;
        }

        if (activeEditor) {
            context += `\nCurrent File: ${activeEditor.document.fileName} (${activeEditor.document.languageId})`;
        }

        return context;
    }

    public dispose(): void {
        // Cleanup - releasing like autumn leaves
        this.participant?.dispose();
        logger.info('Wu Wei Chat Participant disposed - returning to the source 🍃');
    }
}
