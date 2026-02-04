import * as vscode from 'vscode';
import { CLIClient } from './backend/cli-client';
import { TaskTreeProvider } from './views/task-tree-provider';
import { ProgressView } from './views/progress-view';
import { registerCommands } from './commands';

/**
 * Extension activation function
 * Called when the extension is activated (first command execution or view opened)
 */
export function activate(context: vscode.ExtensionContext): void {
    // Log extension activation
    const startTime = Date.now();

    // Initialize backend CLI client
    const cliClient = new CLIClient();

    // Initialize task tree provider for sidebar
    const taskTreeProvider = new TaskTreeProvider(cliClient);
    const treeView = vscode.window.createTreeView('autoClaude.taskTree', {
        treeDataProvider: taskTreeProvider,
        showCollapseAll: true,
    });

    // Initialize progress view for real-time updates
    const progressView = new ProgressView(cliClient);

    // Register command to show CLI output channel
    const showOutputCommand = vscode.commands.registerCommand(
        'autoClaude.showOutput',
        () => {
            cliClient.showOutput();
        }
    );

    // Register command to refresh task tree
    const refreshTasksCommand = vscode.commands.registerCommand(
        'autoClaude.refreshTasks',
        () => {
            taskTreeProvider.refresh();
        }
    );

    // Register all command palette commands (Phase 4)
    const commandDisposables = registerCommands(context, cliClient);

    // Add all disposables to context subscriptions for automatic cleanup
    context.subscriptions.push(
        cliClient,
        taskTreeProvider,
        progressView,
        treeView,
        showOutputCommand,
        refreshTasksCommand,
        ...commandDisposables
    );

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
