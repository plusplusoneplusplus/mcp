import * as vscode from 'vscode';
import { WuWeiDebugPanelProvider } from './debugPanel';
import { WuWeiAgentPanelProvider } from './agentPanel';
import { UnifiedWuWeiChatProvider } from './unifiedChatProvider';
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

    // Create the providers
    const unifiedChatProvider = new UnifiedWuWeiChatProvider(context);
    const debugPanelProvider = new WuWeiDebugPanelProvider(context);
    const agentPanelProvider = new WuWeiAgentPanelProvider(context);

    logger.info('Unified chat, debug, and agent providers created');

    // Register webview providers
    const chatViewProvider = vscode.window.registerWebviewViewProvider('wu-wei.chat', unifiedChatProvider);
    const debugViewProvider = vscode.window.registerWebviewViewProvider('wu-wei.debug', debugPanelProvider);
    const agentViewProvider = vscode.window.registerWebviewViewProvider('wu-wei.agent', agentPanelProvider);

    logger.info('All webview providers registered');

    // Update context based on chat sessions
    const updateContext = () => {
        // For now, we'll assume there are always chats available with unified provider
        vscode.commands.executeCommand('setContext', 'wu-wei.hasNoChats', false);
    };
    updateContext();

    // Register the hello world command
    const helloCommand = vscode.commands.registerCommand('wu-wei.hello', () => {
        logger.info('Hello command executed');
        vscode.window.showInformationMessage('Wu Wei: Effortless automation begins - 无为而治');
    });

    // Register the chat command - now focuses the unified chat view
    const chatCommand = vscode.commands.registerCommand('wu-wei.openChat', () => {
        logger.chat('Focusing chat view');
        vscode.commands.executeCommand('wu-wei.chat.focus');
    });

    // Register new chat command - handled by unified provider
    const newChatCommand = vscode.commands.registerCommand('wu-wei.newChat', () => {
        logger.chat('Creating new chat session via unified provider');
        vscode.commands.executeCommand('wu-wei.chat.focus');
    });

    // Register refresh chats command
    const refreshChatsCommand = vscode.commands.registerCommand('wu-wei.refreshChats', () => {
        logger.chat('Refreshing chat sessions');
        vscode.commands.executeCommand('wu-wei.chat.focus');
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
            const versionParts = vscodeVersion.split('.');
            const majorVersion = parseInt(versionParts[0]);
            const minorVersion = parseInt(versionParts[1]);

            if (majorVersion < 1 || (majorVersion === 1 && minorVersion < 90)) {
                logger.warn(`VS Code version ${vscodeVersion} may not support Language Model API. Recommended: 1.90+`);
                vscode.window.showWarningMessage(`Wu Wei: VS Code ${vscodeVersion} may not support language models. Please update to 1.90+`);
            } else {
                logger.info(`VS Code version ${vscodeVersion} supports Language Model API`);
            }

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

            // Get current Wu Wei unified chat provider state
            const modelState = unifiedChatProvider.getModelState();
            logger.info('Wu Wei Unified Chat Provider state:', JSON.stringify(modelState, null, 2));

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
        try {
            await unifiedChatProvider.forceReloadModels();
            vscode.window.showInformationMessage('Wu Wei: Models reloaded. Check Output panel for details.');
        } catch (error) {
            logger.error('Failed to reload models:', error);
            vscode.window.showErrorMessage('Wu Wei: Failed to reload models. Check Output panel for details.');
        }
    });

    // Register send agent request command
    const sendAgentRequestCommand = vscode.commands.registerCommand('wu-wei.sendAgentRequest', () => {
        logger.info('Send agent request command executed');
        vscode.window.showInformationMessage('Wu Wei: Use the Agent Panel to send requests');
    });

    // Register refresh agents command
    const refreshAgentsCommand = vscode.commands.registerCommand('wu-wei.refreshAgents', () => {
        logger.info('Refresh agents command executed');
        if (agentPanelProvider) {
            vscode.window.showInformationMessage('Wu Wei: Agent list refreshed');
        } else {
            vscode.window.showWarningMessage('Wu Wei: Agent panel not initialized');
        }
    });

    context.subscriptions.push(
        chatViewProvider,
        debugViewProvider,
        agentViewProvider,
        helloCommand,
        chatCommand,
        newChatCommand,
        refreshChatsCommand,
        showLogsCommand,
        clearLogsCommand,
        exportLogsCommand,
        debugModelsCommand,
        forceReloadModelsCommand,
        sendAgentRequestCommand,
        refreshAgentsCommand,
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
