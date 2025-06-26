import * as vscode from 'vscode';
import { WorkspaceInfo } from './types';

/**
 * Analyzes and provides information about the current workspace
 */
export class WorkspaceAnalyzer {
    /**
     * Get comprehensive workspace information
     */
    async getWorkspaceInfo(): Promise<WorkspaceInfo> {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        const activeEditor = vscode.window.activeTextEditor;

        const info: WorkspaceInfo = {
            fileCount: 0,
            languages: []
        };

        if (workspaceFolders) {
            info.fileCount = await this.getWorkspaceFileCount(workspaceFolders);
            info.languages = await this.detectLanguages(workspaceFolders);
        }

        if (activeEditor) {
            info.activeFile = {
                fileName: activeEditor.document.fileName,
                language: activeEditor.document.languageId,
                lineCount: activeEditor.document.lineCount,
                selection: activeEditor.selection
            };
        }

        return info;
    }

    /**
     * Count files in workspace (simplified implementation)
     */
    private async getWorkspaceFileCount(workspaceFolders: readonly vscode.WorkspaceFolder[]): Promise<number> {
        try {
            // Simple approximation - in a real implementation, you'd traverse the directories
            return 42; // Placeholder
        } catch {
            return 0;
        }
    }

    /**
     * Detect programming languages used in workspace
     */
    private async detectLanguages(workspaceFolders: readonly vscode.WorkspaceFolder[]): Promise<string[]> {
        try {
            // Simple detection based on common file extensions
            // In a real implementation, you'd scan the workspace for file types
            const activeEditor = vscode.window.activeTextEditor;
            if (activeEditor) {
                return [activeEditor.document.languageId];
            }
            return ['JavaScript', 'TypeScript']; // Placeholder
        } catch {
            return [];
        }
    }

    /**
     * Get current context from active editor
     */
    getCurrentContext(): string {
        const activeEditor = vscode.window.activeTextEditor;

        if (!activeEditor) {
            return '- No file currently active';
        }

        const selection = activeEditor.selection;
        const selectedText = activeEditor.document.getText(selection);
        const fileName = activeEditor.document.fileName;
        const language = activeEditor.document.languageId;

        let context = `- **Active File**: \`${fileName}\`
- **Language**: ${language}
- **Lines**: ${activeEditor.document.lineCount}
- **Cursor Position**: Line ${selection.start.line + 1}, Column ${selection.start.character + 1}`;

        if (selectedText) {
            context += `\n- **Selected Code:**\n\`\`\`${language}\n${selectedText}\n\`\`\``;
        }

        return context;
    }

    /**
     * Get detected issues from VS Code diagnostics
     */
    getDetectedIssues(): string {
        const problems = vscode.languages.getDiagnostics();

        if (problems.length === 0) {
            return '';
        }

        let detectedIssues = '## 🚨 Detected Issues\n\n';
        let issueCount = 0;

        for (const [uri, diagnostics] of problems) {
            if (diagnostics.length > 0 && issueCount < 5) { // Limit to first 5 files
                detectedIssues += `**${uri.fsPath}:**\n`;
                for (const diagnostic of diagnostics.slice(0, 3)) { // Limit to 3 issues per file
                    const severity = diagnostic.severity === vscode.DiagnosticSeverity.Error ? '❌' :
                        diagnostic.severity === vscode.DiagnosticSeverity.Warning ? '⚠️' : 'ℹ️';
                    detectedIssues += `${severity} Line ${diagnostic.range.start.line + 1}: ${diagnostic.message}\n`;
                }
                issueCount++;
            }
        }

        return detectedIssues;
    }
}
