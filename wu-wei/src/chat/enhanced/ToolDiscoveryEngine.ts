import * as vscode from 'vscode';
import { logger } from '../../logger';

/**
 * Enhanced tool discovery and categorization engine
 */
export class ToolDiscoveryEngine {
    private toolCapabilities: Map<string, ToolCapability> = new Map();
    private toolCategories: Map<string, ToolCategory> = new Map();
    private compatibilityMatrix: Map<string, string[]> = new Map();

    constructor() {
        this.initializeBuiltInCapabilities();
    }

    /**
     * Discover and analyze all available tools
     */
    async discoverTools(): Promise<ToolDiscoveryResult> {
        try {
            const tools = this.getAvailableTools();
            const capabilities: ToolCapability[] = [];

            for (const tool of tools) {
                const capability = await this.analyzeToolCapability(tool);
                this.toolCapabilities.set(tool.name, capability);
                capabilities.push(capability);
            }

            const categories = this.categorizeTools(capabilities);
            const compatibility = this.buildCompatibilityMatrix(capabilities);

            return {
                tools,
                capabilities,
                categories,
                compatibility,
                timestamp: Date.now(),
                totalCount: tools.length
            };

        } catch (error) {
            logger.error('ToolDiscoveryEngine: Tool discovery failed', {
                error: error instanceof Error ? error.message : 'Unknown error'
            });

            return {
                tools: [],
                capabilities: [],
                categories: [],
                compatibility: new Map(),
                timestamp: Date.now(),
                totalCount: 0,
                error: error instanceof Error ? error.message : 'Unknown error'
            };
        }
    }

    /**
     * Get tools filtered by category
     */
    getToolsByCategory(category: ToolCategoryType): vscode.LanguageModelToolInformation[] {
        const categoryData = this.toolCategories.get(category);
        if (!categoryData) {
            return [];
        }

        return categoryData.tools;
    }

    /**
     * Get tools suitable for a specific task
     */
    getToolsForTask(taskDescription: string): ToolRecommendation[] {
        const recommendations: ToolRecommendation[] = [];
        const normalizedTask = taskDescription.toLowerCase();

        for (const [toolName, capability] of this.toolCapabilities) {
            const score = this.calculateTaskRelevanceScore(normalizedTask, capability);

            if (score > 0.3) { // Minimum relevance threshold
                recommendations.push({
                    tool: capability.tool,
                    capability,
                    relevanceScore: score,
                    reasoning: this.generateRecommendationReasoning(normalizedTask, capability, score)
                });
            }
        }

        // Sort by relevance score
        return recommendations.sort((a, b) => b.relevanceScore - a.relevanceScore);
    }

    /**
     * Check tool compatibility
     */
    areToolsCompatible(tool1: string, tool2: string): boolean {
        const compatibleTools = this.compatibilityMatrix.get(tool1);
        return compatibleTools ? compatibleTools.includes(tool2) : false;
    }

    /**
     * Get compatible tools for a given tool
     */
    getCompatibleTools(toolName: string): string[] {
        return this.compatibilityMatrix.get(toolName) || [];
    }

    /**
     * Analyze tool capability
     */
    private async analyzeToolCapability(tool: vscode.LanguageModelToolInformation): Promise<ToolCapability> {
        const capability: ToolCapability = {
            tool,
            name: tool.name,
            description: tool.description || '',
            category: this.inferToolCategory(tool),
            inputTypes: this.analyzeInputTypes(tool.inputSchema),
            outputTypes: this.inferOutputTypes(tool),
            complexity: this.assessComplexity(tool),
            performance: this.assessPerformance(tool),
            reliability: this.assessReliability(tool),
            dependencies: this.analyzeDependencies(tool),
            capabilities: this.extractCapabilities(tool),
            tags: [...(tool.tags || [])],
            lastAnalyzed: Date.now()
        };

        return capability;
    }

    /**
     * Infer tool category from name and description
     */
    private inferToolCategory(tool: vscode.LanguageModelToolInformation): ToolCategoryType {
        const name = tool.name.toLowerCase();
        const description = (tool.description || '').toLowerCase();
        const combined = `${name} ${description}`;

        // File operations
        if (this.matchesKeywords(combined, ['file', 'read', 'write', 'directory', 'folder', 'path'])) {
            return ToolCategoryType.FILE_OPERATIONS;
        }

        // Code analysis
        if (this.matchesKeywords(combined, ['analyze', 'lint', 'format', 'refactor', 'code', 'syntax'])) {
            return ToolCategoryType.CODE_ANALYSIS;
        }

        // Search and query
        if (this.matchesKeywords(combined, ['search', 'find', 'query', 'grep', 'filter'])) {
            return ToolCategoryType.SEARCH_QUERY;
        }

        // Development tools
        if (this.matchesKeywords(combined, ['build', 'compile', 'test', 'debug', 'deploy'])) {
            return ToolCategoryType.DEVELOPMENT;
        }

        // Documentation
        if (this.matchesKeywords(combined, ['document', 'doc', 'readme', 'help', 'explain'])) {
            return ToolCategoryType.DOCUMENTATION;
        }

        // Version control
        if (this.matchesKeywords(combined, ['git', 'commit', 'branch', 'merge', 'version'])) {
            return ToolCategoryType.VERSION_CONTROL;
        }

        // Network/API
        if (this.matchesKeywords(combined, ['http', 'api', 'request', 'fetch', 'network', 'web'])) {
            return ToolCategoryType.NETWORK_API;
        }

        // Data processing
        if (this.matchesKeywords(combined, ['data', 'json', 'xml', 'csv', 'parse', 'transform'])) {
            return ToolCategoryType.DATA_PROCESSING;
        }

        return ToolCategoryType.UTILITY;
    }

    /**
     * Check if text matches any of the keywords
     */
    private matchesKeywords(text: string, keywords: string[]): boolean {
        return keywords.some(keyword => text.includes(keyword));
    }

    /**
     * Analyze input types from schema
     */
    private analyzeInputTypes(schema: any): string[] {
        if (!schema || !schema.properties) {
            return ['unknown'];
        }

        const types: string[] = [];

        for (const [, propSchema] of Object.entries(schema.properties as Record<string, any>)) {
            if (propSchema.type) {
                types.push(propSchema.type);
            }
        }

        return types.length > 0 ? types : ['object'];
    }

    /**
     * Infer output types based on tool purpose
     */
    private inferOutputTypes(tool: vscode.LanguageModelToolInformation): string[] {
        const name = tool.name.toLowerCase();
        const description = (tool.description || '').toLowerCase();

        if (this.matchesKeywords(`${name} ${description}`, ['read', 'get', 'fetch'])) {
            return ['text', 'data'];
        }

        if (this.matchesKeywords(`${name} ${description}`, ['analyze', 'check', 'validate'])) {
            return ['analysis', 'report'];
        }

        if (this.matchesKeywords(`${name} ${description}`, ['search', 'find', 'query'])) {
            return ['results', 'list'];
        }

        return ['text'];
    }

    /**
     * Assess tool complexity
     */
    private assessComplexity(tool: vscode.LanguageModelToolInformation): 'low' | 'medium' | 'high' {
        const schema = tool.inputSchema as any;

        if (!schema || !schema.properties) {
            return 'low';
        }

        const propCount = Object.keys(schema.properties).length;

        if (propCount <= 2) return 'low';
        if (propCount <= 5) return 'medium';
        return 'high';
    }

    /**
     * Assess tool performance characteristics
     */
    private assessPerformance(tool: vscode.LanguageModelToolInformation): PerformanceCharacteristics {
        const name = tool.name.toLowerCase();
        const description = (tool.description || '').toLowerCase();
        const combined = `${name} ${description}`;

        // Network tools are typically slower
        if (this.matchesKeywords(combined, ['http', 'api', 'network', 'fetch', 'download'])) {
            return {
                speed: 'slow',
                resourceUsage: 'medium',
                scalability: 'medium'
            };
        }

        // File operations can vary
        if (this.matchesKeywords(combined, ['file', 'read', 'write', 'directory'])) {
            return {
                speed: 'medium',
                resourceUsage: 'low',
                scalability: 'high'
            };
        }

        // Analysis tools can be resource intensive
        if (this.matchesKeywords(combined, ['analyze', 'parse', 'process', 'transform'])) {
            return {
                speed: 'medium',
                resourceUsage: 'high',
                scalability: 'medium'
            };
        }

        // Default characteristics
        return {
            speed: 'fast',
            resourceUsage: 'low',
            scalability: 'high'
        };
    }

    /**
     * Assess tool reliability
     */
    private assessReliability(tool: vscode.LanguageModelToolInformation): ReliabilityMetrics {
        // This would typically be based on historical data
        // For now, we provide estimated values based on tool type

        const name = tool.name.toLowerCase();
        const description = (tool.description || '').toLowerCase();
        const combined = `${name} ${description}`;

        if (this.matchesKeywords(combined, ['experimental', 'beta', 'preview'])) {
            return {
                errorRate: 0.15,
                successRate: 0.85,
                timeoutRate: 0.05
            };
        }

        if (this.matchesKeywords(combined, ['network', 'api', 'http'])) {
            return {
                errorRate: 0.10,
                successRate: 0.90,
                timeoutRate: 0.08
            };
        }

        return {
            errorRate: 0.05,
            successRate: 0.95,
            timeoutRate: 0.02
        };
    }

    /**
     * Analyze tool dependencies
     */
    private analyzeDependencies(tool: vscode.LanguageModelToolInformation): string[] {
        const dependencies: string[] = [];
        const name = tool.name.toLowerCase();
        const description = (tool.description || '').toLowerCase();
        const combined = `${name} ${description}`;

        if (this.matchesKeywords(combined, ['git'])) {
            dependencies.push('git');
        }

        if (this.matchesKeywords(combined, ['node', 'npm', 'javascript'])) {
            dependencies.push('node.js');
        }

        if (this.matchesKeywords(combined, ['python', 'pip'])) {
            dependencies.push('python');
        }

        if (this.matchesKeywords(combined, ['network', 'http', 'api'])) {
            dependencies.push('network');
        }

        if (this.matchesKeywords(combined, ['workspace', 'file', 'directory'])) {
            dependencies.push('workspace');
        }

        return dependencies;
    }

    /**
     * Extract capabilities from tool
     */
    private extractCapabilities(tool: vscode.LanguageModelToolInformation): string[] {
        const capabilities: string[] = [];
        const name = tool.name.toLowerCase();
        const description = (tool.description || '').toLowerCase();
        const combined = `${name} ${description}`;

        const capabilityMap = {
            'read': ['read', 'get', 'fetch', 'load'],
            'write': ['write', 'save', 'create', 'update'],
            'analyze': ['analyze', 'examine', 'inspect', 'check'],
            'search': ['search', 'find', 'query', 'filter'],
            'transform': ['transform', 'convert', 'format', 'parse'],
            'validate': ['validate', 'verify', 'test', 'check'],
            'execute': ['run', 'execute', 'perform', 'invoke'],
            'monitor': ['monitor', 'watch', 'track', 'observe']
        };

        for (const [capability, keywords] of Object.entries(capabilityMap)) {
            if (this.matchesKeywords(combined, keywords)) {
                capabilities.push(capability);
            }
        }

        return capabilities.length > 0 ? capabilities : ['utility'];
    }

    /**
     * Categorize tools into groups
     */
    private categorizeTools(capabilities: ToolCapability[]): ToolCategory[] {
        const categoryMap = new Map<ToolCategoryType, ToolCapability[]>();

        // Group capabilities by category
        for (const capability of capabilities) {
            const existing = categoryMap.get(capability.category) || [];
            existing.push(capability);
            categoryMap.set(capability.category, existing);
        }

        // Convert to ToolCategory objects
        const categories: ToolCategory[] = [];

        for (const [categoryType, categoryCapabilities] of categoryMap) {
            const category: ToolCategory = {
                type: categoryType,
                name: this.getCategoryDisplayName(categoryType),
                description: this.getCategoryDescription(categoryType),
                tools: categoryCapabilities.map(c => c.tool),
                capabilities: categoryCapabilities,
                count: categoryCapabilities.length
            };

            this.toolCategories.set(categoryType, category);
            categories.push(category);
        }

        return categories;
    }

    /**
     * Build compatibility matrix between tools
     */
    private buildCompatibilityMatrix(capabilities: ToolCapability[]): Map<string, string[]> {
        const matrix = new Map<string, string[]>();

        for (const capability of capabilities) {
            const compatible: string[] = [];

            for (const other of capabilities) {
                if (capability.name === other.name) continue;

                if (this.isCompatible(capability, other)) {
                    compatible.push(other.name);
                }
            }

            matrix.set(capability.name, compatible);
        }

        this.compatibilityMatrix = matrix;
        return matrix;
    }

    /**
     * Check if two tools are compatible
     */
    private isCompatible(tool1: ToolCapability, tool2: ToolCapability): boolean {
        // Tools in the same category are generally compatible
        if (tool1.category === tool2.category) {
            return true;
        }

        // Check for complementary capabilities
        const complementaryPairs = [
            [ToolCategoryType.FILE_OPERATIONS, ToolCategoryType.CODE_ANALYSIS],
            [ToolCategoryType.SEARCH_QUERY, ToolCategoryType.FILE_OPERATIONS],
            [ToolCategoryType.CODE_ANALYSIS, ToolCategoryType.DOCUMENTATION],
            [ToolCategoryType.VERSION_CONTROL, ToolCategoryType.FILE_OPERATIONS],
            [ToolCategoryType.DEVELOPMENT, ToolCategoryType.CODE_ANALYSIS]
        ];

        return complementaryPairs.some(pair =>
            (pair[0] === tool1.category && pair[1] === tool2.category) ||
            (pair[1] === tool1.category && pair[0] === tool2.category)
        );
    }

    /**
     * Calculate task relevance score
     */
    private calculateTaskRelevanceScore(task: string, capability: ToolCapability): number {
        let score = 0;

        // Check name similarity
        if (task.includes(capability.name.toLowerCase())) {
            score += 0.4;
        }

        // Check description similarity
        const descriptionWords = capability.description.toLowerCase().split(' ');
        const taskWords = task.split(' ');

        const commonWords = taskWords.filter(word =>
            descriptionWords.some(descWord => descWord.includes(word) || word.includes(descWord))
        );

        score += (commonWords.length / taskWords.length) * 0.3;

        // Check capabilities match
        const capabilityMatches = capability.capabilities.filter(cap => task.includes(cap));
        score += (capabilityMatches.length / capability.capabilities.length) * 0.3;

        return Math.min(score, 1.0);
    }

    /**
     * Generate recommendation reasoning
     */
    private generateRecommendationReasoning(task: string, capability: ToolCapability, score: number): string {
        const reasons: string[] = [];

        if (task.includes(capability.name.toLowerCase())) {
            reasons.push(`tool name matches task keywords`);
        }

        const matchingCapabilities = capability.capabilities.filter(cap => task.includes(cap));
        if (matchingCapabilities.length > 0) {
            reasons.push(`supports ${matchingCapabilities.join(', ')} operations`);
        }

        if (score > 0.7) {
            reasons.push('high relevance match');
        } else if (score > 0.5) {
            reasons.push('moderate relevance match');
        }

        return reasons.length > 0 ? reasons.join('; ') : 'general utility match';
    }

    /**
     * Get category display name
     */
    private getCategoryDisplayName(category: ToolCategoryType): string {
        const displayNames = {
            [ToolCategoryType.FILE_OPERATIONS]: 'File Operations',
            [ToolCategoryType.CODE_ANALYSIS]: 'Code Analysis',
            [ToolCategoryType.SEARCH_QUERY]: 'Search & Query',
            [ToolCategoryType.DEVELOPMENT]: 'Development Tools',
            [ToolCategoryType.DOCUMENTATION]: 'Documentation',
            [ToolCategoryType.VERSION_CONTROL]: 'Version Control',
            [ToolCategoryType.NETWORK_API]: 'Network & API',
            [ToolCategoryType.DATA_PROCESSING]: 'Data Processing',
            [ToolCategoryType.UTILITY]: 'Utilities'
        };

        return displayNames[category] || 'Unknown';
    }

    /**
     * Get category description
     */
    private getCategoryDescription(category: ToolCategoryType): string {
        const descriptions = {
            [ToolCategoryType.FILE_OPERATIONS]: 'Tools for reading, writing, and managing files and directories',
            [ToolCategoryType.CODE_ANALYSIS]: 'Tools for analyzing, linting, and formatting code',
            [ToolCategoryType.SEARCH_QUERY]: 'Tools for searching and querying content',
            [ToolCategoryType.DEVELOPMENT]: 'Tools for building, testing, and deploying applications',
            [ToolCategoryType.DOCUMENTATION]: 'Tools for creating and managing documentation',
            [ToolCategoryType.VERSION_CONTROL]: 'Tools for version control and collaboration',
            [ToolCategoryType.NETWORK_API]: 'Tools for network operations and API interactions',
            [ToolCategoryType.DATA_PROCESSING]: 'Tools for processing and transforming data',
            [ToolCategoryType.UTILITY]: 'General utility tools and helpers'
        };

        return descriptions[category] || 'Miscellaneous tools';
    }

    /**
     * Get available tools from VS Code API
     */
    private getAvailableTools(): vscode.LanguageModelToolInformation[] {
        try {
            if (vscode.lm && vscode.lm.tools) {
                return Array.from(vscode.lm.tools);
            }
        } catch (error) {
            logger.debug('ToolDiscoveryEngine: Error accessing tools API:', error);
        }

        return [];
    }

    /**
     * Initialize built-in tool capabilities
     */
    private initializeBuiltInCapabilities(): void {
        // This could be enhanced with a configuration file or database
        logger.debug('ToolDiscoveryEngine: Initialized with built-in capabilities');
    }
}

// Enums and interfaces
export enum ToolCategoryType {
    FILE_OPERATIONS = 'file-operations',
    CODE_ANALYSIS = 'code-analysis',
    SEARCH_QUERY = 'search-query',
    DEVELOPMENT = 'development',
    DOCUMENTATION = 'documentation',
    VERSION_CONTROL = 'version-control',
    NETWORK_API = 'network-api',
    DATA_PROCESSING = 'data-processing',
    UTILITY = 'utility'
}

export interface ToolCapability {
    tool: vscode.LanguageModelToolInformation;
    name: string;
    description: string;
    category: ToolCategoryType;
    inputTypes: string[];
    outputTypes: string[];
    complexity: 'low' | 'medium' | 'high';
    performance: PerformanceCharacteristics;
    reliability: ReliabilityMetrics;
    dependencies: string[];
    capabilities: string[];
    tags: string[];
    lastAnalyzed: number;
}

export interface PerformanceCharacteristics {
    speed: 'fast' | 'medium' | 'slow';
    resourceUsage: 'low' | 'medium' | 'high';
    scalability: 'low' | 'medium' | 'high';
}

export interface ReliabilityMetrics {
    errorRate: number;
    successRate: number;
    timeoutRate: number;
}

export interface ToolCategory {
    type: ToolCategoryType;
    name: string;
    description: string;
    tools: vscode.LanguageModelToolInformation[];
    capabilities: ToolCapability[];
    count: number;
}

export interface ToolDiscoveryResult {
    tools: vscode.LanguageModelToolInformation[];
    capabilities: ToolCapability[];
    categories: ToolCategory[];
    compatibility: Map<string, string[]>;
    timestamp: number;
    totalCount: number;
    error?: string;
}

export interface ToolRecommendation {
    tool: vscode.LanguageModelToolInformation;
    capability: ToolCapability;
    relevanceScore: number;
    reasoning: string;
}
