import * as vscode from 'vscode';

/**
 * Enhanced types for the Wu Wei tool calling framework
 */

export interface ToolWorkflowResult {
    toolCallRounds: ToolCallRound[];
    toolCallResults: Record<string, vscode.LanguageModelToolResult>;
    conversationSummary: string;
    metadata: ToolWorkflowMetadata;
}

export interface ToolCallRound {
    response: string;
    toolCalls: vscode.LanguageModelToolCallPart[];
    timestamp: number;
    roundId: string;
}

export interface ToolWorkflowMetadata {
    totalRounds: number;
    toolsUsed: string[];
    executionTime: number;
    errors: ToolError[];
    cacheHits: number;
}

export interface ToolError {
    toolName: string;
    callId: string;
    error: string;
    timestamp: number;
    retryCount: number;
    // Enhanced error recovery fields
    errorType?: string;
    severity?: 'low' | 'medium' | 'high' | 'critical';
    recoveryAttempts?: number;
    lastRecoveryStrategy?: string;
}

export interface ToolParticipantConfig {
    maxToolRounds: number; // Default: 5
    toolTimeout: number; // Default: 30000ms
    enableCaching: boolean; // Default: true
    enableParallelExecution: boolean; // Default: true
    errorRetryAttempts: number; // Default: 3
    debugMode: boolean; // Default: false
    // Enhanced error recovery configuration
    enableAdvancedErrorRecovery: boolean; // Default: true
    maxRecoveryAttempts: number; // Default: 2
    errorRecoveryTimeout: number; // Default: 10000ms
    fallbackToolSuggestions: boolean; // Default: true
}

export interface ToolCallContext {
    userIntent: string;
    availableTools: vscode.LanguageModelToolInformation[];
    conversationHistory: vscode.LanguageModelChatMessage[];
    previousResults: Record<string, vscode.LanguageModelToolResult>;
    roundNumber: number;
}

export interface ToolSelectionResult {
    selectedTools: string[];
    confidence: number;
    reasoning: string;
}

export interface CachedToolResult {
    result: vscode.LanguageModelToolResult;
    timestamp: number;
    inputHash: string;
    expiresAt: number;
}

export interface PromptTemplate {
    id: string;
    name: string;
    template: string;
    variables: string[];
    toolSpecific?: boolean;
    targetTool?: string;
}

export interface ToolDiscoveryResult {
    tools: vscode.LanguageModelToolInformation[];
    categories: Record<string, string[]>;
    capabilities: ToolCapability[];
}

export interface ToolCapability {
    name: string;
    description: string;
    tools: string[];
    confidence: number;
}

export const DEFAULT_TOOL_PARTICIPANT_CONFIG: ToolParticipantConfig = {
    maxToolRounds: 5,
    toolTimeout: 30000,
    enableCaching: true,
    enableParallelExecution: true,
    errorRetryAttempts: 3,
    debugMode: false,
    // Enhanced error recovery defaults
    enableAdvancedErrorRecovery: true,
    maxRecoveryAttempts: 2,
    errorRecoveryTimeout: 10000,
    fallbackToolSuggestions: true
};