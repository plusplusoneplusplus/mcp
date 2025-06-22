import * as vscode from 'vscode';
import { WuWeiChatPanel } from './chatPanel';
import { WuWeiSidebarProvider, WuWeiActionsViewProvider } from './sidebarProvider';

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

    // Create the sidebar provider
    const sidebarProvider = new WuWeiSidebarProvider(context);
    const actionsProvider = new WuWeiActionsViewProvider(context);

    // Register tree data provider
    vscode.window.registerTreeDataProvider('wu-wei.chatSessions', sidebarProvider);

    // Register actions view provider
    vscode.window.registerWebviewViewProvider('wu-wei.actions', actionsProvider);

    // Connect sidebar provider to chat panel
    WuWeiChatPanel.setSidebarProvider(sidebarProvider);

    // Update context based on chat sessions
    const updateContext = () => {
        const hasChats = sidebarProvider.getSessionCount() > 0;
        vscode.commands.executeCommand('setContext', 'wu-wei.hasNoChats', !hasChats);
    };
    updateContext();

    // Register the hello world command
    const helloCommand = vscode.commands.registerCommand('wu-wei.hello', () => {
        vscode.window.showInformationMessage('Wu Wei: Effortless automation begins - 无为而治');
    });

    // Register the chat command
    const chatCommand = vscode.commands.registerCommand('wu-wei.openChat', () => {
        WuWeiChatPanel.createOrShow(context.extensionUri);
    });

    // Register new chat command
    const newChatCommand = vscode.commands.registerCommand('wu-wei.newChat', () => {
        sidebarProvider.createNewChat();
        updateContext();
    });

    // Register refresh chats command
    const refreshChatsCommand = vscode.commands.registerCommand('wu-wei.refreshChats', () => {
        sidebarProvider.refresh();
        updateContext();
    });

    // Register open chat session command
    const openChatSessionCommand = vscode.commands.registerCommand('wu-wei.openChatSession', (sessionId: string) => {
        sidebarProvider.openChat(sessionId);
    });

    // Register delete chat session command
    const deleteChatSessionCommand = vscode.commands.registerCommand('wu-wei.deleteChatSession', (sessionId: string) => {
        sidebarProvider.deleteChat(sessionId);
        updateContext();
    });

    // Register rename chat session command
    const renameChatSessionCommand = vscode.commands.registerCommand('wu-wei.renameChatSession', async (sessionId: string) => {
        await sidebarProvider.renameChat(sessionId);
    });

    context.subscriptions.push(
        helloCommand,
        chatCommand,
        newChatCommand,
        refreshChatsCommand,
        openChatSessionCommand,
        deleteChatSessionCommand,
        renameChatSessionCommand
    );

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
