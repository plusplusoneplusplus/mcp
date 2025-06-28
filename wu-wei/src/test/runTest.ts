import * as path from 'path';
import { runTests } from '@vscode/test-electron';

async function main() {
    try {
        console.log('Starting Wu Wei extension tests (LEGACY MODE)...');
        console.log('⚠️  This runs ALL tests. Consider using faster alternatives:');
        console.log('   npm run test:unit (5 seconds - unit/ directory only)');
        console.log('   npm run test:integration (30-60 seconds - integration/ directory only)');
        console.log('   npm run test:all (runs both unit and integration separately)');
        console.log('');

        // The folder containing the Extension Manifest package.json
        // Passed to `--extensionDevelopmentPath`
        const extensionDevelopmentPath = path.resolve(__dirname, '../../');
        console.log('Extension development path:', extensionDevelopmentPath);

        // The path to test runner (now includes all test suites)
        // Passed to --extensionTestsPath
        const extensionTestsPath = path.resolve(__dirname, './legacySuite/index');
        console.log('Extension tests path:', extensionTestsPath);

        // Download VS Code, unzip it and run all tests
        // This includes tests from both directories:
        // - unit/ (utility tests - fast, no VS Code APIs)
        // - integration/ (extension functionality - requires VS Code)
        await runTests({
            extensionDevelopmentPath,
            extensionTestsPath,
            launchArgs: [
                '--disable-extensions', // Disable other extensions for cleaner test environment
                '--disable-workspace-trust' // Disable workspace trust for testing
            ]
        });

        console.log('All tests completed successfully!');
    } catch (err) {
        console.error('Failed to run tests', err);
        process.exit(1);
    }
}

main();
