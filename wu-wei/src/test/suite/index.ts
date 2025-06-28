import * as path from 'path';
import * as glob from 'glob';
import Mocha from 'mocha';

export function run(): Promise<void> {
    // Create the mocha test
    const mocha = new Mocha({
        ui: 'bdd',
        color: true,
        timeout: 10000
    });

    const testsRoot = path.resolve(__dirname, '..');

    return new Promise((c, e) => {
        // Look for tests only in the suite directory
        const testFiles = glob.sync('suite/**/*.test.js', {
            cwd: testsRoot,
            ignore: ['**/node_modules/**']
        });

        // Add files to the test suite
        testFiles.forEach((f: string) => mocha.addFile(path.resolve(testsRoot, f)));

        try {
            // Run the mocha test
            mocha.run((failures: number) => {
                if (failures > 0) {
                    e(new Error(`${failures} tests failed.`));
                } else {
                    c();
                }
            });
        } catch (err) {
            console.error(err);
            e(err);
        }
    });
}
