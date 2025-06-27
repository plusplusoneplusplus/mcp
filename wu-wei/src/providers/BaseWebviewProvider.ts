import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { logger } from '../logger';

/**
 * Base class for Wu Wei webview providers
 * Provides common functionality for loading and managing webviews
 */
export abstract class BaseWebviewProvider {
    protected _view?: vscode.WebviewView;

    constructor(protected context: vscode.ExtensionContext) { }

    /**
     * Get webview content with separate CSS and JS files
     * @param webview - The webview instance
     * @param htmlFile - Path to HTML file relative to webview directory
     * @param cssFiles - Array of CSS file paths relative to webview directory
     * @param jsFiles - Array of JS file paths relative to webview directory
     * @returns The complete HTML content
     */
    protected getWebviewContent(
        webview: vscode.Webview,
        htmlFile: string,
        cssFiles: string[] = [],
        jsFiles: string[] = []
    ): string {
        try {
            const htmlPath = path.join(this.context.extensionPath, 'out', 'webview', htmlFile);
            let html = fs.readFileSync(htmlPath, 'utf8');

            // Replace CSS URIs
            cssFiles.forEach((cssFile, index) => {
                const cssUri = webview.asWebviewUri(
                    vscode.Uri.joinPath(this.context.extensionUri, 'out', 'webview', cssFile)
                );
                html = html.replace(`{{${this.getCssPlaceholder(index)}}}`, cssUri.toString());
            });

            // Replace JS URIs
            jsFiles.forEach((jsFile, index) => {
                const jsUri = webview.asWebviewUri(
                    vscode.Uri.joinPath(this.context.extensionUri, 'out', 'webview', jsFile)
                );
                html = html.replace(`{{${this.getJsPlaceholder(index)}}}`, jsUri.toString());
            });

            // Replace template variables
            html = this.replaceTemplateVariables(html);

            return html;
        } catch (error) {
            logger.error('Failed to load webview content', error);
            return this.getFallbackHtml(error);
        }
    }

    /**
     * Get CSS placeholder name for replacement
     * @param index - The CSS file index
     * @returns The placeholder name
     */
    private getCssPlaceholder(index: number): string {
        const placeholders = ['BASE_CSS_URI', 'COMPONENTS_CSS_URI', 'AGENT_CSS_URI', 'DEBUG_CSS_URI', 'CHAT_CSS_URI'];
        return placeholders[index] || `CSS_URI_${index}`;
    }

    /**
     * Get JS placeholder name for replacement
     * @param index - The JS file index
     * @returns The placeholder name
     */
    private getJsPlaceholder(index: number): string {
        const placeholders = ['UTILS_JS_URI', 'AGENT_JS_URI', 'DEBUG_JS_URI', 'CHAT_JS_URI'];
        return placeholders[index] || `JS_URI_${index}`;
    }

    /**
     * Replace template variables in HTML
     * @param html - The HTML content
     * @returns HTML with replaced variables
     */
    protected replaceTemplateVariables(html: string): string {
        // Replace extension version
        html = html.replace(/\{\{VERSION\}\}/g, this.getExtensionVersion());

        // Replace VS Code version
        html = html.replace(/\{\{VSCODE_VERSION\}\}/g, vscode.version);

        return html;
    }

    /**
     * Get extension version from package.json
     * @returns The extension version
     */
    protected getExtensionVersion(): string {
        try {
            const packageJsonPath = path.join(this.context.extensionPath, 'package.json');
            const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
            return packageJson.version || '0.1.0';
        } catch (error) {
            logger.debug('Failed to read extension version from package.json', error);
            return '0.1.0'; // Fallback version
        }
    }

    /**
     * Get fallback HTML when loading fails
     * @param error - The error that occurred
     * @returns Fallback HTML content
     */
    protected getFallbackHtml(error: any): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Wu Wei - Error</title>
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
    <h2>Wu Wei Extension</h2>
    <p class="error">⚠️ Failed to load content.</p>
    <p>Please check the extension installation and try again.</p>
    <p><strong>Error:</strong> ${error instanceof Error ? error.message : 'Unknown error'}</p>
</body>
</html>`;
    }

    /**
     * Post a message to the webview
     * @param message - The message to send
     */
    protected postMessage(message: any): void {
        if (this._view) {
            this._view.webview.postMessage(message);
        }
    }

    /**
     * Refresh the webview content
     */
    public abstract refresh(): void;
}
