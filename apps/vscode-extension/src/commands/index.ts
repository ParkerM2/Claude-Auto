import * as vscode from 'vscode';
import { CLIClient } from '../backend/cli-client';
import { SpecListItem } from '../types';
import { createSpecCommand, createSpecFromSelectionCommand } from './create-spec';

/**
 * Command Handlers Module
 *
 * Centralizes all VS Code command registrations for Auto Claude extension.
 * This module exports a single registerCommands function that sets up all
 * command palette commands and their handlers.
 */

/**
 * Register all Auto Claude commands with VS Code
 *
 * @param context - Extension context for subscriptions
 * @param cliClient - Backend CLI client for command execution
 * @returns Array of disposables for command registrations
 */
export function registerCommands(
  context: vscode.ExtensionContext,
  cliClient: CLIClient
): vscode.Disposable[] {
  const disposables: vscode.Disposable[] = [];

  // Command: Create Spec
  disposables.push(
    vscode.commands.registerCommand('autoClaude.createSpec', async () => {
      await createSpecCommand(cliClient);
    })
  );

  // Command: Create Spec from Selection (explicit variant)
  disposables.push(
    vscode.commands.registerCommand('autoClaude.createSpecFromSelection', async () => {
      await createSpecFromSelectionCommand(cliClient);
    })
  );

  // Command: Run Spec
  disposables.push(
    vscode.commands.registerCommand('autoClaude.runSpec', async () => {
      await handleRunSpec(cliClient);
    })
  );

  // Command: Review Changes
  disposables.push(
    vscode.commands.registerCommand('autoClaude.reviewChanges', async () => {
      await handleReviewChanges(cliClient);
    })
  );

  // Command: Merge Worktree
  disposables.push(
    vscode.commands.registerCommand('autoClaude.mergeWorktree', async () => {
      await handleMergeWorktree(cliClient);
    })
  );

  // Command: Discard Worktree
  disposables.push(
    vscode.commands.registerCommand('autoClaude.discardWorktree', async () => {
      await handleDiscardWorktree(cliClient);
    })
  );

  // Command: View QA Report
  disposables.push(
    vscode.commands.registerCommand('autoClaude.viewQAReport', async () => {
      await handleViewQAReport(cliClient);
    })
  );

  return disposables;
}


/**
 * Handle Run Spec command
 * Prompts user to select a spec and runs it
 */
async function handleRunSpec(cliClient: CLIClient): Promise<void> {
  try {
    // Get list of available specs
    const specs = await cliClient.listSpecs();

    if (specs.length === 0) {
      void vscode.window.showInformationMessage('No specs found. Create a spec first.');
      return;
    }

    // Show quick pick for spec selection
    const selectedSpec = await vscode.window.showQuickPick(
      specs.map((spec: SpecListItem) => ({
        label: spec.name,
        description: `Status: ${spec.status}`,
        detail: `ID: ${spec.id} | QA: ${spec.qaStatus || 'N/A'}`,
        spec,
      })),
      {
        placeHolder: 'Select a spec to run',
        matchOnDescription: true,
        matchOnDetail: true,
      }
    );

    if (!selectedSpec) {
      return; // User cancelled
    }

    // Confirm before running
    const confirmation = await vscode.window.showWarningMessage(
      `Run spec "${selectedSpec.spec.name}"? This will start an autonomous build.`,
      { modal: true },
      'Run',
      'Cancel'
    );

    if (confirmation !== 'Run') {
      return;
    }

    // Run the spec
    await cliClient.runSpec(selectedSpec.spec.id);
    void vscode.window.showInformationMessage(
      `Started build for spec: ${selectedSpec.spec.name}`
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    void vscode.window.showErrorMessage(`Failed to run spec: ${errorMessage}`);
  }
}

/**
 * Handle Review Changes command
 * Opens diff view for worktree changes
 */
async function handleReviewChanges(cliClient: CLIClient): Promise<void> {
  try {
    const spec = await selectSpec(cliClient, 'Select a spec to review');
    if (!spec) {
      return;
    }

    // Get worktree status
    const status = await cliClient.reviewWorktree(spec.id);

    if (!status.exists) {
      void vscode.window.showWarningMessage(
        `No worktree found for spec "${spec.name}"`
      );
      return;
    }

    if (!status.hasChanges) {
      void vscode.window.showInformationMessage(
        `No changes to review for spec "${spec.name}"`
      );
      return;
    }

    // TODO: Open diff view WebView (will be implemented in phase 5)
    void vscode.window.showInformationMessage(
      `Review changes for spec "${spec.name}": ${status.filesChanged} files changed`
    );
    cliClient.showOutput();
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    void vscode.window.showErrorMessage(`Failed to review changes: ${errorMessage}`);
  }
}

/**
 * Handle Merge Worktree command
 * Merges worktree changes into main branch
 */
async function handleMergeWorktree(cliClient: CLIClient): Promise<void> {
  try {
    const spec = await selectSpec(cliClient, 'Select a spec to merge');
    if (!spec) {
      return;
    }

    // Confirm before merging
    const confirmation = await vscode.window.showWarningMessage(
      `Merge worktree for spec "${spec.name}" into main branch? This action cannot be undone.`,
      { modal: true },
      'Merge',
      'Cancel'
    );

    if (confirmation !== 'Merge') {
      return;
    }

    // Merge the worktree
    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: `Merging worktree for ${spec.name}...`,
        cancellable: false,
      },
      async () => {
        await cliClient.mergeWorktree(spec.id);
        void vscode.window.showInformationMessage(
          `Successfully merged worktree for spec "${spec.name}"`
        );
      }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    void vscode.window.showErrorMessage(`Failed to merge worktree: ${errorMessage}`);
  }
}

/**
 * Handle Discard Worktree command
 * Discards worktree and all changes
 */
async function handleDiscardWorktree(cliClient: CLIClient): Promise<void> {
  try {
    const spec = await selectSpec(cliClient, 'Select a spec to discard');
    if (!spec) {
      return;
    }

    // Strong confirmation before discarding
    const confirmation = await vscode.window.showWarningMessage(
      `Discard worktree for spec "${spec.name}"? All changes will be permanently lost. This action cannot be undone.`,
      { modal: true },
      'Discard',
      'Cancel'
    );

    if (confirmation !== 'Discard') {
      return;
    }

    // Discard the worktree
    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: `Discarding worktree for ${spec.name}...`,
        cancellable: false,
      },
      async () => {
        await cliClient.discardWorktree(spec.id);
        void vscode.window.showInformationMessage(
          `Successfully discarded worktree for spec "${spec.name}"`
        );
      }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    void vscode.window.showErrorMessage(`Failed to discard worktree: ${errorMessage}`);
  }
}

/**
 * Handle View QA Report command
 * Opens QA report in WebView
 */
async function handleViewQAReport(cliClient: CLIClient): Promise<void> {
  try {
    const spec = await selectSpec(cliClient, 'Select a spec to view QA report');
    if (!spec) {
      return;
    }

    // Get QA status
    const qaReport = await cliClient.getQAStatus(spec.id);

    if (qaReport.status === 'not_started') {
      void vscode.window.showInformationMessage(
        `No QA report available for spec "${spec.name}". Run QA first.`
      );
      return;
    }

    // TODO: Open QA report WebView (will be implemented in phase 5)
    void vscode.window.showInformationMessage(
      `QA Report for "${spec.name}": Status = ${qaReport.status}`
    );
    cliClient.showOutput();
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    void vscode.window.showErrorMessage(`Failed to view QA report: ${errorMessage}`);
  }
}

/**
 * Helper: Select a spec from a quick pick menu
 *
 * @param cliClient - CLI client to fetch specs
 * @param placeholder - Placeholder text for quick pick
 * @returns Selected spec or undefined if cancelled
 */
async function selectSpec(
  cliClient: CLIClient,
  placeholder: string
): Promise<SpecListItem | undefined> {
  const specs = await cliClient.listSpecs();

  if (specs.length === 0) {
    void vscode.window.showInformationMessage('No specs found.');
    return undefined;
  }

  const selected = await vscode.window.showQuickPick(
    specs.map((spec: SpecListItem) => ({
      label: spec.name,
      description: `Status: ${spec.status}`,
      detail: `ID: ${spec.id} | Worktree: ${spec.hasWorktree ? 'Yes' : 'No'}`,
      spec,
    })),
    {
      placeHolder: placeholder,
      matchOnDescription: true,
      matchOnDetail: true,
    }
  );

  return selected?.spec;
}
