/**
 * Shared worktree path utilities
 *
 * Centralizes all worktree path constants and helper functions to avoid duplication
 * and ensure consistent path handling across the application.
 *
 * In dev mode, uses .auto-claude-dev/ to isolate dev data from production.
 */

import path from 'path';
import { existsSync } from 'fs';
import { getAutoClaudeDir } from './dev-mode';

// Export getters that use dynamic paths with proper cross-platform path handling
// These call getAutoClaudeDir() on each invocation to ensure fresh values
export function getTaskWorktreeDirPath(): string {
  return path.join(getAutoClaudeDir(), 'worktrees', 'tasks');
}

export function getTerminalWorktreeDirPath(): string {
  return path.join(getAutoClaudeDir(), 'worktrees', 'terminal');
}

export function getTerminalWorktreeMetadataDirPath(): string {
  return path.join(getAutoClaudeDir(), 'terminal', 'metadata');
}

// Legacy path for backwards compatibility
export const LEGACY_WORKTREE_DIR = '.worktrees';

/**
 * Get the task worktrees directory path
 */
export function getTaskWorktreeDir(projectPath: string): string {
  return path.join(projectPath, getTaskWorktreeDirPath());
}

/**
 * Get the full path for a specific task worktree
 */
export function getTaskWorktreePath(projectPath: string, specId: string): string {
  return path.join(projectPath, getTaskWorktreeDirPath(), specId);
}

/**
 * Validate that a resolved path is within the expected base directory
 * Protects against path traversal attacks (e.g., specId containing "..")
 */
function isPathWithinBase(resolvedPath: string, basePath: string): boolean {
  const normalizedPath = path.resolve(resolvedPath);
  const normalizedBase = path.resolve(basePath);
  return normalizedPath.startsWith(normalizedBase + path.sep) || normalizedPath === normalizedBase;
}

/**
 * Find a task worktree path, checking new location first then legacy
 * Returns the path if found, null otherwise
 * Includes path traversal protection to ensure paths stay within project
 */
export function findTaskWorktree(projectPath: string, specId: string): string | null {
  const normalizedProject = path.resolve(projectPath);

  // Check new path first (uses dynamic getter for dev/prod awareness)
  const newPath = path.join(projectPath, getTaskWorktreeDirPath(), specId);
  const resolvedNewPath = path.resolve(newPath);

  // Validate path stays within project (defense against path traversal)
  if (!isPathWithinBase(resolvedNewPath, normalizedProject)) {
    console.error(`[worktree-paths] Path traversal detected: specId "${specId}" resolves outside project`);
    return null;
  }

  if (existsSync(resolvedNewPath)) return resolvedNewPath;

  // Legacy fallback
  const legacyPath = path.join(projectPath, LEGACY_WORKTREE_DIR, specId);
  const resolvedLegacyPath = path.resolve(legacyPath);

  // Validate legacy path as well
  if (!isPathWithinBase(resolvedLegacyPath, normalizedProject)) {
    console.error(`[worktree-paths] Path traversal detected: specId "${specId}" resolves outside project (legacy)`);
    return null;
  }

  if (existsSync(resolvedLegacyPath)) return resolvedLegacyPath;

  return null;
}

/**
 * Get the terminal worktrees directory path
 */
export function getTerminalWorktreeDir(projectPath: string): string {
  return path.join(projectPath, getTerminalWorktreeDirPath());
}

/**
 * Get the full path for a specific terminal worktree
 */
export function getTerminalWorktreePath(projectPath: string, name: string): string {
  return path.join(projectPath, getTerminalWorktreeDirPath(), name);
}

/**
 * Find a terminal worktree path, checking new location first then legacy
 * Returns the path if found, null otherwise
 * Includes path traversal protection to ensure paths stays within project
 */
export function findTerminalWorktree(projectPath: string, name: string): string | null {
  const normalizedProject = path.resolve(projectPath);

  // Check new path first (uses dynamic getter for dev/prod awareness)
  const newPath = path.join(projectPath, getTerminalWorktreeDirPath(), name);
  const resolvedNewPath = path.resolve(newPath);

  // Validate path stays within project (defense against path traversal)
  if (!isPathWithinBase(resolvedNewPath, normalizedProject)) {
    console.error(`[worktree-paths] Path traversal detected: name "${name}" resolves outside project`);
    return null;
  }

  if (existsSync(resolvedNewPath)) return resolvedNewPath;

  // Legacy fallback (terminal worktrees used terminal-{name} prefix)
  const legacyPath = path.join(projectPath, LEGACY_WORKTREE_DIR, `terminal-${name}`);
  const resolvedLegacyPath = path.resolve(legacyPath);

  // Validate legacy path as well
  if (!isPathWithinBase(resolvedLegacyPath, normalizedProject)) {
    console.error(`[worktree-paths] Path traversal detected: name "${name}" resolves outside project (legacy)`);
    return null;
  }

  if (existsSync(resolvedLegacyPath)) return resolvedLegacyPath;

  return null;
}

/**
 * Get the terminal worktree metadata directory path
 * This is separate from the git worktree to avoid uncommitted files
 */
export function getTerminalWorktreeMetadataDir(projectPath: string): string {
  return path.join(projectPath, getTerminalWorktreeMetadataDirPath());
}

/**
 * Get the metadata file path for a specific terminal worktree
 */
export function getTerminalWorktreeMetadataPath(projectPath: string, name: string): string {
  return path.join(projectPath, getTerminalWorktreeMetadataDirPath(), `${name}.json`);
}
