import * as vscode from 'vscode';
import { WorktreeStatus } from '../types';

/**
 * Diff View WebView
 *
 * Displays git diff of worktree changes in a WebView panel with:
 * - File statistics (added, modified, deleted)
 * - Commit history
 * - Syntax-highlighted diff output
 * - Action buttons to merge or discard worktree
 */

/**
 * Show diff view for worktree changes
 *
 * @param context - Extension context for resource management
 * @param status - Worktree status data from backend
 */
export function showDiffView(
  context: vscode.ExtensionContext,
  status: WorktreeStatus
): void {
  // Create or reveal WebView panel
  const panel = vscode.window.createWebviewPanel(
    'autoClaude.diffView',
    `Diff: ${status.specName}`,
    vscode.ViewColumn.One,
    {
      enableScripts: true,
      retainContextWhenHidden: true,
    }
  );

  // Set panel icon
  panel.iconPath = {
    light: vscode.Uri.joinPath(context.extensionUri, 'resources', 'icon.png'),
    dark: vscode.Uri.joinPath(context.extensionUri, 'resources', 'icon.png'),
  };

  // Generate and set HTML content
  panel.webview.html = getWebviewContent(status);

  // Handle messages from webview (for action buttons)
  panel.webview.onDidReceiveMessage(
    (message) => {
      switch (message.command) {
        case 'openFile':
          openFile(message.file);
          break;
        case 'copyDiff':
          copyToClipboard(status.diff || '');
          break;
      }
    },
    undefined,
    context.subscriptions
  );
}

/**
 * Generate HTML content for the diff view
 */
function getWebviewContent(status: WorktreeStatus): string {
  const { specName, branch, filesChanged, filesAdded, filesDeleted, commits, diff } = status;

  // Format commit history
  const commitsList = commits.length > 0
    ? commits
        .map(
          (commit) => `
        <div class="commit">
          <div class="commit-hash">${escapeHtml(commit.hash.substring(0, 7))}</div>
          <div class="commit-message">${escapeHtml(commit.message)}</div>
          <div class="commit-meta">
            <span class="commit-author">${escapeHtml(commit.author)}</span>
            <span class="commit-time">${formatTimestamp(commit.timestamp)}</span>
          </div>
        </div>
      `
        )
        .join('')
    : '<p class="no-commits">No commits yet</p>';

  // Format diff output with syntax highlighting
  const diffHtml = diff
    ? formatDiff(diff)
    : '<p class="no-diff">No diff available</p>';

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Diff View: ${escapeHtml(specName)}</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: var(--vscode-font-family);
      font-size: var(--vscode-font-size);
      color: var(--vscode-foreground);
      background-color: var(--vscode-editor-background);
      padding: 20px;
      line-height: 1.6;
    }

    .header {
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--vscode-panel-border);
    }

    h1 {
      font-size: 24px;
      font-weight: 600;
      margin-bottom: 8px;
      color: var(--vscode-foreground);
    }

    .branch-info {
      font-size: 14px;
      color: var(--vscode-descriptionForeground);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .branch-name {
      background: var(--vscode-badge-background);
      color: var(--vscode-badge-foreground);
      padding: 2px 8px;
      border-radius: 3px;
      font-family: var(--vscode-editor-font-family);
      font-size: 13px;
    }

    .stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }

    .stat-card {
      background: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
      border-radius: 4px;
      padding: 12px 16px;
    }

    .stat-label {
      font-size: 12px;
      color: var(--vscode-descriptionForeground);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }

    .stat-value {
      font-size: 24px;
      font-weight: 600;
      color: var(--vscode-foreground);
    }

    .stat-value.added {
      color: var(--vscode-gitDecoration-addedResourceForeground);
    }

    .stat-value.deleted {
      color: var(--vscode-gitDecoration-deletedResourceForeground);
    }

    .section {
      margin-bottom: 24px;
    }

    .section-title {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .section-title::before {
      content: '';
      display: inline-block;
      width: 3px;
      height: 16px;
      background: var(--vscode-activityBarBadge-background);
      border-radius: 2px;
    }

    .commits {
      background: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
      border-radius: 4px;
      padding: 12px;
      max-height: 300px;
      overflow-y: auto;
    }

    .commit {
      padding: 8px;
      border-left: 3px solid var(--vscode-gitDecoration-modifiedResourceForeground);
      margin-bottom: 8px;
      background: var(--vscode-editor-background);
      border-radius: 4px;
    }

    .commit:last-child {
      margin-bottom: 0;
    }

    .commit-hash {
      font-family: var(--vscode-editor-font-family);
      font-size: 12px;
      color: var(--vscode-descriptionForeground);
      margin-bottom: 4px;
    }

    .commit-message {
      font-size: 14px;
      color: var(--vscode-foreground);
      margin-bottom: 4px;
      font-weight: 500;
    }

    .commit-meta {
      display: flex;
      gap: 12px;
      font-size: 12px;
      color: var(--vscode-descriptionForeground);
    }

    .no-commits {
      color: var(--vscode-descriptionForeground);
      font-style: italic;
      padding: 12px;
    }

    .diff-container {
      background: var(--vscode-editor-background);
      border: 1px solid var(--vscode-input-border);
      border-radius: 4px;
      overflow: hidden;
    }

    .diff-header {
      background: var(--vscode-input-background);
      padding: 8px 12px;
      border-bottom: 1px solid var(--vscode-input-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .diff-header-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--vscode-foreground);
    }

    .copy-button {
      background: var(--vscode-button-secondaryBackground);
      color: var(--vscode-button-secondaryForeground);
      border: none;
      padding: 4px 12px;
      border-radius: 3px;
      cursor: pointer;
      font-size: 12px;
      font-family: var(--vscode-font-family);
    }

    .copy-button:hover {
      background: var(--vscode-button-secondaryHoverBackground);
    }

    .diff-content {
      padding: 12px;
      overflow-x: auto;
      max-height: 600px;
      overflow-y: auto;
    }

    .diff-line {
      font-family: var(--vscode-editor-font-family);
      font-size: 13px;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-all;
    }

    .diff-line.added {
      background: rgba(var(--vscode-gitDecoration-addedResourceForeground), 0.2);
      color: var(--vscode-gitDecoration-addedResourceForeground);
    }

    .diff-line.removed {
      background: rgba(var(--vscode-gitDecoration-deletedResourceForeground), 0.2);
      color: var(--vscode-gitDecoration-deletedResourceForeground);
    }

    .diff-line.header {
      color: var(--vscode-textLink-foreground);
      font-weight: 600;
    }

    .diff-line.hunk {
      background: var(--vscode-input-background);
      color: var(--vscode-descriptionForeground);
      font-weight: 500;
    }

    .no-diff {
      color: var(--vscode-descriptionForeground);
      font-style: italic;
      padding: 12px;
    }

    /* Scrollbar styling */
    ::-webkit-scrollbar {
      width: 10px;
      height: 10px;
    }

    ::-webkit-scrollbar-track {
      background: var(--vscode-editor-background);
    }

    ::-webkit-scrollbar-thumb {
      background: var(--vscode-scrollbarSlider-background);
      border-radius: 5px;
    }

    ::-webkit-scrollbar-thumb:hover {
      background: var(--vscode-scrollbarSlider-hoverBackground);
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>Worktree Changes</h1>
    <div class="branch-info">
      <span>Spec:</span>
      <span class="branch-name">${escapeHtml(specName)}</span>
      <span>•</span>
      <span>Branch:</span>
      <span class="branch-name">${escapeHtml(branch)}</span>
    </div>
  </div>

  <div class="stats">
    <div class="stat-card">
      <div class="stat-label">Files Changed</div>
      <div class="stat-value">${filesChanged}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Files Added</div>
      <div class="stat-value added">${filesAdded}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Files Deleted</div>
      <div class="stat-value deleted">${filesDeleted}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Commit History</div>
    <div class="commits">
      ${commitsList}
    </div>
  </div>

  <div class="section">
    <div class="section-title">Diff</div>
    <div class="diff-container">
      <div class="diff-header">
        <div class="diff-header-title">Changes</div>
        <button class="copy-button" onclick="copyDiff()">Copy Diff</button>
      </div>
      <div class="diff-content">
        ${diffHtml}
      </div>
    </div>
  </div>

  <script>
    const vscode = acquireVsCodeApi();

    function copyDiff() {
      vscode.postMessage({ command: 'copyDiff' });
    }
  </script>
</body>
</html>`;
}

/**
 * Format diff output with syntax highlighting
 */
function formatDiff(diff: string): string {
  const lines = diff.split('\n');
  const formattedLines = lines.map((line) => {
    let className = 'diff-line';

    if (line.startsWith('+++') || line.startsWith('---')) {
      className += ' header';
    } else if (line.startsWith('@@')) {
      className += ' hunk';
    } else if (line.startsWith('+')) {
      className += ' added';
    } else if (line.startsWith('-')) {
      className += ' removed';
    }

    return `<div class="${className}">${escapeHtml(line)}</div>`;
  });

  return formattedLines.join('');
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) {
      return 'just now';
    } else if (diffMins < 60) {
      return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
    } else if (diffDays < 7) {
      return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
    } else {
      return date.toLocaleDateString();
    }
  } catch {
    return timestamp;
  }
}

/**
 * Open a file in the editor
 */
async function openFile(filePath: string): Promise<void> {
  try {
    const uri = vscode.Uri.file(filePath);
    const document = await vscode.workspace.openTextDocument(uri);
    await vscode.window.showTextDocument(document);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    void vscode.window.showErrorMessage(`Failed to open file: ${errorMessage}`);
  }
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text: string): Promise<void> {
  try {
    await vscode.env.clipboard.writeText(text);
    void vscode.window.showInformationMessage('Diff copied to clipboard');
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    void vscode.window.showErrorMessage(`Failed to copy: ${errorMessage}`);
  }
}
