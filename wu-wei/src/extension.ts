import * as vscode from 'vscode';
import { DebugPanelProvider } from './providers/debugPanelProvider';
import { AgentPanelProvider } from './providers/agentPanelProvider';
import { UnifiedChatProvider } from './providers/unifiedChatProvider';
import { WuWeiChatParticipant } from './chat/WuWeiChatParticipant';
import { PromptStoreProvider } from './promptStore/PromptStoreProvider';
import { PromptManager } from './promptStore/PromptManager';
import { ConfigurationManager } from './promptStore/ConfigurationManager';
import { SessionStateManager } from './promptStore/SessionStateManager';
import { FileOperationManager } from './promptStore/FileOperationManager';
import { TemplateManager } from './promptStore/TemplateManager';
import { FileOperationCommands } from './promptStore/commands';
import { CopilotCompletionSignalTool } from './tools/CopilotCompletionSignalTool';
import { ExecutionTracker } from './tools/ExecutionTracker';
import { CompletionHistoryCommands } from './tools/CompletionHistoryCommands';
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
    const unifiedChatProvider = new UnifiedChatProvider(context);
    const debugPanelProvider = new DebugPanelProvider(context);
    const agentPanelProvider = new AgentPanelProvider(context);

    // Initialize Wu Wei Chat Participant (MVP)
    const chatParticipant = new WuWeiChatParticipant(context);

    // Initialize execution tracker and completion signal tool
    const executionTracker = new ExecutionTracker(context);
    const completionSignalTool = new CopilotCompletionSignalTool(executionTracker);

    // Phase 2: Wire up completion signal integration with agent panel provider
    const completionSignalSubscription = CopilotCompletionSignalTool.onCompletion(
        (completionRecord) => {
            // Forward completion signals to agent panel provider
            agentPanelProvider.onCopilotCompletionSignal(completionRecord);
        }
    );
    context.subscriptions.push(completionSignalSubscription);

    // Initialize completion history commands
    const completionHistoryCommands = new CompletionHistoryCommands(executionTracker);

    // Register completion signal tool
    const toolRegistration = vscode.lm.registerTool('wu-wei_copilot_completion_signal', completionSignalTool);
    context.subscriptions.push(toolRegistration);

    logger.info('Copilot Completion Signal Tool registered successfully with Agent Panel Provider integration');

    // Initialize prompt store with configuration management
    const configManager = new ConfigurationManager(context);
    const sessionStateManager = new SessionStateManager(context);
    const promptManager = new PromptManager();
    const templateManager = new TemplateManager();
    const fileOperationManager = new FileOperationManager(promptManager, configManager);
    const fileOperationCommands = new FileOperationCommands(fileOperationManager, templateManager);
    const promptStoreProvider = new PromptStoreProvider(context.extensionUri, context);

    logger.info('Prompt store infrastructure created with file operations support');

    // Register webview providers
    const chatViewProvider = vscode.window.registerWebviewViewProvider('wu-wei.chat', unifiedChatProvider);
    const debugViewProvider = vscode.window.registerWebviewViewProvider('wu-wei.debug', debugPanelProvider);
    const agentViewProvider = vscode.window.registerWebviewViewProvider('wu-wei.agent', agentPanelProvider);
    const promptStoreViewProvider = vscode.window.registerWebviewViewProvider('wu-wei.promptStore', promptStoreProvider);

    logger.info('All webview providers registered');

    // Initialize prompt manager
    promptManager.initialize().catch(error => {
        logger.error('Failed to initialize prompt manager', error);
    });

    // Initialize template manager
    templateManager.loadCustomTemplates().catch(error => {
        logger.error('Failed to load custom templates', error);
    });

    // Register file operation commands
    const fileOperationDisposables = fileOperationCommands.registerCommands(context);
    context.subscriptions.push(...fileOperationDisposables);

    logger.info('File operation commands registered successfully');

    // Setup configuration change handling
    configManager.onConfigurationChanged(async (newConfig) => {
        logger.info('Configuration changed, updating prompt manager', {
            rootDirectory: newConfig.rootDirectory,
            autoRefresh: newConfig.autoRefresh
        });

        try {
            // Refresh prompts if auto-refresh is enabled
            if (newConfig.autoRefresh) {
                await promptManager.refreshPrompts();
            }

            // Update session state with new directory if changed
            if (newConfig.rootDirectory) {
                await sessionStateManager.setLastRootDirectory(newConfig.rootDirectory);
            }
        } catch (error) {
            logger.error('Failed to handle configuration change', error);
        }
    });

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
        await unifiedChatProvider.showDetailedModelInfo();
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



    // Register refresh agents command
    const refreshAgentsCommand = vscode.commands.registerCommand('wu-wei.refreshAgents', () => {
        logger.info('Refresh agents command executed');
        if (agentPanelProvider) {
            agentPanelProvider.refresh();
            vscode.window.showInformationMessage('Wu Wei: Agent panel refreshed');
        } else {
            vscode.window.showWarningMessage('Wu Wei: Agent panel not initialized');
        }
    });

    // Register show detailed model info command
    const showModelDetailsCommand = vscode.commands.registerCommand('wu-wei.showModelDetails', async () => {
        logger.info('Show model details command executed');
        await unifiedChatProvider.showDetailedModelInfo();
    });

    // Register prompt store commands
    const openPromptStoreCommand = vscode.commands.registerCommand('wu-wei.openPromptStore', () => {
        logger.info('Open prompt store command executed');
        vscode.commands.executeCommand('wu-wei.promptStore.focus');
    });

    // Register prompt store refresh command
    const promptStoreRefreshCommand = vscode.commands.registerCommand('wu-wei.promptStore.refresh', async () => {
        logger.info('Prompt store refresh command executed');
        try {
            promptStoreProvider.refresh();
            vscode.window.showInformationMessage('Wu Wei: Prompt store refreshed');
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            logger.error('Failed to refresh prompt store view', { error: errorMessage });
            vscode.window.showErrorMessage(`Wu Wei: Failed to refresh prompt store: ${errorMessage}`);
        }
    });

    // Register debug command for prompt store
    const debugPromptStoreCommand = vscode.commands.registerCommand('wu-wei.debugPromptStore', async () => {
        logger.info('Debug prompt store command executed');
        try {
            const prompts = promptManager.getAllPrompts();
            const config = promptManager.getConfig();

            const debugInfo = {
                promptCount: prompts.length,
                config: config,
                samplePrompts: prompts.slice(0, 3).map(p => ({
                    id: p.id,
                    fileName: p.fileName,
                    title: p.metadata?.title,
                    filePath: p.filePath
                }))
            };

            logger.info('Prompt store debug info:', debugInfo);

            const message = `Prompt Store Debug:
• Prompts: ${debugInfo.promptCount}
• Root Directory: ${config.rootDirectory || 'Not configured'}
• Auto Refresh: ${config.autoRefresh}
• Sample Prompts: ${debugInfo.samplePrompts.map(p => p.title || p.fileName).join(', ')}`;

            vscode.window.showInformationMessage(message);
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            logger.error('Failed to debug prompt store', { error: errorMessage });
            vscode.window.showErrorMessage(`Debug failed: ${errorMessage}`);
        }
    });

    const refreshPromptsCommand = vscode.commands.registerCommand('wu-wei.refreshPrompts', async () => {
        logger.info('Refresh prompts command executed');
        try {
            await promptManager.refreshPrompts();
            promptStoreProvider.refresh();
            vscode.window.showInformationMessage('Wu Wei: Prompts refreshed');
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            logger.error('Failed to refresh prompts', { error: errorMessage });
            vscode.window.showErrorMessage(`Wu Wei: Failed to refresh prompts: ${errorMessage}`);
        }
    });

    // Register completion history commands
    const completionHistoryCommandDisposables = completionHistoryCommands.registerCommands(context);

    // Listen for completion events
    if (CopilotCompletionSignalTool.onCompletion) {
        CopilotCompletionSignalTool.onCompletion(record => {
            logger.info('Copilot execution completed', {
                executionId: record.executionId,
                status: record.status
            });
        });
    }

    context.subscriptions.push(
        chatViewProvider,
        debugViewProvider,
        agentViewProvider,
        promptStoreViewProvider,
        chatParticipant,
        helloCommand,
        chatCommand,
        newChatCommand,
        refreshChatsCommand,
        showLogsCommand,
        clearLogsCommand,
        exportLogsCommand,
        debugModelsCommand,
        forceReloadModelsCommand,

        refreshAgentsCommand,
        showModelDetailsCommand,
        openPromptStoreCommand,
        promptStoreRefreshCommand,
        debugPromptStoreCommand,
        refreshPromptsCommand,
        ...completionHistoryCommandDisposables,
        executionTracker,
        completionSignalTool,
        completionHistoryCommands,
        promptManager,
        configManager,
        sessionStateManager,
        templateManager,
        fileOperationManager,
        logger
    );

    logger.info('All commands registered successfully');

    // Initialize automation systems
    initializeAutomation(context);

    logger.lifecycle('activate', 'Wu Wei extension activation completed');
}

export function deactivate() {
    logger.lifecycle('deactivate', 'Wu Wei extension deactivated - flowing like water');

    // Phase 2: Clean up completion signal tool resources
    CopilotCompletionSignalTool.dispose();

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
