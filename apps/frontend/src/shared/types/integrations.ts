/**
 * External integrations (GitHub, Jira)
 */

// ============================================
// Jira Integration Types
// ============================================

export interface JiraIssue {
  key: string; // e.g., ES-1234
  id: string;
  summary: string;
  description?: string;
  status: {
    name: string;
    category: 'todo' | 'in_progress' | 'done';
  };
  storyPoints?: number;
  assignee?: {
    displayName: string;
    avatarUrl?: string;
  };
  reporter?: {
    displayName: string;
    avatarUrl?: string;
  };
  priority?: {
    name: string;
    iconUrl?: string;
  };
  labels: string[];
  project: {
    key: string;
    name: string;
  };
  issueType: string;
  url: string;
  createdAt: string;
  updatedAt: string;
}

export interface JiraSyncStatus {
  connected: boolean;
  baseUrl?: string;
  currentUser?: string;
  error?: string;
}

// ============================================
// GitHub Integration Types
// ============================================

export interface GitHubRepository {
  id: number;
  name: string;
  fullName: string; // owner/repo
  description?: string;
  url: string;
  defaultBranch: string;
  private: boolean;
  owner: {
    login: string;
    avatarUrl?: string;
  };
}

export interface GitHubIssue {
  id: number;
  number: number;
  title: string;
  body?: string;
  state: 'open' | 'closed';
  labels: Array<{ id: number; name: string; color: string; description?: string }>;
  assignees: Array<{ login: string; avatarUrl?: string }>;
  author: {
    login: string;
    avatarUrl?: string;
  };
  milestone?: {
    id: number;
    title: string;
    state: 'open' | 'closed';
  };
  createdAt: string;
  updatedAt: string;
  closedAt?: string;
  commentsCount: number;
  url: string;
  htmlUrl: string;
  repoFullName: string;
}

/**
 * Result type for paginated issue fetching
 */
export interface PaginatedIssuesResult {
  issues: GitHubIssue[];
  hasMore: boolean;
}

export interface GitHubSyncStatus {
  connected: boolean;
  repoFullName?: string;
  repoDescription?: string;
  issueCount?: number;
  lastSyncedAt?: string;
  error?: string;
}

/**
 * Information about a worktree created for a GitHub PR
 */
export interface PRWorktreeInfo {
  prNumber: number;
  branch: string;
  worktreePath: string;
  hasWorktree: boolean;
  terminalId?: string;
}

/**
 * Dev command detection result for PR preview
 */
export interface DevCommandInfo {
  command: string;    // e.g., 'npm run dev'
  port: number;       // e.g., 3000, 5173
  cwd?: string;       // Working directory
}

/**
 * CI status check result
 */
export interface CIStatusCheck {
  name: string;
  status: 'success' | 'failure' | 'pending' | 'neutral' | 'skipped';
  conclusion?: string;
  url?: string;
  startedAt?: string;
  completedAt?: string;
}

/**
 * CI status result for a PR
 */
export interface CIStatusResult {
  totalChecks: number;
  passedChecks: number;
  failedChecks: number;
  pendingChecks: number;
  checks: CIStatusCheck[];
}

export interface GitHubImportResult {
  success: boolean;
  imported: number;
  failed: number;
  errors?: string[];
  tasks?: import('./task').Task[];
}

export interface GitHubInvestigationResult {
  success: boolean;
  issueNumber: number;
  analysis: {
    summary: string;
    proposedSolution: string;
    affectedFiles: string[];
    estimatedComplexity: 'simple' | 'standard' | 'complex';
    acceptanceCriteria: string[];
  };
  taskId?: string;
  error?: string;
}

export interface GitHubInvestigationStatus {
  phase: 'idle' | 'fetching' | 'analyzing' | 'creating_task' | 'complete' | 'error';
  issueNumber?: number;
  progress: number;
  message: string;
  error?: string;
}

// ============================================
// Roadmap Integration Types (Canny, etc.)
// ============================================

/**
 * Represents a feedback item from an external roadmap service
 */
export interface RoadmapFeedbackItem {
  externalId: string;
  title: string;
  description: string;
  votes: number;
  status: string;  // Provider-specific status
  url: string;
  createdAt: Date;
  updatedAt?: Date;
  author?: string;
  tags?: string[];
}

/**
 * Connection status for a roadmap provider
 */
export interface RoadmapProviderConnection {
  id: string;
  name: string;
  connected: boolean;
  lastSync?: Date;
  error?: string;
}

/**
 * Configuration for a roadmap provider integration
 */
export interface RoadmapProviderConfig {
  enabled: boolean;
  apiKey?: string;
  boardId?: string;
  autoSync?: boolean;
  syncIntervalMinutes?: number;
}

/**
 * Canny-specific status values
 */
export type CannyStatus = 'open' | 'under review' | 'planned' | 'in progress' | 'complete' | 'closed';
