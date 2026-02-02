# Components Directory Structure

This directory follows feature-based organization where components are grouped by their domain/feature rather than by type.

## Directory Structure

```
components/
├── auth/               # Authentication components (AuthFailureModal, AuthStatusIndicator)
├── changelog/          # Changelog feature (entries, wizard, generation)
├── context/            # Project context management
├── file-explorer/      # File browsing components (FileTree, FileAutocomplete, ImageUpload)
├── git/                # Git setup modals (GitSetupModal, GitHubSetupModal)
├── github-issues/      # GitHub issues integration
├── github-prs/         # GitHub pull requests integration
├── ideation/           # AI-powered ideation feature
├── insights/           # Project insights and competitor analysis
├── jira-tickets/       # Jira integration
├── kanban/             # Kanban board and task cards
├── layout/             # App layout (Sidebar, ProjectTabBar, WelcomeScreen)
├── modals/             # Shared modal dialogs (AddProjectModal, EnvConfigModal)
├── onboarding/         # First-run onboarding wizard
├── project/            # Project management (AddFeatureDialog, SortableFeatureCard)
├── project-settings/   # Per-project settings panels
├── rate-limit/         # Rate limiting UI (indicators, modals)
├── roadmap/            # Product roadmap feature
├── settings/           # App-wide settings components
├── status/             # Status indicators (ClaudeCodeStatusBadge, UsageIndicator)
├── task-detail/        # Task detail view components
├── task-form/          # Task form components and hooks
├── task-wizard/        # Task creation/edit wizard
├── terminal/           # Terminal emulator components
├── ui/                 # Primitive UI components (shadcn)
├── updates/            # App update notifications
├── workspace/          # Workspace management (AddWorkspaceModal)
├── worktrees/          # Git worktree management
└── AgentTools.tsx      # Large agent tools component (root-level)
```

## Naming Conventions

- **Directories**: lowercase with hyphens (`file-explorer/`, `rate-limit/`)
- **Components**: PascalCase (`AuthStatusIndicator.tsx`)
- **Hooks**: camelCase with `use` prefix (`useTerminalEvents.ts`)
- **Tests**: Same name with `.test.tsx` suffix (`AuthStatusIndicator.test.tsx`)
- **Types**: `types.ts` within the directory

## Directory Structure Pattern

Each feature directory should contain:

```
feature/
├── index.ts              # Public exports
├── FeatureMain.tsx       # Main component
├── SubComponent.tsx      # Sub-components
├── hooks/                # Feature-specific hooks
│   └── useFeatureHook.ts
├── types.ts              # TypeScript types
├── utils.ts              # Utility functions
└── FeatureMain.test.tsx  # Tests alongside components
```

## Export Rules

1. Each directory exports via `index.ts`
2. Import from directory, not individual files: `import { Sidebar } from './layout'`
3. Root `components/index.ts` re-exports all directories
4. Conflicting names are renamed (e.g., `TaskCard` → `ChangelogTaskCard`)

## When Adding New Components

1. Identify the feature/domain it belongs to
2. Add to existing directory or create new one if warranted
3. Export from the directory's `index.ts`
4. Add tests alongside the component
5. Update root `components/index.ts` if needed

## Import Examples

```tsx
// Preferred: Import from feature directory
import { Sidebar, WelcomeScreen } from './components/layout';
import { KanbanBoard, TaskCard } from './components/kanban';

// Also works: Import from root index (for convenience)
import { Sidebar, KanbanBoard } from './components';

// Avoid: Direct file imports
import { Sidebar } from './components/layout/Sidebar'; // ❌
```
