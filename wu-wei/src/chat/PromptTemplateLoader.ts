import * as fs from 'fs';
import * as path from 'path';

/**
 * Template loader utility for Wu Wei Chat Participant prompts
 */
export class PromptTemplateLoader {
    private static readonly TEMPLATES_DIR = path.join(__dirname, 'prompts');
    private static templateCache: Map<string, string> = new Map();

    /**
     * Load a template file and cache it
     */
    private static loadTemplate(templateName: string): string {
        if (this.templateCache.has(templateName)) {
            return this.templateCache.get(templateName)!;
        }

        try {
            const templatePath = path.join(this.TEMPLATES_DIR, templateName);
            const content = fs.readFileSync(templatePath, 'utf-8');
            this.templateCache.set(templateName, content);
            return content;
        } catch (error) {
            console.error(`Failed to load template ${templateName}:`, error);
            return `Template ${templateName} not found`;
        }
    }

    /**
     * Replace template variables with actual values
     */
    private static replaceVariables(template: string, variables: Record<string, string>): string {
        let result = template;
        for (const [key, value] of Object.entries(variables)) {
            const placeholder = `{{${key}}}`;
            result = result.replace(new RegExp(placeholder, 'g'), value);
        }
        return result;
    }

    /**
     * Get the base system prompt
     */
    static getBaseSystemPrompt(): string {
        return this.loadTemplate('base-system-prompt.txt');
    }

    /**
     * Get the agent mode enhancement text
     */
    static getAgentModeEnhancement(): string {
        return this.loadTemplate('agent-mode-enhancement.txt');
    }

    /**
     * Get the enhanced system prompt with tools support
     */
    static getEnhancedSystemPrompt(basePrompt: string, hasTools: boolean): string {
        if (!hasTools) {
            return basePrompt;
        }

        const enhancement = this.getAgentModeEnhancement();
        return `${basePrompt}\n\n${enhancement}`;
    }

    /**
     * Get the tools request response template
     */
    static getToolsRequestTemplate(variables: {
        languageModels: string;
        vsCodeTools: string;
    }): string {
        const template = this.loadTemplate('tools-request-template.md');
        return this.replaceVariables(template, {
            LANGUAGE_MODELS: variables.languageModels,
            VS_CODE_TOOLS: variables.vsCodeTools
        });
    }

    /**
     * Get the no workspace template
     */
    static getNoWorkspaceTemplate(): string {
        return this.loadTemplate('no-workspace-template.md');
    }

    /**
     * Get the workspace analysis template
     */
    static getWorkspaceAnalysisTemplate(variables: {
        projectStructure: string;
        totalFiles: string;
        languagesDetected: string;
        currentContext: string;
        availableTools: string;
    }): string {
        const template = this.loadTemplate('workspace-analysis-template.md');
        return this.replaceVariables(template, {
            PROJECT_STRUCTURE: variables.projectStructure,
            TOTAL_FILES: variables.totalFiles,
            LANGUAGES_DETECTED: variables.languagesDetected,
            CURRENT_CONTEXT: variables.currentContext,
            AVAILABLE_TOOLS: variables.availableTools
        });
    }

    /**
     * Get the no code analysis template
     */
    static getNoCodeAnalysisTemplate(): string {
        return this.loadTemplate('no-code-analysis-template.md');
    }

    /**
     * Get the code analysis template
     */
    static getCodeAnalysisTemplate(variables: {
        analysisContext: string;
        requestPrompt: string;
    }): string {
        const template = this.loadTemplate('code-analysis-template.md');
        return this.replaceVariables(template, {
            ANALYSIS_CONTEXT: variables.analysisContext,
            REQUEST_PROMPT: variables.requestPrompt
        });
    }

    /**
     * Get the debug assistant template
     */
    static getDebugAssistantTemplate(variables: {
        currentContext: string;
        detectedIssues?: string;
    }): string {
        const template = this.loadTemplate('debug-assistant-template.md');
        return this.replaceVariables(template, {
            CURRENT_CONTEXT: variables.currentContext,
            DETECTED_ISSUES: variables.detectedIssues || ''
        });
    }

    /**
     * Get the error template
     */
    static getErrorTemplate(errorMessage: string): string {
        const template = this.loadTemplate('error-template.md');
        return this.replaceVariables(template, {
            ERROR_MESSAGE: errorMessage
        });
    }

    /**
     * Get the no models template
     */
    static getNoModelsTemplate(): string {
        return this.loadTemplate('no-models-template.md');
    }

    /**
     * Get the no tools template
     */
    static getNoToolsTemplate(): string {
        return this.loadTemplate('no-tools-template.md');
    }

    /**
     * Get a simple tools list template
     */
    static getToolsListTemplate(toolsList: string): string {
        return `🔧 **Available Development Tools:** ${toolsList}\n\nThese tools can be used to provide enhanced code analysis, debugging assistance, and development guidance.`;
    }

    /**
     * Clear the template cache (useful for development/testing)
     */
    static clearCache(): void {
        this.templateCache.clear();
    }

    /**
     * Get tool execution messages
     */
    static getToolUsingMessage(toolName: string): string {
        return `\n🔧 **Using tool:** ${toolName}\n`;
    }

    static getToolExecutingMessage(toolName: string): string {
        return `\n🔧 **Executing tool:** ${toolName}\n`;
    }

    static getToolParametersMessage(parameters: string): string {
        return `📋 **Parameters:** ${parameters}\n`;
    }

    static getToolCompletedMessage(toolName: string): string {
        return `✅ **Tool completed:** ${toolName}\n`;
    }

    static getToolResultMessage(resultSummary: string): string {
        return `📊 **Result:** ${resultSummary}\n`;
    }

    static getToolErrorMessage(toolName: string, errorMessage: string): string {
        return `\n❌ **Tool error:** ${toolName} - ${errorMessage}\n`;
    }

    static getMaxRoundsReachedMessage(): string {
        return `\n⚠️ **Maximum tool execution rounds reached.** Summarizing results...\n`;
    }

    static getProcessingResultsMessage(count: number): string {
        return `\n📊 **Processing ${count} tool result(s)...**\n`;
    }

    static getToolSuggestionNote(suggestedTools: string[]): string {
        return `\n\n> 💡 **Note**: For a more accurate analysis of your codebase, I could examine your actual files using tools like \`${suggestedTools.join('`, `')}\`. Would you like me to analyze your specific code files?\n`;
    }
}
