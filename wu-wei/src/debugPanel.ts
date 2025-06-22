import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
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
        try {
            // Read HTML template from file
            const htmlPath = path.join(this.context.extensionPath, 'src', 'templates', 'debugPanel.html');
            let html = fs.readFileSync(htmlPath, 'utf8');

            // Replace template variables with actual values
            html = html.replace('{{VERSION}}', this.getExtensionVersion());
            html = html.replace('{{VSCODE_VERSION}}', vscode.version);

            return html;
        } catch (error) {
            logger.error('Failed to load debug panel HTML template', error);

            // Fallback HTML if template loading fails
            return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Wu Wei Debug Panel - Error</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            padding: 20px; 
            background: var(--vscode-sideBar-background); 
            color: var(--vscode-sideBar-foreground); 
        }
        .error { color: var(--vscode-errorForeground); }
    </style>
</head>
<body>
    <h2>Wu Wei Debug Panel</h2>
    <p class="error">⚠️ Failed to load debug panel template.</p>
    <p>Please check the extension installation and try again.</p>
    <p><strong>Error:</strong> ${error instanceof Error ? error.message : 'Unknown error'}</p>
</body>
</html>`;
        }
    }

    private getExtensionVersion(): string {
        try {
            const packageJsonPath = path.join(this.context.extensionPath, 'package.json');
            const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
            return packageJson.version || '0.1.0';
        } catch (error) {
            logger.debug('Failed to read extension version from package.json', error);
            return '0.1.0'; // Fallback version
        }
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
