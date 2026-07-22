"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const chatViewProvider_1 = require("./chatViewProvider");
function activate(context) {
    const provider = new chatViewProvider_1.ChatViewProvider(context);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider('codeAgent.chatView', provider));
    context.subscriptions.push(vscode.commands.registerCommand('codeAgent.openChat', () => {
        vscode.commands.executeCommand('codeAgent.chatView.focus');
    }));
    context.subscriptions.push(vscode.commands.registerCommand('codeAgent.clearChat', () => {
        provider.clearChat();
    }));
}
function deactivate() { }
//# sourceMappingURL=extension.js.map