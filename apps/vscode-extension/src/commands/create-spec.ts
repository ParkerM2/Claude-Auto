import * as vscode from 'vscode';
import * as path from 'path';
import { CLIClient } from '../backend/cli-client';

/**
 * Create Spec Command Handler
 *
 * Handles the 'Auto Claude: Create Spec' command which allows users to create
 * a new spec from selected code, current file, or manual input.
 */

/**
 * Context information extracted from the editor
 */
interface EditorContext {
  filePath?: string;
  selectedText?: string;
  hasSelection: boolean;
  language?: string;
}

/**
 * Extract context from the active editor
 *
 * @returns Editor context or undefined if no active editor
 */
function getEditorContext(): EditorContext | undefined {
  const editor = vscode.window.activeTextEditor;

  if (!editor) {
    return undefined;
  }

  const selection = editor.selection;
  const selectedText = editor.document.getText(selection);
  const hasSelection = !selection.isEmpty;

  return {
    filePath: editor.document.fileName,
    selectedText: hasSelection ? selectedText : undefined,
    hasSelection,
    language: editor.document.languageId,
  };
}

/**
 * Format context information for the backend
 *
 * @param context - Editor context
 * @param taskDescription - User's task description
 * @returns Formatted context string
 */
function formatContextForBackend(
  context: EditorContext,
  taskDescription: string
): string {
  const lines: string[] = [];

  lines.push(`Task: ${taskDescription}`);
  lines.push('');

  if (context.filePath) {
    lines.push(`File: ${context.filePath}`);
    if (context.language) {
      lines.push(`Language: ${context.language}`);
    }
  }

  if (context.hasSelection && context.selectedText) {
    lines.push('');
    lines.push('Selected Code:');
    lines.push('```');
    lines.push(context.selectedText);
    lines.push('```');
  }

  return lines.join('\n');
}

/**
 * Create a temporary context file for the backend
 *
 * @param context - Editor context
 * @param taskDescription - User's task description
 * @returns Path to the temporary context file
 */
async function createContextFile(
  context: EditorContext,
  taskDescription: string
): Promise<string> {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (!workspaceFolder) {
    throw new Error('No workspace folder found');
  }

  // Create a temporary file in the workspace
  const tempDir = path.join(workspaceFolder.uri.fsPath, '.auto-claude', 'tmp');
  const tempFile = path.join(tempDir, `spec-context-${Date.now()}.txt`);

  // Ensure temp directory exists
  const fs = await import('fs');
  await fs.promises.mkdir(tempDir, { recursive: true });

  // Write context to file
  const contextContent = formatContextForBackend(context, taskDescription);
  await fs.promises.writeFile(tempFile, contextContent, 'utf8');

  return tempFile;
}

/**
 * Main handler for the Create Spec command
 *
 * Prompts the user for a task description and creates a spec using the backend CLI.
 * If code is selected, it's included in the spec context.
 *
 * @param cliClient - Backend CLI client for invoking spec creation
 */
export async function createSpecCommand(cliClient: CLIClient): Promise<void> {
  try {
    // Get editor context (if available)
    const context = getEditorContext();

    // Determine prompt based on context
    let promptText = 'Describe the task or feature to create a spec for';
    let placeholder = 'e.g., Add authentication to the application';

    if (context?.hasSelection) {
      promptText = 'Describe what you want to do with the selected code';
      placeholder = 'e.g., Refactor this component to use React hooks';
    } else if (context?.filePath) {
      const fileName = path.basename(context.filePath);
      promptText = `Describe the task related to ${fileName}`;
      placeholder = 'e.g., Add error handling to this file';
    }

    // Prompt user for task description
    const taskDescription = await vscode.window.showInputBox({
      prompt: promptText,
      placeHolder: placeholder,
      validateInput: (value) => {
        return value.trim().length > 0 ? null : 'Task description cannot be empty';
      },
    });

    if (!taskDescription) {
      return; // User cancelled
    }

    // Show progress notification
    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: 'Creating spec...',
        cancellable: false,
      },
      async (progress) => {
        try {
          progress.report({ message: 'Preparing context...' });

          // Create context file if we have editor context
          let contextFile: string | undefined;
          if (context) {
            contextFile = await createContextFile(context, taskDescription);
          }

          progress.report({ message: 'Running spec creation...' });

          // Invoke backend spec creation
          const specId = await cliClient.createSpec(taskDescription, {
            contextFile,
          });

          progress.report({ message: 'Spec created successfully' });

          // Show success message with action to view specs
          const action = await vscode.window.showInformationMessage(
            `Spec created successfully: ${specId}`,
            'View Specs',
            'Run Spec'
          );

          if (action === 'View Specs') {
            // Refresh task tree to show new spec
            await vscode.commands.executeCommand('autoClaude.refreshTasks');
          } else if (action === 'Run Spec') {
            // Immediately run the newly created spec
            await vscode.commands.executeCommand('autoClaude.runSpec');
          }

          // Clean up context file if created
          if (contextFile) {
            const fs = await import('fs');
            await fs.promises.unlink(contextFile).catch(() => {
              // Ignore cleanup errors
            });
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          throw new Error(`Spec creation failed: ${errorMessage}`);
        }
      }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    void vscode.window.showErrorMessage(`Failed to create spec: ${errorMessage}`);
    cliClient.showOutput();
  }
}

/**
 * Create Spec from Selection Command Handler
 *
 * A variant that requires code to be selected. More explicit about the intent.
 *
 * @param cliClient - Backend CLI client
 */
export async function createSpecFromSelectionCommand(cliClient: CLIClient): Promise<void> {
  const context = getEditorContext();

  if (!context) {
    void vscode.window.showErrorMessage('No active editor found');
    return;
  }

  if (!context.hasSelection) {
    void vscode.window.showWarningMessage(
      'No code selected. Please select code to create a spec from.'
    );
    return;
  }

  // Proceed with normal spec creation flow
  await createSpecCommand(cliClient);
}
