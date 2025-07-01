/**
 * Wu Wei Agent Interface
 * Abstract interfaces for agent communication following MCP/A2A patterns
 */

/**
 * Base interface for agent requests and responses
 */
export interface AgentMessage {
    id: string;
    timestamp: Date;
    type: 'request' | 'response' | 'error';
    method?: string;
    params?: any;
    result?: any;
    error?: AgentError;
}

/**
 * Agent error structure
 */
export interface AgentError {
    code: number;
    message: string;
    data?: any;
}

/**
 * Agent request structure (similar to JSON-RPC)
 */
export interface AgentRequest {
    id: string;
    method: string;
    params: any;
    timestamp: Date;
}

/**
 * Agent response structure (similar to JSON-RPC)
 */
export interface AgentResponse {
    id: string;
    result?: any;
    error?: AgentError;
    timestamp: Date;
}

/**
 * Agent capabilities structure
 */
export interface AgentCapabilities {
    name: string;
    version: string;
    methods: string[];
    description?: string;
    metadata?: {
        promptSupport?: {
            supportsPrompts: boolean;
            supportsTsxMessages?: boolean;
            promptParameterName?: string;
            variableResolution?: boolean;
        };
        [key: string]: any;
    };
}

/**
 * Abstract base class for Wu Wei agents
 * Follows MCP (Model Context Protocol) patterns
 */
export abstract class AbstractAgent {
    protected _capabilities: AgentCapabilities;
    protected _isActive: boolean = false;

    constructor(capabilities: AgentCapabilities) {
        this._capabilities = capabilities;
    }

    /**
     * Get agent capabilities
     */
    getCapabilities(): AgentCapabilities {
        return { ...this._capabilities };
    }

    /**
     * Check if agent is active
     */
    isActive(): boolean {
        return this._isActive;
    }

    /**
     * Activate the agent
     */
    async activate(): Promise<void> {
        this._isActive = true;
    }

    /**
     * Deactivate the agent
     */
    async deactivate(): Promise<void> {
        this._isActive = false;
    }

    /**
     * Process an agent request
     * This is the main entry point for agent communication
     */
    async processRequest(request: AgentRequest): Promise<AgentResponse> {
        if (!this._isActive) {
            return {
                id: request.id,
                error: {
                    code: -32002,
                    message: 'Agent is not active'
                },
                timestamp: new Date()
            };
        }

        try {
            // Check if method is supported
            if (!this._capabilities.methods.includes(request.method)) {
                return {
                    id: request.id,
                    error: {
                        code: -32601,
                        message: `Method '${request.method}' not found`
                    },
                    timestamp: new Date()
                };
            }

            // Execute the method
            const result = await this.executeMethod(request.method, request.params);

            return {
                id: request.id,
                result,
                timestamp: new Date()
            };
        } catch (error) {
            return {
                id: request.id,
                error: {
                    code: -32603,
                    message: 'Internal error',
                    data: error instanceof Error ? error.message : String(error)
                },
                timestamp: new Date()
            };
        }
    }

    /**
     * Execute a specific method - to be implemented by concrete agents
     */
    protected abstract executeMethod(method: string, params: any): Promise<any>;

    /**
     * Generate a unique request ID
     */
    protected generateRequestId(): string {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
}

/**
 * Example concrete agent implementation
 */
export class WuWeiExampleAgent extends AbstractAgent {
    constructor() {
        super({
            name: 'wu-wei-example',
            version: '1.0.0',
            methods: ['echo', 'status', 'execute'],
            description: 'Example Wu Wei agent for demonstration purposes'
        });
    }

    protected async executeMethod(method: string, params: any): Promise<any> {
        switch (method) {
            case 'echo':
                return {
                    message: params.message || 'No message provided',
                    timestamp: new Date().toISOString()
                };

            case 'status':
                return {
                    status: 'active',
                    capabilities: this._capabilities,
                    uptime: Date.now()
                };

            case 'execute':
                // Simulate some work
                await new Promise(resolve => setTimeout(resolve, 100));
                return {
                    action: params.action || 'default',
                    result: 'Executed successfully',
                    parameters: params
                };

            default:
                throw new Error(`Unsupported method: ${method}`);
        }
    }
}

/**
 * GitHub Copilot Agent implementation
 * Uses VSCode's workbench.action.chat.openAgent command to interact with Copilot
 */
export class GitHubCopilotAgent extends AbstractAgent {
    constructor() {
        super({
            name: 'github-copilot',
            version: '1.0.0',
            methods: ['openAgent', 'ask'],
            description: 'GitHub Copilot agent for AI-powered coding assistance',
            metadata: {
                supportsStreaming: true,
                requiresWorkspace: true
            }
        });
    }

    protected async executeMethod(method: string, params: any): Promise<any> {
        // Import vscode dynamically to avoid issues during testing
        const vscode = await import('vscode');

        switch (method) {
            case 'openAgent':
                return await this.handleOpenAgent(params, vscode);

            case 'ask':
                return await this.handleAskRequest(params, vscode);

            default:
                throw new Error(`Unsupported method: ${method}`);
        }
    }

    private async handleOpenAgent(params: any, vscode: typeof import('vscode')): Promise<any> {
        try {
            const agentId = params.agentId || '';
            const query = params.message || params.query || '';

            // First, open a new chat to ensure we start fresh
            await vscode.commands.executeCommand('workbench.action.chat.newChat');

            // Wait a moment for the chat to initialize
            await new Promise(resolve => setTimeout(resolve, 500));

            // Then open the agent with the query (don't prepend agentId if query already contains it)
            const finalQuery = query ? (query.includes('@') ? query : `${agentId} ${query}`) : agentId;
            await vscode.commands.executeCommand('workbench.action.chat.openAgent', {
                query: finalQuery,
                isPartialQuery: !query
            });

            return {
                success: true,
                message: 'New chat opened and agent request sent successfully',
                agentId,
                query,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            throw new Error(`Failed to open agent: ${error instanceof Error ? error.message : String(error)}`);
        }
    }

    private async handleAskRequest(params: any, vscode: typeof import('vscode')): Promise<any> {
        try {
            const question = params.question || params.message || '';
            const context = params.context || '';

            if (!question) {
                throw new Error('Question is required for ask request');
            }

            // First, open a new chat to ensure we start fresh
            await vscode.commands.executeCommand('workbench.action.chat.newChat');

            // Wait a moment for the chat to initialize
            await new Promise(resolve => setTimeout(resolve, 500));

            // Let the user or prompt control agent selection
            const fullQuery = context ? `${question} Context: ${context}` : question;

            // Then execute the ask command
            await vscode.commands.executeCommand('workbench.action.chat.openAgent', {
                query: fullQuery,
                isPartialQuery: false
            });

            return {
                success: true,
                message: 'New chat opened and ask request sent successfully',
                question,
                context,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            throw new Error(`Failed to process ask request: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
}

/**
 * Agent registry for managing multiple agents
 */
export class AgentRegistry {
    private agents: Map<string, AbstractAgent> = new Map();

    /**
     * Register an agent
     */
    registerAgent(agent: AbstractAgent): void {
        const capabilities = agent.getCapabilities();
        this.agents.set(capabilities.name, agent);
    }

    /**
     * Get an agent by name
     */
    getAgent(name: string): AbstractAgent | undefined {
        return this.agents.get(name);
    }

    /**
     * Get all registered agents
     */
    getAllAgents(): AbstractAgent[] {
        return Array.from(this.agents.values());
    }

    /**
     * Get agent capabilities
     */
    getAgentCapabilities(): AgentCapabilities[] {
        return Array.from(this.agents.values()).map(agent => agent.getCapabilities());
    }
}
