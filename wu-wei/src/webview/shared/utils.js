// Wu Wei Extension - Shared JavaScript Utilities

/**
 * Common utilities for Wu Wei webviews
 */
class WuWeiUtils {
    /**
     * Post a message to the VS Code extension
     * @param {string} command - The command to send
     * @param {object} data - Additional data to send
     */
    static postMessage(command, data = {}) {
        if (typeof vscode !== 'undefined') {
            vscode.postMessage({ command, ...data });
        } else {
            console.warn('Wu Wei Utils: vscode API not available');
        }
    }

    /**
     * Show a confirmation dialog
     * @param {string} message - The confirmation message
     * @returns {boolean} - True if confirmed
     */
    static confirm(message) {
        return confirm(message);
    }

    /**
     * Show an alert dialog
     * @param {string} message - The alert message
     */
    static alert(message) {
        alert(message);
    }

    /**
     * Safely get element by ID
     * @param {string} id - The element ID
     * @returns {HTMLElement|null} - The element or null
     */
    static getElementById(id) {
        return document.getElementById(id);
    }

    /**
     * Safely set element text content
     * @param {string} id - The element ID
     * @param {string} text - The text to set
     */
    static setElementText(id, text) {
        const element = this.getElementById(id);
        if (element) {
            element.textContent = text;
        }
    }

    /**
     * Safely set element HTML content
     * @param {string} id - The element ID
     * @param {string} html - The HTML to set
     */
    static setElementHTML(id, html) {
        const element = this.getElementById(id);
        if (element) {
            element.innerHTML = html;
        }
    }

    /**
     * Toggle element visibility
     * @param {string} id - The element ID
     * @param {boolean} visible - Whether to show or hide
     */
    static toggleElementVisibility(id, visible) {
        const element = this.getElementById(id);
        if (element) {
            element.style.display = visible ? 'block' : 'none';
        }
    }

    /**
     * Log a message with Wu Wei prefix
     * @param {string} level - Log level (log, warn, error)
     * @param {string} message - The message to log
     * @param {any} data - Additional data to log
     */
    static log(level, message, data = null) {
        const prefix = '[Wu Wei Frontend]';
        if (data) {
            console[level](prefix, message, data);
        } else {
            console[level](prefix, message);
        }
    }
}

// Make available globally
window.WuWeiUtils = WuWeiUtils;
