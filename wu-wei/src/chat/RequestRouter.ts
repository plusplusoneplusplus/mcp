import { RequestAnalysis } from './types';

/**
 * Analyzes user requests and determines appropriate handling strategy
 */
export class RequestRouter {
    /**
     * Detect if a prompt should definitely trigger tool usage and provide guidance
     */
    shouldUseTool(prompt: string): RequestAnalysis {
        const lowerPrompt = prompt.toLowerCase();

        // Patterns that should always trigger tool usage
        const patterns = [
            {
                keywords: ['explain', 'codebase', 'code base', 'project structure'],
                reason: 'Codebase explanation requires examining actual files',
                tools: ['copilot_searchCodebase', 'copilot_listDirectory', 'copilot_findFiles']
            },
            {
                keywords: ['analyze', 'file', 'function', 'class', 'method'],
                reason: 'Code analysis requires reading specific files',
                tools: ['copilot_readFile', 'copilot_searchWorkspaceSymbols']
            },
            {
                keywords: ['find', 'search', 'locate', 'where is'],
                reason: 'Finding code requires searching the workspace',
                tools: ['copilot_findTextInFiles', 'copilot_searchCodebase', 'copilot_searchWorkspaceSymbols']
            },
            {
                keywords: ['debug', 'error', 'bug', 'issue', 'problem'],
                reason: 'Debugging requires examining actual code and diagnostics',
                tools: ['copilot_readFile', 'copilot_findTextInFiles']
            }
        ];

        for (const pattern of patterns) {
            if (pattern.keywords.some(keyword => lowerPrompt.includes(keyword))) {
                return {
                    shouldUse: true,
                    reason: pattern.reason,
                    suggestedTools: pattern.tools
                };
            }
        }

        return {
            shouldUse: false,
            reason: 'Generic prompt may not require tool usage',
            suggestedTools: []
        };
    }

    /**
     * Determine if this is a code analysis request
     */
    isCodeAnalysisRequest(prompt: string): boolean {
        const analysisKeywords = [
            'analyze', 'analysis', 'review', 'check', 'examine', 'inspect',
            'code quality', 'best practices', 'performance', 'optimize',
            'refactor', 'improve', 'suggestions', 'patterns'
        ];

        const lowerPrompt = prompt.toLowerCase();
        return analysisKeywords.some(keyword => lowerPrompt.includes(keyword));
    }

    /**
     * Determine if this is a debugging request
     */
    isDebuggingRequest(prompt: string): boolean {
        const debugKeywords = [
            'debug', 'bug', 'error', 'issue', 'problem', 'fix',
            'broken', 'not working', 'exception', 'crash',
            'troubleshoot', 'diagnose'
        ];

        const lowerPrompt = prompt.toLowerCase();
        return debugKeywords.some(keyword => lowerPrompt.includes(keyword));
    }

    /**
     * Determine request type for routing
     */
    getRequestType(prompt: string): 'code-analysis' | 'debugging' | 'tools' | 'workspace' | 'general' {
        const lowerPrompt = prompt.toLowerCase();

        if (lowerPrompt.includes('tools') || lowerPrompt.includes('list tools')) {
            return 'tools';
        }

        if (lowerPrompt.includes('workspace') || lowerPrompt.includes('project')) {
            return 'workspace';
        }

        if (this.isCodeAnalysisRequest(prompt)) {
            return 'code-analysis';
        }

        if (this.isDebuggingRequest(prompt)) {
            return 'debugging';
        }

        return 'general';
    }
}
