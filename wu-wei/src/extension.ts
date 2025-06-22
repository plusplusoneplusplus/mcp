import * as vscode from 'vscode';
import { WuWeiChatPanel } from './chatPanel';
import { WuWeiSidebarProvider, WuWeiActionsViewProvider } from './sidebarProvider';
import { WuWeiDebugPanelProvider } from './debugPanel';
import { logger } from './logger';

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
    logger.lifecycle('activate', 'Wu Wei extension is now active - 无为而治');

    // Create the sidebar provider
    const sidebarProvider = new WuWeiSidebarProvider(context);
    const actionsProvider = new WuWeiActionsViewProvider(context);
    const debugPanelProvider = new WuWeiDebugPanelProvider(context);

    logger.info('Sidebar, actions, and debug providers created');

    // Register tree data provider
    vscode.window.registerTreeDataProvider('wu-wei.chatSessions', sidebarProvider);
    logger.info('Tree data provider registered for chat sessions');

    // Register actions view provider
    vscode.window.registerWebviewViewProvider('wu-wei.actions', actionsProvider);
    logger.info('Webview provider registered for actions panel');

    // Register debug panel provider
    vscode.window.registerWebviewViewProvider('wu-wei.debug', debugPanelProvider);
    logger.info('Webview provider registered for debug panel');

    // Connect sidebar provider to chat panel
    WuWeiChatPanel.setSidebarProvider(sidebarProvider);
    logger.info('Sidebar provider connected to chat panel');

    // Update context based on chat sessions
    const updateContext = () => {
        const hasChats = sidebarProvider.getSessionCount() > 0;
        vscode.commands.executeCommand('setContext', 'wu-wei.hasNoChats', !hasChats);
    };
    updateContext();

    // Register the hello world command
    const helloCommand = vscode.commands.registerCommand('wu-wei.hello', () => {
        logger.info('Hello command executed');
        vscode.window.showInformationMessage('Wu Wei: Effortless automation begins - 无为而治');
    });

    // Register the chat command
    const chatCommand = vscode.commands.registerCommand('wu-wei.openChat', () => {
        logger.chat('Opening chat panel');
        WuWeiChatPanel.createOrShow(context.extensionUri);
    });

    // Register new chat command
    const newChatCommand = vscode.commands.registerCommand('wu-wei.newChat', () => {
        logger.chat('Creating new chat session');
        sidebarProvider.createNewChat();
        updateContext();
    });

    // Register refresh chats command
    const refreshChatsCommand = vscode.commands.registerCommand('wu-wei.refreshChats', () => {
        logger.chat('Refreshing chat sessions');
        sidebarProvider.refresh();
        updateContext();
    });

    // Register open chat session command
    const openChatSessionCommand = vscode.commands.registerCommand('wu-wei.openChatSession', (sessionIdOrItem: string | any) => {
        // Handle both direct sessionId strings and tree item objects
        const sessionId = typeof sessionIdOrItem === 'string' ? sessionIdOrItem : sessionIdOrItem?.sessionId || sessionIdOrItem?.id;

        logger.chat('Opening chat session command called', sessionId, {
            argumentType: typeof sessionIdOrItem,
            argumentValue: sessionIdOrItem
        });

        if (!sessionId) {
            logger.error('No valid session ID found in openChatSession command', { argument: sessionIdOrItem });
            vscode.window.showErrorMessage('Wu Wei: Invalid chat session ID');
            return;
        }

        sidebarProvider.openChat(sessionId);
    });

    // Register delete chat session command
    const deleteChatSessionCommand = vscode.commands.registerCommand('wu-wei.deleteChatSession', (item: any) => {
        logger.debug('Delete command called with item', item);
        const sessionId = item?.sessionId || item?.id || item;
        logger.chat('Deleting chat session', sessionId);
        sidebarProvider.deleteChat(sessionId);
        updateContext();
    });

    // Register rename chat session command
    const renameChatSessionCommand = vscode.commands.registerCommand('wu-wei.renameChatSession', async (item: any) => {
        logger.debug('Rename command called with item', item);
        const sessionId = item?.sessionId || item?.id || item;
        logger.chat('Renaming chat session', sessionId);
        await sidebarProvider.renameChat(sessionId);
    });

    // Register show logs command
    const showLogsCommand = vscode.commands.registerCommand('wu-wei.showLogs', () => {
        logger.info('Show logs command executed');
        logger.show();
    });

    // Register clear logs command
    const clearLogsCommand = vscode.commands.registerCommand('wu-wei.clearLogs', () => {
        logger.info('Clear logs command executed');
        logger.clear();
        vscode.window.showInformationMessage('Wu Wei: Output logs cleared');
    });

    // Register export logs command
    const exportLogsCommand = vscode.commands.registerCommand('wu-wei.exportLogs', async () => {
        logger.info('Export logs command executed');

        try {
            const uri = await vscode.window.showSaveDialog({
                defaultUri: vscode.Uri.file(`wu-wei-logs-${new Date().toISOString().split('T')[0]}.txt`),
                filters: {
                    'Text Files': ['txt'],
                    'All Files': ['*']
                }
            });

            if (uri) {
                vscode.window.showInformationMessage('Wu Wei: Log export feature coming soon');
                logger.info('Log export requested to', uri.fsPath);
            }
        } catch (error) {
            logger.error('Error in export logs command', error);
            vscode.window.showErrorMessage('Wu Wei: Failed to export logs');
        }
    });

    context.subscriptions.push(
        helloCommand,
        chatCommand,
        newChatCommand,
        refreshChatsCommand,
        openChatSessionCommand,
        deleteChatSessionCommand,
        renameChatSessionCommand,
        showLogsCommand,
        clearLogsCommand,
        exportLogsCommand,
        logger
    );

    logger.info('All commands registered successfully');

    // Initialize automation systems
    initializeAutomation(context);

    logger.lifecycle('activate', 'Wu Wei extension activation completed');
}

export function deactivate() {
    logger.lifecycle('deactivate', 'Wu Wei extension deactivated - flowing like water');
    logger.dispose();
}

/**
 * Initialize the automation systems
 * Following wu wei principles: set up the foundation, then let it flow naturally
 */
function initializeAutomation(context: vscode.ExtensionContext) {
    try {
        // Check if automation is enabled
        const config = vscode.workspace.getConfiguration('wu-wei');
        const automationEnabled = config.get<boolean>('enableAutomation', true);

        logger.automation('Checking automation configuration', { enabled: automationEnabled });

        if (automationEnabled) {
            logger.automation('Wu Wei automation systems initialized');
            // Future: Register automation providers here
        } else {
            logger.automation('Wu Wei automation systems disabled by configuration');
        }
    } catch (error) {
        logger.error('Failed to initialize automation systems', error);
    }
}
