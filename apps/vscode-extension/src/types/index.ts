/**
 * TypeScript types for Auto Claude backend responses and CLI output
 *
 * These types mirror the data structures used by the Python backend CLI
 * to ensure type-safe communication between the VS Code extension and backend.
 */

/**
 * Task/subtask status values from implementation_plan.json
 */
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

/**
 * Phase types in the implementation workflow
 */
export type PhaseType = 'setup' | 'implementation' | 'integration' | 'testing';

/**
 * Build/plan status values
 */
export type BuildStatus = 'not_started' | 'in_progress' | 'completed' | 'failed' | 'paused';

/**
 * QA validation status
 */
export type QAStatus = 'not_started' | 'in_progress' | 'passed' | 'failed' | 'rejected';

/**
 * Verification types for subtasks
 */
export interface Verification {
  type: 'command' | 'manual' | 'e2e';
  command?: string;
  expected?: string;
  instructions?: string;
  steps?: string[];
}

/**
 * Subtask definition from implementation_plan.json
 */
export interface Task {
  id: string;
  description: string;
  service: string;
  files_to_modify: string[];
  files_to_create: string[];
  patterns_from: string[];
  verification: Verification;
  status: TaskStatus;
  notes: string;
  all_services?: boolean;
}

/**
 * Phase definition from implementation_plan.json
 */
export interface Phase {
  id: string;
  name: string;
  type: PhaseType;
  description: string;
  depends_on: string[];
  parallel_safe: boolean;
  subtasks: Task[];
}

/**
 * Complete spec document structure
 */
export interface Spec {
  feature: string;
  workflow_type: string;
  workflow_rationale: string;
  phases: Phase[];
  summary: {
    total_phases: number;
    total_subtasks: number;
    services_involved: string[];
    parallelism?: {
      max_parallel_phases: number;
      parallel_groups: Array<{
        phases: string[];
        reason: string;
      }>;
      recommended_workers: number;
      speedup_estimate: string;
    };
  };
  verification_strategy?: {
    risk_level: string;
    skip_validation: boolean;
    test_creation_phase: string;
    test_types_required: string[];
    security_scanning_required: boolean;
    staging_deployment_required: boolean;
    acceptance_criteria: string[];
    verification_steps: Array<{
      name: string;
      command: string;
      expected_outcome: string;
      type: string;
      required: boolean;
      blocking: boolean;
    }>;
    reasoning: string;
  };
  qa_acceptance?: {
    unit_tests: {
      required: boolean;
      commands: string[];
      minimum_coverage: number | null;
    };
    integration_tests: {
      required: boolean;
      commands: string[];
      services_to_test: string[];
    };
    e2e_tests: {
      required: boolean;
      commands: string[];
      flows: string[];
    };
    browser_verification: {
      required: boolean;
      pages: string[];
    };
    database_verification: {
      required: boolean;
      checks: string[];
    };
  };
  qa_signoff: QASignoff | null;
  status: BuildStatus;
  planStatus: BuildStatus;
  updated_at: string;
}

/**
 * QA sign-off information
 */
export interface QASignoff {
  status: QAStatus;
  timestamp: string;
  issues: string[];
  tests_passed: boolean;
  reviewer?: string;
}

/**
 * QA report structure
 */
export interface QAReport {
  specId: string;
  specName: string;
  status: QAStatus;
  timestamp: string;
  acceptanceCriteria: Array<{
    criterion: string;
    status: 'passed' | 'failed' | 'not_tested';
    details: string;
  }>;
  issues: Array<{
    severity: 'critical' | 'major' | 'minor';
    description: string;
    location?: string;
    recommendation?: string;
  }>;
  testResults?: {
    unit: { passed: number; failed: number; skipped: number };
    integration: { passed: number; failed: number; skipped: number };
    e2e: { passed: number; failed: number; skipped: number };
  };
  summary: string;
}

/**
 * Build progress data for real-time updates
 */
export interface BuildProgress {
  specId: string;
  specName: string;
  phase: 'idle' | 'planning' | 'coding' | 'qa_review' | 'qa_fixing' | 'complete' | 'failed';
  phaseProgress: number; // 0-100
  overallProgress: number; // 0-100
  currentSubtask?: string;
  currentSubtaskId?: string;
  completedSubtasks: number;
  totalSubtasks: number;
  message?: string;
  timestamp: string;
  // Track completed phases to prevent overlaps
  completedPhases?: string[];
}

/**
 * Git worktree status information
 */
export interface WorktreeStatus {
  specId: string;
  specName: string;
  worktreePath: string;
  branch: string;
  exists: boolean;
  isClean: boolean;
  hasChanges: boolean;
  filesChanged: number;
  filesAdded: number;
  filesDeleted: number;
  uncommittedChanges: boolean;
  commits: Array<{
    hash: string;
    message: string;
    author: string;
    timestamp: string;
  }>;
  diff?: string;
}

/**
 * Generic CLI response structure
 */
export interface CLIResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: string;
}

/**
 * List of specs returned by --list command
 */
export interface SpecListItem {
  id: string;
  name: string;
  status: BuildStatus;
  hasWorktree: boolean;
  qaStatus?: QAStatus;
  lastUpdated: string;
}

/**
 * Process output event data
 */
export interface ProcessOutputData {
  specId: string;
  type: 'stdout' | 'stderr';
  data: string;
  timestamp: string;
}

/**
 * Process exit event data
 */
export interface ProcessExitData {
  specId: string;
  code: number | null;
  signal: string | null;
  timestamp: string;
}

/**
 * Backend command types
 */
export type BackendCommand =
  | 'list'
  | 'run'
  | 'review'
  | 'merge'
  | 'discard'
  | 'qa'
  | 'qa-status'
  | 'review-status'
  | 'create-pr';

/**
 * Backend command options
 */
export interface BackendCommandOptions {
  spec?: string;
  projectDir?: string;
  model?: string;
  verbose?: boolean;
  isolated?: boolean;
  direct?: boolean;
  maxIterations?: number;
  prTarget?: string;
  prTitle?: string;
  prDraft?: boolean;
}
