import * as vscode from 'vscode';
import { CLIClient } from '../backend/cli-client';
import { createSpecCommand, createSpecFromSelectionCommand } from './create-spec';
import {
  runSpecCommand,
  reviewChangesCommand,
  mergeWorktreeCommand,
  discardWorktreeCommand,
  viewQAReportCommand,
} from './workspace';

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
      await runSpecCommand(cliClient);
    })
  );

  // Command: Review Changes
  disposables.push(
    vscode.commands.registerCommand('autoClaude.reviewChanges', async () => {
      await reviewChangesCommand(cliClient);
    })
  );

  // Command: Merge Worktree
  disposables.push(
    vscode.commands.registerCommand('autoClaude.mergeWorktree', async () => {
      await mergeWorktreeCommand(cliClient);
    })
  );

  // Command: Discard Worktree
  disposables.push(
    vscode.commands.registerCommand('autoClaude.discardWorktree', async () => {
      await discardWorktreeCommand(cliClient);
    })
  );

  // Command: View QA Report
  disposables.push(
    vscode.commands.registerCommand('autoClaude.viewQAReport', async () => {
      await viewQAReportCommand(cliClient);
    })
  );

  return disposables;
}
