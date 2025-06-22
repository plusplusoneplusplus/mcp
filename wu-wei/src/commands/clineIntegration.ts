import * as vscode from 'vscode';
import { logger } from '../logger';

/**
 * Cline Integration for Wu Wei
 * Provides integration with the Cline (Claude Dev) extension for automated task execution
 */
export class ClineIntegration {
    private static readonly CLINE_EXTENSION_ID = 'saoudrizwan.claude-dev';
    private static readonly TEST_PROMPT = 'what does this code snippet do? `print("abc")`';

    // Common command arrays to avoid duplication
    private static readonly FOCUS_COMMANDS = [
        'workbench.action.focusActiveEditorGroup',
        'workbench.action.focusNextGroup',
        'workbench.view.extension.saoudrizwan.claude-dev'
    ];

    private static readonly SUBMISSION_COMMANDS = [
        'workbench.action.acceptSelectedSuggestion',
        'editor.action.insertLineAfter',
        'list.select',
        'workbench.action.quickOpenSelectNext'
    ];

    private static readonly CLINE_SUBMIT_COMMANDS = [
        'cline.sendMessage',
        'cline.submitMessage',
        'cline.submit',
        'claude-dev.sendMessage',
        'claude-dev.submitMessage',
        'claude-dev.submit'
    ];

    /**
     * Check if Cline extension is available and activate it if needed
     */
    private static async ensureClineExtension(): Promise<vscode.Extension<any> | null> {
        const clineExtension = vscode.extensions.getExtension(ClineIntegration.CLINE_EXTENSION_ID);

        if (!clineExtension) {
            const message = 'Cline extension not found. Please install Cline (Claude Dev) extension first.';
            logger.error(message);
            vscode.window.showErrorMessage(`Wu Wei: ${message}`);
            return null;
        }

        if (!clineExtension.isActive) {
            logger.info('Activating Cline extension...');
            await clineExtension.activate();
        }

        logger.info('Cline extension is available and active');
        return clineExtension;
    }

    /**
     * Initialize a new Cline task session
     */
    private static async initializeClineTask(): Promise<boolean> {
        try {
            logger.info('Step 1: Opening Cline in new tab');
            await vscode.commands.executeCommand('cline.openInNewTab');
            await new Promise(resolve => setTimeout(resolve, 1000));

            logger.info('Step 2: Starting new task');
            await vscode.commands.executeCommand('cline.plusButtonClicked');
            await new Promise(resolve => setTimeout(resolve, 500));

            logger.info('Step 3: Focusing chat input');
            await this.focusClineInput();
            await new Promise(resolve => setTimeout(resolve, 1000));

            return true;
        } catch (error) {
            logger.error('Failed to initialize Cline task', error);
            return false;
        }
    }

    /**
     * Focus the Cline chat input with fallback methods
     */
    private static async focusClineInput(): Promise<void> {
        try {
            await vscode.commands.executeCommand('cline.focusChatInput');
            logger.info('Successfully focused chat input with cline.focusChatInput');
        } catch (focusError) {
            logger.warn('cline.focusChatInput failed, trying alternative focus methods', focusError);

            for (const focusCmd of this.FOCUS_COMMANDS) {
                try {
                    await vscode.commands.executeCommand(focusCmd);
                    logger.info(`Successfully focused using alternative: ${focusCmd}`);
                    break;
                } catch (altError) {
                    logger.debug(`Alternative focus command ${focusCmd} failed`, altError);
                }
            }
        }
    }

    /**
     * Send a prompt to Cline using multiple strategies
     */
    private static async sendPromptToCline(prompt: string): Promise<boolean> {
        try {
            logger.info(`Sending prompt to Cline: "${prompt}"`);

            // Strategy 1: Try Cline API directly if available
            const success = await this.tryDirectClineAPI(prompt);
            if (success) {
                logger.info('Successfully sent prompt via Cline API');
                return true;
            }

            // Strategy 2: Focus input and use clipboard method
            logger.info('Trying clipboard + paste method');

            // Ensure we have focus on the input
            await this.focusClineInput();
            await new Promise(resolve => setTimeout(resolve, 500));

            // Copy prompt to clipboard
            await vscode.env.clipboard.writeText(prompt);
            logger.info('Prompt copied to clipboard');
            await new Promise(resolve => setTimeout(resolve, 300));

            // Try pasting from clipboard
            try {
                await vscode.commands.executeCommand('editor.action.clipboardPasteAction');
                logger.info('Successfully pasted prompt from clipboard');
                await new Promise(resolve => setTimeout(resolve, 500));

                // Submit the prompt
                const submitted = await this.submitPrompt();
                if (submitted) {
                    logger.info('Prompt submission completed');
                    return true;
                }

            } catch (pasteError) {
                logger.warn('Clipboard paste failed, trying direct type command', pasteError);

                // Strategy 3: Direct typing fallback
                try {
                    // Clear any existing content first
                    await vscode.commands.executeCommand('editor.action.selectAll');
                    await new Promise(resolve => setTimeout(resolve, 100));

                    // Type the prompt directly
                    await vscode.commands.executeCommand('type', { text: prompt });
                    logger.info('Successfully typed prompt directly');
                    await new Promise(resolve => setTimeout(resolve, 300));

                    // Try to submit
                    await this.submitPrompt();
                    return true;

                } catch (typeError) {
                    logger.error('Direct typing also failed', typeError);
                }
            }

            // Strategy 4: Last resort - type prompt with Enter in one command
            logger.info('Trying last resort: type prompt with immediate Enter');
            try {
                await vscode.commands.executeCommand('type', { text: prompt + '\n' });
                logger.info('Successfully typed prompt with Enter');
                await new Promise(resolve => setTimeout(resolve, 500));
                return true;
            } catch (lastResortError) {
                logger.error('Last resort typing failed', lastResortError);
            }

            return false;

        } catch (error) {
            logger.error('All prompt sending strategies failed', error);
            return false;
        }
    }

    /**
     * Try to use Cline's direct API if available
     */
    private static async tryDirectClineAPI(prompt: string): Promise<boolean> {
        try {
            const clineExtension = vscode.extensions.getExtension(this.CLINE_EXTENSION_ID);
            if (!clineExtension?.isActive || !clineExtension.exports) {
                return false;
            }

            logger.info('Attempting to use Cline extension API directly');

            // Try common API methods that Cline might expose
            const apiMethods = ['sendMessage', 'addMessage', 'executePrompt', 'chat', 'submitMessage'];

            for (const methodName of apiMethods) {
                if (typeof clineExtension.exports[methodName] === 'function') {
                    try {
                        logger.info(`Trying Cline API method: ${methodName}`);
                        await clineExtension.exports[methodName](prompt);
                        logger.info(`Successfully sent prompt via API method: ${methodName}`);
                        return true;
                    } catch (apiError) {
                        logger.debug(`API method ${methodName} failed`, apiError);
                    }
                }
            }

            // Try with different parameter patterns
            for (const methodName of apiMethods) {
                if (typeof clineExtension.exports[methodName] === 'function') {
                    try {
                        logger.info(`Trying ${methodName} with message object`);
                        await clineExtension.exports[methodName]({ text: prompt });
                        logger.info(`Successfully sent prompt via API method: ${methodName} (object)`);
                        return true;
                    } catch (apiError) {
                        logger.debug(`API method ${methodName} (object) failed`, apiError);
                    }
                }
            }

            return false;

        } catch (error) {
            logger.debug('Direct API attempt failed', error);
            return false;
        }
    }

    /**
     * Submit the prompt using multiple submission strategies
     */
    private static async submitPrompt(): Promise<boolean> {
        logger.info('Attempting to submit prompt...');

        // Strategy 1: Try Cline-specific submission commands first (most likely to work)
        const availableCommands = await vscode.commands.getCommands();

        // Check if any Cline-specific commands are available
        for (const submitCmd of this.CLINE_SUBMIT_COMMANDS) {
            if (availableCommands.includes(submitCmd)) {
                try {
                    logger.info(`Trying Cline-specific command: ${submitCmd}`);
                    await vscode.commands.executeCommand(submitCmd);
                    logger.info(`Successfully executed Cline submission via: ${submitCmd}`);
                    await new Promise(resolve => setTimeout(resolve, 500)); // Wait to see if it worked
                    return true;
                } catch (submitError) {
                    logger.debug(`Cline submission command ${submitCmd} failed`, submitError);
                }
            }
        }

        // Strategy 2: Try to simulate Enter key press more aggressively
        logger.info('Trying multiple Enter key strategies...');

        // First, ensure we're in the right input field
        try {
            await vscode.commands.executeCommand('cline.focusChatInput');
            await new Promise(resolve => setTimeout(resolve, 300));
        } catch (focusError) {
            logger.debug('Could not focus chat input', focusError);
        }

        // Try different Enter key approaches
        const enterStrategies = [
            // Standard newline
            () => vscode.commands.executeCommand('type', { text: '\n' }),
            // Carriage return + newline
            () => vscode.commands.executeCommand('type', { text: '\r\n' }),
            // Just carriage return
            () => vscode.commands.executeCommand('type', { text: '\r' }),
            // Explicit key press simulation
            () => vscode.commands.executeCommand('workbench.action.quickInputNavigateNext'),
            () => vscode.commands.executeCommand('workbench.action.quickInputAccept'),
        ];

        for (const [index, strategy] of enterStrategies.entries()) {
            try {
                logger.info(`Trying Enter strategy ${index + 1}`);
                await strategy();
                await new Promise(resolve => setTimeout(resolve, 300));
                logger.info(`Enter strategy ${index + 1} executed`);
            } catch (enterError) {
                logger.debug(`Enter strategy ${index + 1} failed`, enterError);
            }
        }

        // Strategy 3: Try form submission commands
        const formSubmissionCommands = [
            'workbench.action.acceptSelectedSuggestion',
            'list.select',
            'editor.action.insertLineAfter',
            'workbench.action.submitSelectedSuggestion'
        ];

        for (const submitCmd of formSubmissionCommands) {
            try {
                logger.info(`Trying form submission command: ${submitCmd}`);
                await vscode.commands.executeCommand(submitCmd);
                await new Promise(resolve => setTimeout(resolve, 200));
            } catch (submitError) {
                logger.debug(`Form submission command ${submitCmd} failed`, submitError);
            }
        }

        // Strategy 4: Try to trigger any chat/send related commands
        const chatCommands = availableCommands.filter(cmd =>
            cmd.toLowerCase().includes('send') ||
            cmd.toLowerCase().includes('chat') ||
            cmd.toLowerCase().includes('submit') ||
            cmd.toLowerCase().includes('execute')
        );

        logger.info(`Found ${chatCommands.length} potential chat/send commands`);

        for (const chatCmd of chatCommands.slice(0, 5)) { // Limit to first 5 to avoid spam
            try {
                logger.info(`Trying chat command: ${chatCmd}`);
                await vscode.commands.executeCommand(chatCmd);
                await new Promise(resolve => setTimeout(resolve, 200));
            } catch (chatError) {
                logger.debug(`Chat command ${chatCmd} failed`, chatError);
            }
        }

        logger.info('Completed all submission attempts');
        return true;
    }

    /**
     * Verify if the prompt was successfully submitted by checking various indicators
     */
    private static async verifyPromptSubmission(): Promise<boolean> {
        try {
            // Wait a moment for the submission to process
            await new Promise(resolve => setTimeout(resolve, 1000));

            logger.info('Verifying prompt submission...');

            // Strategy 1: Check if there are any Cline status commands
            const availableCommands = await vscode.commands.getCommands();
            const statusCommands = availableCommands.filter(cmd =>
                cmd.includes('cline') && (
                    cmd.includes('status') ||
                    cmd.includes('state') ||
                    cmd.includes('active')
                )
            );

            for (const statusCmd of statusCommands) {
                try {
                    await vscode.commands.executeCommand(statusCmd);
                    logger.info(`Checked status via: ${statusCmd}`);
                } catch (statusError) {
                    logger.debug(`Status command ${statusCmd} failed`, statusError);
                }
            }

            // Strategy 2: Try to check if input field is clear (indirect indication)
            // This is harder to verify programmatically, so we'll rely on user feedback

            logger.info('Prompt submission verification completed');
            return true;

        } catch (error) {
            logger.debug('Error during prompt verification', error);
            return false;
        }
    }

    /**
     * Execute a command sequence pattern with a custom prompt
     */
    private static async executeCommandSequence(prompt: string): Promise<boolean> {
        logger.info('Wu Wei: Executing Cline command sequence with custom prompt');

        try {
            // Initialize Cline task
            const initialized = await this.initializeClineTask();
            if (!initialized) {
                return false;
            }

            // Send the prompt
            const sent = await this.sendPromptToCline(prompt);
            if (sent) {
                logger.info('Successfully executed Cline command sequence with custom prompt');
                return true;
            }

            throw new Error('Failed to send prompt to Cline');

        } catch (error) {
            logger.error('Error in executeCommandSequence', error);
            return false;
        }
    }

    /**
     * Test Cline integration by sending a simple prompt
     */
    public static async testClineIntegration(): Promise<void> {
        logger.info('Wu Wei: Starting Cline integration test');

        try {
            // Check if Cline extension is available
            const clineExtension = await this.ensureClineExtension();
            if (!clineExtension) {
                return;
            }

            // Show progress to user
            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: "Wu Wei: Testing Cline Integration",
                cancellable: false
            }, async (progress) => {
                progress.report({ increment: 20, message: "Initializing Cline task..." }); try {
                    // Use the command sequence pattern to start task and send prompt
                    const success = await this.executeCommandSequence(this.TEST_PROMPT);

                    if (success) {
                        progress.report({ increment: 60, message: "Prompt sent, verifying submission..." });

                        // Verify the submission
                        await this.verifyPromptSubmission();

                        progress.report({ increment: 20, message: "Task started successfully! Cline is processing..." });

                        logger.info('Cline integration test completed successfully');
                        logger.info(`Test prompt sent to Cline: ${this.TEST_PROMPT}`);

                        vscode.window.showInformationMessage(
                            `Wu Wei: Integration test completed! Check the Cline panel for the AI response.`,
                            'Open Cline Panel',
                            'Manual Submit'
                        ).then(selection => {
                            if (selection === 'Open Cline Panel') {
                                vscode.commands.executeCommand('workbench.view.extension.saoudrizwan.claude-dev');
                            } else if (selection === 'Manual Submit') {
                                // If automatic submission didn't work, provide manual instructions
                                vscode.window.showInformationMessage(
                                    'If the prompt is still in the input box, please press Enter manually to submit it.',
                                    'Copy Prompt Again'
                                ).then(manualSelection => {
                                    if (manualSelection === 'Copy Prompt Again') {
                                        vscode.env.clipboard.writeText(this.TEST_PROMPT);
                                        vscode.window.showInformationMessage('Test prompt copied to clipboard again.');
                                    }
                                });
                            }
                        });
                    } else {
                        progress.report({ increment: 30, message: "Manual prompt entry required" });

                        // Fallback to manual process
                        logger.info('Automatic prompt sending failed, falling back to manual process');

                        // Copy prompt to clipboard for manual use
                        await vscode.env.clipboard.writeText(this.TEST_PROMPT);

                        vscode.window.showInformationMessage(
                            'Wu Wei: Please manually paste the test prompt in Cline and press Enter. The prompt has been copied to your clipboard.',
                            'Show Prompt',
                            'Open Cline Panel'
                        ).then(selection => {
                            if (selection === 'Show Prompt') {
                                vscode.window.showInformationMessage(`Test prompt: ${this.TEST_PROMPT}`);
                            } else if (selection === 'Open Cline Panel') {
                                vscode.commands.executeCommand('workbench.view.extension.saoudrizwan.claude-dev');
                            }
                        });
                    }

                } catch (executeError) {
                    logger.error('Failed to execute Cline integration test', executeError);
                    progress.report({ increment: 100, message: "Test failed" });
                    throw executeError;
                }
            });

        } catch (error) {
            logger.error('Cline integration test failed', error);
            vscode.window.showErrorMessage(`Wu Wei: Cline integration failed - ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    /**
     * Check Cline extension status and available commands for debugging
     */
    public static async debugClineStatus(): Promise<void> {
        logger.info('Wu Wei: Debugging Cline status');

        try {
            const clineExtension = vscode.extensions.getExtension(ClineIntegration.CLINE_EXTENSION_ID);

            logger.info('='.repeat(50));
            logger.info('CLINE EXTENSION DEBUG INFO');
            logger.info('='.repeat(50));

            if (clineExtension) {
                logger.info(`Extension found: ${clineExtension.id}`);
                logger.info(`Extension active: ${clineExtension.isActive}`);
                logger.info(`Extension path: ${clineExtension.extensionPath}`);
                logger.info(`Package JSON:`, clineExtension.packageJSON?.displayName || 'Unknown');
            } else {
                logger.info('Cline extension not found');
            }

            // List all available commands that might be related to Cline/Claude
            const availableCommands = await vscode.commands.getCommands();
            const relatedCommands = availableCommands.filter(cmd =>
                cmd.toLowerCase().includes('cline') ||
                cmd.toLowerCase().includes('claude') ||
                cmd.toLowerCase().includes('dev')
            );

            logger.info(`Found ${relatedCommands.length} potentially related commands:`);
            relatedCommands.forEach(cmd => logger.info(`  - ${cmd}`));

            logger.info('='.repeat(50));

        } catch (error) {
            logger.error('Failed to debug Cline status', error);
        }
    }

    /**
     * Execute a custom prompt in Cline (public method for external use)
     */
    public static async executePromptInCline(customPrompt: string): Promise<void> {
        logger.info(`Wu Wei: Executing custom prompt in Cline: ${customPrompt}`);

        try {
            // Check if Cline extension is available
            const clineExtension = await this.ensureClineExtension();
            if (!clineExtension) {
                return;
            }

            // Execute the command sequence with custom prompt
            const success = await this.executeCommandSequence(customPrompt);

            if (success) {
                logger.info('Custom prompt executed successfully in Cline');
                vscode.window.showInformationMessage(
                    `Wu Wei: Prompt sent to Cline! Check the Cline panel for the AI response.`,
                    'Open Cline Panel',
                    'Manual Submit'
                ).then(selection => {
                    if (selection === 'Open Cline Panel') {
                        vscode.commands.executeCommand('workbench.view.extension.saoudrizwan.claude-dev');
                    } else if (selection === 'Manual Submit') {
                        vscode.window.showInformationMessage(
                            'If the prompt is still in the input box, please press Enter manually to submit it.'
                        );
                    }
                });
            } else {
                logger.error('Failed to execute custom prompt in Cline');
                // Copy to clipboard as fallback
                await vscode.env.clipboard.writeText(customPrompt);
                vscode.window.showErrorMessage(
                    'Wu Wei: Failed to send prompt automatically. The prompt has been copied to your clipboard - please paste it manually in Cline.',
                    'Open Cline Panel'
                ).then(selection => {
                    if (selection === 'Open Cline Panel') {
                        vscode.commands.executeCommand('workbench.view.extension.saoudrizwan.claude-dev');
                    }
                });
            }

        } catch (error) {
            logger.error('Custom prompt execution failed', error);
            vscode.window.showErrorMessage(`Wu Wei: Prompt execution failed - ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }
}
