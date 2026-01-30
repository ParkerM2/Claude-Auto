/**
 * Jira Issue IPC Handlers
 *
 * Handles fetching issues from Jira Cloud REST API.
 * Uses Basic auth with email + API token.
 */

import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../../shared/constants';
import type { IPCResult, JiraIssue, JiraSyncStatus } from '../../../shared/types';
import { projectStore } from '../../project-store';
import { parseEnvFile } from '../utils';
import { existsSync, readFileSync } from 'fs';
import path from 'path';
import type { JiraConfig } from './types';

/**
 * Get Jira configuration from project .env file
 */
function getJiraConfig(projectId: string): JiraConfig | null {
  const project = projectStore.getProject(projectId);
  if (!project?.autoBuildPath) {
    return null;
  }

  const envPath = path.join(project.path, project.autoBuildPath, '.env');
  if (!existsSync(envPath)) {
    return null;
  }

  try {
    const content = readFileSync(envPath, 'utf-8');
    const vars = parseEnvFile(content);

    const baseUrl = vars['JIRA_BASE_URL'];
    const email = vars['JIRA_EMAIL'];
    const apiToken = vars['JIRA_API_TOKEN'];
    const projectKey = vars['JIRA_PROJECT_KEY'];

    if (!baseUrl || !email || !apiToken) {
      return null;
    }

    return {
      baseUrl: baseUrl.replace(/\/$/, ''), // Remove trailing slash
      email,
      apiToken,
      projectKey,
    };
  } catch {
    return null;
  }
}

/**
 * Make authenticated request to Jira REST API
 */
async function jiraFetch<T>(
  config: JiraConfig,
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const credentials = Buffer.from(`${config.email}:${config.apiToken}`).toString('base64');

  const response = await fetch(`${config.baseUrl}/rest/api/3${endpoint}`, {
    ...options,
    headers: {
      'Authorization': `Basic ${credentials}`,
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = `Jira API error (${response.status})`;
    try {
      const errorJson = JSON.parse(errorText);
      if (errorJson.errorMessages) {
        errorMessage = errorJson.errorMessages.join('; ');
      } else if (errorJson.message) {
        errorMessage = errorJson.message;
      }
    } catch {
      // Use default message
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

/**
 * Convert Jira API issue to our JiraIssue type
 */
function convertIssue(issue: any, baseUrl: string): JiraIssue {
  const fields = issue.fields || {};

  // Extract status category
  const statusCategory = fields.status?.statusCategory?.key || 'undefined';
  const categoryMap: Record<string, 'todo' | 'in_progress' | 'done'> = {
    'new': 'todo',
    'undefined': 'todo',
    'indeterminate': 'in_progress',
    'done': 'done',
  };

  // Extract story points from common custom field names
  let storyPoints: number | undefined;
  for (const fieldKey of ['customfield_10016', 'customfield_10021', 'storyPoints']) {
    if (fields[fieldKey] !== undefined && fields[fieldKey] !== null) {
      const parsed = parseFloat(fields[fieldKey]);
      if (!isNaN(parsed)) {
        storyPoints = parsed;
        break;
      }
    }
  }

  // Parse description (handle ADF format)
  let description: string | undefined;
  if (fields.description) {
    if (typeof fields.description === 'string') {
      description = fields.description;
    } else if (typeof fields.description === 'object') {
      description = extractAdfText(fields.description);
    }
  }

  return {
    key: issue.key,
    id: issue.id,
    summary: fields.summary || '',
    description,
    status: {
      name: fields.status?.name || 'Unknown',
      category: categoryMap[statusCategory] || 'todo',
    },
    storyPoints,
    assignee: fields.assignee ? {
      displayName: fields.assignee.displayName || 'Unknown',
      avatarUrl: fields.assignee.avatarUrls?.['48x48'],
    } : undefined,
    reporter: fields.reporter ? {
      displayName: fields.reporter.displayName || 'Unknown',
      avatarUrl: fields.reporter.avatarUrls?.['48x48'],
    } : undefined,
    priority: fields.priority ? {
      name: fields.priority.name || 'None',
      iconUrl: fields.priority.iconUrl,
    } : undefined,
    labels: fields.labels || [],
    project: {
      key: fields.project?.key || '',
      name: fields.project?.name || '',
    },
    issueType: fields.issuetype?.name || 'Task',
    url: `${baseUrl}/browse/${issue.key}`,
    createdAt: fields.created || '',
    updatedAt: fields.updated || '',
  };
}

/**
 * Extract plain text from Atlassian Document Format (ADF)
 */
function extractAdfText(adf: any): string {
  const content = adf.content || [];
  const textParts: string[] = [];

  for (const block of content) {
    if (block.type === 'paragraph') {
      for (const inline of block.content || []) {
        if (inline.type === 'text') {
          textParts.push(inline.text || '');
        }
      }
      textParts.push('\n');
    } else if (block.type === 'bulletList') {
      for (const item of block.content || []) {
        if (item.type === 'listItem') {
          for (const para of item.content || []) {
            for (const inline of para.content || []) {
              if (inline.type === 'text') {
                textParts.push(`- ${inline.text || ''}\n`);
              }
            }
          }
        }
      }
    } else if (block.type === 'heading') {
      for (const inline of block.content || []) {
        if (inline.type === 'text') {
          textParts.push(`## ${inline.text || ''}\n`);
        }
      }
    }
  }

  return textParts.join('').trim();
}

/**
 * Register Jira issue-related IPC handlers
 */
export function registerJiraIssueHandlers(): void {
  // Check Jira connection status
  ipcMain.handle(
    IPC_CHANNELS.JIRA_CHECK_CONNECTION,
    async (_, projectId: string): Promise<IPCResult<JiraSyncStatus>> => {
      const config = getJiraConfig(projectId);
      if (!config) {
        return {
          success: true,
          data: {
            connected: false,
            error: 'Jira not configured. Add credentials in Settings.',
          },
        };
      }

      try {
        const user = await jiraFetch<any>(config, '/myself');
        return {
          success: true,
          data: {
            connected: true,
            baseUrl: config.baseUrl,
            currentUser: user.displayName || user.emailAddress,
          },
        };
      } catch (error) {
        return {
          success: true,
          data: {
            connected: false,
            baseUrl: config.baseUrl,
            error: error instanceof Error ? error.message : 'Connection failed',
          },
        };
      }
    }
  );

  // Get issues assigned to current user
  ipcMain.handle(
    IPC_CHANNELS.JIRA_GET_MY_ISSUES,
    async (_, projectId: string): Promise<IPCResult<JiraIssue[]>> => {
      const config = getJiraConfig(projectId);
      if (!config) {
        return { success: false, error: 'Jira not configured' };
      }

      try {
        // Build JQL query
        const jqlParts = ['assignee = currentUser()'];
        if (config.projectKey) {
          jqlParts.push(`project = ${config.projectKey}`);
        }
        jqlParts.push('ORDER BY updated DESC');

        const jql = jqlParts.slice(0, 2).join(' AND ') + ' ' + jqlParts[2];

        const params = new URLSearchParams({
          jql,
          maxResults: '50',
          fields: 'summary,description,status,priority,assignee,reporter,labels,project,issuetype,created,updated,customfield_10016,customfield_10021',
        });

        const data = await jiraFetch<any>(config, `/search?${params.toString()}`);
        const issues = (data.issues || []).map((issue: any) =>
          convertIssue(issue, config.baseUrl)
        );

        return { success: true, data: issues };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to fetch issues',
        };
      }
    }
  );

  // Get a specific issue by key
  ipcMain.handle(
    IPC_CHANNELS.JIRA_GET_ISSUE,
    async (_, projectId: string, issueKey: string): Promise<IPCResult<JiraIssue>> => {
      const config = getJiraConfig(projectId);
      if (!config) {
        return { success: false, error: 'Jira not configured' };
      }

      try {
        const params = new URLSearchParams({
          fields: 'summary,description,status,priority,assignee,reporter,labels,project,issuetype,created,updated,customfield_10016,customfield_10021',
        });

        const data = await jiraFetch<any>(config, `/issue/${issueKey}?${params.toString()}`);
        const issue = convertIssue(data, config.baseUrl);

        return { success: true, data: issue };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to fetch issue',
        };
      }
    }
  );
}
