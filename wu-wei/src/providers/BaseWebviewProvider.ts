import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { logger } from '../logger';

/**
 * Resource configuration for webview content
 */
export interface WebviewResourceConfig {
    htmlFile: string;
    cssResources?: Record<string, string>;
    jsResources?: Record<string, string>;
}

/**
 * Base class for Wu Wei webview providers
 * Provides common functionality for loading and managing webviews with named resource mapping
 */
export abstract class BaseWebviewProvider {
    protected _view?: vscode.WebviewView;

    constructor(protected context: vscode.ExtensionContext) { }

    /**
     * Get webview content with named resource mapping
     * @param webview - The webview instance
     * @param config - Resource configuration object
     * @returns The complete HTML content
     */
    protected getWebviewContent(webview: vscode.Webview, config: WebviewResourceConfig): string {
        try {
            const htmlPath = path.join(this.context.extensionPath, 'out', 'webview', config.htmlFile);
            let html = fs.readFileSync(htmlPath, 'utf8');

            // Replace CSS resources
            if (config.cssResources) {
                for (const [placeholder, resourcePath] of Object.entries(config.cssResources)) {
                    if (resourcePath && resourcePath.trim()) {
                        const cssUri = webview.asWebviewUri(
                            vscode.Uri.joinPath(this.context.extensionUri, 'out', 'webview', resourcePath)
                        );
                        logger.debug(`Replacing CSS placeholder {{${placeholder}}} with ${cssUri.toString()}`);
                        html = html.replace(`{{${placeholder}}}`, cssUri.toString());
                    } else {
                        logger.debug(`Removing empty CSS placeholder {{${placeholder}}}`);
                        html = this.removePlaceholderElement(html, placeholder, 'link');
                    }
                }
            }

            // Replace JS resources
            if (config.jsResources) {
                for (const [placeholder, resourcePath] of Object.entries(config.jsResources)) {
                    if (resourcePath && resourcePath.trim()) {
                        const jsUri = webview.asWebviewUri(
                            vscode.Uri.joinPath(this.context.extensionUri, 'out', 'webview', resourcePath)
                        );
                        logger.debug(`Replacing JS placeholder {{${placeholder}}} with ${jsUri.toString()}`);
                        html = html.replace(`{{${placeholder}}}`, jsUri.toString());
                    } else {
                        logger.debug(`Removing empty JS placeholder {{${placeholder}}}`);
                        html = this.removePlaceholderElement(html, placeholder, 'script');
                    }
                }
            }

            // Replace template variables
            html = this.replaceTemplateVariables(html);

            // Remove any remaining unreplaced placeholders
            html = this.removeUnreplacedPlaceholders(html);

            // Log final HTML for debugging
            logger.debug('Final webview HTML length:', html.length);
            logger.debug('Final HTML contains placeholders:', html.includes('{{'));

            return html;
        } catch (error) {
            logger.error('Failed to load webview content', error);
            return this.getFallbackHtml(error);
        }
    }

    /**
     * Legacy method for backward compatibility
     * @deprecated Use getWebviewContent with WebviewResourceConfig instead
     */
    protected getWebviewContentLegacy(
        webview: vscode.Webview,
        htmlFile: string,
        cssFiles: string[] = [],
        jsFiles: string[] = []
    ): string {
        logger.warn('Using deprecated getWebviewContentLegacy method. Consider migrating to named resource mapping.');

        // Convert to new format
        const config: WebviewResourceConfig = {
            htmlFile,
            cssResources: {},
            jsResources: {}
        };

        // Map CSS files to standard placeholders
        const cssPlaceholders = ['BASE_CSS_URI', 'COMPONENTS_CSS_URI', 'PROMPT_STORE_CSS_URI', 'AGENT_CSS_URI', 'DEBUG_CSS_URI', 'CHAT_CSS_URI'];
        cssFiles.forEach((file, index) => {
            if (file && cssPlaceholders[index]) {
                config.cssResources![cssPlaceholders[index]] = file;
            }
        });

        // Map JS files to standard placeholders
        const jsPlaceholders = ['UTILS_JS_URI', 'PROMPT_STORE_JS_URI', 'AGENT_JS_URI', 'DEBUG_JS_URI', 'CHAT_JS_URI'];
        jsFiles.forEach((file, index) => {
            if (file && jsPlaceholders[index]) {
                config.jsResources![jsPlaceholders[index]] = file;
            }
        });

        return this.getWebviewContent(webview, config);
    }

    /**
     * Remove HTML element containing a placeholder
     * @param html - The HTML content
     * @param placeholder - The placeholder name
     * @param elementType - The HTML element type ('link' or 'script')
     * @returns HTML with the element removed
     */
    private removePlaceholderElement(html: string, placeholder: string, elementType: 'link' | 'script'): string {
        if (elementType === 'link') {
            const linkPattern = new RegExp(`<link[^>]*href="\\{\\{${placeholder}\\}\\}"[^>]*>\\s*`, 'g');
            return html.replace(linkPattern, '');
        } else if (elementType === 'script') {
            const scriptPattern = new RegExp(`<script[^>]*src="\\{\\{${placeholder}\\}\\}"[^>]*></script>\\s*`, 'g');
            return html.replace(scriptPattern, '');
        }
        return html;
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
     * Remove any remaining unreplaced placeholders
     * @param html - The HTML content
     * @returns HTML with unreplaced placeholders removed
     */
    private removeUnreplacedPlaceholders(html: string): string {
        // Remove any remaining {{PLACEHOLDER}} patterns in href and src attributes
        html = html.replace(/<link[^>]*href="\{\{[^}]+\}\}"[^>]*>\s*/g, '');
        html = html.replace(/<script[^>]*src="\{\{[^}]+\}\}"[^>]*><\/script>\s*/g, '');

        // Log warning for any remaining placeholders
        const remainingPlaceholders = html.match(/\{\{[^}]+\}\}/g);
        if (remainingPlaceholders) {
            logger.warn('Found unreplaced placeholders in HTML:', remainingPlaceholders);
        }

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
