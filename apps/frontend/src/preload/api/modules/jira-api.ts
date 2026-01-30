import { IPC_CHANNELS } from '../../../shared/constants';
import type { JiraIssue, JiraSyncStatus, IPCResult } from '../../../shared/types';
import { invokeIpc } from './ipc-utils';

/**
 * Jira Integration API operations
 */
export interface JiraAPI {
  checkConnection: (projectId: string) => Promise<IPCResult<JiraSyncStatus>>;
  getMyIssues: (projectId: string) => Promise<IPCResult<JiraIssue[]>>;
  getIssue: (projectId: string, issueKey: string) => Promise<IPCResult<JiraIssue>>;
}

/**
 * Creates the Jira Integration API implementation
 */
export const createJiraAPI = (): JiraAPI => ({
  checkConnection: (projectId: string): Promise<IPCResult<JiraSyncStatus>> =>
    invokeIpc(IPC_CHANNELS.JIRA_CHECK_CONNECTION, projectId),

  getMyIssues: (projectId: string): Promise<IPCResult<JiraIssue[]>> =>
    invokeIpc(IPC_CHANNELS.JIRA_GET_MY_ISSUES, projectId),

  getIssue: (projectId: string, issueKey: string): Promise<IPCResult<JiraIssue>> =>
    invokeIpc(IPC_CHANNELS.JIRA_GET_ISSUE, projectId, issueKey),
});
