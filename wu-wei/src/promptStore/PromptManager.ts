/**
 * Prompt Manager - Core business logic for managing prompts
 * Following wu wei principles: simple, efficient management that flows naturally
 */

import * as vscode from 'vscode';
import * as fs from 'fs/promises';
import * as path from 'path';
import { Prompt, PromptStoreConfig, SearchFilter, FileWatcherEvent } from './types';
import { PromptFileWatcher } from './PromptFileWatcher';
import { MetadataParser } from './MetadataParser';
import { DEFAULT_CONFIG, LOG_CATEGORIES } from './constants';
import { WuWeiLogger } from '../logger';

export class PromptManager {
    private logger: WuWeiLogger;
    private config: PromptStoreConfig;
    private prompts: Map<string, Prompt> = new Map();
    private fileWatcher: PromptFileWatcher;
    private metadataParser: MetadataParser;
    private eventEmitter: vscode.EventEmitter<Prompt[]>;

    // Public event for external listeners
    public readonly onPromptsChanged: vscode.Event<Prompt[]>;

    constructor(config?: Partial<PromptStoreConfig>) {
        this.logger = WuWeiLogger.getInstance();
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.fileWatcher = new PromptFileWatcher();
        this.metadataParser = new MetadataParser();
        this.eventEmitter = new vscode.EventEmitter<Prompt[]>();
        this.onPromptsChanged = this.eventEmitter.event;

        this.setupFileWatcher();
    }

    /**
     * Initialize the prompt manager
     */
    public async initialize(): Promise<void> {
        try {
            this.logger.info('Initializing Prompt Manager');

            // Start file watcher
            await this.fileWatcher.startWatching(this.config.watchPaths);

            // Load initial prompts
            await this.refreshPrompts();

            this.logger.info('Prompt Manager initialized successfully', {
                promptCount: this.prompts.size,
                watchPaths: this.config.watchPaths
            });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to initialize Prompt Manager', { error: errorMessage });
            throw error;
        }
    }

    /**
     * Get all prompts
     */
    public getAllPrompts(): Prompt[] {
        return Array.from(this.prompts.values());
    }

    /**
     * Get a prompt by ID
     */
    public getPrompt(id: string): Prompt | undefined {
        return this.prompts.get(id);
    }

    /**
     * Search prompts based on filter criteria
     */
    public searchPrompts(filter: SearchFilter): Prompt[] {
        let results = this.getAllPrompts();

        // Filter by query
        if (filter.query) {
            const query = filter.query.toLowerCase();
            results = results.filter(prompt =>
                prompt.metadata.title.toLowerCase().includes(query) ||
                (prompt.metadata.description?.toLowerCase().includes(query)) ||
                prompt.content.toLowerCase().includes(query) ||
                (prompt.metadata.tags?.some(tag => tag.toLowerCase().includes(query)))
            );
        }

        // Filter by category
        if (filter.category) {
            results = results.filter(prompt =>
                prompt.metadata.category === filter.category
            );
        }

        // Filter by tags
        if (filter.tags && filter.tags.length > 0) {
            results = results.filter(prompt =>
                filter.tags!.some(tag =>
                    prompt.metadata.tags?.includes(tag)
                )
            );
        }

        // Filter by author
        if (filter.author) {
            results = results.filter(prompt =>
                prompt.metadata.author === filter.author
            );
        }

        // Filter by date range
        if (filter.modifiedAfter) {
            results = results.filter(prompt =>
                prompt.lastModified >= filter.modifiedAfter!
            );
        }

        if (filter.modifiedBefore) {
            results = results.filter(prompt =>
                prompt.lastModified <= filter.modifiedBefore!
            );
        }

        // Filter by parameters
        if (filter.hasParameters !== undefined) {
            results = results.filter(prompt =>
                filter.hasParameters ?
                    (prompt.metadata.parameters && prompt.metadata.parameters.length > 0) :
                    (!prompt.metadata.parameters || prompt.metadata.parameters.length === 0)
            );
        }

        return this.sortPrompts(results);
    }

    /**
     * Refresh all prompts from file system
     */
    public async refreshPrompts(): Promise<void> {
        try {
            this.logger.info('Refreshing prompts from file system');

            const newPrompts = new Map<string, Prompt>();

            for (const watchPath of this.config.watchPaths) {
                const resolvedPath = this.resolvePath(watchPath);
                await this.loadPromptsFromPath(resolvedPath, newPrompts);
            }

            this.prompts = newPrompts;
            this.eventEmitter.fire(this.getAllPrompts());

            this.logger.info('Prompts refreshed', { count: this.prompts.size });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to refresh prompts', { error: errorMessage });
        }
    }

    /**
     * Update configuration
     */
    public updateConfig(newConfig: Partial<PromptStoreConfig>): void {
        this.config = { ...this.config, ...newConfig };
        this.logger.info('Configuration updated', newConfig);
    }

    /**
     * Get current configuration
     */
    public getConfig(): PromptStoreConfig {
        return { ...this.config };
    }

    /**
     * Dispose of resources
     */
    public dispose(): void {
        this.fileWatcher.dispose();
        this.eventEmitter.dispose();
    }

    /**
     * Setup file watcher event handling
     */
    private setupFileWatcher(): void {
        this.fileWatcher.onFileChanged(async (event: FileWatcherEvent) => {
            try {
                switch (event.type) {
                    case 'add':
                    case 'change':
                        await this.handleFileChanged(event.filePath);
                        break;
                    case 'unlink':
                        await this.handleFileDeleted(event.filePath);
                        break;
                    case 'error':
                        this.logger.error('File watcher error', event.details);
                        break;
                }
            } catch (error) {
                const errorMessage = error instanceof Error ? error.message : String(error);
                this.logger.error('Error handling file watcher event', {
                    event: event.type,
                    file: event.filePath,
                    error: errorMessage
                });
            }
        });
    }

    /**
     * Handle file changed event
     */
    private async handleFileChanged(filePath: string): Promise<void> {
        const prompt = await this.loadPromptFromFile(filePath);
        if (prompt) {
            this.prompts.set(prompt.id, prompt);
            this.eventEmitter.fire(this.getAllPrompts());
            this.logger.debug('Prompt updated', { id: prompt.id, file: filePath });
        }
    }

    /**
     * Handle file deleted event
     */
    private async handleFileDeleted(filePath: string): Promise<void> {
        const promptId = this.generatePromptId(filePath);
        if (this.prompts.has(promptId)) {
            this.prompts.delete(promptId);
            this.eventEmitter.fire(this.getAllPrompts());
            this.logger.debug('Prompt removed', { id: promptId, file: filePath });
        }
    }

    /**
     * Load prompts from a specific path
     */
    private async loadPromptsFromPath(dirPath: string, prompts: Map<string, Prompt>): Promise<void> {
        try {
            const stat = await fs.stat(dirPath);
            if (!stat.isDirectory()) {
                return;
            }

            const entries = await fs.readdir(dirPath, { withFileTypes: true });

            for (const entry of entries) {
                const fullPath = path.join(dirPath, entry.name);

                if (entry.isDirectory()) {
                    await this.loadPromptsFromPath(fullPath, prompts);
                } else if (this.isPromptFile(entry.name)) {
                    const prompt = await this.loadPromptFromFile(fullPath);
                    if (prompt) {
                        prompts.set(prompt.id, prompt);
                    }
                }
            }
        } catch (error) {
            // Directory might not exist, which is OK
            this.logger.debug('Could not load prompts from path', { path: dirPath });
        }
    }

    /**
     * Load a single prompt from file
     */
    private async loadPromptFromFile(filePath: string): Promise<Prompt | null> {
        try {
            const content = await fs.readFile(filePath, 'utf-8');
            const stat = await fs.stat(filePath);

            const { metadata, content: promptContent } = this.metadataParser.parseMetadata(content);

            if (!metadata) {
                this.logger.warn('Failed to parse metadata for prompt', { file: filePath });
                return null;
            }

            const validation = this.metadataParser.validateMetadata(metadata);

            const prompt: Prompt = {
                id: this.generatePromptId(filePath),
                filePath,
                fileName: path.basename(filePath),
                metadata,
                content: promptContent,
                lastModified: stat.mtime,
                isValid: validation.isValid,
                validationErrors: validation.errors.map(e => e.message)
            };

            return prompt;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to load prompt from file', {
                file: filePath,
                error: errorMessage
            });
            return null;
        }
    }

    /**
     * Generate a unique ID for a prompt based on its file path
     */
    private generatePromptId(filePath: string): string {
        // Use relative path as ID to make it stable across different machines
        const workspaceRoot = vscode.workspace.rootPath;
        if (workspaceRoot && filePath.startsWith(workspaceRoot)) {
            return path.relative(workspaceRoot, filePath);
        }
        return filePath;
    }

    /**
     * Check if a file is a prompt file
     */
    private isPromptFile(fileName: string): boolean {
        const ext = path.extname(fileName).toLowerCase();
        return ['.md', '.markdown', '.txt'].includes(ext);
    }

    /**
     * Sort prompts based on configuration
     */
    private sortPrompts(prompts: Prompt[]): Prompt[] {
        return prompts.sort((a, b) => {
            let comparison = 0;

            switch (this.config.sortBy) {
                case 'name':
                    comparison = a.metadata.title.localeCompare(b.metadata.title);
                    break;
                case 'modified':
                    comparison = a.lastModified.getTime() - b.lastModified.getTime();
                    break;
                case 'category':
                    comparison = (a.metadata.category || '').localeCompare(b.metadata.category || '');
                    break;
                case 'author':
                    comparison = (a.metadata.author || '').localeCompare(b.metadata.author || '');
                    break;
            }

            return this.config.sortOrder === 'desc' ? -comparison : comparison;
        });
    }

    /**
     * Resolve workspace-relative paths
     */
    private resolvePath(inputPath: string): string {
        const workspaceRoot = vscode.workspace.rootPath;
        if (!workspaceRoot) {
            return inputPath;
        }

        const resolved = inputPath.replace('${workspaceFolder}', workspaceRoot);
        return path.isAbsolute(resolved) ? resolved : path.join(workspaceRoot, resolved);
    }
}
