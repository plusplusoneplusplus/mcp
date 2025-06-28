import * as path from 'path';
import * as glob from 'glob';
import Mocha from 'mocha';

export function run(): Promise<void> {
    // Create the mocha test for integration tests
    const mocha = new Mocha({
        ui: 'tdd',
        color: true,
        timeout: 15000, // Longer timeout for integration tests
        reporter: 'spec'
    });

    const testsRoot = path.resolve(__dirname, '..');

    return new Promise((c, e) => {
        console.log('Running Wu Wei Integration Tests...');
        console.log('Tests root:', testsRoot);

        // Simple pattern for integration tests - require VS Code APIs
        const testFiles = glob.sync('integration/**/*.test.js', {
            cwd: testsRoot,
            ignore: ['**/node_modules/**']
        });

        console.log(`Found ${testFiles.length} integration test files:`, testFiles);

        if (testFiles.length === 0) {
            console.log('No integration test files found. Make sure tests are compiled to .js files.');
            console.log('Integration tests should be in: integration/**/*.test.ts');
            console.log('These tests CAN import VS Code APIs and test extension functionality.');
            c();
            return;
        }

        // Add files to the test suite
        testFiles.forEach((f: string) => {
            const fullPath = path.resolve(testsRoot, f);
            console.log(`Adding integration test file: ${fullPath}`);
            mocha.addFile(fullPath);
        });

        try {
            // Run the mocha test
            mocha.run((failures: number) => {
                if (failures > 0) {
                    console.error(`${failures} integration tests failed.`);
                    e(new Error(`${failures} integration tests failed.`));
                } else {
                    console.log('All integration tests passed!');
                    c();
                }
            });
        } catch (err) {
            console.error('Error running integration tests:', err);
            e(err);
        }
    });
} 