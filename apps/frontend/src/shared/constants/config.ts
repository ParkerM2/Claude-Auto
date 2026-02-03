/**
 * Application configuration constants
 * Default settings, file paths, and project structure
 */

// ============================================
// Terminal Timing Constants
// ============================================

/** Delay for DOM updates before terminal operations (refit, resize) */
export const TERMINAL_DOM_UPDATE_DELAY_MS = 50;

// ============================================
// UI Scale Constants
// ============================================

export const UI_SCALE_MIN = 75;
export const UI_SCALE_MAX = 200;
export const UI_SCALE_DEFAULT = 100;
export const UI_SCALE_STEP = 5;

// ============================================
// Font Settings Constants
// ============================================

export const LETTER_SPACING_MIN = -0.05;
export const LETTER_SPACING_MAX = 0.1;
export const LETTER_SPACING_DEFAULT = 0;
export const LETTER_SPACING_STEP = 0.005;

// Default font families (system fonts as fallback)
export const DEFAULT_FONT_SANS_SERIF = 'Inter';
export const DEFAULT_FONT_SERIF = 'Georgia';
export const DEFAULT_FONT_MONO = 'JetBrains Mono';

// ============================================
// Default App Settings
// ============================================

export const DEFAULT_APP_SETTINGS = {
  theme: 'system' as const,
  colorTheme: 'default' as const,
  defaultModel: 'opus',
  agentFramework: 'auto-claude',
  pythonPath: undefined as string | undefined,
  gitPath: undefined as string | undefined,
  githubCLIPath: undefined as string | undefined,
  autoBuildPath: undefined as string | undefined,
  autoUpdateAutoBuild: true,
  autoNameTerminals: true,
  onboardingCompleted: false,
  notifications: {
    onTaskComplete: true,
    onTaskFailed: true,
    onReviewNeeded: true,
    sound: false
  },
  // Global API keys (used as defaults for all projects)
  globalClaudeOAuthToken: undefined as string | undefined,
  globalOpenAIApiKey: undefined as string | undefined,
  // Selected agent profile - defaults to 'auto' for per-phase optimized model selection
  selectedAgentProfile: 'auto',
  // Changelog preferences (persisted between sessions)
  changelogFormat: 'keep-a-changelog' as const,
  changelogAudience: 'user-facing' as const,
  changelogEmojiLevel: 'none' as const,
  // UI Scale (default 100% - standard size)
  uiScale: UI_SCALE_DEFAULT,
  // Beta updates opt-in (receive pre-release versions)
  betaUpdates: false,
  // Language preference (default to English)
  language: 'en' as const,
  // Anonymous error reporting (Sentry) - enabled by default to help improve the app
  sentryEnabled: true,
  // Auto-name Claude terminals based on initial message (enabled by default)
  autoNameClaudeTerminals: true
};

// ============================================
// Default Project Settings
// ============================================

export const DEFAULT_PROJECT_SETTINGS = {
  model: 'opus',
  memoryBackend: 'file' as const,
  linearSync: false,
  notifications: {
    onTaskComplete: true,
    onTaskFailed: true,
    onReviewNeeded: true,
    sound: false
  },
  // Graphiti MCP server for agent-accessible knowledge graph (enabled by default)
  graphitiMcpEnabled: true,
  // Environment-aware MCP URL: development mode uses mock server (port 8001), production uses real server (port 8000)
  graphitiMcpUrl: import.meta.env.VITE_API_MODE === 'development'
    ? 'http://localhost:8001/mcp/'
    : 'http://localhost:8000/mcp/',
  // Include CLAUDE.md instructions in agent context (enabled by default)
  useClaudeMd: true
};

// ============================================
// Auto Build File Paths
// ============================================

// Default auto-claude directory (production). In dev mode, main process uses .auto-claude-dev
// via getAutoClaudeDir() from dev-mode.ts. The actual directory is stored in project.autoBuildPath.
const DEFAULT_AUTO_CLAUDE_DIR = '.auto-claude';

// File paths relative to project
// NOTE: Directory paths (SPECS_DIR, ROADMAP_DIR, etc.) use the default production path.
// Main process code should use the helper functions or project.autoBuildPath for dev-aware paths.
export const AUTO_BUILD_PATHS = {
  // Directory paths (relative to project root) - these use DEFAULT for backwards compatibility
  // For dev-aware paths, use getSpecsDir/getRoadmapDir/getIdeationDir with project.autoBuildPath
  SPECS_DIR: `${DEFAULT_AUTO_CLAUDE_DIR}/specs`,
  ROADMAP_DIR: `${DEFAULT_AUTO_CLAUDE_DIR}/roadmap`,
  IDEATION_DIR: `${DEFAULT_AUTO_CLAUDE_DIR}/ideation`,
  PROJECT_INDEX: `${DEFAULT_AUTO_CLAUDE_DIR}/project_index.json`,

  // File names (relative to spec/feature directory) - these don't change between dev/prod
  IMPLEMENTATION_PLAN: 'implementation_plan.json',
  SPEC_FILE: 'spec.md',
  QA_REPORT: 'qa_report.md',
  BUILD_PROGRESS: 'build-progress.txt',
  CONTEXT: 'context.json',
  REQUIREMENTS: 'requirements.json',
  ROADMAP_FILE: 'roadmap.json',
  ROADMAP_DISCOVERY: 'roadmap_discovery.json',
  COMPETITOR_ANALYSIS: 'competitor_analysis.json',
  IDEATION_FILE: 'ideation.json',
  IDEATION_CONTEXT: 'ideation_context.json',
  GRAPHITI_STATE: '.graphiti_state.json'
} as const;

/**
 * Get the specs directory path.
 * Uses the provided autoBuildPath (which is dev-aware in main process).
 * Falls back to production default if not provided.
 */
export function getSpecsDir(autoBuildPath: string | undefined): string {
  const basePath = autoBuildPath || DEFAULT_AUTO_CLAUDE_DIR;
  return `${basePath}/specs`;
}

/**
 * Get the roadmap directory path.
 * Uses the provided autoBuildPath (which is dev-aware in main process).
 */
export function getRoadmapDir(autoBuildPath: string | undefined): string {
  const basePath = autoBuildPath || DEFAULT_AUTO_CLAUDE_DIR;
  return `${basePath}/roadmap`;
}

/**
 * Get the ideation directory path.
 * Uses the provided autoBuildPath (which is dev-aware in main process).
 */
export function getIdeationDir(autoBuildPath: string | undefined): string {
  const basePath = autoBuildPath || DEFAULT_AUTO_CLAUDE_DIR;
  return `${basePath}/ideation`;
}

/**
 * Get the project index file path.
 * Uses the provided autoBuildPath (which is dev-aware in main process).
 */
export function getProjectIndexPath(autoBuildPath: string | undefined): string {
  const basePath = autoBuildPath || DEFAULT_AUTO_CLAUDE_DIR;
  return `${basePath}/project_index.json`;
}
