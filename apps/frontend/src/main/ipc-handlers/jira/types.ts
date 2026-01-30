/**
 * Jira integration types for IPC handlers
 */

export interface JiraConfig {
  baseUrl: string;
  email: string;
  apiToken: string;
  projectKey?: string;
}

export interface JiraConnectionStatus {
  connected: boolean;
  baseUrl?: string;
  currentUser?: string;
  error?: string;
}
