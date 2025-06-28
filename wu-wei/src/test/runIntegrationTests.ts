import * as path from 'path';
import { runTests } from '@vscode/test-electron';

async function main() {
    try {
        console.log('Starting Wu Wei VS Code Integration Tests...');

        // The folder containing the Extension Manifest package.json
        // Passed to `--extensionDevelopmentPath`
        const extensionDevelopmentPath = path.resolve(__dirname, '../../');
        console.log('Extension development path:', extensionDevelopmentPath);

        // The path to test runner for integration tests
        // Passed to --extensionTestsPath
        const extensionTestsPath = path.resolve(__dirname, './suiteIntegration/index');
        console.log('Extension tests path:', extensionTestsPath);

        // Download VS Code, unzip it and run integration tests
        // This includes tests that depend on VS Code environment:
        // - Extension functionality tests
        // - Chat participant tests  
        // - PromptStore tests that use VS Code APIs
        // - File operation tests that need VS Code workspace
        await runTests({
            extensionDevelopmentPath,
            extensionTestsPath,
            launchArgs: [
                '--disable-extensions', // Disable other extensions for cleaner test environment
                '--disable-workspace-trust' // Disable workspace trust for testing
            ]
        });

        console.log('All integration tests completed successfully!');
    } catch (err) {
        console.error('Failed to run integration tests:', err);
        process.exit(1);
    }
}

main(); 