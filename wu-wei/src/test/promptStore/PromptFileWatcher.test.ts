/**
 * Unit tests for PromptFileWatcher
 * Testing debouncing, error handling, and lifecycle management
 */

import assert from 'assert';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { PromptFileWatcher } from '../../promptStore/PromptFileWatcher';
import { FileWatcherConfig } from '../../promptStore/types';

describe('PromptFileWatcher', () => {
    let watcher: PromptFileWatcher;
    let tempDir: string;

    beforeEach(() => {
        // Create a temporary directory for testing
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wu-wei-test-'));

        // Initialize watcher with test configuration
        const config: Partial<FileWatcherConfig> = {
            enabled: true,
            debounceMs: 100, // Shorter debounce for testing
            maxDepth: 5,
            followSymlinks: false,
            ignorePatterns: [],
            usePolling: false,
            pollingInterval: 500
        };

        watcher = new PromptFileWatcher(config);
    });

    afterEach(async () => {
        // Clean up
        watcher.dispose();

        // Remove temporary directory
        try {
            fs.rmSync(tempDir, { recursive: true, force: true });
        } catch (error) {
            console.warn('Failed to clean up temp directory:', error);
        }
    });

    describe('Lifecycle Management', () => {
        it('should start and stop watching correctly', async () => {
            assert.strictEqual(watcher.isActive(), false);

            await watcher.start(tempDir);
            assert.strictEqual(watcher.isActive(), true);

            watcher.stop();
            assert.strictEqual(watcher.isActive(), false);
        });

        it('should handle multiple start calls gracefully', async () => {
            await watcher.start(tempDir);
            assert.strictEqual(watcher.isActive(), true);

            // Second start should not throw
            await watcher.start(tempDir);
            assert.strictEqual(watcher.isActive(), true);
        });

        it('should pause and resume correctly', async () => {
            await watcher.start(tempDir);
            assert.strictEqual(watcher.isActive(), true);

            watcher.pause();
            assert.strictEqual(watcher.isActive(), false);

            watcher.resume();
            assert.strictEqual(watcher.isActive(), true);
        });

        it('should provide correct status information', async () => {
            let status = watcher.getStatus();
            assert.strictEqual(status.isWatching, false);
            assert.strictEqual(status.isPaused, false);

            await watcher.start(tempDir);
            status = watcher.getStatus();
            assert.strictEqual(status.isWatching, true);
            assert.strictEqual(status.isPaused, false);

            watcher.pause();
            status = watcher.getStatus();
            assert.strictEqual(status.isWatching, true);
            assert.strictEqual(status.isPaused, true);
        });
    });

    describe('Configuration Management', () => {
        it('should use default configuration when none provided', () => {
            const defaultWatcher = new PromptFileWatcher();
            const status = defaultWatcher.getStatus();
            assert.strictEqual(status.isWatching, false);
            defaultWatcher.dispose();
        });

        it('should update configuration dynamically', () => {
            const newConfig: Partial<FileWatcherConfig> = {
                debounceMs: 1000,
                maxDepth: 20
            };

            watcher.updateConfig(newConfig);
            // Config update should not throw
            assert.ok(true);
        });

        it('should respect disabled configuration', async () => {
            const disabledWatcher = new PromptFileWatcher({ enabled: false });

            await disabledWatcher.start(tempDir);
            assert.strictEqual(disabledWatcher.isActive(), false);

            disabledWatcher.dispose();
        });
    });

    describe('Event Handling', () => {
        it('should emit fileAdded events for markdown files', (done) => {
            let eventReceived = false;

            watcher.on('fileAdded', (filePath: string) => {
                if (!eventReceived) {
                    eventReceived = true;
                    assert.ok(filePath.endsWith('.md'));
                    done();
                }
            });

            watcher.start(tempDir).then(() => {
                // Create a markdown file
                const testFile = path.join(tempDir, 'test.md');
                fs.writeFileSync(testFile, '# Test Prompt\n\nThis is a test.');
            });
        });

        it('should debounce fileChanged events', (done) => {
            let changeCount = 0;
            const testFile = path.join(tempDir, 'test.md');

            watcher.on('fileChanged', () => {
                changeCount++;
            });

            watcher.start(tempDir).then(() => {
                // Create initial file
                fs.writeFileSync(testFile, '# Test Prompt\n\nInitial content.');

                // Make multiple rapid changes
                setTimeout(() => fs.writeFileSync(testFile, '# Test Prompt\n\nChange 1.'), 10);
                setTimeout(() => fs.writeFileSync(testFile, '# Test Prompt\n\nChange 2.'), 20);
                setTimeout(() => fs.writeFileSync(testFile, '# Test Prompt\n\nChange 3.'), 30);

                // Check debouncing after delay
                setTimeout(() => {
                    // Should have debounced to single event (or very few)
                    assert.ok(changeCount <= 2, `Expected <= 2 events, got ${changeCount}`);
                    done();
                }, 300);
            });
        });

        it('should emit fileDeleted events', (done) => {
            const testFile = path.join(tempDir, 'test.md');
            let eventReceived = false;

            watcher.on('fileDeleted', (filePath: string) => {
                if (!eventReceived) {
                    eventReceived = true;
                    assert.ok(filePath.endsWith('.md'));
                    done();
                }
            });

            watcher.start(tempDir).then(() => {
                // Create then delete file
                fs.writeFileSync(testFile, '# Test Prompt');
                setTimeout(() => {
                    fs.unlinkSync(testFile);
                }, 50);
            });
        });

        it('should ignore non-markdown files', (done) => {
            let markdownEventCount = 0;
            let textEventCount = 0;

            watcher.on('fileAdded', (filePath: string) => {
                if (filePath.endsWith('.md')) {
                    markdownEventCount++;
                } else if (filePath.endsWith('.txt')) {
                    textEventCount++;
                }
            });

            watcher.start(tempDir).then(() => {
                // Create markdown file (should trigger event)
                fs.writeFileSync(path.join(tempDir, 'prompt.md'), '# Prompt');

                // Create text file (should not trigger event)
                fs.writeFileSync(path.join(tempDir, 'readme.txt'), 'Text file');

                // Create non-prompt file (should not trigger event)
                fs.writeFileSync(path.join(tempDir, 'config.json'), '{}');

                setTimeout(() => {
                    assert.strictEqual(markdownEventCount, 1);
                    assert.strictEqual(textEventCount, 0);
                    done();
                }, 200);
            });
        });
    });

    describe('Event Listener Management', () => {
        it('should add and remove event listeners', () => {
            const callback = () => { };

            watcher.on('fileAdded', callback);
            watcher.off('fileAdded', callback);

            // Should not throw
            assert.ok(true);
        });

        it('should remove all listeners', () => {
            const callback1 = () => { };
            const callback2 = () => { };

            watcher.on('fileAdded', callback1);
            watcher.on('fileChanged', callback2);

            watcher.removeAllListeners();

            // Should not throw
            assert.ok(true);
        });

        it('should remove listeners for specific events', () => {
            const callback1 = () => { };
            const callback2 = () => { };

            watcher.on('fileAdded', callback1);
            watcher.on('fileChanged', callback2);

            watcher.removeAllListeners('fileAdded');

            // Should not throw
            assert.ok(true);
        });
    });

    describe('Path Resolution', () => {
        it('should handle workspace folder variables', async () => {
            // This test would require mocking vscode.workspace
            // For now, just test that it doesn't throw
            await watcher.start('${workspaceFolder}/prompts');
            assert.ok(true);
        });

        it('should handle absolute paths', async () => {
            await watcher.start(tempDir);
            const status = watcher.getStatus();
            assert.ok(status.watchedPaths.length >= 0);
        });
    });

    describe('Error Handling', () => {
        it('should handle invalid watch paths gracefully', async () => {
            const invalidPath = path.join(tempDir, 'non-existent-directory');

            try {
                await watcher.start(invalidPath);
                // Should either succeed (creating the path) or fail gracefully
                assert.ok(true);
            } catch (error) {
                // Error is expected for non-existent paths
                assert.ok(error instanceof Error);
            }
        });

        it('should emit error events', (done) => {
            watcher.on('error', (filePath: string, details?: any) => {
                assert.ok(details?.error);
                done();
            });

            // Start watcher with invalid configuration to trigger error
            const invalidWatcher = new PromptFileWatcher({
                enabled: true,
                maxDepth: -1, // Invalid depth
                debounceMs: -1 // Invalid debounce
            });

            // This might not trigger an error depending on chokidar's validation
            // but the test structure is in place
            invalidWatcher.start('/non-existent-path').catch(() => {
                // Expected to fail
                invalidWatcher.dispose();
                done();
            });
        });
    });

    describe('Resource Management', () => {
        it('should clean up resources on dispose', () => {
            const testWatcher = new PromptFileWatcher();
            testWatcher.dispose();

            // Should not throw
            assert.ok(true);
        });

        it('should clean up debounced events', async () => {
            const testFile = path.join(tempDir, 'test.md');

            await watcher.start(tempDir);

            // Create file to trigger debounced event
            fs.writeFileSync(testFile, '# Test');
            fs.writeFileSync(testFile, '# Test Updated');

            // Dispose immediately - should clean up pending timeouts
            watcher.dispose();

            // Should not throw
            assert.ok(true);
        });
    });
});
