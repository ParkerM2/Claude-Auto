/**
 * Component exports index
 *
 * Re-exports components from feature directories.
 * Note: Some exports are renamed to avoid naming conflicts:
 * - TaskCard: exported from kanban/ (changelog/TaskCard is renamed ChangelogTaskCard)
 * - WizardStep: type exported from onboarding/ (changelog/WizardStep is renamed ChangelogWizardStep)
 * - GeneralSettings: exported from settings/ (project-settings/GeneralSettings is renamed ProjectGeneralSettings)
 * - useImageUpload: exported from task-form/ (changelog/useImageUpload is renamed useChangelogImageUpload)
 */

// Auth
export * from './auth';

// Changelog - export with renames to avoid conflicts
export {
  Changelog,
  ChangelogHeader,
  ChangelogFilters,
  ChangelogList,
  TaskCard as ChangelogTaskCard,
  CommitCard,
  Step2ConfigureGenerate,
  Step3ReleaseArchive,
  ConfigurationPanel,
  PreviewPanel,
  Step3SuccessScreen,
  GitHubReleaseCard,
  ArchiveTasksCard,
  useChangelog,
  useImageUpload as useChangelogImageUpload,
} from './changelog';
export type { WizardStep as ChangelogWizardStep } from './changelog';

// Context
export * from './context';

// File Explorer
export * from './file-explorer';

// Git
export * from './git';

// GitHub Issues
export * from './github-issues';

// GitHub PRs
export * from './github-prs';

// Ideation
export * from './ideation';

// Insights
export * from './insights';

// Jira Tickets
export * from './jira-tickets';

// Kanban - main TaskCard comes from here
export * from './kanban';

// Layout
export * from './layout';

// Modals
export * from './modals';

// Onboarding - main WizardStep comes from here
export * from './onboarding';

// Project
export * from './project';

// Project Settings - export with rename to avoid conflict with settings/GeneralSettings
export {
  GeneralSettings as ProjectGeneralSettings,
  IntegrationSettings,
  SecuritySettings,
  useProjectSettings,
  AutoBuildIntegration,
  ClaudeAuthSection,
  GitHubIntegrationSection,
  MemoryBackendSection,
  AgentConfigSection,
  NotificationsSection,
  CollapsibleSection,
  PasswordInput,
  StatusBadge,
  ConnectionStatus,
  InfrastructureStatus,
} from './project-settings';
export type { UseProjectSettingsReturn } from './project-settings';

// Rate Limit
export * from './rate-limit';

// Roadmap
export * from './roadmap';

// Settings - main GeneralSettings comes from here
export * from './settings';

// Status
export * from './status';

// Task Detail
export * from './task-detail';

// Task Form
export * from './task-form';

// Task Wizard
export * from './task-wizard';

// Terminal
export * from './terminal';

// Updates
export * from './updates';

// Workspace
export * from './workspace';

// Worktrees
export * from './worktrees';

// Root-level components
export * from './AgentTools';
