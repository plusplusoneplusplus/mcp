import * as vscode from 'vscode';
import { WuWeiChatPanel } from './chatPanel';
import { WuWeiSidebarProvider, WuWeiActionsViewProvider } from './sidebarProvider';
import { WuWeiDebugPanelProvider } from './debugPanel';
import { logger } from './logger';
import { ClineIntegration } from './commands/clineIntegration';

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
        console.log('[Wu Wei Extension] wu-wei.showLogs command executed');
        logger.info('Show logs command executed from debug panel');
        logger.show();
        vscode.window.showInformationMessage('Wu Wei: Output panel opened - check the "Wu Wei" channel');
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

    // Register debug models command
    const debugModelsCommand = vscode.commands.registerCommand('wu-wei.debugModels', async () => {
        logger.info('Debug models command executed');

        try {
            // Show debug output channel first
            logger.show();

            logger.info('='.repeat(80));
            logger.info('WU WEI MODEL DEBUGGING SESSION STARTED');
            logger.info('='.repeat(80));

            // Check VSCode version
            const vscodeVersion = vscode.version;
            logger.info(`VSCode Version: ${vscodeVersion}`);

            // Check if language model API exists
            logger.info(`Language Model API Available: ${!!vscode.lm}`);

            if (!vscode.lm) {
                logger.error('VSCode Language Model API is not available. Please ensure VSCode 1.90+ is installed.');
                vscode.window.showErrorMessage('Wu Wei: Language Model API not available. Please update VSCode to 1.90+');
                return;
            }

            // Check installed extensions
            const extensions = vscode.extensions.all;
            const languageModelExtensions = extensions.filter(ext =>
                ext.id.includes('copilot') ||
                ext.id.includes('gpt') ||
                ext.id.includes('claude') ||
                ext.packageJSON?.contributes?.languageModels
            );

            logger.info(`Total Extensions Installed: ${extensions.length}`);
            logger.info(`Language Model Related Extensions: ${languageModelExtensions.length}`);

            languageModelExtensions.forEach(ext => {
                logger.info(`  - ${ext.id} (${ext.packageJSON?.displayName || 'Unknown'}) - Active: ${ext.isActive}`);
                if (ext.packageJSON?.contributes?.languageModels) {
                    logger.info(`    Contributes Language Models: ${JSON.stringify(ext.packageJSON.contributes.languageModels, null, 2)}`);
                }
            });

            // Try to get models with detailed logging
            logger.info('Attempting to fetch language models...');

            const startTime = Date.now();
            try {
                const models = await vscode.lm.selectChatModels();
                const endTime = Date.now();

                logger.info(`Model fetch completed in ${endTime - startTime}ms`);
                logger.info(`Found ${models.length} models:`);

                models.forEach((model, index) => {
                    logger.info(`  Model ${index + 1}:`);
                    logger.info(`    Family: ${model.family}`);
                    logger.info(`    Vendor: ${model.vendor}`);
                    logger.info(`    Name: ${model.name}`);
                    logger.info(`    ID: ${model.id}`);
                    logger.info(`    Max Input Tokens: ${model.maxInputTokens}`);
                    logger.info(`    String Representation: ${model.toString()}`);
                });

                if (models.length === 0) {
                    logger.warn('No models found. This could indicate:');
                    logger.warn('  1. No language model extensions are installed (e.g., GitHub Copilot)');
                    logger.warn('  2. Extensions are installed but not activated');
                    logger.warn('  3. Extensions are not properly configured');
                    logger.warn('  4. You need to sign in to the language model service');

                    vscode.window.showWarningMessage('Wu Wei: No language models found. Check the Output panel for details.');
                } else {
                    vscode.window.showInformationMessage(`Wu Wei: Found ${models.length} language models. Check Output panel for details.`);
                }

            } catch (modelError) {
                const endTime = Date.now();
                logger.error(`Model fetch failed after ${endTime - startTime}ms`, modelError);
                vscode.window.showErrorMessage('Wu Wei: Failed to fetch models. Check Output panel for details.');
            }

            // Get current Wu Wei chat panel state if it exists
            if (WuWeiChatPanel.currentPanel) {
                logger.info('Wu Wei Chat Panel is currently open');
                // Could add more panel-specific debugging here
            } else {
                logger.info('Wu Wei Chat Panel is not currently open');
            }

            logger.info('='.repeat(80));
            logger.info('WU WEI MODEL DEBUGGING SESSION COMPLETED');
            logger.info('='.repeat(80));

        } catch (error) {
            logger.error('Error in debug models command', error);
            vscode.window.showErrorMessage('Wu Wei: Debug models command failed');
        }
    });

    // Register force reload models command
    const forceReloadModelsCommand = vscode.commands.registerCommand('wu-wei.forceReloadModels', async () => {
        logger.info('Force reload models command executed');

        if (WuWeiChatPanel.currentPanel) {
            logger.info('Chat panel exists, forcing model reload...');
            // Access the private method through the class - this is for debugging purposes
            (WuWeiChatPanel.currentPanel as any)._loadAvailableModels();
            vscode.window.showInformationMessage('Wu Wei: Model reload initiated. Check Output panel for progress.');
        } else {
            logger.warn('No chat panel currently open to reload models');
            vscode.window.showWarningMessage('Wu Wei: No chat panel open. Open a chat first.');
        }
    });

    // Register Cline integration test command
    const testClineCommand = vscode.commands.registerCommand('wu-wei.testCline', async () => {
        logger.info('Test Cline integration command executed');
        await ClineIntegration.testClineIntegration();
    });

    // Register Cline debug command
    const debugClineCommand = vscode.commands.registerCommand('wu-wei.debugCline', async () => {
        logger.info('Debug Cline status command executed');
        await ClineIntegration.debugClineStatus();
        logger.show(); // Show the output panel to see debug info
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
        debugModelsCommand,
        forceReloadModelsCommand,
        testClineCommand,
        debugClineCommand,
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
