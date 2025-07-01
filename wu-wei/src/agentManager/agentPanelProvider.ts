import * as vscode from 'vscode';
import { BaseWebviewProvider, WebviewResourceConfig } from '../providers/BaseWebviewProvider';
import { logger } from '../logger';
import {
    AbstractAgent,
    AgentRequest,
    AgentResponse,
    AgentRegistry,
    WuWeiExampleAgent,
    GitHubCopilotAgent,
    AgentMessage
} from './agentInterface';
import { PromptService, PromptUsageContext } from '../shared/promptManager/types';
import { PromptServiceFactory } from '../shared/promptManager/PromptServiceFactory';
import { ExecutionTracker, CompletionRecord } from '../tools/ExecutionTracker';
import { ExecutionRegistry, ActiveExecution } from './ExecutionRegistry';
import { PromptEnhancer } from './PromptEnhancer';

/**
 * Configuration interface for agent prompt handling
 */
interface AgentPromptConfig {
    maxTokens: number;
    historyMessageCount: number;
}

/**
 * Wu Wei Agent Panel Provider (Enhanced with Prompt Integration and Execution Tracking)
 * Provides a panel for triggering agents with messages using separated HTML, CSS, and JavaScript files
 * 
 * Features:
 * - Phase 1: Basic agent execution and communication
 * - Phase 2: Execution tracking and completion signal integration
 * - Phase 4: Prompt selection and integration capabilities
 * 
 * Phase 2 adds complete execution lifecycle management:
 * - Real-time execution status tracking
 * - Completion signal integration with CopilotCompletionSignalTool
 * - Execution history and analytics
 * - UI status updates and progress indicators
 */
export class AgentPanelProvider extends BaseWebviewProvider implements vscode.WebviewViewProvider {
    private _agentRegistry: AgentRegistry;
    private _messageHistory: AgentMessage[] = [];
    private _promptService: PromptService;
    private _selectedPromptContext?: PromptUsageContext;
    private _agentPromptConfig: AgentPromptConfig = {
        maxTokens: 4096,
        historyMessageCount: 4
    };

    // Phase 2: Execution tracking and completion signal integration
    // These components provide complete execution lifecycle management using ExecutionRegistry:
    // - _executionRegistry: Central registry for tracking all executions with smart correlation
    // - _executionTracker: Persistent storage and history of all executions
    // - _completionEventEmitter: Event system for completion signal distribution
    private _executionRegistry: ExecutionRegistry;
    private _executionTracker: ExecutionTracker;
    private _completionEventEmitter: vscode.EventEmitter<CompletionRecord> = new vscode.EventEmitter<CompletionRecord>();
    public readonly onCompletionSignal: vscode.Event<CompletionRecord> = this._completionEventEmitter.event;

    constructor(context: vscode.ExtensionContext) {
        super(context);
        logger.debug('Wu Wei Agent Panel Provider initialized with prompt integration');

        // Phase 2: Initialize execution tracking system for complete lifecycle management
        // This enables real-time monitoring of agent executions from start to completion
        this._executionRegistry = new ExecutionRegistry();
        this._executionTracker = new ExecutionTracker(context);

        // Initialize prompt service
        this._promptService = PromptServiceFactory.createService(context);
        this.setupPromptEventHandlers();

        // Initialize prompt service asynchronously
        this.initializePromptService();

        // Initialize agent registry
        this._agentRegistry = new AgentRegistry();

        // Register example agent
        const exampleAgent = new WuWeiExampleAgent();
        this._agentRegistry.registerAgent(exampleAgent);

        // Register GitHub Copilot agent
        const copilotAgent = new GitHubCopilotAgent();
        this._agentRegistry.registerAgent(copilotAgent);

        // Phase 2: Setup completion signal monitoring system
        // This establishes the connection for receiving completion signals from CopilotCompletionSignalTool
        this.setupCompletionSignalMonitoring();

        // Activate the example agent
        exampleAgent.activate().then(() => {
            logger.info('Example agent activated');
        }).catch((error: any) => {
            logger.error('Failed to activate example agent', error);
        });

        // Activate the GitHub Copilot agent
        copilotAgent.activate().then(() => {
            logger.info('GitHub Copilot agent activated');
        }).catch((error: any) => {
            logger.error('Failed to activate GitHub Copilot agent', error);
        });
    }

    private setupPromptEventHandlers(): void {
        this._promptService.onPromptsChanged(this.handlePromptsChanged.bind(this));
        this._promptService.onPromptSelected(this.handlePromptSelected.bind(this));
    }

    /**
     * Format prompt data for UI display
     */
    private formatPromptForUI(prompt: any) {
        return {
            id: prompt.id,
            title: prompt.metadata.title,
            category: prompt.metadata.category,
            description: prompt.metadata.description,
            tags: prompt.metadata.tags
        };
    }

    /**
     * Format prompt context for UI display
     */
    private formatPromptContextForUI(context: PromptUsageContext) {
        return {
            id: context.prompt.id,
            title: context.prompt.metadata.title,
            content: context.prompt.content,
            parameters: context.metadata.parameters || [],
            usageInstructions: context.metadata.usageInstructions
        };
    }

    /**
     * Send error message to webview
     */
    private sendErrorToWebview(action: string, error: unknown): void {
        this._view?.webview.postMessage({
            command: 'error',
            error: `Failed to ${action}: ${error instanceof Error ? error.message : String(error)}`
        });
    }

    private async handlePromptsChanged(prompts: any[]): Promise<void> {
        if (this._view) {
            this._view.webview.postMessage({
                command: 'updateAvailablePrompts',
                prompts: prompts.map(p => this.formatPromptForUI(p))
            });
        }
    }

    private async handlePromptSelected(context: PromptUsageContext): Promise<void> {
        this._selectedPromptContext = context;

        if (this._view) {
            this._view.webview.postMessage({
                command: 'promptSelected',
                promptContext: this.formatPromptContextForUI(context)
            });
        }
    }

    resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        token: vscode.CancellationToken
    ): void {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.context.extensionUri]
        };

        // Load HTML with named resource mapping
        webviewView.webview.html = this.getWebviewContent(webviewView.webview, this.getAgentPanelConfig());

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async message => {
            logger.debug('Received message from agent panel webview:', message);
            await this.handleMessage(message);
        });

        // Send initial data
        this.sendAgentCapabilities();
        this.sendMessageHistory();
        this.sendAvailablePrompts();

        // Phase 2: Send initial execution state to newly connected webview
        // This ensures the UI has current execution status and history immediately
        this.sendPendingExecutions();
        this.sendExecutionHistory();

        logger.debug('Wu Wei Agent Panel webview resolved with prompt integration and execution tracking');
    }

    protected async handleMessage(message: any): Promise<void> {
        switch (message.command) {
            case 'sendAgentRequestWithPrompt':
                await this.handleAgentRequestWithPrompt(
                    message.agentName,
                    message.method,
                    message.params,
                    message.promptContext
                );
                break;
            case 'selectPrompt':
                await this.handleSelectPrompt(message.promptId);
                break;
            case 'renderPromptWithVariables':
                await this.handleRenderPrompt(message.promptId, message.variables);
                break;
            case 'getAvailablePrompts':
                await this.sendAvailablePrompts();
                break;
            case 'clearHistory':
                this.clearMessageHistory();
                break;
            case 'getAgentCapabilities':
                this.sendAgentCapabilities();
                break;
            // Phase 2: Enhanced webview commands for execution management
            // These commands provide real-time execution control and monitoring capabilities
            case 'getPendingExecutions':
                this.sendPendingExecutions();
                break;
            case 'cancelExecution':
                await this.handleCancelExecution(message.executionId);
                break;
            case 'getExecutionHistory':
                await this.sendExecutionHistory();
                break;
            default:
                logger.warn('Unknown command received from agent panel:', message.command);
        }
    }

    private async handleSelectPrompt(promptId: string): Promise<void> {
        try {
            const context = await this._promptService.selectPromptForUse(promptId);
            this._selectedPromptContext = context;

            this._view?.webview.postMessage({
                command: 'promptSelected',
                promptContext: this.formatPromptContextForUI(context)
            });
        } catch (error) {
            this.sendErrorToWebview('select prompt', error);
        }
    }

    private async handleRenderPrompt(promptId: string, variables: Record<string, any>): Promise<void> {
        try {
            const rendered = await this._promptService.renderPromptWithVariables(promptId, variables);

            this._view?.webview.postMessage({
                command: 'promptRendered',
                rendered
            });
        } catch (error) {
            this.sendErrorToWebview('render prompt', error);
        }
    }

    private async handleAgentRequestWithPrompt(
        agentName: string,
        method: string,
        params: any,
        promptContext?: any
    ): Promise<void> {
        // Phase 3: Generate unique execution ID and register with ExecutionRegistry
        const executionId = this.generateExecutionId();

        try {
            logger.info(`Processing agent request with prompt: ${agentName}.${method}`, {
                executionId,
                params,
                promptContext
            });

            const agent = this._agentRegistry.getAgent(agentName);
            if (!agent) {
                throw new Error(`Agent '${agentName}' not found`);
            }

            // Extract task description for execution tracking
            const taskDescription = PromptEnhancer.extractTaskDescription(params, promptContext);

            // Phase 3: Register execution with ExecutionRegistry for smart correlation
            this._executionRegistry.registerExecution({
                executionId,
                agentName,
                method,
                taskDescription,
                startTime: new Date(),
                status: 'executing',
                originalParams: params,
                promptContext
            });

            // Enhance parameters with prompt context using PromptEnhancer
            let enhancedParams = await PromptEnhancer.enhanceParamsWithPrompt({
                promptService: this._promptService,
                promptContext,
                agent,
                userParams: params
            });

            // Phase 3: For GitHub Copilot, inject execution context into the prompt itself
            // This ensures Copilot gets clear instructions to call the completion signal tool
            if (agentName === 'github-copilot') {
                const messageParam = enhancedParams.message || enhancedParams.query || enhancedParams.input || '';

                // Create execution context
                const executionContext = PromptEnhancer.createExecutionContext(
                    executionId,
                    taskDescription,
                    agentName
                );

                // Enhance the prompt with execution tracking instructions
                const enhancedPrompt = PromptEnhancer.enhancePromptWithExecutionContext(
                    messageParam,
                    executionContext
                );

                // Update the appropriate parameter
                if (enhancedParams.message) {
                    enhancedParams.message = enhancedPrompt;
                } else if (enhancedParams.query) {
                    enhancedParams.query = enhancedPrompt;
                } else if (enhancedParams.input) {
                    enhancedParams.input = enhancedPrompt;
                } else {
                    enhancedParams.message = enhancedPrompt;
                }
            }

            // Process the request
            const request: AgentRequest = {
                id: this.generateMessageId(),
                method,
                params: enhancedParams,
                timestamp: new Date()
            };

            // Add request to message history with execution correlation
            this.addMessageToHistory({
                id: request.id,
                timestamp: request.timestamp,
                type: 'request',
                method: request.method,
                params: {
                    // Clean the prompt for display in message history
                    ...request.params,
                    message: agentName === 'github-copilot' && request.params.message
                        ? PromptEnhancer.cleanPromptForDisplay(request.params.message)
                        : request.params.message,
                    executionId // Links this request to its eventual completion signal
                }
            });

            // Send execution start update to UI
            this.sendExecutionStatusUpdate(executionId, 'executing', {
                agentName,
                method,
                taskDescription,
                startTime: new Date()
            });

            const response = await agent.processRequest(request);

            // Add response to message history
            this.addMessageToHistory({
                id: response.id,
                timestamp: response.timestamp,
                type: 'response',
                result: response.result,
                error: response.error
            });

            // Phase 3: Handle immediate completion for non-Copilot agents
            // GitHub Copilot will signal completion via CopilotCompletionSignalTool,
            // but other agents complete immediately and need manual completion handling
            if (agentName !== 'github-copilot') {
                // For non-Copilot agents, mark as completed immediately
                setTimeout(() => {
                    this.handleImmediateCompletion(executionId, response);
                }, 100); // Small delay to ensure UI updates are processed
            }

        } catch (error) {
            // Phase 3: Comprehensive error handling with execution state cleanup
            this._executionRegistry.failExecution(executionId, error instanceof Error ? error.message : String(error));

            this.addMessageToHistory({
                id: this.generateMessageId(),
                timestamp: new Date(),
                type: 'error',
                error: {
                    code: -32603,
                    message: 'Request failed',
                    data: error instanceof Error ? error.message : String(error)
                }
            });

            // Send error update to UI
            this.sendExecutionStatusUpdate(executionId, 'failed', {
                error: error instanceof Error ? error.message : String(error)
            });
        }
    }

    /**
     * Update agent prompt configuration
     */
    public updateAgentPromptConfig(config: Partial<AgentPromptConfig>): void {
        this._agentPromptConfig = { ...this._agentPromptConfig, ...config };
        logger.info('Agent prompt configuration updated', this._agentPromptConfig);
    }

    /**
     * Get current agent prompt configuration
     */
    public getAgentPromptConfig(): AgentPromptConfig {
        return { ...this._agentPromptConfig };
    }

    private async sendAvailablePrompts(): Promise<void> {
        try {
            const prompts = await this._promptService.getAllPrompts();

            if (this._view) {
                this._view.webview.postMessage({
                    command: 'updateAvailablePrompts',
                    prompts: prompts.map(p => this.formatPromptForUI(p))
                });
            }
        } catch (error) {
            logger.error('Failed to load available prompts', error);
            if (this._view) {
                this._view.webview.postMessage({
                    command: 'updateAvailablePrompts',
                    prompts: []
                });
            }
        }
    }

    private addMessageToHistory(message: AgentMessage): void {
        this._messageHistory.push(message);

        // Keep only last 100 messages
        if (this._messageHistory.length > 100) {
            this._messageHistory = this._messageHistory.slice(-100);
        }

        this.sendMessageHistory();
    }

    private sendAgentCapabilities(): void {
        if (!this._view) {
            return;
        }

        const capabilities = this._agentRegistry.getAgentCapabilities();
        this._view.webview.postMessage({
            command: 'updateAgentCapabilities',
            capabilities
        });
    }

    private sendMessageHistory(): void {
        if (!this._view) {
            return;
        }

        this._view.webview.postMessage({
            command: 'updateMessageHistory',
            messages: this._messageHistory
        });
    }

    private clearMessageHistory(): void {
        logger.info('Clearing agent message history');
        this._messageHistory = [];
        this.sendMessageHistory();
        vscode.window.showInformationMessage('Wu Wei: Message history cleared');
    }

    /**
     * Refresh the webview content
     */
    public refresh(): void {
        if (this._view) {
            this._view.webview.html = this.getWebviewContent(this._view.webview, this.getAgentPanelConfig());

            // Re-send initial data after refresh
            setTimeout(() => {
                this.sendAgentCapabilities();
                this.sendMessageHistory();
                this.sendAvailablePrompts();
                // Phase 2: Include execution data in webview refresh
                // Ensure execution state and history are available after UI refresh
                this.sendPendingExecutions();
                this.sendExecutionHistory();
            }, 100);
        }
    }

    private generateMessageId(): string {
        return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Phase 2: Generate unique execution ID for tracking
     * Creates a time-based unique identifier for correlating execution start with completion signals
     */
    private generateExecutionId(): string {
        return `wu-wei-agent-exec-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Phase 2: Handle immediate completion for non-Copilot agents
     * 
     * Non-Copilot agents (like WuWeiExampleAgent) complete synchronously and don't use
     * the CopilotCompletionSignalTool. This method creates a synthetic completion record
     * to maintain consistent execution tracking across all agent types.
     */
    private handleImmediateCompletion(executionId: string, response: AgentResponse): void {
        const activeExecution = this._executionRegistry.getActiveExecution(executionId);
        if (!activeExecution) {
            logger.warn('Attempted to complete unknown execution', { executionId });
            return;
        }

        // Mark execution as completed in registry
        const completedExecution = this._executionRegistry.completeExecution(executionId);
        if (!completedExecution) {
            return;
        }

        // Create a completion record for immediate completion
        const completionRecord: CompletionRecord = {
            executionId,
            taskDescription: completedExecution.taskDescription,
            status: response.error ? 'error' : 'success',
            summary: response.result?.message || response.result?.content || 'Agent execution completed',
            metadata: {
                duration: new Date().getTime() - completedExecution.startTime.getTime(),
                toolsUsed: [completedExecution.agentName]
            },
            timestamp: new Date()
        };

        // Process the completion
        this.onCopilotCompletionSignal(completionRecord);
    }

    /**
     * Get the webview resource configuration for the agent panel
     * @returns WebviewResourceConfig for the agent panel
     */
    private getAgentPanelConfig(): WebviewResourceConfig {
        return {
            htmlFile: 'agent/index.html',
            cssResources: {
                'BASE_CSS_URI': 'shared/base.css',
                'COMPONENTS_CSS_URI': 'shared/components.css',
                'AGENT_CSS_URI': 'agent/style.css'
            },
            jsResources: {
                'UTILS_JS_URI': 'shared/utils.js',
                'AGENT_JS_URI': 'agent/main.js'
            }
        };
    }

    private async initializePromptService(): Promise<void> {
        try {
            await this._promptService.initialize();
            logger.info('Prompt service initialized for agent panel');
        } catch (error) {
            logger.error('Failed to initialize prompt service for agent panel', error);
        }
    }

    /**
     * Phase 2: Setup completion signal monitoring system
     * 
     * Establishes the infrastructure for receiving completion signals from the
     * CopilotCompletionSignalTool. The actual event wiring is done in extension.ts
     * to connect the tool's static event emitter to this provider's handler.
     */
    private setupCompletionSignalMonitoring(): void {
        // Listen for completion events from the completion signal tool
        // This will be connected when the tool is registered in extension.ts
        logger.debug('Setting up completion signal monitoring for agent panel');
    }

    /**
     * Phase 2: Handle completion signal from CopilotCompletionSignalTool
     * 
     * This is the core integration point that completes the execution tracking loop.
     * When a completion signal is received:
     * 1. Correlates the signal with the pending execution using executionId
     * 2. Updates execution status and calculates duration
     * 3. Adds completion details to message history
     * 4. Notifies the UI of completion
     * 5. Shows user notification if configured
     * 6. Cleans up tracking resources
     */
    public onCopilotCompletionSignal(completionRecord: CompletionRecord): void {
        try {
            logger.info('Received completion signal', {
                executionId: completionRecord.executionId,
                status: completionRecord.status
            });

            // Try to correlate the completion with an active execution
            let activeExecution = this._executionRegistry.correlateByExecutionId(completionRecord.executionId);

            // If no direct match, use smart correlation
            if (!activeExecution) {
                activeExecution = this._executionRegistry.smartCorrelate(
                    completionRecord.executionId,
                    completionRecord.taskDescription
                );
            }

            if (activeExecution) {
                // Mark execution as completed in registry
                const completedExecution = this._executionRegistry.completeExecution(activeExecution.executionId);

                if (completedExecution) {
                    // Calculate duration
                    const duration = new Date().getTime() - completedExecution.startTime.getTime();

                    // Add completion details to message history
                    this.addCompletionToHistory(completedExecution, completionRecord, duration);

                    // Send completion update to UI
                    this.sendExecutionStatusUpdate(completedExecution.executionId, 'completed', {
                        completionRecord,
                        duration
                    });

                    // Show completion notification
                    this.showExecutionCompletionNotification(completedExecution, completionRecord);

                    logger.debug('Successfully processed completion signal', {
                        executionId: completionRecord.executionId,
                        correlatedWith: completedExecution.executionId,
                        duration
                    });
                } else {
                    logger.warn('Failed to complete execution in registry', {
                        executionId: activeExecution.executionId
                    });
                }
            } else {
                logger.warn('Could not correlate completion signal with any active execution', {
                    executionId: completionRecord.executionId,
                    taskDescription: completionRecord.taskDescription,
                    activeExecutionsCount: this._executionRegistry.getActiveExecutions().length
                });

                // Still add to message history for debugging
                this.addStandaloneCompletionToHistory(completionRecord);
            }

            // Emit completion event for any external listeners
            this._completionEventEmitter.fire(completionRecord);

        } catch (error) {
            logger.error('Failed to process completion signal', {
                executionId: completionRecord.executionId,
                error: error instanceof Error ? error.message : String(error)
            });
        }
    }

    /**
     * Add standalone completion to message history when no active execution is found
     */
    private addStandaloneCompletionToHistory(completionRecord: CompletionRecord): void {
        const completionMessage: AgentMessage = {
            id: this.generateMessageId(),
            timestamp: completionRecord.timestamp,
            type: 'response',
            result: {
                type: 'standalone-completion-signal',
                executionId: completionRecord.executionId,
                status: completionRecord.status,
                taskDescription: completionRecord.taskDescription,
                summary: completionRecord.summary,
                metadata: completionRecord.metadata
            }
        };

        this.addMessageToHistory(completionMessage);
    }

    /**
     * Phase 2: Initialize execution tracking and register for completion signals
     * 
     * Begins the execution lifecycle tracking by:
     * 1. Creating a PendingExecution record with metadata
     * 2. Adding it to the tracking map for completion correlation
     * 3. Sending initial status update to the UI
     * 4. Logging the execution start for debugging
     */
    /**
     * Phase 3: Add completion details to message history with enhanced metadata
     * 
     * Creates a specialized completion message that includes:
     * - Original execution context (agent, method, start time)
     * - Completion details (status, summary, duration)
     * - Enhanced metadata for analytics and debugging
     * This provides a complete audit trail of the execution lifecycle.
     */
    private addCompletionToHistory(
        activeExecution: ActiveExecution,
        completionRecord: CompletionRecord,
        duration: number
    ): void {
        // Add enhanced completion message to history
        const completionMessage: AgentMessage = {
            id: this.generateMessageId(),
            timestamp: completionRecord.timestamp,
            type: 'response',
            result: {
                type: 'completion-signal',
                executionId: completionRecord.executionId,
                status: completionRecord.status,
                taskDescription: completionRecord.taskDescription,
                summary: completionRecord.summary,
                duration,
                agentName: activeExecution.agentName,
                method: activeExecution.method,
                metadata: {
                    ...completionRecord.metadata,
                    startTime: activeExecution.startTime.toISOString(),
                    endTime: completionRecord.timestamp.toISOString(),
                    duration
                }
            }
        };

        this.addMessageToHistory(completionMessage);
    }

    /**
     * Phase 2: Send real-time execution status updates to the UI
     * 
     * Provides live feedback to the webview about execution state changes.
     * Used for progress indicators, completion notifications, and status displays.
     */
    private sendExecutionStatusUpdate(
        executionId: string,
        status: string,
        details?: any
    ): void {
        if (this._view) {
            this._view.webview.postMessage({
                command: 'executionStatusUpdate',
                executionId,
                status,
                details,
                timestamp: new Date().toISOString()
            });
        }
    }

    /**
     * Phase 2: Show execution completion notification to user
     * 
     * Displays appropriate notification based on completion status and user preferences.
     * Respects the showExecutionCompletionNotifications configuration setting.
     */
    private showExecutionCompletionNotification(
        activeExecution: ActiveExecution,
        completionRecord: CompletionRecord
    ): void {
        const config = vscode.workspace.getConfiguration('wu-wei');
        const showNotifications = config.get<boolean>('showExecutionCompletionNotifications', true);

        if (!showNotifications) {
            return;
        }

        const statusIcon = this.getExecutionStatusIcon(completionRecord.status);
        const message = `${statusIcon} ${activeExecution.agentName}: ${completionRecord.taskDescription}`;

        if (completionRecord.status === 'success') {
            vscode.window.showInformationMessage(message);
        } else if (completionRecord.status === 'partial') {
            vscode.window.showWarningMessage(message);
        } else {
            vscode.window.showErrorMessage(message);
        }
    }

    /**
     * Phase 2: Get appropriate icon for execution status display
     * 
     * Provides consistent visual indicators for different execution states
     * used in notifications and UI status displays.
     */
    private getExecutionStatusIcon(status: string): string {
        switch (status) {
            case 'success': return '✅';
            case 'partial': return '⚠️';
            case 'error': return '❌';
            case 'executing': return '⏳';
            case 'pending': return '🟡';
            default: return '📝';
        }
    }

    /**
     * Phase 2: Send current pending executions to UI
     * 
     * Provides real-time view of all currently executing operations
     * including execution metadata, duration, and status for UI display.
     */
    private sendPendingExecutions(): void {
        if (!this._view) {
            return;
        }

        const activeExecutions = this._executionRegistry.getActiveExecutions().map(execution => ({
            executionId: execution.executionId,
            agentName: execution.agentName,
            method: execution.method,
            taskDescription: execution.taskDescription,
            status: execution.status,
            startTime: execution.startTime.toISOString(),
            duration: new Date().getTime() - execution.startTime.getTime()
        }));

        this._view.webview.postMessage({
            command: 'updatePendingExecutions',
            executions: activeExecutions
        });
    }

    /**
     * Phase 2: Handle user-initiated execution cancellation
     * 
     * Allows users to cancel running executions through the UI.
     * Note: This marks the execution as cancelled in our tracking system,
     * but cannot actually stop the underlying agent execution (e.g., Copilot chat).
     */
    private async handleCancelExecution(executionId: string): Promise<void> {
        const activeExecution = this._executionRegistry.getActiveExecution(executionId);
        if (!activeExecution) {
            logger.warn('Attempted to cancel unknown execution', { executionId });
            return;
        }

        try {
            // Cancel the execution in the registry
            const cancelled = this._executionRegistry.cancelExecution(executionId);

            if (cancelled) {
                // Send cancellation status update to UI
                this.sendExecutionStatusUpdate(executionId, 'cancelled', {
                    reason: 'User cancelled',
                    duration: new Date().getTime() - activeExecution.startTime.getTime()
                });

                // Add cancellation message to history
                this.addMessageToHistory({
                    id: this.generateMessageId(),
                    timestamp: new Date(),
                    type: 'error',
                    error: {
                        code: -32000,
                        message: 'Execution cancelled by user',
                        data: { executionId, taskDescription: activeExecution.taskDescription }
                    }
                });

                logger.info('Execution cancelled by user', { executionId });
            }

        } catch (error) {
            logger.error('Failed to cancel execution', {
                executionId,
                error: error instanceof Error ? error.message : String(error)
            });
        }
    }

    /**
     * Phase 2: Send execution history and statistics to UI
     * 
     * Provides comprehensive execution analytics including:
     * - Recent execution history (last 50 executions)
     * - Success/failure statistics
     * - Performance metrics (average duration, etc.)
     * Used for execution history views and performance dashboards.
     */
    private async sendExecutionHistory(): Promise<void> {
        if (!this._view) {
            return;
        }

        try {
            const history = this._executionTracker.getCompletionHistory(50); // Last 50 executions
            const stats = this._executionTracker.getCompletionStats();

            this._view.webview.postMessage({
                command: 'updateExecutionHistory',
                history: history.map(record => ({
                    executionId: record.executionId,
                    taskDescription: record.taskDescription,
                    status: record.status,
                    summary: record.summary,
                    timestamp: record.timestamp.toISOString(),
                    duration: record.metadata?.duration,
                    toolsUsed: record.metadata?.toolsUsed,
                    filesModified: record.metadata?.filesModified
                })),
                stats
            });

        } catch (error) {
            logger.error('Failed to send execution history', {
                error: error instanceof Error ? error.message : String(error)
            });

            this._view.webview.postMessage({
                command: 'updateExecutionHistory',
                history: [],
                stats: { total: 0, successful: 0, partial: 0, errors: 0 }
            });
        }
    }

    /**
     * Phase 2: Cleanup and resource disposal
     * 
     * Properly disposes of all Phase 2 resources including:
     * - Pending execution tracking
     * - Completion event emitter
     * - Execution tracker persistent storage
     * Ensures no memory leaks when the provider is disposed.
     */
    public dispose(): void {
        // Clean up execution registry
        this._executionRegistry.dispose();

        // Dispose event emitter
        this._completionEventEmitter.dispose();

        // Dispose execution tracker
        this._executionTracker.dispose();

        logger.debug('Agent Panel Provider disposed');
    }
}
