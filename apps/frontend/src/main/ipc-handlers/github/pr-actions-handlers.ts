/**
 * GitHub PR Actions IPC handlers
 *
 * Handles PR quick actions for the PRActionsDropdown:
 * 1. Detect dev command from package.json
 * 2. Spawn dev server and open browser
 * 3. Get CI status for a PR
 * 4. Request changes on a PR
 */

import { ipcMain, BrowserWindow, shell } from 'electron';
import { readFileSync, existsSync } from 'fs';
import path from 'path';
import { IPC_CHANNELS } from '../../../shared/constants';
import type { IPCResult, DevCommandInfo, CIStatusResult, CIStatusCheck } from '../../../shared/types';
import { getGitHubConfig, githubFetch } from './utils';
import { withProject } from './utils/project-middleware';
import { createContextLogger } from './utils/logger';
import {
  getTerminalWorktreeMetadataDir,
  getTerminalWorktreeMetadataPath,
} from '../../worktree-paths';
import { readdirSync } from 'fs';

const { debug: debugLog } = createContextLogger('GitHub PR Actions');
const debugError = (message: string, data?: unknown) => debugLog(message, data);

// Common dev script names in package.json
const DEV_SCRIPTS = ['dev', 'start', 'serve', 'preview', 'development'];

// Common port patterns in dev commands
const PORT_PATTERNS = [
  /--port[= ](\d+)/i,
  /-p[= ]?(\d+)/i,
  /PORT[= ](\d+)/i,
  /:(\d{4,5})/,  // Match ports in URLs like localhost:3000
];

// Default ports for common frameworks
const DEFAULT_PORTS: Record<string, number> = {
  'vite': 5173,
  'next': 3000,
  'create-react-app': 3000,
  'gatsby': 8000,
  'nuxt': 3000,
  'vue-cli': 8080,
  'angular': 4200,
  'svelte': 5000,
  'remix': 3000,
};

/**
 * Detect the dev command and port from package.json
 */
function detectDevCommand(worktreePath: string): DevCommandInfo | null {
  const packageJsonPath = path.join(worktreePath, 'package.json');

  if (!existsSync(packageJsonPath)) {
    debugLog('No package.json found at:', packageJsonPath);
    return null;
  }

  try {
    const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));
    const scripts = packageJson.scripts || {};
    const devDependencies = packageJson.devDependencies || {};
    const dependencies = packageJson.dependencies || {};

    // Find the first matching dev script
    let devScript: string | null = null;
    let devCommand: string | null = null;

    for (const scriptName of DEV_SCRIPTS) {
      if (scripts[scriptName]) {
        devScript = scriptName;
        devCommand = scripts[scriptName];
        break;
      }
    }

    if (!devScript || !devCommand) {
      debugLog('No dev script found in package.json');
      return null;
    }

    // Try to detect port from the command
    let port = 3000; // Default fallback

    for (const pattern of PORT_PATTERNS) {
      const match = devCommand.match(pattern);
      if (match && match[1]) {
        port = parseInt(match[1], 10);
        break;
      }
    }

    // If no port in command, try to detect from framework
    if (port === 3000) {
      if (devDependencies.vite || dependencies.vite) {
        port = DEFAULT_PORTS.vite;
      } else if (devDependencies.next || dependencies.next) {
        port = DEFAULT_PORTS.next;
      } else if (devDependencies['@angular/cli']) {
        port = DEFAULT_PORTS.angular;
      } else if (devDependencies.gatsby) {
        port = DEFAULT_PORTS.gatsby;
      } else if (devDependencies.nuxt || dependencies.nuxt) {
        port = DEFAULT_PORTS.nuxt;
      }
    }

    // Detect package manager
    const packageManager = existsSync(path.join(worktreePath, 'pnpm-lock.yaml')) ? 'pnpm' :
                          existsSync(path.join(worktreePath, 'yarn.lock')) ? 'yarn' :
                          existsSync(path.join(worktreePath, 'bun.lockb')) ? 'bun' : 'npm';

    const command = `${packageManager} run ${devScript}`;

    debugLog('Detected dev command:', { command, port, worktreePath });

    return {
      command,
      port,
      cwd: worktreePath,
    };
  } catch (error) {
    debugError('Error parsing package.json:', error);
    return null;
  }
}

/**
 * Find the worktree path for a given PR number
 */
function findPRWorktreePath(projectPath: string, prNumber: number): string | null {
  const metadataDir = getTerminalWorktreeMetadataDir(projectPath);
  if (!existsSync(metadataDir)) {
    return null;
  }

  try {
    const files = readdirSync(metadataDir).filter(f => f.endsWith('.json'));
    for (const file of files) {
      const name = file.replace('.json', '');
      // Check if this worktree is for this PR (by name convention)
      if (name.startsWith(`pr-${prNumber}-`)) {
        const metadataPath = getTerminalWorktreeMetadataPath(projectPath, name);
        if (existsSync(metadataPath)) {
          const config = JSON.parse(readFileSync(metadataPath, 'utf-8'));
          if (existsSync(config.worktreePath)) {
            return config.worktreePath;
          }
        }
      }
    }
  } catch (error) {
    debugError('Error finding PR worktree:', error);
  }

  return null;
}

/**
 * Register PR actions IPC handlers
 */
export function registerPRActionsHandlers(getMainWindow: () => BrowserWindow | null): void {
  // Detect dev command from package.json in worktree
  ipcMain.handle(
    IPC_CHANNELS.GITHUB_PR_DETECT_DEV_COMMAND,
    async (_event, projectId: string, worktreePath: string): Promise<IPCResult<DevCommandInfo | null>> => {
      return withProject(projectId, async (_project) => {
        try {
          const devCommand = detectDevCommand(worktreePath);
          return {
            success: true,
            data: devCommand,
          };
        } catch (error) {
          debugError('Error detecting dev command:', error);
          return {
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          };
        }
      });
    }
  );

  // Spawn dev server and open browser
  ipcMain.handle(
    IPC_CHANNELS.GITHUB_PR_SPAWN_DEV_SERVER,
    async (_event, projectId: string, prNumber: number): Promise<IPCResult<{ terminalId: string; port: number }>> => {
      return withProject(projectId, async (project) => {
        try {
          // Find the worktree for this PR
          const worktreePath = findPRWorktreePath(project.path, prNumber);
          if (!worktreePath) {
            return {
              success: false,
              error: 'No worktree found for this PR. Create a worktree first.',
            };
          }

          // Detect the dev command
          const devCommand = detectDevCommand(worktreePath);
          if (!devCommand) {
            return {
              success: false,
              error: 'No dev command found in package.json. Check that scripts.dev or scripts.start exists.',
            };
          }

          // Get the main window to send terminal creation event
          const mainWindow = getMainWindow();
          if (!mainWindow) {
            return {
              success: false,
              error: 'Main window not available',
            };
          }

          // Create a terminal at the worktree path
          // This will be handled by the existing terminal creation IPC
          const terminalId = `pr-${prNumber}-dev-${Date.now()}`;

          // Send event to renderer to create terminal
          mainWindow.webContents.send(IPC_CHANNELS.TERMINAL_CREATE, {
            terminalId,
            cwd: worktreePath,
            name: `PR #${prNumber} Dev Server`,
          });

          // Wait a moment for terminal to initialize, then send the dev command
          setTimeout(() => {
            mainWindow.webContents.send(IPC_CHANNELS.TERMINAL_INPUT, {
              terminalId,
              data: devCommand.command + '\n',
            });
          }, 500);

          // Wait for server to start, then open browser
          setTimeout(() => {
            shell.openExternal(`http://localhost:${devCommand.port}`);
          }, 3000);

          debugLog('Spawned dev server:', { terminalId, port: devCommand.port, worktreePath });

          return {
            success: true,
            data: {
              terminalId,
              port: devCommand.port,
            },
          };
        } catch (error) {
          debugError('Error spawning dev server:', error);
          return {
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          };
        }
      });
    }
  );

  // Get CI status for a PR
  ipcMain.handle(
    IPC_CHANNELS.GITHUB_PR_GET_CI_STATUS,
    async (_event, projectId: string, prNumber: number): Promise<IPCResult<CIStatusResult>> => {
      return withProject(projectId, async (project) => {
        try {
          const config = await getGitHubConfig(project);
          if (!config) {
            return { success: false, error: 'GitHub not configured for this project' };
          }

          // Get PR to find head SHA
          const prData = await githubFetch(config.token, `/repos/${config.repo}/pulls/${prNumber}`) as {
            head: { sha: string };
          };

          // Get check runs for the commit
          const checkRunsData = await githubFetch(
            config.token,
            `/repos/${config.repo}/commits/${prData.head.sha}/check-runs`
          ) as {
            total_count: number;
            check_runs: Array<{
              name: string;
              status: string;
              conclusion: string | null;
              html_url: string;
              started_at: string;
              completed_at: string | null;
            }>;
          };

          const checks: CIStatusCheck[] = checkRunsData.check_runs.map(run => {
            let status: CIStatusCheck['status'] = 'pending';
            if (run.status === 'completed') {
              if (run.conclusion === 'success') status = 'success';
              else if (run.conclusion === 'failure') status = 'failure';
              else if (run.conclusion === 'neutral') status = 'neutral';
              else if (run.conclusion === 'skipped') status = 'skipped';
            }

            return {
              name: run.name,
              status,
              conclusion: run.conclusion || undefined,
              url: run.html_url,
              startedAt: run.started_at,
              completedAt: run.completed_at || undefined,
            };
          });

          const passedChecks = checks.filter(c => c.status === 'success').length;
          const failedChecks = checks.filter(c => c.status === 'failure').length;
          const pendingChecks = checks.filter(c => c.status === 'pending').length;

          return {
            success: true,
            data: {
              totalChecks: checks.length,
              passedChecks,
              failedChecks,
              pendingChecks,
              checks,
            },
          };
        } catch (error) {
          debugError('Error getting CI status:', error);
          return {
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          };
        }
      });
    }
  );

  // Request changes on a PR
  ipcMain.handle(
    IPC_CHANNELS.GITHUB_PR_REQUEST_CHANGES,
    async (_event, projectId: string, prNumber: number, comment: string): Promise<IPCResult<boolean>> => {
      return withProject(projectId, async (project) => {
        try {
          const config = await getGitHubConfig(project);
          if (!config) {
            return { success: false, error: 'GitHub not configured for this project' };
          }

          // Create a review with REQUEST_CHANGES event
          await githubFetch(
            config.token,
            `/repos/${config.repo}/pulls/${prNumber}/reviews`,
            {
              method: 'POST',
              body: JSON.stringify({
                body: comment,
                event: 'REQUEST_CHANGES',
              }),
            }
          );

          debugLog('Requested changes on PR:', { prNumber, comment: comment.substring(0, 50) });

          return {
            success: true,
            data: true,
          };
        } catch (error) {
          debugError('Error requesting changes:', error);
          return {
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          };
        }
      });
    }
  );
}
