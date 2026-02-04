import * as vscode from 'vscode';
import { QAReport } from '../types';

/**
 * QA Report WebView
 *
 * Displays QA validation results in a WebView panel with:
 * - Overall pass/fail status with visual indicators
 * - Acceptance criteria with individual pass/fail status
 * - Issues list organized by severity (critical, major, minor)
 * - Test results breakdown (unit, integration, e2e)
 * - Summary and recommendations
 */

/**
 * Show QA report view for validation results
 *
 * @param context - Extension context for resource management
 * @param report - QA report data from backend
 */
export function showQAReport(
  context: vscode.ExtensionContext,
  report: QAReport
): void {
  // Create or reveal WebView panel
  const panel = vscode.window.createWebviewPanel(
    'autoClaude.qaReport',
    `QA Report: ${report.specName}`,
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
  panel.webview.html = getWebviewContent(report);

  // Handle messages from webview (for action buttons)
  panel.webview.onDidReceiveMessage(
    (message) => {
      switch (message.command) {
        case 'copyReport':
          copyToClipboard(formatReportAsText(report));
          break;
        case 'openIssue':
          if (message.location) {
            openFile(message.location);
          }
          break;
      }
    },
    undefined,
    context.subscriptions
  );
}

/**
 * Generate HTML content for the QA report view
 */
function getWebviewContent(report: QAReport): string {
  const { specName, status, timestamp, acceptanceCriteria, issues, testResults, summary } = report;

  // Determine status color and icon
  const statusInfo = getStatusInfo(status);

  // Format acceptance criteria
  const criteriaHtml = acceptanceCriteria.length > 0
    ? acceptanceCriteria
        .map(
          (criterion) => `
        <div class="criterion ${criterion.status}">
          <div class="criterion-header">
            <span class="criterion-icon">${getCriterionIcon(criterion.status)}</span>
            <span class="criterion-text">${escapeHtml(criterion.criterion)}</span>
          </div>
          ${criterion.details ? `<div class="criterion-details">${escapeHtml(criterion.details)}</div>` : ''}
        </div>
      `
        )
        .join('')
    : '<p class="no-data">No acceptance criteria defined</p>';

  // Format issues by severity
  const issuesHtml = issues.length > 0
    ? formatIssuesBySeverity(issues)
    : '<p class="no-data">No issues found</p>';

  // Format test results
  const testResultsHtml = testResults ? formatTestResults(testResults) : '';

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>QA Report: ${escapeHtml(specName)}</title>
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

    .spec-info {
      font-size: 14px;
      color: var(--vscode-descriptionForeground);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .spec-name {
      background: var(--vscode-badge-background);
      color: var(--vscode-badge-foreground);
      padding: 2px 8px;
      border-radius: 3px;
      font-family: var(--vscode-editor-font-family);
      font-size: 13px;
    }

    .status-banner {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px;
      border-radius: 6px;
      margin-bottom: 24px;
      font-size: 16px;
      font-weight: 600;
    }

    .status-banner.passed {
      background: rgba(var(--vscode-testing-iconPassed), 0.15);
      color: var(--vscode-testing-iconPassed);
      border-left: 4px solid var(--vscode-testing-iconPassed);
    }

    .status-banner.failed {
      background: rgba(var(--vscode-testing-iconFailed), 0.15);
      color: var(--vscode-testing-iconFailed);
      border-left: 4px solid var(--vscode-testing-iconFailed);
    }

    .status-banner.rejected {
      background: rgba(var(--vscode-errorForeground), 0.15);
      color: var(--vscode-errorForeground);
      border-left: 4px solid var(--vscode-errorForeground);
    }

    .status-banner.in_progress {
      background: rgba(var(--vscode-progressBar-background), 0.15);
      color: var(--vscode-progressBar-background);
      border-left: 4px solid var(--vscode-progressBar-background);
    }

    .status-icon {
      font-size: 24px;
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

    .criteria-container {
      background: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
      border-radius: 4px;
      padding: 12px;
    }

    .criterion {
      padding: 12px;
      margin-bottom: 8px;
      background: var(--vscode-editor-background);
      border-radius: 4px;
      border-left: 3px solid transparent;
    }

    .criterion:last-child {
      margin-bottom: 0;
    }

    .criterion.passed {
      border-left-color: var(--vscode-testing-iconPassed);
    }

    .criterion.failed {
      border-left-color: var(--vscode-testing-iconFailed);
    }

    .criterion.not_tested {
      border-left-color: var(--vscode-descriptionForeground);
    }

    .criterion-header {
      display: flex;
      align-items: flex-start;
      gap: 8px;
    }

    .criterion-icon {
      font-size: 16px;
      flex-shrink: 0;
      margin-top: 2px;
    }

    .criterion-text {
      font-size: 14px;
      color: var(--vscode-foreground);
      font-weight: 500;
      flex: 1;
    }

    .criterion-details {
      margin-top: 8px;
      margin-left: 24px;
      font-size: 13px;
      color: var(--vscode-descriptionForeground);
      padding: 8px;
      background: var(--vscode-input-background);
      border-radius: 3px;
    }

    .issues-container {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .severity-group {
      background: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
      border-radius: 4px;
      padding: 12px;
    }

    .severity-header {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .severity-badge {
      padding: 2px 8px;
      border-radius: 3px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .severity-badge.critical {
      background: var(--vscode-errorForeground);
      color: var(--vscode-editor-background);
    }

    .severity-badge.major {
      background: var(--vscode-editorWarning-foreground);
      color: var(--vscode-editor-background);
    }

    .severity-badge.minor {
      background: var(--vscode-editorInfo-foreground);
      color: var(--vscode-editor-background);
    }

    .issue {
      padding: 12px;
      margin-bottom: 8px;
      background: var(--vscode-editor-background);
      border-radius: 4px;
    }

    .issue:last-child {
      margin-bottom: 0;
    }

    .issue-description {
      font-size: 14px;
      color: var(--vscode-foreground);
      margin-bottom: 6px;
    }

    .issue-location {
      font-size: 12px;
      color: var(--vscode-descriptionForeground);
      font-family: var(--vscode-editor-font-family);
      margin-bottom: 6px;
      cursor: pointer;
    }

    .issue-location:hover {
      text-decoration: underline;
    }

    .issue-recommendation {
      font-size: 13px;
      color: var(--vscode-descriptionForeground);
      padding: 8px;
      background: var(--vscode-input-background);
      border-radius: 3px;
      border-left: 2px solid var(--vscode-activityBarBadge-background);
    }

    .test-results-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
    }

    .test-result-card {
      background: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
      border-radius: 4px;
      padding: 16px;
    }

    .test-type {
      font-size: 12px;
      color: var(--vscode-descriptionForeground);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 8px;
    }

    .test-stats {
      display: flex;
      gap: 16px;
    }

    .test-stat {
      display: flex;
      flex-direction: column;
    }

    .test-stat-label {
      font-size: 11px;
      color: var(--vscode-descriptionForeground);
      margin-bottom: 2px;
    }

    .test-stat-value {
      font-size: 20px;
      font-weight: 600;
    }

    .test-stat-value.passed {
      color: var(--vscode-testing-iconPassed);
    }

    .test-stat-value.failed {
      color: var(--vscode-testing-iconFailed);
    }

    .test-stat-value.skipped {
      color: var(--vscode-descriptionForeground);
    }

    .summary-container {
      background: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
      border-radius: 4px;
      padding: 16px;
    }

    .summary-text {
      font-size: 14px;
      color: var(--vscode-foreground);
      line-height: 1.6;
      white-space: pre-wrap;
    }

    .actions {
      display: flex;
      gap: 12px;
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid var(--vscode-panel-border);
    }

    .action-button {
      background: var(--vscode-button-background);
      color: var(--vscode-button-foreground);
      border: none;
      padding: 8px 16px;
      border-radius: 3px;
      cursor: pointer;
      font-size: 13px;
      font-family: var(--vscode-font-family);
      font-weight: 500;
    }

    .action-button:hover {
      background: var(--vscode-button-hoverBackground);
    }

    .action-button.secondary {
      background: var(--vscode-button-secondaryBackground);
      color: var(--vscode-button-secondaryForeground);
    }

    .action-button.secondary:hover {
      background: var(--vscode-button-secondaryHoverBackground);
    }

    .no-data {
      color: var(--vscode-descriptionForeground);
      font-style: italic;
      padding: 12px;
    }

    .timestamp {
      font-size: 12px;
      color: var(--vscode-descriptionForeground);
      margin-top: 4px;
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
    <h1>QA Validation Report</h1>
    <div class="spec-info">
      <span>Spec:</span>
      <span class="spec-name">${escapeHtml(specName)}</span>
    </div>
    <div class="timestamp">${formatTimestamp(timestamp)}</div>
  </div>

  <div class="status-banner ${status}">
    <span class="status-icon">${statusInfo.icon}</span>
    <span>${statusInfo.text}</span>
  </div>

  <div class="section">
    <div class="section-title">Acceptance Criteria</div>
    <div class="criteria-container">
      ${criteriaHtml}
    </div>
  </div>

  ${issues.length > 0 ? `
  <div class="section">
    <div class="section-title">Issues Found (${issues.length})</div>
    <div class="issues-container">
      ${issuesHtml}
    </div>
  </div>
  ` : ''}

  ${testResultsHtml}

  <div class="section">
    <div class="section-title">Summary</div>
    <div class="summary-container">
      <div class="summary-text">${escapeHtml(summary)}</div>
    </div>
  </div>

  <div class="actions">
    <button class="action-button" onclick="copyReport()">Copy Report</button>
  </div>

  <script>
    const vscode = acquireVsCodeApi();

    function copyReport() {
      vscode.postMessage({ command: 'copyReport' });
    }

    function openIssue(location) {
      vscode.postMessage({ command: 'openIssue', location: location });
    }
  </script>
</body>
</html>`;
}

/**
 * Get status information for display
 */
function getStatusInfo(status: string): { icon: string; text: string } {
  switch (status) {
    case 'passed':
      return { icon: '✓', text: 'All acceptance criteria passed' };
    case 'failed':
      return { icon: '✗', text: 'Some acceptance criteria failed' };
    case 'rejected':
      return { icon: '⚠', text: 'QA rejected - issues require fixes' };
    case 'in_progress':
      return { icon: '⟳', text: 'QA validation in progress' };
    default:
      return { icon: '●', text: 'QA not started' };
  }
}

/**
 * Get icon for criterion status
 */
function getCriterionIcon(status: string): string {
  switch (status) {
    case 'passed':
      return '✓';
    case 'failed':
      return '✗';
    case 'not_tested':
      return '○';
    default:
      return '○';
  }
}

/**
 * Format issues grouped by severity
 */
function formatIssuesBySeverity(issues: Array<{
  severity: 'critical' | 'major' | 'minor';
  description: string;
  location?: string;
  recommendation?: string;
}>): string {
  const grouped = {
    critical: issues.filter(i => i.severity === 'critical'),
    major: issues.filter(i => i.severity === 'major'),
    minor: issues.filter(i => i.severity === 'minor'),
  };

  const html: string[] = [];

  for (const [severity, items] of Object.entries(grouped)) {
    if (items.length === 0) {
      continue;
    }

    const issuesHtml = items
      .map(
        (issue) => `
        <div class="issue">
          <div class="issue-description">${escapeHtml(issue.description)}</div>
          ${issue.location ? `<div class="issue-location" onclick="openIssue('${escapeHtml(issue.location)}')">📍 ${escapeHtml(issue.location)}</div>` : ''}
          ${issue.recommendation ? `<div class="issue-recommendation">💡 ${escapeHtml(issue.recommendation)}</div>` : ''}
        </div>
      `
      )
      .join('');

    html.push(`
      <div class="severity-group">
        <div class="severity-header">
          <span class="severity-badge ${severity}">${severity}</span>
          <span>${items.length} issue${items.length === 1 ? '' : 's'}</span>
        </div>
        ${issuesHtml}
      </div>
    `);
  }

  return html.join('');
}

/**
 * Format test results section
 */
function formatTestResults(testResults: {
  unit: { passed: number; failed: number; skipped: number };
  integration: { passed: number; failed: number; skipped: number };
  e2e: { passed: number; failed: number; skipped: number };
}): string {
  return `
  <div class="section">
    <div class="section-title">Test Results</div>
    <div class="test-results-grid">
      <div class="test-result-card">
        <div class="test-type">Unit Tests</div>
        <div class="test-stats">
          <div class="test-stat">
            <div class="test-stat-label">Passed</div>
            <div class="test-stat-value passed">${testResults.unit.passed}</div>
          </div>
          <div class="test-stat">
            <div class="test-stat-label">Failed</div>
            <div class="test-stat-value failed">${testResults.unit.failed}</div>
          </div>
          <div class="test-stat">
            <div class="test-stat-label">Skipped</div>
            <div class="test-stat-value skipped">${testResults.unit.skipped}</div>
          </div>
        </div>
      </div>
      <div class="test-result-card">
        <div class="test-type">Integration Tests</div>
        <div class="test-stats">
          <div class="test-stat">
            <div class="test-stat-label">Passed</div>
            <div class="test-stat-value passed">${testResults.integration.passed}</div>
          </div>
          <div class="test-stat">
            <div class="test-stat-label">Failed</div>
            <div class="test-stat-value failed">${testResults.integration.failed}</div>
          </div>
          <div class="test-stat">
            <div class="test-stat-label">Skipped</div>
            <div class="test-stat-value skipped">${testResults.integration.skipped}</div>
          </div>
        </div>
      </div>
      <div class="test-result-card">
        <div class="test-type">E2E Tests</div>
        <div class="test-stats">
          <div class="test-stat">
            <div class="test-stat-label">Passed</div>
            <div class="test-stat-value passed">${testResults.e2e.passed}</div>
          </div>
          <div class="test-stat">
            <div class="test-stat-label">Failed</div>
            <div class="test-stat-value failed">${testResults.e2e.failed}</div>
          </div>
          <div class="test-stat">
            <div class="test-stat-label">Skipped</div>
            <div class="test-stat-value skipped">${testResults.e2e.skipped}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
  `;
}

/**
 * Format QA report as plain text for copying
 */
function formatReportAsText(report: QAReport): string {
  let text = `QA Validation Report\n`;
  text += `===================\n\n`;
  text += `Spec: ${report.specName}\n`;
  text += `Status: ${report.status.toUpperCase()}\n`;
  text += `Timestamp: ${report.timestamp}\n\n`;

  text += `Acceptance Criteria\n`;
  text += `-------------------\n`;
  for (const criterion of report.acceptanceCriteria) {
    const icon = getCriterionIcon(criterion.status);
    text += `${icon} ${criterion.criterion}\n`;
    if (criterion.details) {
      text += `  ${criterion.details}\n`;
    }
  }
  text += `\n`;

  if (report.issues.length > 0) {
    text += `Issues Found (${report.issues.length})\n`;
    text += `-------------\n`;
    for (const issue of report.issues) {
      text += `[${issue.severity.toUpperCase()}] ${issue.description}\n`;
      if (issue.location) {
        text += `  Location: ${issue.location}\n`;
      }
      if (issue.recommendation) {
        text += `  Recommendation: ${issue.recommendation}\n`;
      }
      text += `\n`;
    }
  }

  if (report.testResults) {
    text += `Test Results\n`;
    text += `------------\n`;
    text += `Unit: ${report.testResults.unit.passed} passed, ${report.testResults.unit.failed} failed, ${report.testResults.unit.skipped} skipped\n`;
    text += `Integration: ${report.testResults.integration.passed} passed, ${report.testResults.integration.failed} failed, ${report.testResults.integration.skipped} skipped\n`;
    text += `E2E: ${report.testResults.e2e.passed} passed, ${report.testResults.e2e.failed} failed, ${report.testResults.e2e.skipped} skipped\n\n`;
  }

  text += `Summary\n`;
  text += `-------\n`;
  text += `${report.summary}\n`;

  return text;
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
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
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
    void vscode.window.showInformationMessage('QA report copied to clipboard');
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    void vscode.window.showErrorMessage(`Failed to copy: ${errorMessage}`);
  }
}
