/**
 * Simple test to verify the PromptManager file system operations
 */

import * as assert from 'assert';
import * as path from 'path';
import * as fs from 'fs/promises';
import * as os from 'os';
import { PromptManager } from '../../promptStore/PromptManager';

describe('PromptManager Basic File Operations', () => {
    let tempDir: string;
    let promptManager: PromptManager;

    beforeEach(async () => {
        tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'prompt-test-'));
        promptManager = new PromptManager({
            watchPaths: [tempDir],
            autoRefresh: false,
            enableCache: false
        });
    });

    afterEach(async () => {
        promptManager.dispose();
        await fs.rm(tempDir, { recursive: true, force: true }).catch(() => { });
    });

    it('should scan empty directory', async () => {
        const files = await promptManager.scanDirectory(tempDir);
        assert.strictEqual(files.length, 0);
    });

    it('should create and load a simple prompt', async () => {
        const prompt = await promptManager.createPrompt('Test Prompt');

        assert.strictEqual(prompt.metadata.title, 'Test Prompt');
        assert(prompt.filePath.endsWith('.md'));

        // Verify file exists
        const exists = await fs.access(prompt.filePath).then(() => true).catch(() => false);
        assert(exists);

        // Load it back
        const loaded = await promptManager.loadPrompt(prompt.filePath);
        assert.strictEqual(loaded.metadata.title, 'Test Prompt');
    });

    it('should handle file system operations', async () => {
        // Create a simple markdown file
        const testFile = path.join(tempDir, 'test.md');
        await fs.writeFile(testFile, '# Test\nContent');

        // Scan should find it
        const files = await promptManager.scanDirectory(tempDir);
        assert.strictEqual(files.length, 1);
        assert(files[0].endsWith('test.md'));

        // Load all should work
        const prompts = await promptManager.loadAllPrompts(tempDir);
        assert(prompts.length >= 1);
    });
});
