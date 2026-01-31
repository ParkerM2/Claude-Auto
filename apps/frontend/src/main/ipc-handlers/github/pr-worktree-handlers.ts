/**
 * GitHub PR Worktree IPC handlers
 *
 * Handles creating worktrees from PR branches for making changes:
 * 1. Checkout PR branch to a new worktree
 * 2. Check if PR already has an associated worktree
 */

import { ipcMain } from 'electron';
import { execFileSync } from 'child_process';
import { IPC_CHANNELS } from '../../../shared/constants';
import type { IPCResult, PRWorktreeInfo } from '../../../shared/types';
import { getGitHubConfig, githubFetch } from './utils';
import { withProject } from './utils/project-middleware';
import { createContextLogger } from './utils/logger';
import { getToolPath } from '../../cli-tool-manager';
import { getIsolatedGitEnv } from '../../utils/git-isolation';
import {
  getTerminalWorktreeDir,
  getTerminalWorktreePath,
  getTerminalWorktreeMetadataDir,
  getTerminalWorktreeMetadataPath,
} from '../../worktree-paths';
import { existsSync, mkdirSync, writeFileSync, readFileSync, readdirSync } from 'fs';
import path from 'path';
import type { TerminalWorktreeConfig } from '../../../shared/types';

const { debug: debugLog } = createContextLogger('GitHub PR Worktree');
const debugError = (message: string, data?: unknown) => debugLog(message, data);

// Validation regex for worktree names - lowercase alphanumeric with dashes/underscores
const WORKTREE_NAME_REGEX = /^[a-z0-9][a-z0-9_-]*[a-z0-9]$|^[a-z0-9]$/;

/**
 * Generate a worktree name from PR number and branch
 */
function generateWorktreeName(prNumber: number, headRef: string): string {
  // Create a short version of the branch name
  const shortBranch = headRef
    .replace(/^refs\/heads\//, '')
    .replace(/[^a-zA-Z0-9-_]/g, '-')
    .toLowerCase()
    .substring(0, 20);
  return `pr-${prNumber}-${shortBranch}`;
}

/**
 * Save worktree config to metadata directory
 */
function saveWorktreeConfig(projectPath: string, name: string, config: TerminalWorktreeConfig): void {
  const metadataDir = getTerminalWorktreeMetadataDir(projectPath);
  mkdirSync(metadataDir, { recursive: true });
  const metadataPath = getTerminalWorktreeMetadataPath(projectPath, name);
  writeFileSync(metadataPath, JSON.stringify(config, null, 2));
}

/**
 * Load worktree config from metadata directory
 */
function loadWorktreeConfig(projectPath: string, name: string): TerminalWorktreeConfig | null {
  const metadataPath = getTerminalWorktreeMetadataPath(projectPath, name);
  if (existsSync(metadataPath)) {
    try {
      return JSON.parse(readFileSync(metadataPath, 'utf-8'));
    } catch (error) {
      debugError('Corrupted config at: ' + metadataPath, error);
      return null;
    }
  }
  return null;
}

/**
 * Find existing worktree for a PR number
 */
function findPRWorktree(projectPath: string, prNumber: number): TerminalWorktreeConfig | null {
  const metadataDir = getTerminalWorktreeMetadataDir(projectPath);
  if (!existsSync(metadataDir)) {
    return null;
  }

  try {
    const files = readdirSync(metadataDir).filter(f => f.endsWith('.json'));
    for (const file of files) {
      const name = file.replace('.json', '');
      const config = loadWorktreeConfig(projectPath, name);
      // Check if this worktree is for this PR (by name convention or metadata)
      if (config && name.startsWith(`pr-${prNumber}-`)) {
        // Verify the worktree still exists
        if (existsSync(config.worktreePath)) {
          return config;
        }
      }
    }
  } catch (error) {
    debugError('Error searching for PR worktree:', error);
  }

  return null;
}

/**
 * Register PR worktree IPC handlers
 */
export function registerPRWorktreeHandlers(): void {
  // Get worktree status for a PR
  ipcMain.handle(
    IPC_CHANNELS.GITHUB_PR_GET_WORKTREE_STATUS,
    async (_event, projectId: string, prNumber: number): Promise<IPCResult<PRWorktreeInfo>> => {
      return withProject(projectId, async (project) => {
        try {
          const existingWorktree = findPRWorktree(project.path, prNumber);

          if (existingWorktree) {
            return {
              success: true,
              data: {
                prNumber,
                branch: existingWorktree.branchName,
                worktreePath: existingWorktree.worktreePath,
                hasWorktree: true,
                terminalId: existingWorktree.terminalId,
              },
            };
          }

          return {
            success: true,
            data: {
              prNumber,
              branch: '',
              worktreePath: '',
              hasWorktree: false,
            },
          };
        } catch (error) {
          debugError('Error checking PR worktree status:', error);
          return {
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          };
        }
      });
    }
  );

  // Checkout PR to a new worktree
  ipcMain.handle(
    IPC_CHANNELS.GITHUB_PR_CHECKOUT_WORKTREE,
    async (_event, projectId: string, prNumber: number): Promise<IPCResult<PRWorktreeInfo>> => {
      return withProject(projectId, async (project) => {
        try {
          // Check if worktree already exists
          const existingWorktree = findPRWorktree(project.path, prNumber);
          if (existingWorktree) {
            return {
              success: true,
              data: {
                prNumber,
                branch: existingWorktree.branchName,
                worktreePath: existingWorktree.worktreePath,
                hasWorktree: true,
                terminalId: existingWorktree.terminalId,
              },
            };
          }

          // Get GitHub config
          const config = await getGitHubConfig(project);
          if (!config) {
            return { success: false, error: 'GitHub not configured for this project' };
          }

          // Fetch PR details to get branch name
          const prData = await githubFetch(config.token, `/repos/${config.repo}/pulls/${prNumber}`) as {
            head: { ref: string; sha: string };
            base: { ref: string };
            title: string;
          };

          const headRef = prData.head.ref;
          const worktreeName = generateWorktreeName(prNumber, headRef);

          // Validate worktree name
          if (!WORKTREE_NAME_REGEX.test(worktreeName)) {
            return { success: false, error: 'Invalid worktree name generated' };
          }

          const worktreePath = getTerminalWorktreePath(project.path, worktreeName);
          const branchName = `pr/${prNumber}/${headRef}`;

          debugLog('Creating PR worktree:', { prNumber, headRef, worktreeName, worktreePath });

          // Ensure worktree directory parent exists
          mkdirSync(getTerminalWorktreeDir(project.path), { recursive: true });

          // Fetch the PR branch from remote
          try {
            execFileSync(getToolPath('git'), ['fetch', 'origin', `pull/${prNumber}/head:${branchName}`], {
              cwd: project.path,
              encoding: 'utf-8',
              stdio: ['pipe', 'pipe', 'pipe'],
              env: getIsolatedGitEnv(),
            });
            debugLog('Fetched PR branch:', branchName);
          } catch (fetchError) {
            // Try alternative fetch method
            try {
              execFileSync(getToolPath('git'), ['fetch', 'origin', headRef], {
                cwd: project.path,
                encoding: 'utf-8',
                stdio: ['pipe', 'pipe', 'pipe'],
                env: getIsolatedGitEnv(),
              });
              debugLog('Fetched PR branch via head ref:', headRef);
            } catch (altFetchError) {
              debugError('Failed to fetch PR branch:', altFetchError);
              return { success: false, error: 'Failed to fetch PR branch from remote' };
            }
          }

          // Create worktree using the fetched branch
          try {
            execFileSync(getToolPath('git'), ['worktree', 'add', worktreePath, branchName], {
              cwd: project.path,
              encoding: 'utf-8',
              stdio: ['pipe', 'pipe', 'pipe'],
              env: getIsolatedGitEnv(),
            });
            debugLog('Created worktree at:', worktreePath);
          } catch (worktreeError) {
            // If branch already exists locally, try using it directly
            try {
              execFileSync(getToolPath('git'), ['worktree', 'add', worktreePath, `origin/${headRef}`], {
                cwd: project.path,
                encoding: 'utf-8',
                stdio: ['pipe', 'pipe', 'pipe'],
                env: getIsolatedGitEnv(),
              });
              debugLog('Created worktree using origin ref:', `origin/${headRef}`);
            } catch (retryError) {
              debugError('Failed to create worktree:', retryError);
              return { success: false, error: 'Failed to create worktree for PR branch' };
            }
          }

          // Save worktree config
          // Note: terminalId is empty initially - it will be set when user opens a terminal in this worktree
          const worktreeConfig: TerminalWorktreeConfig = {
            name: worktreeName,
            worktreePath,
            branchName,
            baseBranch: prData.base.ref,
            hasGitBranch: true,
            createdAt: new Date().toISOString(),
            terminalId: '', // Will be populated when terminal is opened
          };
          saveWorktreeConfig(project.path, worktreeName, worktreeConfig);

          debugLog('PR worktree created successfully:', { prNumber, worktreePath });

          return {
            success: true,
            data: {
              prNumber,
              branch: branchName,
              worktreePath,
              hasWorktree: true,
            },
          };
        } catch (error) {
          debugError('Error creating PR worktree:', error);
          return {
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          };
        }
      });
    }
  );
}
