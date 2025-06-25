/**
 * Prompt Manager - Core business logic for managing prompts
 * Following wu wei principles: simple, efficient management that flows naturally
 */

import * as vscode from 'vscode';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as yaml from 'yaml';
import { Prompt, PromptStoreConfig, SearchFilter, FileWatcherEvent, PromptMetadata } from './types';
import { PromptFileWatcher } from './PromptFileWatcher';
import { MetadataParser } from './MetadataParser';
import { DEFAULT_CONFIG, LOG_CATEGORIES } from './constants';
import { WuWeiLogger } from '../logger';
import { FileUtils } from './utils/fileUtils';

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

    // =======================
    // File System Operations
    // =======================

    /**
     * Scan directory for markdown files recursively
     */
    async scanDirectory(rootPath: string): Promise<string[]> {
        const files: string[] = [];
        const stack = [rootPath];

        while (stack.length > 0) {
            const currentPath = stack.pop()!;

            try {
                const entries = await fs.readdir(currentPath, { withFileTypes: true });

                for (const entry of entries) {
                    const fullPath = path.join(currentPath, entry.name);
                    const relativePath = path.relative(rootPath, fullPath);

                    // Check if path should be excluded
                    if (FileUtils.shouldExcludePath(relativePath, this.config.excludePatterns) ||
                        FileUtils.shouldExcludePath(fullPath, this.config.excludePatterns)) {
                        continue;
                    }

                    if (entry.isDirectory() && !FileUtils.shouldIgnore(entry.name, this.config.excludePatterns)) {
                        stack.push(fullPath);
                    } else if (entry.isFile() && FileUtils.isMarkdownFile(entry.name) && !FileUtils.shouldIgnore(entry.name, this.config.excludePatterns)) {
                        files.push(fullPath);
                    }
                }
            } catch (error) {
                this.logger.error(`Failed to scan directory ${currentPath}:`, error);
                // Continue with other directories instead of failing completely
            }
        }

        this.logger.debug(`Scanned directory ${rootPath}, found ${files.length} markdown files`);
        return files;
    }

    /**
     * Load a single prompt from file path
     */
    async loadPrompt(filePath: string): Promise<Prompt> {
        const prompt = await this.loadPromptFromFile(filePath);
        if (!prompt) {
            throw new Error(`Failed to load prompt from ${filePath}`);
        }
        return prompt;
    }

    /**
     * Load all prompts from a root path
     */
    async loadAllPrompts(rootPath: string): Promise<Prompt[]> {
        const prompts: Prompt[] = [];
        const files = await this.scanDirectory(rootPath);

        const loadPromises = files.map(async (filePath) => {
            try {
                const prompt = await this.loadPromptFromFile(filePath);
                if (prompt) {
                    prompts.push(prompt);
                }
            } catch (error) {
                this.logger.warn(`Failed to load prompt from ${filePath}:`, error);
            }
        });

        await Promise.all(loadPromises);

        this.logger.info(`Loaded ${prompts.length} prompts from ${rootPath}`);
        return prompts;
    }

    /**
     * Save a prompt to file system
     */
    async savePrompt(prompt: Prompt): Promise<void> {
        try {
            // Validate the prompt has required fields
            if (!prompt.metadata.title) {
                throw new Error('Prompt must have a title');
            }

            // Create backup if file already exists
            if (await FileUtils.pathExists(prompt.filePath)) {
                await FileUtils.createBackup(prompt.filePath);
            }

            // Generate file content
            const content = this.generateFileContent(prompt);

            // Use atomic write operation
            await FileUtils.writeFileAtomic(prompt.filePath, content);

            // Update in memory cache
            prompt.lastModified = new Date();
            this.prompts.set(prompt.id, prompt);

            // Notify listeners
            this.eventEmitter.fire(this.getAllPrompts());

            this.logger.info(`Saved prompt: ${prompt.metadata.title} to ${prompt.filePath}`);
        } catch (error) {
            this.logger.error(`Failed to save prompt ${prompt.id}:`, error);
            throw error;
        }
    }

    /**
     * Delete a prompt file
     */
    async deletePrompt(filePath: string): Promise<void> {
        try {
            // Create backup before deletion
            if (await FileUtils.pathExists(filePath)) {
                await FileUtils.createBackup(filePath);
                await fs.unlink(filePath);
            }

            // Remove from memory cache
            const promptId = this.generatePromptId(filePath);
            this.prompts.delete(promptId);

            // Notify listeners
            this.eventEmitter.fire(this.getAllPrompts());

            this.logger.info(`Deleted prompt file: ${filePath}`);
        } catch (error) {
            this.logger.error(`Failed to delete prompt ${filePath}:`, error);
            throw error;
        }
    }

    /**
     * Create a new prompt file
     */
    async createPrompt(name: string, category?: string): Promise<Prompt> {
        try {
            // Generate safe file name
            const fileName = FileUtils.generateSafeFileName(name);

            // Determine file path
            let basePath = this.config.watchPaths[0]; // Use first watch path
            if (category) {
                basePath = path.join(basePath, category);
            }

            // Resolve workspace variables
            basePath = this.resolvePath(basePath);

            // Ensure directory exists
            await FileUtils.ensureDirectory(basePath);

            const filePath = path.join(basePath, fileName);

            // Check if file already exists
            if (await FileUtils.pathExists(filePath)) {
                throw new Error(`A prompt with the name "${name}" already exists in this category`);
            }

            // Create prompt object
            const prompt: Prompt = {
                id: this.generatePromptId(filePath),
                filePath,
                fileName,
                metadata: {
                    title: name,
                    description: '',
                    category: category || 'General',
                    tags: [],
                    created: new Date(),
                    modified: new Date()
                },
                content: '# ' + name + '\n\nEnter your prompt content here...',
                lastModified: new Date(),
                isValid: true
            };

            // Save the prompt
            await this.savePrompt(prompt);

            this.logger.info(`Created new prompt: ${name} at ${filePath}`);
            return prompt;
        } catch (error) {
            this.logger.error(`Failed to create prompt "${name}":`, error);
            throw error;
        }
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
            const files = await this.scanDirectory(dirPath);

            const loadPromises = files.map(async (filePath) => {
                const prompt = await this.loadPromptFromFile(filePath);
                if (prompt) {
                    prompts.set(prompt.id, prompt);
                }
            });

            await Promise.all(loadPromises);
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
            const parseResult = await this.metadataParser.parseFile(filePath);

            if (!parseResult.success || !parseResult.prompt) {
                this.logger.warn('Failed to parse prompt file', {
                    file: filePath,
                    errors: parseResult.errors.map(e => e.message).join(', ')
                });
                return null;
            }

            if (parseResult.warnings.length > 0) {
                this.logger.warn('Prompt file has validation warnings', {
                    file: filePath,
                    warnings: parseResult.warnings.map(w => w.message).join(', ')
                });
            }

            return parseResult.prompt;
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
        return FileUtils.isMarkdownFile(fileName);
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

    /**
     * Generate file content from prompt object
     */
    private generateFileContent(prompt: Prompt): string {
        let content = '';

        // Add YAML frontmatter if metadata exists
        if (Object.keys(prompt.metadata).length > 0) {
            // Create a clean metadata object without undefined values
            const cleanMetadata: any = {};

            Object.entries(prompt.metadata).forEach(([key, value]) => {
                if (value !== undefined && value !== null && value !== '') {
                    if (Array.isArray(value) && value.length === 0) {
                        return; // Skip empty arrays
                    }
                    cleanMetadata[key] = value;
                }
            });

            if (Object.keys(cleanMetadata).length > 0) {
                content += '---\n';
                content += yaml.stringify(cleanMetadata);
                content += '---\n\n';
            }
        }

        // Add the main content
        content += prompt.content;

        return content;
    }
}
