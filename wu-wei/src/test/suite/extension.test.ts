import assert from 'assert';
import * as vscode from 'vscode';
import * as myExtension from '../../extension';

/**
 * Basic Wu Wei Extension Tests
 * 
 * Following Wu Wei philosophy: simple, natural, flowing tests
 * that verify core functionality without excessive complexity.
 */

describe('Wu Wei Extension Test Suite', () => {
    before(() => {
        vscode.window.showInformationMessage('Start Wu Wei tests.');
    });

    it('should have activate function', () => {
        assert.ok(typeof myExtension.activate === 'function');
    });

    it('should have deactivate function', () => {
        assert.ok(typeof myExtension.deactivate === 'function');
    });

    it('should be able to get Wu Wei configuration', () => {
        const config = vscode.workspace.getConfiguration('wu-wei');
        assert.ok(config);

        // Test default configuration values
        const enableAutomation = config.get('enableAutomation');
        assert.strictEqual(enableAutomation, true);

        const preferredModel = config.get('preferredModel');
        assert.strictEqual(preferredModel, 'gpt-4o');
    });

    it('should register wu-wei.hello command', async () => {
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('wu-wei.hello'), 'wu-wei.hello command should be registered');
    });

    it('should register wu-wei.openChat command', async () => {
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('wu-wei.openChat'), 'wu-wei.openChat command should be registered');
    });

    it('should register wu-wei.newChat command', async () => {
        const commands = await vscode.commands.getCommands(true);
        assert.ok(commands.includes('wu-wei.newChat'), 'wu-wei.newChat command should be registered');
    });
});
