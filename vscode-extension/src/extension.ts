import * as vscode from 'vscode';
import { ChatViewProvider } from './chatViewProvider';

export function activate(context: vscode.ExtensionContext) {
    const provider = new ChatViewProvider(context);

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('codeAgent.chatView', provider)
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codeAgent.openChat', () => {
            vscode.commands.executeCommand('codeAgent.chatView.focus');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codeAgent.clearChat', () => {
            provider.clearChat();
        })
    );
}

export function deactivate() {}
