/**
 * Auto Claude path utilities for main process
 *
 * Provides dev-aware path helpers that use .auto-claude-dev in development
 * and .auto-claude in production. This ensures data isolation between
 * dev testing and production use.
 *
 * USE THESE FUNCTIONS instead of AUTO_BUILD_PATHS constants when constructing
 * paths in main process code.
 */

import path from 'path';
import { getAutoClaudeDir } from './dev-mode';

/**
 * Get the specs directory path for a project.
 * In dev mode: .auto-claude-dev/specs
 * In production: .auto-claude/specs
 */
export function getSpecsDirPath(projectPath: string): string {
  return path.join(projectPath, getAutoClaudeDir(), 'specs');
}

/**
 * Get the roadmap directory path for a project.
 * In dev mode: .auto-claude-dev/roadmap
 * In production: .auto-claude/roadmap
 */
export function getRoadmapDirPath(projectPath: string): string {
  return path.join(projectPath, getAutoClaudeDir(), 'roadmap');
}

/**
 * Get the ideation directory path for a project.
 * In dev mode: .auto-claude-dev/ideation
 * In production: .auto-claude/ideation
 */
export function getIdeationDirPath(projectPath: string): string {
  return path.join(projectPath, getAutoClaudeDir(), 'ideation');
}

/**
 * Get the insights directory path for a project.
 * In dev mode: .auto-claude-dev/insights
 * In production: .auto-claude/insights
 */
export function getInsightsDirPath(projectPath: string): string {
  return path.join(projectPath, getAutoClaudeDir(), 'insights');
}

/**
 * Get the project index file path.
 * In dev mode: .auto-claude-dev/project_index.json
 * In production: .auto-claude/project_index.json
 */
export function getProjectIndexPath(projectPath: string): string {
  return path.join(projectPath, getAutoClaudeDir(), 'project_index.json');
}

/**
 * Get the auto-claude directory relative path (for use with autoBuildPath).
 * Returns the directory name without project path prefix.
 * In dev mode: .auto-claude-dev
 * In production: .auto-claude
 */
export function getAutoClaudeDirRelative(): string {
  return getAutoClaudeDir();
}

/**
 * Get a path within the auto-claude directory.
 * Use this for constructing arbitrary paths within the data directory.
 *
 * @param projectPath - The project root path
 * @param subPath - Path relative to the auto-claude directory (e.g., 'specs/001-feature')
 */
export function getAutoClaudePath(projectPath: string, subPath: string): string {
  return path.join(projectPath, getAutoClaudeDir(), subPath);
}

/**
 * Get the relative path (from project root) for a subdirectory within auto-claude.
 * Useful for constructing paths that need to be stored/displayed.
 *
 * @param subPath - Path relative to the auto-claude directory (e.g., 'specs')
 * @returns The full relative path (e.g., '.auto-claude-dev/specs' in dev mode)
 */
export function getAutoClaudeRelativePath(subPath: string): string {
  return `${getAutoClaudeDir()}/${subPath}`;
}
