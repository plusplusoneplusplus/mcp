import * as vscode from 'vscode';

export interface WuWeiToolMetadata {
    toolCallsMetadata: ToolCallsMetadata;
}

export interface ToolCallsMetadata {
    toolCallRounds: ToolCallRound[];
    toolCallResults: Record<string, string>;
}

export interface ToolCallRound {
    response: string;
    toolCalls: vscode.LanguageModelToolCallPart[];
}

export function isWuWeiToolMetadata(obj: unknown): obj is WuWeiToolMetadata {
    return !!obj &&
        !!(obj as WuWeiToolMetadata).toolCallsMetadata &&
        Array.isArray((obj as WuWeiToolMetadata).toolCallsMetadata.toolCallRounds);
}

export interface RequestAnalysis {
    shouldUse: boolean;
    reason: string;
    suggestedTools: string[];
}

export interface WorkspaceInfo {
    fileCount: number;
    languages: string[];
    activeFile?: {
        fileName: string;
        language: string;
        lineCount: number;
        selection?: vscode.Selection;
    };
}
