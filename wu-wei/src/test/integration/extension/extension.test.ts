import assert from 'assert';
import * as vscode from 'vscode';
import * as myExtension from '../../../extension';

/**
 * Basic Wu Wei Extension Tests
 * 
 * Following Wu Wei philosophy: simple, natural, flowing tests
 * that verify core functionality without excessive complexity.
 */

suite('Wu Wei Extension Test Suite', () => {
    suiteSetup(async () => {
        vscode.window.showInformationMessage('Start Wu Wei tests.');

        // Wait for the extension to be activated
        const extension = vscode.extensions.getExtension('wu-wei.wu-wei');
        if (extension && !extension.isActive) {
            await extension.activate();
        }

        // Give a bit more time for command registration
        await new Promise(resolve => setTimeout(resolve, 1000));
    });

    test('should have activate function', () => {
        assert.ok(typeof myExtension.activate === 'function');
    });

    test('should have deactivate function', () => {
        assert.ok(typeof myExtension.deactivate === 'function');
    });

    test('should be able to get Wu Wei configuration', () => {
        const config = vscode.workspace.getConfiguration('wu-wei');
        assert.ok(config);

        // Test default configuration values
        const enableAutomation = config.get('enableAutomation');
        assert.strictEqual(enableAutomation, true);

        const preferredModel = config.get('preferredModel');
        assert.strictEqual(preferredModel, 'gpt-4o');
    });

    test('should register wu-wei.hello command', async () => {
        const commands = await vscode.commands.getCommands(true);
        const hasCommand = commands.includes('wu-wei.hello');
        console.log('Available wu-wei commands:', commands.filter(cmd => cmd.startsWith('wu-wei')));
        assert.ok(hasCommand, 'wu-wei.hello command should be registered');
    });

    test('should register wu-wei.openChat command', async () => {
        const commands = await vscode.commands.getCommands(true);
        const hasCommand = commands.includes('wu-wei.openChat');
        assert.ok(hasCommand, 'wu-wei.openChat command should be registered');
    });

    test('should register wu-wei.newChat command', async () => {
        const commands = await vscode.commands.getCommands(true);
        const hasCommand = commands.includes('wu-wei.newChat');
        assert.ok(hasCommand, 'wu-wei.newChat command should be registered');
    });
});
