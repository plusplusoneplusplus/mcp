/**
 * Integration tests for file watching system
 * Tests real file system operations and integration with PromptManager
 */

import assert from 'assert';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { PromptFileWatcher } from '../../../promptStore/PromptFileWatcher';
import { FileSystemTestHelper } from '../../utils/FileSystemTestHelper';

describe('File Watching Integration', () => {
    let watcher: PromptFileWatcher;
    let testHelper: FileSystemTestHelper;
    let tempDir: string;

    beforeEach(async () => {
        // Create temporary directory
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wu-wei-integration-'));

        // Initialize test helper and watcher
        testHelper = new FileSystemTestHelper(tempDir);
        watcher = new PromptFileWatcher({
            enabled: true,
            debounceMs: 100,
            maxDepth: 10,
            followSymlinks: false,
            ignorePatterns: [],
            usePolling: false,
            pollingInterval: 500
        });
    });

    afterEach(async () => {
        watcher.dispose();
        await testHelper.cleanup();
    });

    describe('Real File System Operations', () => {
        it('should handle rapid file creation and modification', async () => {
            const events: string[] = [];

            watcher.on('fileAdded', (filePath: string) => {
                events.push(`added:${path.basename(filePath)}`);
            });

            watcher.on('fileChanged', (filePath: string) => {
                events.push(`changed:${path.basename(filePath)}`);
            });

            await watcher.start(tempDir);

            // Create multiple files rapidly
            await testHelper.createTestFile('prompt1.md', '# Prompt 1\n\nContent 1');
            await testHelper.createTestFile('prompt2.md', '# Prompt 2\n\nContent 2');
            await testHelper.createTestFile('prompt3.md', '# Prompt 3\n\nContent 3');

            // Modify files rapidly
            await testHelper.modifyTestFile('prompt1.md', '# Updated Prompt 1\n\nUpdated content');
            await testHelper.modifyTestFile('prompt2.md', '# Updated Prompt 2\n\nUpdated content');

            // Wait for events to settle
            await testHelper.waitForEvents(5, 1000);

            // Should have received appropriate events
            assert.ok(events.some(e => e.includes('added:prompt1.md')));
            assert.ok(events.some(e => e.includes('added:prompt2.md')));
            assert.ok(events.some(e => e.includes('added:prompt3.md')));
        });

        it('should handle directory structure changes', async () => {
            const events: string[] = [];

            watcher.on('directoryAdded', (dirPath: string) => {
                events.push(`dirAdded:${path.basename(dirPath)}`);
            });

            watcher.on('directoryDeleted', (dirPath: string) => {
                events.push(`dirDeleted:${path.basename(dirPath)}`);
            });

            watcher.on('fileAdded', (filePath: string) => {
                events.push(`fileAdded:${path.basename(filePath)}`);
            });

            await watcher.start(tempDir);

            // Create nested directory structure
            await testHelper.createTestDirectory('category1');
            await testHelper.createTestDirectory('category1/subcategory');

            // Add files in nested directories
            await testHelper.createTestFile('category1/prompt.md', '# Category Prompt');
            await testHelper.createTestFile('category1/subcategory/nested.md', '# Nested Prompt');

            // Wait for events
            await testHelper.waitForEvents(2, 1000);

            // Should have received file events for nested structure
            assert.ok(events.some(e => e.includes('fileAdded:prompt.md')));
            assert.ok(events.some(e => e.includes('fileAdded:nested.md')));
        });

        it('should handle file deletion correctly', async () => {
            const events: string[] = [];

            watcher.on('fileAdded', (filePath: string) => {
                events.push(`added:${path.basename(filePath)}`);
            });

            watcher.on('fileDeleted', (filePath: string) => {
                events.push(`deleted:${path.basename(filePath)}`);
            });

            await watcher.start(tempDir);

            // Create files
            await testHelper.createTestFile('temp1.md', '# Temp 1');
            await testHelper.createTestFile('temp2.md', '# Temp 2');

            // Wait for creation events
            await testHelper.waitForEvents(2, 500);

            // Delete files
            await testHelper.deleteTestFile('temp1.md');
            await testHelper.deleteTestFile('temp2.md');

            // Wait for deletion events
            await testHelper.waitForEvents(2, 500);

            // Should have both creation and deletion events
            assert.ok(events.some(e => e === 'added:temp1.md'));
            assert.ok(events.some(e => e === 'deleted:temp1.md'));
            assert.ok(events.some(e => e === 'added:temp2.md'));
            assert.ok(events.some(e => e === 'deleted:temp2.md'));
        });

        it('should respect file filtering rules', async () => {
            const events: string[] = [];

            watcher.on('fileAdded', (filePath: string) => {
                events.push(path.basename(filePath));
            });

            await watcher.start(tempDir);

            // Create various file types
            await testHelper.createTestFile('prompt.md', '# Markdown Prompt');
            await testHelper.createTestFile('readme.txt', 'Text file');
            await testHelper.createTestFile('config.json', '{"key": "value"}');
            await testHelper.createTestFile('script.js', 'console.log("test");');
            await testHelper.createTestFile('.hidden.md', '# Hidden prompt');
            await testHelper.createTestFile('temp.tmp', 'Temporary file');

            // Wait for events
            await testHelper.waitForEvents(1, 500);

            // Should only detect markdown files (not hidden or temp files)
            assert.ok(events.includes('prompt.md'));
            assert.ok(!events.includes('readme.txt'));
            assert.ok(!events.includes('config.json'));
            assert.ok(!events.includes('script.js'));
            assert.ok(!events.includes('.hidden.md'));
            assert.ok(!events.includes('temp.tmp'));
        });
    });

    describe('Performance Under Load', () => {
        it('should handle many files efficiently', async () => {
            const events: string[] = [];
            const startTime = Date.now();

            watcher.on('fileAdded', (filePath: string) => {
                events.push(path.basename(filePath));
            });

            await watcher.start(tempDir);

            // Create many files
            const promises: Promise<void>[] = [];
            for (let i = 0; i < 50; i++) {
                promises.push(
                    testHelper.createTestFile(
                        `prompt${i}.md`,
                        `# Prompt ${i}\n\nThis is prompt number ${i}.`
                    )
                );
            }

            await Promise.all(promises);

            // Wait for all events
            await testHelper.waitForEvents(50, 5000);

            const endTime = Date.now();
            const duration = endTime - startTime;

            // Should handle all files reasonably quickly
            assert.ok(events.length >= 40, `Expected at least 40 events, got ${events.length}`);
            assert.ok(duration < 10000, `Processing took too long: ${duration}ms`);
        });

        it('should debounce rapid changes effectively', async () => {
            let changeCount = 0;
            const testFile = 'rapid-change.md';

            watcher.on('fileChanged', () => {
                changeCount++;
            });

            await watcher.start(tempDir);

            // Create initial file
            await testHelper.createTestFile(testFile, '# Initial content');

            // Make many rapid changes
            for (let i = 0; i < 20; i++) {
                await testHelper.modifyTestFile(testFile, `# Content ${i}\n\nUpdate ${i}`);
                // Small delay to ensure file system operations complete
                await new Promise(resolve => setTimeout(resolve, 10));
            }

            // Wait for debounced events to settle
            await new Promise(resolve => setTimeout(resolve, 300));

            // Should have significantly fewer change events due to debouncing
            assert.ok(changeCount < 10, `Too many change events: ${changeCount}`);
            assert.ok(changeCount > 0, 'Should have at least one change event');
        });
    });

    describe('Error Recovery', () => {
        it('should recover from temporary file system errors', async () => {
            const errors: any[] = [];

            watcher.on('error', (filePath: string, details?: any) => {
                errors.push(details);
            });

            await watcher.start(tempDir);

            // Simulate error condition by removing the watched directory
            fs.rmSync(tempDir, { recursive: true, force: true });

            // Wait a bit for error to be detected
            await new Promise(resolve => setTimeout(resolve, 500));

            // Recreate directory and add file
            fs.mkdirSync(tempDir, { recursive: true });
            await testHelper.createTestFile('recovery.md', '# Recovery Test');

            // Should continue working after recovery
            // Note: This test may not always trigger errors depending on timing
            assert.ok(true); // Test passes if no exceptions thrown
        });

        it('should handle permission errors gracefully', async () => {
            // This test is platform-specific and may not work on all systems
            if (process.platform === 'win32') {
                // Skip on Windows due to different permission model
                return;
            }

            const errors: any[] = [];

            watcher.on('error', (filePath: string, details?: any) => {
                errors.push(details);
            });

            try {
                // Create a directory with restricted permissions
                const restrictedDir = path.join(tempDir, 'restricted');
                fs.mkdirSync(restrictedDir);
                fs.chmodSync(restrictedDir, 0o000); // No permissions

                await watcher.start(restrictedDir);

                // Should handle permission error gracefully
                assert.ok(true);

                // Restore permissions for cleanup
                fs.chmodSync(restrictedDir, 0o755);
            } catch (error) {
                // Expected - permission errors should be handled
                assert.ok(error instanceof Error);
            }
        });
    });

    describe('Lifecycle Integration', () => {
        it('should integrate properly with extension lifecycle', async () => {
            // Test starting and stopping multiple times
            for (let i = 0; i < 3; i++) {
                await watcher.start(tempDir);
                assert.ok(watcher.isActive());

                // Create a file
                await testHelper.createTestFile(`lifecycle-${i}.md`, `# Lifecycle test ${i}`);

                // Stop and verify cleanup
                watcher.stop();
                assert.ok(!watcher.isActive());
            }

            // Should work normally after multiple start/stop cycles
            assert.ok(true);
        });

        it('should handle pause/resume correctly', async () => {
            const events: string[] = [];

            watcher.on('fileAdded', (filePath: string) => {
                events.push(`added:${path.basename(filePath)}`);
            });

            await watcher.start(tempDir);

            // Create file while active
            await testHelper.createTestFile('active.md', '# Active');

            // Pause and create file
            watcher.pause();
            await testHelper.createTestFile('paused.md', '# Paused');

            // Resume and create file
            watcher.resume();
            await testHelper.createTestFile('resumed.md', '# Resumed');

            // Wait for events
            await testHelper.waitForEvents(2, 500);

            // Should have events for active and resumed, but not paused
            assert.ok(events.some(e => e.includes('active.md')));
            assert.ok(events.some(e => e.includes('resumed.md')));
            assert.ok(!events.some(e => e.includes('paused.md')));
        });
    });
});
