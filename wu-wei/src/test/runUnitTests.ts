import * as path from 'path';
import * as glob from 'glob';
import Mocha from 'mocha';

export function run(): Promise<void> {
    // Create the mocha test for unit tests only
    const mocha = new Mocha({
        ui: 'tdd',
        color: true,
        timeout: 5000, // Shorter timeout for unit tests
        reporter: 'spec'
    });

    const testsRoot = path.resolve(__dirname);

    return new Promise((c, e) => {
        console.log('Running Wu Wei Unit Tests...');
        console.log('Tests root:', testsRoot);

        // Simple pattern for unit tests - no VS Code dependencies
        const testFiles = glob.sync('unit/**/*.test.js', {
            cwd: testsRoot,
            ignore: ['**/node_modules/**']
        });

        console.log(`Found ${testFiles.length} unit test files:`, testFiles);

        if (testFiles.length === 0) {
            console.log('No unit test files found. Make sure tests are compiled to .js files.');
            console.log('Unit tests should be in: unit/**/*.test.ts');
            console.log('These tests should NOT import VS Code APIs and should be fast to execute.');
            c();
            return;
        }

        // Add files to the test suite
        testFiles.forEach((f: string) => {
            const fullPath = path.resolve(testsRoot, f);
            console.log(`Adding test file: ${fullPath}`);
            mocha.addFile(fullPath);
        });

        try {
            // Run the mocha test
            mocha.run((failures: number) => {
                if (failures > 0) {
                    console.error(`${failures} unit tests failed.`);
                    e(new Error(`${failures} unit tests failed.`));
                } else {
                    console.log('All unit tests passed!');
                    c();
                }
            });
        } catch (err) {
            console.error('Error running unit tests:', err);
            e(err);
        }
    });
}

// Allow running this script directly
if (require.main === module) {
    run().catch(err => {
        console.error('Unit test runner failed:', err);
        process.exit(1);
    });
} 