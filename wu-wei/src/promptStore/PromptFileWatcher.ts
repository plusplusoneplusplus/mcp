/**
 * File Watcher for monitoring prompt files
 * Following wu wei principles: gentle observation that flows with file system changes
 * Enhanced with debouncing, error handling, and event management
 */

import * as chokidar from 'chokidar';
import * as vscode from 'vscode';
import * as path from 'path';
import { EventEmitter } from 'events';
import { FileWatcherEvent, FileWatcherConfig, FileWatcherEventType, FileWatcherEventCallback } from './types';
import { WATCHER_CONFIG, FILE_PATTERNS } from './constants';
import { WuWeiLogger } from '../logger';

export class PromptFileWatcher {
    private logger: WuWeiLogger;
    private watcher: chokidar.FSWatcher | null = null;
    private eventEmitter: EventEmitter;
    private isWatching: boolean = false;
    private isPaused: boolean = false;
    private debouncedEvents = new Map<string, NodeJS.Timeout>();
    private config: FileWatcherConfig;

    // VS Code event emitter for external listeners
    private vscodeEventEmitter: vscode.EventEmitter<FileWatcherEvent>;
    public readonly onFileChanged: vscode.Event<FileWatcherEvent>;

    constructor(config?: Partial<FileWatcherConfig>) {
        this.logger = WuWeiLogger.getInstance();
        this.eventEmitter = new EventEmitter();
        this.vscodeEventEmitter = new vscode.EventEmitter<FileWatcherEvent>();
        this.onFileChanged = this.vscodeEventEmitter.event;

        // Default configuration
        this.config = {
            enabled: true,
            debounceMs: WATCHER_CONFIG.DEBOUNCE_MS,
            maxDepth: WATCHER_CONFIG.MAX_DEPTH,
            followSymlinks: WATCHER_CONFIG.FOLLOW_SYMLINKS,
            ignorePatterns: [],
            usePolling: WATCHER_CONFIG.USE_POLLING,
            pollingInterval: WATCHER_CONFIG.POLL_INTERVAL,
            ...config
        };
    }

    /**
     * Start watching the specified root path
     */
    public async start(rootPath: string): Promise<void> {
        if (this.isWatching) {
            this.logger.warn('File watcher is already running');
            return;
        }

        if (!this.config.enabled) {
            this.logger.info('File watcher is disabled');
            return;
        }

        try {
            this.stop(); // Clean up existing watcher

            const resolvedPath = this.resolvePath(rootPath);

            this.watcher = chokidar.watch(resolvedPath, {
                ignored: this.buildIgnorePatterns(),
                persistent: true,
                ignoreInitial: true,
                followSymlinks: this.config.followSymlinks,
                depth: this.config.maxDepth,
                usePolling: this.config.usePolling,
                interval: this.config.pollingInterval,
                awaitWriteFinish: WATCHER_CONFIG.AWAIT_WRITE_FINISH
            });

            this.setupEventHandlers();
            this.isWatching = true;
            this.isPaused = false;

            this.logger.info('File watcher started', {
                path: resolvedPath,
                config: this.config
            });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to start file watcher', { error: errorMessage });
            throw error;
        }
    }

    /**
     * Stop watching files
     */
    public stop(): void {
        if (!this.isWatching || !this.watcher) {
            return;
        }

        try {
            // Clear all debounced events
            this.clearDebouncedEvents();

            // Close the watcher
            this.watcher.close();
            this.watcher = null;
            this.isWatching = false;
            this.isPaused = false;

            this.logger.info('File watcher stopped');
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to stop file watcher', { error: errorMessage });
        }
    }

    /**
     * Pause file watching (keeps watcher alive but ignores events)
     */
    public pause(): void {
        if (this.isWatching) {
            this.isPaused = true;
            this.logger.debug('File watcher paused');
        }
    }

    /**
     * Resume file watching
     */
    public resume(): void {
        if (this.isWatching) {
            this.isPaused = false;
            this.logger.debug('File watcher resumed');
        }
    }

    /**
     * Check if currently watching
     */
    public isActive(): boolean {
        return this.isWatching && !this.isPaused;
    }

    /**
     * Get current watching status
     */
    public getStatus(): { isWatching: boolean; isPaused: boolean; watchedPaths: string[] } {
        return {
            isWatching: this.isWatching,
            isPaused: this.isPaused,
            watchedPaths: this.getWatchedPaths()
        };
    }

    /**
     * Update configuration
     */
    public updateConfig(newConfig: Partial<FileWatcherConfig>): void {
        this.config = { ...this.config, ...newConfig };
        this.logger.debug('File watcher configuration updated', this.config);
    }

    /**
     * Add event listener
     */
    public on(event: FileWatcherEventType, callback: FileWatcherEventCallback): void {
        this.eventEmitter.on(event, callback);
    }

    /**
     * Remove event listener
     */
    public off(event: FileWatcherEventType, callback: FileWatcherEventCallback): void {
        this.eventEmitter.off(event, callback);
    }

    /**
     * Remove all listeners for an event
     */
    public removeAllListeners(event?: FileWatcherEventType): void {
        if (event) {
            this.eventEmitter.removeAllListeners(event);
        } else {
            this.eventEmitter.removeAllListeners();
        }
    }

    /**
     * Get watched paths
     */
    public getWatchedPaths(): string[] {
        if (!this.watcher) {
            return [];
        }
        const watched = this.watcher.getWatched();
        return watched ? Object.keys(watched) : [];
    }

    /**
     * Dispose of resources
     */
    public dispose(): void {
        this.stop();
        this.removeAllListeners();
        this.vscodeEventEmitter.dispose();
        this.clearDebouncedEvents();
    }

    /**
     * Resolve workspace-relative paths to absolute paths
     */
    private resolvePath(watchPath: string): string {
        const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (!workspaceRoot) {
            this.logger.warn('No workspace root found, using provided path as-is');
            return watchPath;
        }

        // Replace ${workspaceFolder} variable
        const resolved = watchPath.replace('${workspaceFolder}', workspaceRoot);
        return path.isAbsolute(resolved) ? resolved : path.join(workspaceRoot, resolved);
    }

    /**
     * Build ignore patterns for chokidar
     */
    private buildIgnorePatterns(): (RegExp | string)[] {
        const patterns = [...WATCHER_CONFIG.IGNORED, ...this.config.ignorePatterns];
        return patterns;
    }

    /**
     * Setup event handlers for the file watcher
     */
    private setupEventHandlers(): void {
        if (!this.watcher) {
            return;
        }

        this.watcher
            .on('add', (filePath) => this.handleFileAdded(filePath))
            .on('change', (filePath) => this.handleFileChanged(filePath))
            .on('unlink', (filePath) => this.handleFileDeleted(filePath))
            .on('addDir', (dirPath) => this.handleDirectoryAdded(dirPath))
            .on('unlinkDir', (dirPath) => this.handleDirectoryDeleted(dirPath))
            .on('error', (error) => this.handleWatcherError(error))
            .on('ready', () => this.handleWatcherReady());
    }

    /**
     * Handle file added event
     */
    private handleFileAdded(filePath: string): void {
        if (this.isPaused || !this.isMarkdownFile(filePath)) {
            return;
        }

        this.emitEvent('fileAdded', filePath);
        this.emitVSCodeEvent('add', filePath);
    }

    /**
     * Handle file changed event with debouncing
     */
    private handleFileChanged(filePath: string): void {
        if (this.isPaused || !this.isMarkdownFile(filePath)) {
            return;
        }

        // Clear existing timeout for this file
        const existingTimeout = this.debouncedEvents.get(filePath);
        if (existingTimeout) {
            clearTimeout(existingTimeout);
        }

        // Set new debounced timeout
        const timeout = setTimeout(() => {
            this.debouncedEvents.delete(filePath);
            this.emitEvent('fileChanged', filePath);
            this.emitVSCodeEvent('change', filePath);
        }, this.config.debounceMs);

        this.debouncedEvents.set(filePath, timeout);
    }

    /**
     * Handle file deleted event
     */
    private handleFileDeleted(filePath: string): void {
        if (this.isPaused || !this.isMarkdownFile(filePath)) {
            return;
        }

        // Clear any pending debounced events for this file
        const existingTimeout = this.debouncedEvents.get(filePath);
        if (existingTimeout) {
            clearTimeout(existingTimeout);
            this.debouncedEvents.delete(filePath);
        }

        this.emitEvent('fileDeleted', filePath);
        this.emitVSCodeEvent('unlink', filePath);
    }

    /**
     * Handle directory added event
     */
    private handleDirectoryAdded(dirPath: string): void {
        if (this.isPaused) {
            return;
        }

        this.emitEvent('directoryAdded', dirPath);
        this.logger.debug('Directory added', { path: dirPath });
    }

    /**
     * Handle directory deleted event
     */
    private handleDirectoryDeleted(dirPath: string): void {
        if (this.isPaused) {
            return;
        }

        this.emitEvent('directoryDeleted', dirPath);
        this.logger.debug('Directory deleted', { path: dirPath });
    }

    /**
     * Handle watcher error
     */
    private handleWatcherError(error: Error): void {
        this.logger.error('File watcher error', { error: error.message, stack: error.stack });
        this.emitEvent('error', '', { error: error.message });
        this.emitVSCodeEvent('error', '', { error: error.message });

        // Attempt to recover from certain types of errors
        this.attemptRecovery(error);
    }

    /**
     * Handle watcher ready event
     */
    private handleWatcherReady(): void {
        this.logger.debug('File watcher ready');
    }

    /**
     * Attempt to recover from watcher errors
     */
    private attemptRecovery(error: Error): void {
        const errorMessage = error.message.toLowerCase();

        // Handle common error scenarios
        if (errorMessage.includes('enospc') || errorMessage.includes('watch limit')) {
            this.logger.warn('File system watch limit reached, switching to polling mode');
            this.config.usePolling = true;
        } else if (errorMessage.includes('permission') || errorMessage.includes('eacces')) {
            this.logger.error('Permission denied, file watcher may not work properly');
        } else {
            this.logger.warn('Unknown file watcher error, continuing with current configuration');
        }
    }

    /**
     * Check if a file is a markdown file
     */
    private isMarkdownFile(filePath: string): boolean {
        const ext = path.extname(filePath).toLowerCase();
        return ['.md', '.markdown'].includes(ext);
    }

    /**
     * Emit an event to internal listeners
     */
    private emitEvent(eventType: FileWatcherEventType, filePath: string, details?: any): void {
        this.eventEmitter.emit(eventType, filePath, details);
    }

    /**
     * Emit a VS Code event
     */
    private emitVSCodeEvent(type: FileWatcherEvent['type'], filePath: string, details?: any): void {
        const event: FileWatcherEvent = {
            type,
            filePath,
            timestamp: new Date(),
            details
        };

        this.vscodeEventEmitter.fire(event);
        this.logger.debug('File watcher event emitted', event);
    }

    /**
     * Clear all debounced events
     */
    private clearDebouncedEvents(): void {
        for (const timeout of this.debouncedEvents.values()) {
            clearTimeout(timeout);
        }
        this.debouncedEvents.clear();
    }
}
