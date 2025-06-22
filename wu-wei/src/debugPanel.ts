import * as vscode from 'vscode';
import { logger } from './logger';

/**
 * Wu Wei Debug Panel Provider
 * Provides debugging functionality including log viewing and clearing
 */
export class WuWeiDebugPanelProvider implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;

    constructor(private context: vscode.ExtensionContext) {
        logger.debug('Wu Wei Debug Panel Provider initialized');
    }

    resolveWebviewView(webviewView: vscode.WebviewView, context: vscode.WebviewViewResolveContext, token: vscode.CancellationToken): void {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.context.extensionUri]
        };

        webviewView.webview.html = this.getDebugHtml();

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(message => {
            switch (message.command) {
                case 'showLogs':
                    vscode.commands.executeCommand('wu-wei.showLogs');
                    break;
                case 'clearLogs':
                    vscode.commands.executeCommand('wu-wei.clearLogs');
                    break;
                case 'exportLogs':
                    this.exportLogs();
                    break;
                case 'refreshDebugInfo':
                    this.refreshDebugInfo();
                    break;
            }
        });

        logger.debug('Wu Wei Debug Panel webview resolved');
    }

    private getDebugHtml(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wu Wei Debug Panel</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 12px;
            background: var(--vscode-sideBar-background);
            color: var(--vscode-sideBar-foreground);
            font-size: 13px;
            line-height: 1.4;
        }
        
        .debug-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .section {
            background: var(--vscode-editor-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 6px;
            padding: 12px;
        }
        
        .section-title {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 8px;
            color: var(--vscode-foreground);
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .section-title .icon {
            font-size: 16px;
        }
        
        .debug-actions {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        
        .debug-btn {
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            border: 1px solid var(--vscode-button-border, transparent);
            padding: 8px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 6px;
            width: 100%;
            text-align: left;
            transition: background-color 0.1s ease;
        }
        
        .debug-btn:hover {
            background: var(--vscode-button-secondaryHoverBackground);
        }
        
        .debug-btn:active {
            transform: translateY(1px);
        }
        
        .debug-btn.primary {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
        }
        
        .debug-btn.primary:hover {
            background: var(--vscode-button-hoverBackground);
        }
        
        .debug-btn.danger {
            background: var(--vscode-errorForeground);
            color: var(--vscode-editor-background);
        }
        
        .debug-btn.danger:hover {
            opacity: 0.9;
        }
        
        .debug-btn .icon {
            width: 14px;
            height: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
        }
        
        .debug-info {
            background: var(--vscode-textCodeBlock-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 4px;
            padding: 8px;
            font-family: var(--vscode-editor-font-family, 'SF Mono', Consolas, monospace);
            font-size: 11px;
            line-height: 1.3;
        }
        
        .debug-info-item {
            display: flex;
            justify-content: space-between;
            padding: 2px 0;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        
        .debug-info-item:last-child {
            border-bottom: none;
        }
        
        .debug-info-label {
            color: var(--vscode-descriptionForeground);
            min-width: 80px;
        }
        
        .debug-info-value {
            color: var(--vscode-foreground);
            font-weight: 500;
        }
        
        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }
        
        .status-good {
            background: var(--vscode-testing-iconPassed);
        }
        
        .status-warning {
            background: var(--vscode-testing-iconQueued);
        }
        
        .status-error {
            background: var(--vscode-testing-iconFailed);
        }
        
        .help-text {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
            font-style: italic;
            margin-top: 6px;
            padding: 6px 8px;
            background: var(--vscode-textBlockQuote-background);
            border-left: 3px solid var(--vscode-textBlockQuote-border);
            border-radius: 3px;
        }
        
        .divider {
            height: 1px;
            background: var(--vscode-panel-border);
            margin: 8px 0;
        }
    </style>
</head>
<body>
    <div class="debug-container">
        <!-- Debug Actions Section -->
        <div class="section">
            <div class="section-title">
                <span class="icon">🔧</span>
                Debug Actions
            </div>
            <div class="debug-actions">
                <button class="debug-btn primary" onclick="showLogs()">
                    <span class="icon">📄</span>
                    <span>Show Debug Logs</span>
                </button>
                
                <button class="debug-btn" onclick="exportLogs()">
                    <span class="icon">💾</span>
                    <span>Export Logs</span>
                </button>
                
                <div class="divider"></div>
                
                <button class="debug-btn danger" onclick="clearLogs()">
                    <span class="icon">🗑️</span>
                    <span>Clear All Logs</span>
                </button>
            </div>
        </div>
        
        <!-- Debug Information Section -->
        <div class="section">
            <div class="section-title">
                <span class="icon">📊</span>
                System Information
                <button class="debug-btn" onclick="refreshDebugInfo()" style="margin-left: auto; padding: 4px 8px; font-size: 10px;">
                    <span class="icon">🔄</span>
                    Refresh
                </button>
            </div>
            <div class="debug-info" id="debugInfo">
                <div class="debug-info-item">
                    <span class="debug-info-label">Extension:</span>
                    <span class="debug-info-value">
                        <span class="status-indicator status-good"></span>
                        Wu Wei Active
                    </span>
                </div>
                <div class="debug-info-item">
                    <span class="debug-info-label">Version:</span>
                    <span class="debug-info-value">0.1.0</span>
                </div>
                <div class="debug-info-item">
                    <span class="debug-info-label">VSCode:</span>
                    <span class="debug-info-value" id="vscodeVersion">Loading...</span>
                </div>
                <div class="debug-info-item">
                    <span class="debug-info-label">Logging:</span>
                    <span class="debug-info-value">
                        <span class="status-indicator status-good"></span>
                        Enabled
                    </span>
                </div>
            </div>
            
            <div class="help-text">
                Debug logs help track extension behavior and troubleshoot issues. 
                Use "Show Debug Logs" to view detailed output in the Output panel.
            </div>
        </div>
        
        <!-- Debug Tips Section -->
        <div class="section">
            <div class="section-title">
                <span class="icon">💡</span>
                Debug Tips
            </div>
            <div style="font-size: 11px; line-height: 1.4; color: var(--vscode-descriptionForeground);">
                <p style="margin-bottom: 6px;">• Check the Output panel (Wu Wei) for detailed logs</p>
                <p style="margin-bottom: 6px;">• Use Developer Tools (F12) for webview debugging</p>
                <p style="margin-bottom: 6px;">• Export logs before reporting issues</p>
                <p>• Clear logs periodically to maintain performance</p>
            </div>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        
        function showLogs() {
            vscode.postMessage({ command: 'showLogs' });
        }
        
        function clearLogs() {
            if (confirm('Are you sure you want to clear all debug logs? This action cannot be undone.')) {
                vscode.postMessage({ command: 'clearLogs' });
            }
        }
        
        function exportLogs() {
            vscode.postMessage({ command: 'exportLogs' });
        }
        
        function refreshDebugInfo() {
            vscode.postMessage({ command: 'refreshDebugInfo' });
            
            // Update VSCode version
            const vscodeVersionElement = document.getElementById('vscodeVersion');
            if (vscodeVersionElement) {
                vscodeVersionElement.textContent = '${vscode.version}' || 'Unknown';
            }
        }
        
        // Initialize on load
        document.addEventListener('DOMContentLoaded', () => {
            refreshDebugInfo();
        });
    </script>
</body>
</html>`;
    }

    private async exportLogs(): Promise<void> {
        try {
            logger.info('Export logs requested from debug panel');

            // Show save dialog
            const uri = await vscode.window.showSaveDialog({
                defaultUri: vscode.Uri.file(`wu-wei-logs-${new Date().toISOString().split('T')[0]}.txt`),
                filters: {
                    'Text Files': ['txt'],
                    'All Files': ['*']
                }
            });

            if (uri) {
                // This would need to be implemented in the logger
                // For now, show a message that the feature is planned
                vscode.window.showInformationMessage('Wu Wei: Log export feature coming soon');
                logger.info('Log export saved to', uri.fsPath);
            }
        } catch (error) {
            logger.error('Error exporting logs', error);
            vscode.window.showErrorMessage('Wu Wei: Failed to export logs');
        }
    }

    private refreshDebugInfo(): void {
        logger.debug('Debug info refresh requested');

        // Update webview with fresh debug information
        if (this._view) {
            // You could send updated data to the webview here
            // For now, the webview handles its own refresh
            logger.debug('Debug panel refreshed');
        }
    }

    /**
     * Refresh the debug panel view
     */
    public refresh(): void {
        if (this._view) {
            this._view.webview.html = this.getDebugHtml();
            logger.debug('Debug panel view refreshed');
        }
    }
}
