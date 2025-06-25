/**
 * File Watcher for monitoring prompt files
 * Following wu wei principles: gentle observation that flows with file system changes
 */

import * as chokidar from 'chokidar';
import * as vscode from 'vscode';
import * as path from 'path';
import { FileWatcherEvent } from './types';
import { WATCHER_CONFIG, FILE_PATTERNS } from './constants';
import { WuWeiLogger } from '../logger';

export class PromptFileWatcher {
    private logger: WuWeiLogger;
    private watcher: chokidar.FSWatcher | null = null;
    private eventEmitter: vscode.EventEmitter<FileWatcherEvent>;
    private isWatching: boolean = false;

    // Public event for external listeners
    public readonly onFileChanged: vscode.Event<FileWatcherEvent>;

    constructor() {
        this.logger = WuWeiLogger.getInstance();
        this.eventEmitter = new vscode.EventEmitter<FileWatcherEvent>();
        this.onFileChanged = this.eventEmitter.event;
    }

    /**
     * Start watching the specified paths
     */
    public async startWatching(watchPaths: string[]): Promise<void> {
        if (this.isWatching) {
            this.logger.warn('File watcher is already running');
            return;
        }

        try {
            const resolvedPaths = this.resolveWatchPaths(watchPaths);

            this.watcher = chokidar.watch(resolvedPaths, {
                ignored: WATCHER_CONFIG.IGNORED,
                persistent: true,
                ignoreInitial: false,
                followSymlinks: true,
                cwd: vscode.workspace.rootPath,
                usePolling: WATCHER_CONFIG.USE_POLLING,
                interval: WATCHER_CONFIG.POLL_INTERVAL,
                atomic: WATCHER_CONFIG.ATOMIC_WRITES
            });

            this.setupEventHandlers();
            this.isWatching = true;

            this.logger.info('File watcher started', { paths: resolvedPaths });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to start file watcher', { error: errorMessage });
            throw error;
        }
    }

    /**
     * Stop watching files
     */
    public async stopWatching(): Promise<void> {
        if (!this.isWatching || !this.watcher) {
            return;
        }

        try {
            await this.watcher.close();
            this.watcher = null;
            this.isWatching = false;
            this.logger.info('File watcher stopped');
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to stop file watcher', { error: errorMessage });
        }
    }

    /**
     * Check if currently watching
     */
    public get watching(): boolean {
        return this.isWatching;
    }

    /**
     * Get watched paths
     */
    public getWatchedPaths(): string[] {
        if (!this.watcher) {
            return [];
        }
        return this.watcher.getWatched() ? Object.keys(this.watcher.getWatched()) : [];
    }

    /**
     * Dispose of resources
     */
    public dispose(): void {
        this.stopWatching();
        this.eventEmitter.dispose();
    }

    /**
     * Resolve workspace-relative paths to absolute paths
     */
    private resolveWatchPaths(watchPaths: string[]): string[] {
        const workspaceRoot = vscode.workspace.rootPath;
        if (!workspaceRoot) {
            this.logger.warn('No workspace root found, using provided paths as-is');
            return watchPaths;
        }

        return watchPaths.map(watchPath => {
            // Replace ${workspaceFolder} variable
            const resolved = watchPath.replace('${workspaceFolder}', workspaceRoot);
            return path.isAbsolute(resolved) ? resolved : path.join(workspaceRoot, resolved);
        });
    }

    /**
     * Setup event handlers for the file watcher
     */
    private setupEventHandlers(): void {
        if (!this.watcher) {
            return;
        }

        this.watcher.on('add', (filePath: string) => {
            if (this.isPromptFile(filePath)) {
                this.emitEvent('add', filePath);
            }
        });

        this.watcher.on('change', (filePath: string) => {
            if (this.isPromptFile(filePath)) {
                this.emitEvent('change', filePath);
            }
        });

        this.watcher.on('unlink', (filePath: string) => {
            if (this.isPromptFile(filePath)) {
                this.emitEvent('unlink', filePath);
            }
        });

        this.watcher.on('error', (error: Error) => {
            this.logger.error('File watcher error', error);
            this.emitEvent('error', '', { error: error.message });
        });

        this.watcher.on('ready', () => {
            this.logger.debug('File watcher ready');
        });
    }

    /**
     * Check if a file is a prompt file based on extension
     */
    private isPromptFile(filePath: string): boolean {
        const ext = path.extname(filePath).toLowerCase();
        return ['.md', '.markdown', '.txt'].includes(ext);
    }

    /**
     * Emit a file watcher event
     */
    private emitEvent(type: FileWatcherEvent['type'], filePath: string, details?: any): void {
        const event: FileWatcherEvent = {
            type,
            filePath,
            timestamp: new Date(),
            details
        };

        this.eventEmitter.fire(event);
        this.logger.debug('File watcher event', event);
    }
}
