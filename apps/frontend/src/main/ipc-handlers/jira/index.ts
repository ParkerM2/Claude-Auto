/**
 * Jira integration IPC handlers
 *
 * Main entry point that registers all Jira-related handlers.
 */

import { registerJiraIssueHandlers } from './issue-handlers';

/**
 * Register all Jira-related IPC handlers
 */
export function registerJiraHandlers(): void {
  registerJiraIssueHandlers();
}
