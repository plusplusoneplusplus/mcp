/**
 * File system utilities for the Prompt Store
 * Following wu wei principles: simple, efficient file operations
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { WuWeiLogger } from '../../logger';

export interface FileStats {
    size: number;
    mtime: Date;
    birthtime: Date;
    isDirectory: boolean;
    isFile: boolean;
    permissions: string;
}

export interface ScanOptions {
    includePatterns?: string[];
    excludePatterns?: string[];
    maxDepth?: number;
    followSymlinks?: boolean;
}

export class FileUtils {
    private static logger = WuWeiLogger.getInstance();

    /**
     * Check if a file name is a markdown file
     */
    static isMarkdownFile(fileName: string): boolean {
        const ext = path.extname(fileName).toLowerCase();
        return ['.md', '.markdown'].includes(ext);
    }

    /**
     * Check if a file/directory should be ignored
     */
    static shouldIgnore(fileName: string, excludePatterns: string[] = []): boolean {
        // Ignore hidden files and directories
        if (fileName.startsWith('.')) {
            return true;
        }

        // Check exclude patterns
        for (const pattern of excludePatterns) {
            if (this.matchesPattern(fileName, pattern)) {
                return true;
            }
        }

        return false;
    }

    /**
     * Simple pattern matching (supports * wildcard and ** for recursive)
     */
    static matchesPattern(str: string, pattern: string): boolean {
        // Normalize path separators for cross-platform compatibility
        const normalizedStr = str.replace(/\\/g, '/');
        const normalizedPattern = pattern.replace(/\\/g, '/');

        // Handle ** pattern for recursive matching
        if (normalizedPattern.includes('**')) {
            const regexPattern = normalizedPattern
                .replace(/\*\*/g, '.*')
                .replace(/(?<!\.\*)\*(?!\*)/g, '[^/]*');
            const regex = new RegExp(`^${regexPattern}$`, 'i');
            return regex.test(normalizedStr);
        }

        // Convert simple glob pattern to regex
        const regexPattern = normalizedPattern
            .replace(/\*/g, '.*')
            .replace(/\?/g, '.');

        const regex = new RegExp(`^${regexPattern}$`, 'i');
        return regex.test(normalizedStr);
    }

    /**
 * Check if a path should be excluded based on patterns
 */
    static shouldExcludePath(filePath: string, excludePatterns: string[] = []): boolean {
        // Normalize path separators
        const normalizedPath = filePath.replace(/\\/g, '/');

        for (const pattern of excludePatterns) {
            // Check exact match
            if (this.matchesPattern(normalizedPath, pattern)) {
                return true;
            }

            // For patterns with **, check if any part of the path matches
            if (pattern.includes('**')) {
                // Extract the core directory name from patterns like **/node_modules/**
                const dirPattern = pattern.replace(/^\*\*\//, '').replace(/\/\*\*$/, '');

                // Check if any path segment matches the directory pattern
                const pathParts = normalizedPath.split('/');
                for (const part of pathParts) {
                    if (this.matchesPattern(part, dirPattern)) {
                        return true;
                    }
                }

                // Also check if the path contains the pattern as a substring
                const segments = normalizedPath.split('/');
                for (let i = 0; i < segments.length; i++) {
                    for (let j = i; j < segments.length; j++) {
                        const subPath = segments.slice(i, j + 1).join('/');
                        if (this.matchesPattern(subPath, dirPattern)) {
                            return true;
                        }
                    }
                }
            } else {
                // Check if any parent directory matches the pattern
                const pathParts = normalizedPath.split('/');
                for (let i = 0; i < pathParts.length; i++) {
                    const partialPath = pathParts.slice(0, i + 1).join('/');
                    if (this.matchesPattern(partialPath, pattern)) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    /**
     * Get detailed file statistics
     */
    static async getFileStats(filePath: string): Promise<FileStats | null> {
        try {
            const stats = await fs.stat(filePath);
            return {
                size: stats.size,
                mtime: stats.mtime,
                birthtime: stats.birthtime,
                isDirectory: stats.isDirectory(),
                isFile: stats.isFile(),
                permissions: stats.mode.toString(8)
            };
        } catch (error) {
            this.logger.debug(`Failed to get stats for ${filePath}:`, error);
            return null;
        }
    }

    /**
     * Ensure directory exists, creating it if necessary
     */
    static async ensureDirectory(dirPath: string): Promise<void> {
        try {
            await fs.access(dirPath);
        } catch {
            // Directory doesn't exist, create it
            await fs.mkdir(dirPath, { recursive: true });
            this.logger.debug(`Created directory: ${dirPath}`);
        }
    }

    /**
     * Atomic file write operation
     */
    static async writeFileAtomic(filePath: string, content: string): Promise<void> {
        const tempPath = `${filePath}.tmp.${Date.now()}.${Math.random().toString(36).substr(2, 9)}`;

        try {
            // Ensure parent directory exists
            await this.ensureDirectory(path.dirname(filePath));

            // Write to temporary file
            await fs.writeFile(tempPath, content, 'utf8');

            // Atomic rename
            await fs.rename(tempPath, filePath);

            this.logger.debug(`Successfully wrote file: ${filePath}`);
        } catch (error) {
            // Clean up temp file on error
            try {
                await fs.unlink(tempPath);
            } catch (cleanupError) {
                this.logger.debug(`Failed to cleanup temp file ${tempPath}:`, cleanupError);
            }
            throw error;
        }
    }

    /**
     * Read file with proper error handling
     */
    static async readFileContent(filePath: string): Promise<string> {
        try {
            return await fs.readFile(filePath, 'utf8');
        } catch (error) {
            this.logger.error(`Failed to read file ${filePath}:`, error);
            throw error;
        }
    }

    /**
     * Check if path exists and is accessible
     */
    static async pathExists(filePath: string): Promise<boolean> {
        try {
            await fs.access(filePath);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Generate a safe filename from a title
     */
    static generateSafeFileName(title: string, extension: string = '.md'): string {
        // Remove or replace invalid characters
        const safe = title
            .replace(/[<>:"/\\|?*]/g, '')  // Remove invalid filename characters
            .replace(/\s+/g, '-')          // Replace spaces with hyphens
            .replace(/[^\w\-_.]/g, '')     // Keep only word chars, hyphens, underscores, and dots
            .toLowerCase();

        return `${safe}${extension}`;
    }

    /**
     * Get relative path from workspace root
     */
    static getRelativePath(filePath: string, basePath?: string): string {
        if (!basePath) {
            // Try to use VS Code workspace root
            const vscode = require('vscode');
            basePath = vscode.workspace.rootPath;
        }

        if (basePath && filePath.startsWith(basePath)) {
            return path.relative(basePath, filePath);
        }

        return filePath;
    }

    /**
     * Validate that a file path is safe (within allowed directories)
     */
    static isPathSafe(filePath: string, allowedPaths: string[]): boolean {
        const normalizedPath = path.normalize(filePath);

        // Check for path traversal attempts
        if (normalizedPath.includes('..')) {
            return false;
        }

        // Check if path is within allowed directories
        return allowedPaths.some(allowedPath => {
            const normalizedAllowed = path.normalize(allowedPath);
            return normalizedPath.startsWith(normalizedAllowed);
        });
    }

    /**
     * Create a backup of a file before modification
     */
    static async createBackup(filePath: string): Promise<string> {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const backupPath = `${filePath}.backup.${timestamp}`;

        try {
            await fs.copyFile(filePath, backupPath);
            this.logger.debug(`Created backup: ${backupPath}`);
            return backupPath;
        } catch (error) {
            this.logger.error(`Failed to create backup of ${filePath}:`, error);
            throw error;
        }
    }
}
