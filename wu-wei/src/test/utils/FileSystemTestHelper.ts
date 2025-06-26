/**
 * Test utility for file system operations
 * Provides helper methods for creating, modifying, and managing test files
 */

import * as fs from 'fs';
import * as path from 'path';

export class FileSystemTestHelper {
    private testDir: string;
    private eventCount: number = 0;
    private expectedEvents: number = 0;
    private eventWaiters: Array<{ resolve: () => void; timeout: NodeJS.Timeout }> = [];

    constructor(testDirectory: string) {
        this.testDir = testDirectory;
    }

    /**
     * Create a test file with the specified content
     */
    async createTestFile(relativePath: string, content: string): Promise<void> {
        const fullPath = path.join(this.testDir, relativePath);
        const dir = path.dirname(fullPath);

        // Ensure directory exists
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }

        fs.writeFileSync(fullPath, content, 'utf8');

        // Small delay to ensure file system operation completes
        await this.delay(10);
    }

    /**
     * Modify an existing test file
     */
    async modifyTestFile(relativePath: string, content: string): Promise<void> {
        const fullPath = path.join(this.testDir, relativePath);

        if (!fs.existsSync(fullPath)) {
            throw new Error(`File does not exist: ${fullPath}`);
        }

        fs.writeFileSync(fullPath, content, 'utf8');

        // Small delay to ensure file system operation completes
        await this.delay(10);
    }

    /**
     * Delete a test file
     */
    async deleteTestFile(relativePath: string): Promise<void> {
        const fullPath = path.join(this.testDir, relativePath);

        if (fs.existsSync(fullPath)) {
            fs.unlinkSync(fullPath);
        }

        // Small delay to ensure file system operation completes
        await this.delay(10);
    }

    /**
     * Create a test directory
     */
    async createTestDirectory(relativePath: string): Promise<void> {
        const fullPath = path.join(this.testDir, relativePath);

        if (!fs.existsSync(fullPath)) {
            fs.mkdirSync(fullPath, { recursive: true });
        }

        // Small delay to ensure file system operation completes
        await this.delay(10);
    }

    /**
     * Delete a test directory
     */
    async deleteTestDirectory(relativePath: string): Promise<void> {
        const fullPath = path.join(this.testDir, relativePath);

        if (fs.existsSync(fullPath)) {
            fs.rmSync(fullPath, { recursive: true, force: true });
        }

        // Small delay to ensure file system operation completes
        await this.delay(10);
    }

    /**
     * Wait for a specified number of events within a timeout
     */
    async waitForEvents(expectedCount: number, timeoutMs: number = 1000): Promise<void> {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                // Remove this waiter
                this.eventWaiters = this.eventWaiters.filter(w => w.timeout !== timeout);
                resolve(); // Don't reject, just resolve to allow tests to continue
            }, timeoutMs);

            const waiter = {
                resolve: () => {
                    clearTimeout(timeout);
                    this.eventWaiters = this.eventWaiters.filter(w => w !== waiter);
                    resolve();
                },
                timeout
            };

            this.eventWaiters.push(waiter);
            this.expectedEvents = expectedCount;
            this.checkEventCompletion();
        });
    }

    /**
     * Notify that an event occurred (to be called by tests)
     */
    notifyEvent(): void {
        this.eventCount++;
        this.checkEventCompletion();
    }

    /**
     * Reset event counter
     */
    resetEventCounter(): void {
        this.eventCount = 0;
        this.expectedEvents = 0;
    }

    /**
     * Get the absolute path for a relative path
     */
    getAbsolutePath(relativePath: string): string {
        return path.join(this.testDir, relativePath);
    }

    /**
     * Check if a file exists
     */
    fileExists(relativePath: string): boolean {
        return fs.existsSync(this.getAbsolutePath(relativePath));
    }

    /**
     * Read file content
     */
    readFile(relativePath: string): string {
        return fs.readFileSync(this.getAbsolutePath(relativePath), 'utf8');
    }

    /**
     * List files in a directory
     */
    listFiles(relativePath: string = ''): string[] {
        const fullPath = path.join(this.testDir, relativePath);

        if (!fs.existsSync(fullPath)) {
            return [];
        }

        return fs.readdirSync(fullPath);
    }

    /**
     * Create multiple test files at once
     */
    async createMultipleFiles(files: Array<{ path: string; content: string }>): Promise<void> {
        const promises = files.map(file => this.createTestFile(file.path, file.content));
        await Promise.all(promises);
    }

    /**
     * Clean up all test files and directories
     */
    async cleanup(): Promise<void> {
        try {
            // Clear any pending waiters
            for (const waiter of this.eventWaiters) {
                clearTimeout(waiter.timeout);
                waiter.resolve();
            }
            this.eventWaiters = [];

            // Remove test directory
            if (fs.existsSync(this.testDir)) {
                fs.rmSync(this.testDir, { recursive: true, force: true });
            }
        } catch (error) {
            console.warn('Failed to cleanup test directory:', error);
        }
    }

    /**
     * Create a nested directory structure for testing
     */
    async createDirectoryStructure(structure: Record<string, string | Record<string, any>>): Promise<void> {
        for (const [name, content] of Object.entries(structure)) {
            if (typeof content === 'string') {
                // It's a file
                await this.createTestFile(name, content);
            } else {
                // It's a directory
                await this.createTestDirectory(name);

                // Recursively create nested structure
                const nestedHelper = new FileSystemTestHelper(this.getAbsolutePath(name));
                await nestedHelper.createDirectoryStructure(content);
            }
        }
    }

    /**
     * Simulate rapid file changes for testing debouncing
     */
    async simulateRapidChanges(relativePath: string, changeCount: number, intervalMs: number = 50): Promise<void> {
        // Create initial file
        await this.createTestFile(relativePath, '# Initial content');

        // Make rapid changes
        for (let i = 0; i < changeCount; i++) {
            await this.modifyTestFile(relativePath, `# Content ${i}\n\nUpdate number ${i}`);
            await this.delay(intervalMs);
        }
    }

    /**
     * Wait for file system to settle (useful after rapid operations)
     */
    async waitForFileSystemToSettle(delayMs: number = 100): Promise<void> {
        await this.delay(delayMs);
    }

    /**
     * Simple delay utility
     */
    private async delay(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Check if expected events have been reached
     */
    private checkEventCompletion(): void {
        if (this.eventCount >= this.expectedEvents && this.eventWaiters.length > 0) {
            const waiter = this.eventWaiters[0];
            waiter.resolve();
        }
    }
}
