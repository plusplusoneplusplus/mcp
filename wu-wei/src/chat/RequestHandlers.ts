import * as vscode from 'vscode';
import { logger } from '../logger';
import { PromptTemplateLoader } from './PromptTemplateLoader';
import { ToolManager } from './ToolManager';
import { WorkspaceAnalyzer } from './WorkspaceAnalyzer';

/**
 * Handles specific types of chat requests with specialized responses
 */
export class RequestHandlers {
    constructor(
        private toolManager: ToolManager,
        private workspaceAnalyzer: WorkspaceAnalyzer
    ) { }

    /**
     * Handle requests to list available tools
     */
    async handleListToolsCommand(stream: vscode.ChatResponseStream): Promise<void> {
        const tools = this.toolManager.getAvailableTools();

        if (tools.length === 0) {
            stream.markdown(PromptTemplateLoader.getNoToolsTemplate());
            return;
        }

        const toolsList = tools.map(tool => tool.name).join(', ');
        stream.markdown(PromptTemplateLoader.getToolsListTemplate(toolsList));
    }

    /**
     * Handle requests about available tools and capabilities
     */
    async handleToolsRequest(stream: vscode.ChatResponseStream): Promise<void> {
        logger.info('Request Handlers: Handling tools request');

        const models = await vscode.lm.selectChatModels();
        const tools = this.toolManager.getAvailableTools();

        const languageModels = models.length > 0 ?
            models.map(m => `- **${m.id}** (${m.vendor}/${m.family}) - ${m.maxInputTokens} tokens`).join('\n') :
            '- No language models currently available';

        const vsCodeTools = tools.length > 0 ?
            tools.map(tool => `- **${tool.name}** - ${tool.description || 'Advanced development capability'}`).join('\n') :
            '- No VS Code tools currently available\n- Tools become available when you install extensions that provide them';

        stream.markdown(PromptTemplateLoader.getToolsRequestTemplate({
            languageModels,
            vsCodeTools
        }));
    }

    /**
     * Handle workspace analysis requests
     */
    async handleWorkspaceRequest(stream: vscode.ChatResponseStream): Promise<void> {
        logger.info('Request Handlers: Handling workspace request');

        const workspaceFolders = vscode.workspace.workspaceFolders;
        const tools = this.toolManager.getAvailableTools();

        if (!workspaceFolders) {
            stream.markdown(PromptTemplateLoader.getNoWorkspaceTemplate());
            return;
        }

        // Get workspace information
        const workspaceInfo = await this.workspaceAnalyzer.getWorkspaceInfo();
        const currentContext = this.workspaceAnalyzer.getCurrentContext();

        const projectStructure = workspaceFolders.map(folder => `- **${folder.name}**\n  \`${folder.uri.fsPath}\``).join('\n');

        const availableTools = tools.length > 0 ?
            `${tools.map(tool => `- **${tool.name}** - Advanced code analysis capabilities`).join('\n')}` :
            '- Basic file and project analysis available';

        stream.markdown(PromptTemplateLoader.getWorkspaceAnalysisTemplate({
            projectStructure,
            totalFiles: workspaceInfo.fileCount.toString(),
            languagesDetected: workspaceInfo.languages.length > 0 ? workspaceInfo.languages.join(', ') : 'Analyzing...',
            currentContext,
            availableTools
        }));
    }

    /**
     * Handle code analysis requests
     */
    async handleCodeAnalysisRequest(stream: vscode.ChatResponseStream, request: vscode.ChatRequest): Promise<void> {
        logger.info('Request Handlers: Handling code analysis request');

        const activeEditor = vscode.window.activeTextEditor;
        const workspaceFolders = vscode.workspace.workspaceFolders;

        if (!activeEditor && !workspaceFolders) {
            stream.markdown(PromptTemplateLoader.getNoCodeAnalysisTemplate());
            return;
        }

        let analysisContext = '';

        if (activeEditor) {
            const selection = activeEditor.selection;
            const selectedText = activeEditor.document.getText(selection);
            const fileName = activeEditor.document.fileName;
            const language = activeEditor.document.languageId;

            analysisContext = `**Current File:** \`${fileName}\` (${language})
**Lines:** ${activeEditor.document.lineCount}`;

            if (selectedText) {
                analysisContext += `\n**Selected Code:**\n\`\`\`${language}\n${selectedText}\n\`\`\``;
            }
        }

        if (workspaceFolders) {
            analysisContext += `\n**Workspace:** ${workspaceFolders.map(f => f.name).join(', ')}`;
        }

        stream.markdown(PromptTemplateLoader.getCodeAnalysisTemplate({
            analysisContext,
            requestPrompt: request.prompt
        }));
    }

    /**
     * Handle debugging requests
     */
    async handleDebuggingRequest(stream: vscode.ChatResponseStream): Promise<void> {
        logger.info('Request Handlers: Handling debugging request');

        const currentContext = this.workspaceAnalyzer.getCurrentContext();
        const detectedIssues = this.workspaceAnalyzer.getDetectedIssues();

        stream.markdown(PromptTemplateLoader.getDebugAssistantTemplate({
            currentContext,
            detectedIssues
        }));
    }
}
