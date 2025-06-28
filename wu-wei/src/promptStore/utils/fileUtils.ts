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
            // Special handling for patterns like **/something/**
            if (normalizedPattern.startsWith('**/') && normalizedPattern.endsWith('/**')) {
                const middle = normalizedPattern.slice(3, -3);
                const regexPattern = `(.*/)?(${middle.replace(/\*/g, '[^/]*')})(/.*)`;
                const regex = new RegExp(`^${regexPattern}$`, 'i');
                return regex.test(normalizedStr);
            }
            // Handle patterns like **/something
            else if (normalizedPattern.startsWith('**/')) {
                const suffix = normalizedPattern.slice(3);
                const regexPattern = `(.*/)?(${suffix.replace(/\*/g, '[^/]*')})$`;
                const regex = new RegExp(`^${regexPattern}$`, 'i');
                return regex.test(normalizedStr);
            }
            // Handle patterns like something/**
            else if (normalizedPattern.endsWith('/**')) {
                const prefix = normalizedPattern.slice(0, -3);
                const regexPattern = `^(${prefix.replace(/\*/g, '[^/]*')})(/.*)`;
                const regex = new RegExp(`^${regexPattern}$`, 'i');
                return regex.test(normalizedStr);
            }
            // Handle patterns like src/**/*.tsx
            else {
                // Replace ** with a pattern that matches any number of path segments including none
                let regexPattern = normalizedPattern
                    .replace(/\*\*/g, '.*')
                    .replace(/(?<!\.\*)\*(?!\*)/g, '[^/]*')
                    .replace(/\?/g, '.');

                const regex = new RegExp(`^${regexPattern}$`, 'i');
                return regex.test(normalizedStr);
            }
        }

        // Convert simple glob pattern to regex
        const regexPattern = normalizedPattern
            .replace(/\*/g, '[^/]*')
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
            // Direct pattern match
            if (this.matchesPattern(normalizedPath, pattern)) {
                return true;
            }

            // For patterns with **, check if any part of the path matches
            if (pattern.includes('**')) {
                // Handle patterns like **/node_modules/**
                if (pattern.startsWith('**/') && pattern.endsWith('/**')) {
                    const dirName = pattern.slice(3, -3);
                    const pathParts = normalizedPath.split('/');

                    // Check if any directory in the path matches
                    for (const part of pathParts) {
                        if (this.matchesPattern(part, dirName)) {
                            return true;
                        }
                    }
                }
                // Handle patterns like **/something
                else if (pattern.startsWith('**/')) {
                    const suffix = pattern.slice(3);
                    const pathParts = normalizedPath.split('/');

                    // Check if the file or any parent path ends with the suffix
                    for (let i = 0; i < pathParts.length; i++) {
                        const subPath = pathParts.slice(i).join('/');
                        if (this.matchesPattern(subPath, suffix)) {
                            return true;
                        }
                    }
                }
                // Handle patterns like something/**
                else if (pattern.endsWith('/**')) {
                    const prefix = pattern.slice(0, -3);
                    const pathParts = normalizedPath.split('/');

                    // Check if any parent path matches the prefix
                    for (let i = 0; i < pathParts.length; i++) {
                        const subPath = pathParts.slice(0, i + 1).join('/');
                        if (this.matchesPattern(subPath, prefix)) {
                            return true;
                        }
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
        // Handle empty or whitespace-only titles
        if (!title || !title.trim()) {
            return extension;
        }

        // Remove or replace invalid characters
        let safe = title
            .trim()                        // Remove leading/trailing whitespace
            .replace(/[<>:"/\\|?*]/g, '')  // Remove invalid filename characters
            .replace(/\s+/g, '-')          // Replace spaces with hyphens
            .replace(/[^\w\-_.]/g, '')     // Keep only word chars, hyphens, underscores, and dots
            .replace(/^[-_]+|[-_]+$/g, '') // Remove leading/trailing hyphens and underscores
            .replace(/[-_]+/g, '-')        // Collapse multiple hyphens and underscores to single hyphen
            .toLowerCase();

        // Handle edge case where all characters were removed
        if (!safe) {
            return extension;
        }

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
