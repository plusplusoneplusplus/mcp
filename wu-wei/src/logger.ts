import * as vscode from 'vscode';

/**
 * Wu Wei Logger - Centralized logging for the extension
 * Follows wu wei principles: simple, natural, and flowing like water
 */
export class WuWeiLogger {
    private static instance: WuWeiLogger;
    private outputChannel: vscode.OutputChannel;

    private constructor() {
        this.outputChannel = vscode.window.createOutputChannel('Wu Wei');
    }

    public static getInstance(): WuWeiLogger {
        if (!WuWeiLogger.instance) {
            WuWeiLogger.instance = new WuWeiLogger();
        }
        return WuWeiLogger.instance;
    }

    /**
     * Log an info message
     */
    public info(message: string, data?: any): void {
        const timestamp = new Date().toISOString();
        const logMessage = `[${timestamp}] [INFO] ${message}`;

        this.outputChannel.appendLine(logMessage);
        if (data) {
            this.outputChannel.appendLine(`Data: ${JSON.stringify(data, null, 2)}`);
        }

        // Also log to console for development
        console.log(logMessage, data || '');
    }

    /**
     * Log a warning message
     */
    public warn(message: string, data?: any): void {
        const timestamp = new Date().toISOString();
        const logMessage = `[${timestamp}] [WARN] ${message}`;

        this.outputChannel.appendLine(logMessage);
        if (data) {
            this.outputChannel.appendLine(`Data: ${JSON.stringify(data, null, 2)}`);
        }

        console.warn(logMessage, data || '');
    }

    /**
     * Log an error message
     */
    public error(message: string, error?: any): void {
        const timestamp = new Date().toISOString();
        const logMessage = `[${timestamp}] [ERROR] ${message}`;

        this.outputChannel.appendLine(logMessage);
        if (error) {
            if (error instanceof Error) {
                this.outputChannel.appendLine(`Error: ${error.message}`);
                this.outputChannel.appendLine(`Stack: ${error.stack}`);
            } else {
                this.outputChannel.appendLine(`Error: ${JSON.stringify(error, null, 2)}`);
            }
        }

        console.error(logMessage, error || '');
    }

    /**
     * Log a debug message (only shown in development)
     */
    public debug(message: string, data?: any): void {
        const timestamp = new Date().toISOString();
        const logMessage = `[${timestamp}] [DEBUG] ${message}`;

        this.outputChannel.appendLine(logMessage);
        if (data) {
            this.outputChannel.appendLine(`Data: ${JSON.stringify(data, null, 2)}`);
        }

        console.log(logMessage, data || '');
    }

    /**
     * Log chat-related activities
     */
    public chat(action: string, sessionId?: string, data?: any): void {
        const timestamp = new Date().toISOString();
        const sessionInfo = sessionId ? `[Session: ${sessionId}]` : '';
        const logMessage = `[${timestamp}] [CHAT] ${action} ${sessionInfo}`;

        this.outputChannel.appendLine(logMessage);
        if (data) {
            this.outputChannel.appendLine(`Data: ${JSON.stringify(data, null, 2)}`);
        }

        console.log(logMessage, data || '');
    }

    /**
     * Log automation-related activities
     */
    public automation(action: string, data?: any): void {
        const timestamp = new Date().toISOString();
        const logMessage = `[${timestamp}] [AUTOMATION] ${action}`;

        this.outputChannel.appendLine(logMessage);
        if (data) {
            this.outputChannel.appendLine(`Data: ${JSON.stringify(data, null, 2)}`);
        }

        console.log(logMessage, data || '');
    }

    /**
     * Show the output channel
     */
    public show(): void {
        this.outputChannel.show();
    }

    /**
     * Clear the output channel
     */
    public clear(): void {
        this.outputChannel.clear();
    }

    /**
     * Dispose of the output channel
     */
    public dispose(): void {
        this.outputChannel.dispose();
    }

    /**
     * Log extension lifecycle events
     */
    public lifecycle(event: 'activate' | 'deactivate' | 'error', message?: string): void {
        const timestamp = new Date().toISOString();
        const logMessage = `[${timestamp}] [LIFECYCLE] Extension ${event}${message ? ': ' + message : ''}`;

        this.outputChannel.appendLine('='.repeat(60));
        this.outputChannel.appendLine(logMessage);
        this.outputChannel.appendLine('='.repeat(60));

        console.log(logMessage);
    }

    /**
     * Log with custom level
     */
    public log(level: string, message: string, data?: any): void {
        const timestamp = new Date().toISOString();
        const logMessage = `[${timestamp}] [${level.toUpperCase()}] ${message}`;

        this.outputChannel.appendLine(logMessage);
        if (data) {
            this.outputChannel.appendLine(`Data: ${JSON.stringify(data, null, 2)}`);
        }

        console.log(logMessage, data || '');
    }
}

// Export a singleton instance for easy use throughout the extension
export const logger = WuWeiLogger.getInstance();
