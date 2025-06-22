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
            console.log('[Wu Wei Extension] Received message from webview:', message);
            switch (message.command) {
                case 'showLogs':
                    console.log('[Wu Wei Extension] showLogs command received');
                    vscode.commands.executeCommand('wu-wei.showLogs');
                    break;
                case 'clearLogs':
                    console.log('[Wu Wei Extension] clearLogs command received');
                    vscode.commands.executeCommand('wu-wei.clearLogs');
                    break;
                case 'exportLogs':
                    console.log('[Wu Wei Extension] exportLogs command received');
                    this.exportLogs();
                    break;
                case 'refreshDebugInfo':
                    console.log('[Wu Wei Extension] refreshDebugInfo command received');
                    this.refreshDebugInfo();
                    break;
                case 'runCommands':
                    console.log('[Wu Wei Extension] runCommands command received');
                    this.runCommands(message.commands);
                    break;
                default:
                    console.log('[Wu Wei Extension] Unknown command received:', message.command);
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
        
        .help-text code {
            font-family: var(--vscode-editor-font-family, 'SF Mono', Consolas, monospace);
            background: var(--vscode-textCodeBlock-background);
            padding: 1px 3px;
            border-radius: 2px;
            font-size: 10px;
            font-style: normal;
        }
        
        .divider {
            height: 1px;
            background: var(--vscode-panel-border);
            margin: 8px 0;
        }
        
        .command-executor {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .command-textarea {
            width: 100%;
            min-height: 80px;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            border-radius: 4px;
            padding: 8px;
            font-family: var(--vscode-editor-font-family, 'SF Mono', Consolas, monospace);
            font-size: 11px;
            line-height: 1.4;
            resize: vertical;
            outline: none;
        }
        
        .command-textarea:focus {
            border-color: var(--vscode-focusBorder);
            box-shadow: 0 0 0 1px var(--vscode-focusBorder);
        }
        
        .command-textarea::placeholder {
            color: var(--vscode-input-placeholderForeground);
        }
        
        .command-actions {
            display: flex;
            gap: 6px;
        }
        
        .command-output {
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid var(--vscode-panel-border);
        }
        
        .command-result {
            padding: 4px 0;
            border-bottom: 1px solid var(--vscode-panel-border);
            font-size: 11px;
        }
        
        .command-result:last-child {
            border-bottom: none;
        }
        
        .command-result-success {
            color: var(--vscode-testing-iconPassed);
        }
        
        .command-result-error {
            color: var(--vscode-testing-iconFailed);
        }
        
        .command-result-command {
            font-weight: 500;
            color: var(--vscode-foreground);
        }
        
        .command-result-message {
            color: var(--vscode-descriptionForeground);
            margin-left: 12px;
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
        
        <!-- Command Execution Section -->
        <div class="section">
            <div class="section-title">
                <span class="icon">⚡</span>
                Run VS Code Commands
            </div>
            <div class="command-executor">
                <textarea 
                    id="commandInput" 
                    placeholder="Enter VS Code commands, one per line&#10;Examples:&#10;workbench.action.files.newUntitledFile&#10;insertText:Hello World (uses copy-paste)&#10;workbench.action.focusActiveEditorGroup&#10;type[{text:&quot;console.log('test');&quot;}]&#10;editor.action.clipboardPasteAction&#10;workbench.action.files.save"
                    rows="6"
                    class="command-textarea"
                ></textarea>
                
                <div class="command-actions">
                    <button class="debug-btn primary" onclick="runCommands()">
                        <span class="icon">▶️</span>
                        <span>Execute Commands</span>
                    </button>
                    
                    <button class="debug-btn" onclick="clearCommands()">
                        <span class="icon">🧹</span>
                        <span>Clear</span>
                    </button>
                </div>
                
                <div class="command-output" id="commandOutput" style="display: none;">
                    <div class="section-title" style="margin-bottom: 4px; font-size: 12px;">
                        <span class="icon">📤</span>
                        Execution Results
                    </div>
                    <div class="debug-info" id="commandResults"></div>
                </div>
            </div>
            
            <div class="help-text">
                Enter VS Code commands to execute, one per line. Supported formats:<br>
                • Standard commands: <code>workbench.action.files.save</code><br>
                • Text insertion: <code>type[{text:"Hello"}]</code> or <code>insertText:Hello</code> (uses copy-paste)<br>
                • Commands with args: <code>command:{arg1:"value1",arg2:value2}</code><br>
                💡 Text insertion now uses clipboard copy-paste for universal compatibility!<br>
                Works in: editors, chat inputs, search boxes, terminals, and most text fields.<br>
                Example: Click in any text area → <code>insertText:Your text here</code><br>
                Commands execute sequentially with a 300ms delay between each.<br>
                Use the Command Palette (Cmd+Shift+P) to find command IDs.
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
            console.log('[Wu Wei Frontend] showLogs button clicked');
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
        
        function runCommands() {
            const commandInput = document.getElementById('commandInput');
            const commandText = commandInput.value.trim();
            
            if (!commandText) {
                alert('Please enter at least one command to execute.');
                return;
            }
            
            // Split commands by lines and filter out empty lines
            const commands = commandText
                .split('\\n')
                .map(cmd => cmd.trim())
                .filter(cmd => cmd.length > 0);
            
            if (commands.length === 0) {
                alert('No valid commands found. Please enter commands separated by line breaks.');
                return;
            }
            
            console.log('[Wu Wei Frontend] Executing commands:', commands);
            
            // Show loading state
            const outputSection = document.getElementById('commandOutput');
            const resultsDiv = document.getElementById('commandResults');
            outputSection.style.display = 'block';
            resultsDiv.innerHTML = '<div class="command-result">⏳ Executing commands...</div>';
            
            // Send commands to backend
            vscode.postMessage({ 
                command: 'runCommands', 
                commands: commands 
            });
        }
        
        function clearCommands() {
            const commandInput = document.getElementById('commandInput');
            commandInput.value = '';
            
            const outputSection = document.getElementById('commandOutput');
            outputSection.style.display = 'none';
        }
        
        // Function to update command results (called from backend)
        function updateCommandResults(results) {
            const resultsDiv = document.getElementById('commandResults');
            const outputSection = document.getElementById('commandOutput');
            
            if (!results || results.length === 0) {
                resultsDiv.innerHTML = '<div class="command-result command-result-error">No results received</div>';
                return;
            }
            
            let html = '';
            results.forEach((result, index) => {
                const statusClass = result.success ? 'command-result-success' : 'command-result-error';
                const statusIcon = result.success ? '✅' : '❌';
                
                html += \`
                    <div class="command-result">
                        <div class="command-result-command">\${statusIcon} \${result.command}</div>
                        \${result.message ? \`<div class="command-result-message">\${result.message}</div>\` : ''}
                    </div>
                \`;
            });
            
            resultsDiv.innerHTML = html;
            outputSection.style.display = 'block';
        }
        
        // Initialize on load
        document.addEventListener('DOMContentLoaded', () => {
            refreshDebugInfo();
        });
        
        // Listen for messages from the extension
        window.addEventListener('message', event => {
            const message = event.data;
            
            switch (message.command) {
                case 'updateCommandResults':
                    updateCommandResults(message.results);
                    break;
                default:
                    console.log('[Wu Wei Frontend] Unknown message from extension:', message);
            }
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

    private async runCommands(commands: string[]): Promise<void> {
        try {
            logger.info('Run commands requested from debug panel', { commandCount: commands.length, commands });

            const results: Array<{ command: string; success: boolean; message?: string }> = [];

            for (let i = 0; i < commands.length; i++) {
                const command = commands[i];
                try {
                    logger.debug('Executing command:', command);

                    // Parse and execute the command
                    const result = await this.parseAndExecuteCommand(command);

                    results.push({
                        command,
                        success: true,
                        message: result || 'Command executed successfully'
                    });

                    logger.debug('Command executed successfully:', command);
                } catch (error) {
                    const errorMessage = error instanceof Error ? error.message : 'Unknown error';

                    results.push({
                        command,
                        success: false,
                        message: `Error: ${errorMessage}`
                    });

                    logger.error('Command execution failed', { command, error });
                }

                // Add delay between commands (except after the last command)
                if (i < commands.length - 1) {
                    logger.debug('Waiting 300ms before next command...');
                    await new Promise(resolve => setTimeout(resolve, 300));
                }
            }

            // Send results back to webview
            if (this._view) {
                await this._view.webview.postMessage({
                    command: 'updateCommandResults',
                    results: results
                });
            }

            // Show summary notification
            const successCount = results.filter(r => r.success).length;
            const failCount = results.length - successCount;

            if (failCount === 0) {
                vscode.window.showInformationMessage(`Wu Wei: Successfully executed ${successCount} command(s)`);
            } else if (successCount === 0) {
                vscode.window.showErrorMessage(`Wu Wei: Failed to execute ${failCount} command(s)`);
            } else {
                vscode.window.showWarningMessage(`Wu Wei: Executed ${successCount} command(s), ${failCount} failed`);
            }

        } catch (error) {
            logger.error('Error in runCommands', error);
            vscode.window.showErrorMessage('Wu Wei: Failed to execute commands');

            // Send error to webview
            if (this._view) {
                await this._view.webview.postMessage({
                    command: 'updateCommandResults',
                    results: [{
                        command: 'System Error',
                        success: false,
                        message: 'Failed to process command execution request'
                    }]
                });
            }
        }
    }

    private async parseAndExecuteCommand(command: string): Promise<string | undefined> {
        // Handle different command formats

        // 1. Handle type[{text:"abc"}] format for text insertion
        const typeMatch = command.match(/^type\[\{text:"([^"]+)"\}\]$/);
        if (typeMatch) {
            const text = typeMatch[1];
            return await this.executeTypeCommand(text);
        }

        // 2. Handle type:{text} format for text insertion
        const typeSimpleMatch = command.match(/^type:(.+)$/);
        if (typeSimpleMatch) {
            const text = typeSimpleMatch[1];
            return await this.executeTypeCommand(text);
        }

        // 3. Handle insertText:text format for text insertion
        const insertTextMatch = command.match(/^insertText:(.+)$/);
        if (insertTextMatch) {
            const text = insertTextMatch[1];
            return await this.executeTypeCommand(text);
        }

        // 3a. Handle clipboard commands
        const clipboardCopyMatch = command.match(/^clipboard:copy:(.+)$/);
        if (clipboardCopyMatch) {
            const text = clipboardCopyMatch[1];
            await vscode.env.clipboard.writeText(text);
            return `Copied to clipboard: "${text}"`;
        }

        const clipboardPasteMatch = command.match(/^clipboard:paste$/);
        if (clipboardPasteMatch) {
            await vscode.commands.executeCommand('editor.action.clipboardPasteAction');
            const clipboardText = await vscode.env.clipboard.readText();
            return `Pasted from clipboard: "${clipboardText.substring(0, 50)}${clipboardText.length > 50 ? '...' : ''}"`;
        }

        // 4. Handle commands with arguments in JSON format: command:{arg1:value1,arg2:value2}
        const commandWithArgsMatch = command.match(/^([^:]+):\{(.+)\}$/);
        if (commandWithArgsMatch) {
            const commandName = commandWithArgsMatch[1];
            const argsString = commandWithArgsMatch[2];

            try {
                // Simple parser for key:value pairs
                const args: any = {};
                const pairs = argsString.split(',');
                for (const pair of pairs) {
                    const [key, value] = pair.split(':').map(s => s.trim());
                    if (key && value) {
                        // Try to parse as JSON value, fallback to string
                        try {
                            args[key] = JSON.parse(value);
                        } catch {
                            args[key] = value.replace(/^["']|["']$/g, ''); // Remove quotes
                        }
                    }
                }

                await vscode.commands.executeCommand(commandName, args);
                return `Executed ${commandName} with arguments: ${JSON.stringify(args)}`;
            } catch (error) {
                throw new Error(`Failed to parse command arguments: ${error}`);
            }
        }

        // 5. Handle commands with single argument: command:argument
        const commandWithArgMatch = command.match(/^([^:]+):(.+)$/);
        if (commandWithArgMatch) {
            const commandName = commandWithArgMatch[1];
            const arg = commandWithArgMatch[2];

            // Try to parse as JSON, fallback to string
            let parsedArg;
            try {
                parsedArg = JSON.parse(arg);
            } catch {
                parsedArg = arg;
            }

            await vscode.commands.executeCommand(commandName, parsedArg);
            return `Executed ${commandName} with argument: ${arg}`;
        }

        // 6. Handle standard VS Code commands without arguments
        await vscode.commands.executeCommand(command);
        return undefined; // Will use default success message
    }

    private async executeTypeCommand(text: string): Promise<string> {
        try {
            // Use the universal copy-paste approach which works everywhere
            // This is much more reliable than the 'type' command

            // Step 1: Save current clipboard content (to restore later)
            let originalClipboard = '';
            try {
                originalClipboard = await vscode.env.clipboard.readText();
            } catch {
                // If we can't read clipboard, that's okay, we'll just proceed
            }

            // Step 2: Copy our text to clipboard
            await vscode.env.clipboard.writeText(text);

            // Step 3: Paste using the standard paste command (Ctrl+V equivalent)
            await vscode.commands.executeCommand('editor.action.clipboardPasteAction');

            // Step 4: Small delay before restoring clipboard
            await new Promise(resolve => setTimeout(resolve, 100));

            // Step 5: Restore original clipboard content (if we had any)
            if (originalClipboard) {
                try {
                    await vscode.env.clipboard.writeText(originalClipboard);
                } catch {
                    // If restoration fails, that's okay
                }
            }

            return `Inserted text: "${text}" (using clipboard copy-paste)`;

        } catch (error) {
            logger.debug('Clipboard copy-paste failed, trying fallback methods', { error });

            // Fallback: Try direct editor insertion if we have an active editor
            try {
                const activeEditor = vscode.window.activeTextEditor;
                if (activeEditor) {
                    const position = activeEditor.selection.active;
                    await activeEditor.edit(editBuilder => {
                        editBuilder.insert(position, text);
                    });
                    return `Inserted text: "${text}" (using editor.edit fallback)`;
                }

                // If no active editor, provide helpful error message
                throw new Error(`Text insertion failed. Please:
1. Click in a text area, editor, or input field first
2. Then run the text insertion command
3. Make sure the target accepts text input

The copy-paste method works in most contexts but requires a focused text input.`);

            } catch (fallbackError) {
                throw new Error(`All text insertion methods failed: ${error}. Fallback error: ${fallbackError}`);
            }
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
