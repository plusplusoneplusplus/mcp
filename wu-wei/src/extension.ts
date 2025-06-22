import * as vscode from 'vscode';
import { WuWeiChatPanel } from './chatPanel';

/**
 * Wu Wei Extension - Effortless Work Automation
 * 
 * Philosophy: 无为而治 (Wu Wei Er Zhi)
 * "Govern by doing nothing that goes against nature"
 * 
 * This extension embodies the principle of effortless action,
 * automating work tasks with minimal friction and maximum flow.
 */

export function activate(context: vscode.ExtensionContext) {
    console.log('Wu Wei extension is now active - 无为而治');

    // Register the hello world command
    const helloCommand = vscode.commands.registerCommand('wu-wei.hello', () => {
        vscode.window.showInformationMessage('Wu Wei: Effortless automation begins - 无为而治');
    });

    // Register the chat command
    const chatCommand = vscode.commands.registerCommand('wu-wei.openChat', () => {
        WuWeiChatPanel.createOrShow(context.extensionUri);
    });

    context.subscriptions.push(helloCommand, chatCommand);

    // Initialize automation systems
    initializeAutomation(context);
}

export function deactivate() {
    console.log('Wu Wei extension deactivated - flowing like water');
}


/**
 * Initialize the automation systems
 * Following wu wei principles: set up the foundation, then let it flow naturally
 */
function initializeAutomation(context: vscode.ExtensionContext) {
    // Check if automation is enabled
    const config = vscode.workspace.getConfiguration('wu-wei');
    const automationEnabled = config.get<boolean>('enableAutomation', true);

    if (automationEnabled) {
        console.log('Wu Wei automation systems initialized');
        // Future: Register automation providers here
    }
}
