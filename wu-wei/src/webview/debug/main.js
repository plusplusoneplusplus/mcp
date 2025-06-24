// Wu Wei Debug Panel JavaScript
const vscode = acquireVsCodeApi();

function showLogs() {
    console.log('[Wu Wei Frontend] showLogs button clicked');
    try {
        vscode.postMessage({ command: 'showLogs' });
        console.log('[Wu Wei Frontend] showLogs message sent successfully');
    } catch (error) {
        console.error('[Wu Wei Frontend] Error sending showLogs message:', error);
    }
}

function clearLogs() {
    console.log('[Wu Wei Frontend] clearLogs button clicked');
    if (confirm('Are you sure you want to clear all debug logs? This action cannot be undone.')) {
        try {
            vscode.postMessage({ command: 'clearLogs' });
            console.log('[Wu Wei Frontend] clearLogs message sent successfully');
        } catch (error) {
            console.error('[Wu Wei Frontend] Error sending clearLogs message:', error);
        }
    }
}

function exportLogs() {
    console.log('[Wu Wei Frontend] exportLogs button clicked');
    try {
        vscode.postMessage({ command: 'exportLogs' });
        console.log('[Wu Wei Frontend] exportLogs message sent successfully');
    } catch (error) {
        console.error('[Wu Wei Frontend] Error sending exportLogs message:', error);
    }
}

function refreshDebugInfo() {
    vscode.postMessage({ command: 'refreshDebugInfo' });

    // Note: The actual update will happen when we receive 'updateDebugInfo' message from extension
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
        .split('\n')
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

        html += `
            <div class="command-result">
                <div class="command-result-command">${statusIcon} ${result.command}</div>
                ${result.message ? `<div class="command-result-message">${result.message}</div>` : ''}
            </div>
        `;
    });

    resultsDiv.innerHTML = html;
    outputSection.style.display = 'block';
}

// Function to update debug information (called from backend)
function updateDebugInfo(data) {
    console.log('[Wu Wei Frontend] Updating debug info:', data);

    // Update VS Code version
    const vscodeVersionElement = document.getElementById('vscodeVersion');
    if (vscodeVersionElement && data.vscodeVersion) {
        vscodeVersionElement.textContent = data.vscodeVersion;
    }

    // You could update other debug info here as well
    // For example, if there were elements for extension version, timestamp, etc.
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
        case 'updateDebugInfo':
            updateDebugInfo(message.data);
            break;
        default:
            console.log('[Wu Wei Frontend] Unknown message from extension:', message);
    }
});
