import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
  let disposable = vscode.commands.registerCommand('aiAutoContinue.helloWorld', () => {
    vscode.window.showInformationMessage('Hello from AI Auto Continue Extension!');
  });
  context.subscriptions.push(disposable);
}

export function deactivate() {}
