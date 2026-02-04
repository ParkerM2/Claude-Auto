import * as vscode from 'vscode';

/**
 * Extension activation function
 * Called when the extension is activated (first command execution or view opened)
 */
export function activate(context: vscode.ExtensionContext): void {
    // Log extension activation
    const startTime = Date.now();

    // Register disposables for cleanup on deactivation
    const disposables: vscode.Disposable[] = [];

    // TODO: Register commands (will be implemented in phase 4)
    // TODO: Register tree data providers (will be implemented in phase 3)
    // TODO: Initialize backend CLI client (will be implemented in phase 2)

    // Add all disposables to context subscriptions for automatic cleanup
    context.subscriptions.push(...disposables);

    const activationTime = Date.now() - startTime;
    void vscode.window.showInformationMessage(
        `Auto Claude extension activated in ${activationTime}ms`
    );
}

/**
 * Extension deactivation function
 * Called when the extension is deactivated (VS Code shutdown or extension reload)
 */
export function deactivate(): void {
    // Cleanup will be handled automatically by disposing context.subscriptions
    // Additional cleanup can be added here if needed (e.g., killing processes, closing connections)
}
