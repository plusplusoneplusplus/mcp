/**
 * Unit tests for FileUtils
 * Testing wu wei principle: comprehensive file system utility validation
 */

import * as assert from 'assert';
import * as fs from 'fs/promises';
import * as path from 'path';
import { FileUtils, FileStats } from '../../../promptStore/utils/fileUtils';

suite('FileUtils Tests', () => {
    let tempDir: string;

    setup(async () => {
        // Create temporary directory for testing
        tempDir = path.join(__dirname, 'test-fileutils-' + Date.now());
        await fs.mkdir(tempDir, { recursive: true });
    });

    teardown(async () => {
        // Clean up temporary directory
        try {
            await fs.rm(tempDir, { recursive: true, force: true });
        } catch (error) {
            // Ignore cleanup errors
        }
    });

    suite('isMarkdownFile', () => {
        test('Should identify markdown files with .md extension', () => {
            assert.strictEqual(FileUtils.isMarkdownFile('test.md'), true);
            assert.strictEqual(FileUtils.isMarkdownFile('README.md'), true);
            assert.strictEqual(FileUtils.isMarkdownFile('path/to/file.md'), true);
        });

        test('Should identify markdown files with .markdown extension', () => {
            assert.strictEqual(FileUtils.isMarkdownFile('test.markdown'), true);
            assert.strictEqual(FileUtils.isMarkdownFile('README.markdown'), true);
            assert.strictEqual(FileUtils.isMarkdownFile('path/to/file.markdown'), true);
        });

        test('Should reject non-markdown files', () => {
            assert.strictEqual(FileUtils.isMarkdownFile('test.txt'), false);
            assert.strictEqual(FileUtils.isMarkdownFile('test.js'), false);
            assert.strictEqual(FileUtils.isMarkdownFile('test.json'), false);
            assert.strictEqual(FileUtils.isMarkdownFile('test'), false);
            assert.strictEqual(FileUtils.isMarkdownFile(''), false);
        });

        test('Should be case insensitive', () => {
            assert.strictEqual(FileUtils.isMarkdownFile('test.MD'), true);
            assert.strictEqual(FileUtils.isMarkdownFile('test.Md'), true);
            assert.strictEqual(FileUtils.isMarkdownFile('test.MARKDOWN'), true);
        });
    });

    suite('shouldIgnore', () => {
        test('Should ignore hidden files and directories', () => {
            assert.strictEqual(FileUtils.shouldIgnore('.hidden'), true);
            assert.strictEqual(FileUtils.shouldIgnore('.gitignore'), true);
            assert.strictEqual(FileUtils.shouldIgnore('.vscode'), true);
        });

        test('Should not ignore regular files', () => {
            assert.strictEqual(FileUtils.shouldIgnore('regular.md'), false);
            assert.strictEqual(FileUtils.shouldIgnore('test-file.txt'), false);
        });

        test('Should ignore files matching exclude patterns', () => {
            const excludePatterns = ['*.tmp', 'node_modules', 'dist/*'];

            assert.strictEqual(FileUtils.shouldIgnore('temp.tmp', excludePatterns), true);
            assert.strictEqual(FileUtils.shouldIgnore('node_modules', excludePatterns), true);
            assert.strictEqual(FileUtils.shouldIgnore('file.js', excludePatterns), false);
        });

        test('Should handle empty exclude patterns', () => {
            assert.strictEqual(FileUtils.shouldIgnore('test.md', []), false);
            assert.strictEqual(FileUtils.shouldIgnore('test.md'), false);
        });
    });

    suite('matchesPattern', () => {
        test('Should match exact strings', () => {
            assert.strictEqual(FileUtils.matchesPattern('test.md', 'test.md'), true);
            assert.strictEqual(FileUtils.matchesPattern('test.md', 'other.md'), false);
        });

        test('Should match simple wildcard patterns', () => {
            assert.strictEqual(FileUtils.matchesPattern('test.md', '*.md'), true);
            assert.strictEqual(FileUtils.matchesPattern('test.txt', '*.md'), false);
            assert.strictEqual(FileUtils.matchesPattern('test.md', 'test.*'), true);
        });

        test('Should match recursive wildcard patterns', () => {
            assert.strictEqual(FileUtils.matchesPattern('path/to/file.md', '**/file.md'), true);
            assert.strictEqual(FileUtils.matchesPattern('deep/nested/path/file.md', '**/file.md'), true);
            assert.strictEqual(FileUtils.matchesPattern('file.md', '**/file.md'), true);
        });

        test('Should handle complex patterns', () => {
            assert.strictEqual(FileUtils.matchesPattern('node_modules/package/index.js', '**/node_modules/**'), true);
            assert.strictEqual(FileUtils.matchesPattern('src/components/Button.tsx', 'src/**/*.tsx'), true);
            assert.strictEqual(FileUtils.matchesPattern('dist/bundle.js', 'dist/**'), true);
        });

        test('Should be case insensitive', () => {
            assert.strictEqual(FileUtils.matchesPattern('TEST.MD', '*.md'), true);
            assert.strictEqual(FileUtils.matchesPattern('File.TXT', '*.txt'), true);
        });

        test('Should handle cross-platform path separators', () => {
            assert.strictEqual(FileUtils.matchesPattern('path\\to\\file.md', '**/file.md'), true);
            assert.strictEqual(FileUtils.matchesPattern('path/to/file.md', '**/file.md'), true);
        });

        test('Should handle question mark wildcards', () => {
            assert.strictEqual(FileUtils.matchesPattern('test1.md', 'test?.md'), true);
            assert.strictEqual(FileUtils.matchesPattern('test12.md', 'test?.md'), false);
            assert.strictEqual(FileUtils.matchesPattern('testa.md', 'test?.md'), true);
        });
    });

    suite('shouldExcludePath', () => {
        test('Should exclude paths matching patterns', () => {
            const excludePatterns = ['**/node_modules/**', '**/.git/**', 'dist/**'];

            assert.strictEqual(FileUtils.shouldExcludePath('project/node_modules/package', excludePatterns), true);
            assert.strictEqual(FileUtils.shouldExcludePath('project/.git/config', excludePatterns), true);
            assert.strictEqual(FileUtils.shouldExcludePath('dist/bundle.js', excludePatterns), true);
        });

        test('Should not exclude non-matching paths', () => {
            const excludePatterns = ['**/node_modules/**', '**/.git/**'];

            assert.strictEqual(FileUtils.shouldExcludePath('src/components/Button.tsx', excludePatterns), false);
            assert.strictEqual(FileUtils.shouldExcludePath('docs/README.md', excludePatterns), false);
        });

        test('Should handle recursive patterns correctly', () => {
            const excludePatterns = ['**/temp/**'];

            assert.strictEqual(FileUtils.shouldExcludePath('project/temp/file.txt', excludePatterns), true);
            assert.strictEqual(FileUtils.shouldExcludePath('temp/file.txt', excludePatterns), true);
            assert.strictEqual(FileUtils.shouldExcludePath('project/src/temp/nested/file.txt', excludePatterns), true);
        });

        test('Should handle cross-platform paths', () => {
            const excludePatterns = ['**/node_modules/**'];

            assert.strictEqual(FileUtils.shouldExcludePath('project\\node_modules\\package', excludePatterns), true);
            assert.strictEqual(FileUtils.shouldExcludePath('project/node_modules/package', excludePatterns), true);
        });

        test('Should handle empty exclude patterns', () => {
            assert.strictEqual(FileUtils.shouldExcludePath('any/path/file.txt', []), false);
        });
    });

    suite('getFileStats', () => {
        test('Should return file statistics for existing files', async () => {
            const testFile = path.join(tempDir, 'test-stats.md');
            const testContent = '# Test File\nContent for testing file stats.';
            await fs.writeFile(testFile, testContent, 'utf8');

            const stats = await FileUtils.getFileStats(testFile);

            assert(stats !== null);
            assert.strictEqual(stats.isFile, true);
            assert.strictEqual(stats.isDirectory, false);
            assert.strictEqual(stats.size, testContent.length);
            assert(stats.mtime instanceof Date);
            assert(stats.birthtime instanceof Date);
            assert(typeof stats.permissions === 'string');
        });

        test('Should return directory statistics', async () => {
            const testDir = path.join(tempDir, 'test-dir');
            await fs.mkdir(testDir);

            const stats = await FileUtils.getFileStats(testDir);

            assert(stats !== null);
            assert.strictEqual(stats.isFile, false);
            assert.strictEqual(stats.isDirectory, true);
        });

        test('Should return null for non-existent files', async () => {
            const nonExistentFile = path.join(tempDir, 'does-not-exist.md');
            const stats = await FileUtils.getFileStats(nonExistentFile);

            assert.strictEqual(stats, null);
        });
    });

    suite('ensureDirectory', () => {
        test('Should create directory if it does not exist', async () => {
            const newDir = path.join(tempDir, 'new-directory');

            // Verify directory doesn't exist
            const existsBefore = await fs.access(newDir).then(() => true).catch(() => false);
            assert.strictEqual(existsBefore, false);

            await FileUtils.ensureDirectory(newDir);

            // Verify directory was created
            const existsAfter = await fs.access(newDir).then(() => true).catch(() => false);
            assert.strictEqual(existsAfter, true);

            const stats = await fs.stat(newDir);
            assert(stats.isDirectory());
        });

        test('Should not fail if directory already exists', async () => {
            const existingDir = path.join(tempDir, 'existing-directory');
            await fs.mkdir(existingDir);

            // Should not throw error
            await FileUtils.ensureDirectory(existingDir);

            // Verify directory still exists
            const stats = await fs.stat(existingDir);
            assert(stats.isDirectory());
        });

        test('Should create nested directories', async () => {
            const nestedDir = path.join(tempDir, 'level1', 'level2', 'level3');

            await FileUtils.ensureDirectory(nestedDir);

            const stats = await fs.stat(nestedDir);
            assert(stats.isDirectory());
        });
    });

    suite('writeFileAtomic', () => {
        test('Should write file atomically', async () => {
            const testFile = path.join(tempDir, 'atomic-test.md');
            const content = '# Atomic Write Test\nThis content was written atomically.';

            await FileUtils.writeFileAtomic(testFile, content);

            const readContent = await fs.readFile(testFile, 'utf8');
            assert.strictEqual(readContent, content);
        });

        test('Should create parent directories if needed', async () => {
            const testFile = path.join(tempDir, 'nested', 'dirs', 'atomic-test.md');
            const content = '# Nested Atomic Write Test';

            await FileUtils.writeFileAtomic(testFile, content);

            const readContent = await fs.readFile(testFile, 'utf8');
            assert.strictEqual(readContent, content);
        });

        test('Should overwrite existing files', async () => {
            const testFile = path.join(tempDir, 'overwrite-test.md');
            const originalContent = '# Original Content';
            const newContent = '# New Content';

            // Write original content
            await fs.writeFile(testFile, originalContent, 'utf8');

            // Overwrite with atomic write
            await FileUtils.writeFileAtomic(testFile, newContent);

            const readContent = await fs.readFile(testFile, 'utf8');
            assert.strictEqual(readContent, newContent);
        });

        test('Should handle write errors gracefully', async () => {
            // Try to write to an invalid path (should fail)
            const invalidPath = path.join('/invalid/path/that/does/not/exist', 'test.md');

            try {
                await FileUtils.writeFileAtomic(invalidPath, 'content');
                assert.fail('Should have thrown an error');
            } catch (error) {
                assert(error instanceof Error);
            }
        });
    });

    suite('readFileContent', () => {
        test('Should read file content correctly', async () => {
            const testFile = path.join(tempDir, 'read-test.md');
            const content = '# Read Test\nThis is test content for reading.';
            await fs.writeFile(testFile, content, 'utf8');

            const readContent = await FileUtils.readFileContent(testFile);
            assert.strictEqual(readContent, content);
        });

        test('Should handle UTF-8 encoding properly', async () => {
            const testFile = path.join(tempDir, 'utf8-test.md');
            const content = '# UTF-8 Test\nSpecial characters: üñíçødé 🚀 中文';
            await fs.writeFile(testFile, content, 'utf8');

            const readContent = await FileUtils.readFileContent(testFile);
            assert.strictEqual(readContent, content);
        });

        test('Should throw error for non-existent files', async () => {
            const nonExistentFile = path.join(tempDir, 'does-not-exist.md');

            try {
                await FileUtils.readFileContent(nonExistentFile);
                assert.fail('Should have thrown an error');
            } catch (error) {
                assert(error instanceof Error);
            }
        });
    });

    suite('pathExists', () => {
        test('Should return true for existing files', async () => {
            const testFile = path.join(tempDir, 'exists-test.md');
            await fs.writeFile(testFile, '# Exists Test', 'utf8');

            const exists = await FileUtils.pathExists(testFile);
            assert.strictEqual(exists, true);
        });

        test('Should return true for existing directories', async () => {
            const testDir = path.join(tempDir, 'exists-dir');
            await fs.mkdir(testDir);

            const exists = await FileUtils.pathExists(testDir);
            assert.strictEqual(exists, true);
        });

        test('Should return false for non-existent paths', async () => {
            const nonExistentPath = path.join(tempDir, 'does-not-exist');

            const exists = await FileUtils.pathExists(nonExistentPath);
            assert.strictEqual(exists, false);
        });
    });

    suite('generateSafeFileName', () => {
        test('Should generate safe filenames from titles', () => {
            assert.strictEqual(FileUtils.generateSafeFileName('My Test Prompt'), 'my-test-prompt.md');
            assert.strictEqual(FileUtils.generateSafeFileName('Another Title'), 'another-title.md');
        });

        test('Should handle special characters', () => {
            assert.strictEqual(FileUtils.generateSafeFileName('Title with: special <chars>'), 'title-with-special-chars.md');
            assert.strictEqual(FileUtils.generateSafeFileName('File/Path\\Test'), 'filepathtest.md');
            assert.strictEqual(FileUtils.generateSafeFileName('Test|File?Name'), 'testfilename.md');
        });

        test('Should handle custom extensions', () => {
            assert.strictEqual(FileUtils.generateSafeFileName('Test', '.txt'), 'test.txt');
            assert.strictEqual(FileUtils.generateSafeFileName('Config', '.json'), 'config.json');
        });

        test('Should handle multiple spaces and special cases', () => {
            assert.strictEqual(FileUtils.generateSafeFileName('  Multiple   Spaces  '), 'multiple-spaces.md');
            assert.strictEqual(FileUtils.generateSafeFileName('___Underscores___'), 'underscores.md');
            assert.strictEqual(FileUtils.generateSafeFileName('123 Numbers'), '123-numbers.md');
        });

        test('Should handle empty and edge cases', () => {
            assert.strictEqual(FileUtils.generateSafeFileName(''), '.md');
            assert.strictEqual(FileUtils.generateSafeFileName('   '), '.md');
            assert.strictEqual(FileUtils.generateSafeFileName('!!!'), '.md');
        });
    });

    suite('getRelativePath', () => {
        test('Should return relative path when file is within base path', () => {
            const basePath = '/home/user/workspace';
            const filePath = '/home/user/workspace/src/components/Button.tsx';

            const relative = FileUtils.getRelativePath(filePath, basePath);
            assert.strictEqual(relative, 'src/components/Button.tsx');
        });

        test('Should return full path when file is outside base path', () => {
            const basePath = '/home/user/workspace';
            const filePath = '/home/other/project/file.txt';

            const relative = FileUtils.getRelativePath(filePath, basePath);
            assert.strictEqual(relative, filePath);
        });

        test('Should handle missing base path', () => {
            const filePath = '/some/file/path.txt';

            const relative = FileUtils.getRelativePath(filePath);
            // Should return the original path when no base path is provided and no VS Code workspace
            assert.strictEqual(relative, filePath);
        });

        test('Should handle cross-platform paths', () => {
            const basePath = 'C:\\Users\\user\\workspace';
            const filePath = 'C:\\Users\\user\\workspace\\src\\file.ts';

            const relative = FileUtils.getRelativePath(filePath, basePath);
            assert(relative.includes('src'));
        });
    });

    suite('isPathSafe', () => {
        test('Should allow paths within allowed directories', () => {
            const allowedPaths = ['/home/user/workspace', '/home/user/documents'];

            assert.strictEqual(FileUtils.isPathSafe('/home/user/workspace/src/file.ts', allowedPaths), true);
            assert.strictEqual(FileUtils.isPathSafe('/home/user/documents/notes.md', allowedPaths), true);
        });

        test('Should reject paths outside allowed directories', () => {
            const allowedPaths = ['/home/user/workspace'];

            assert.strictEqual(FileUtils.isPathSafe('/home/other/file.ts', allowedPaths), false);
            assert.strictEqual(FileUtils.isPathSafe('/etc/passwd', allowedPaths), false);
        });

        test('Should reject path traversal attempts', () => {
            const allowedPaths = ['/home/user/workspace'];

            assert.strictEqual(FileUtils.isPathSafe('/home/user/workspace/../../../etc/passwd', allowedPaths), false);
            assert.strictEqual(FileUtils.isPathSafe('../outside/file.txt', allowedPaths), false);
        });

        test('Should handle normalized paths correctly', () => {
            const allowedPaths = ['/home/user/workspace'];

            // These should be safe after normalization
            assert.strictEqual(FileUtils.isPathSafe('/home/user/workspace/./src/file.ts', allowedPaths), true);
        });

        test('Should handle empty allowed paths', () => {
            assert.strictEqual(FileUtils.isPathSafe('/any/path/file.txt', []), false);
        });
    });

    suite('createBackup', () => {
        test('Should create backup of existing file', async () => {
            const originalFile = path.join(tempDir, 'backup-test.md');
            const content = '# Original Content\nThis will be backed up.';
            await fs.writeFile(originalFile, content, 'utf8');

            const backupPath = await FileUtils.createBackup(originalFile);

            // Verify backup exists
            const backupExists = await fs.access(backupPath).then(() => true).catch(() => false);
            assert.strictEqual(backupExists, true);

            // Verify backup content matches original
            const backupContent = await fs.readFile(backupPath, 'utf8');
            assert.strictEqual(backupContent, content);

            // Verify backup path format
            assert(backupPath.includes('backup-test.md.backup.'));
            assert(backupPath.includes(originalFile));
        });

        test('Should generate unique backup filenames', async () => {
            const originalFile = path.join(tempDir, 'multi-backup-test.md');
            const content = '# Content for multiple backups';
            await fs.writeFile(originalFile, content, 'utf8');

            const backup1 = await FileUtils.createBackup(originalFile);

            // Wait a bit to ensure different timestamp
            await new Promise(resolve => setTimeout(resolve, 10));

            const backup2 = await FileUtils.createBackup(originalFile);

            assert.notStrictEqual(backup1, backup2);

            // Both backups should exist
            const backup1Exists = await fs.access(backup1).then(() => true).catch(() => false);
            const backup2Exists = await fs.access(backup2).then(() => true).catch(() => false);
            assert.strictEqual(backup1Exists, true);
            assert.strictEqual(backup2Exists, true);
        });

        test('Should throw error for non-existent files', async () => {
            const nonExistentFile = path.join(tempDir, 'does-not-exist.md');

            try {
                await FileUtils.createBackup(nonExistentFile);
                assert.fail('Should have thrown an error');
            } catch (error) {
                assert(error instanceof Error);
            }
        });
    });

    suite('Cross-platform compatibility', () => {
        test('Should handle Windows-style paths', () => {
            const windowsPath = 'C:\\Users\\user\\Documents\\file.md';
            assert.strictEqual(FileUtils.isMarkdownFile(windowsPath), true);
        });

        test('Should handle Unix-style paths', () => {
            const unixPath = '/home/user/documents/file.md';
            assert.strictEqual(FileUtils.isMarkdownFile(unixPath), true);
        });

        test('Should normalize path separators in pattern matching', () => {
            // Test both directions
            assert.strictEqual(FileUtils.matchesPattern('path\\to\\file.md', 'path/to/file.md'), true);
            assert.strictEqual(FileUtils.matchesPattern('path/to/file.md', 'path\\to\\file.md'), true);
        });

        test('Should handle mixed path separators', () => {
            const mixedPath = 'C:\\Users/user\\Documents/file.md';
            assert.strictEqual(FileUtils.isMarkdownFile(mixedPath), true);
        });
    });

    suite('Edge cases and error handling', () => {
        test('Should handle empty strings gracefully', () => {
            assert.strictEqual(FileUtils.isMarkdownFile(''), false);
            assert.strictEqual(FileUtils.shouldIgnore(''), false);
            assert.strictEqual(FileUtils.matchesPattern('', ''), true);
            assert.strictEqual(FileUtils.matchesPattern('test', ''), false);
        });

        test('Should handle null and undefined gracefully', () => {
            // These would cause TypeScript errors, but testing runtime behavior
            assert.strictEqual(FileUtils.shouldIgnore('test', undefined), false);
        });

        test('Should handle very long filenames', () => {
            const longName = 'a'.repeat(300) + '.md';
            assert.strictEqual(FileUtils.isMarkdownFile(longName), true);
        });

        test('Should handle special Unicode characters', () => {
            const unicodeName = 'тест-файл-中文-🚀.md';
            assert.strictEqual(FileUtils.isMarkdownFile(unicodeName), true);

            const safeName = FileUtils.generateSafeFileName('тест файл 中文 🚀');
            assert(safeName.endsWith('.md'));
        });
    });
}); 