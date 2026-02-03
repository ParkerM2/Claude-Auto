/**
 * Dev mode detection and data isolation utilities
 *
 * In development mode, we use separate data directories to prevent
 * dev testing from affecting production data:
 * - .auto-claude-dev/ instead of .auto-claude/ for project data
 * - {userData}-dev/ for app-level data (handled in index.ts)
 *
 * This isolation ensures that running `npm run dev` doesn't show or modify
 * production tasks, specs, and other data.
 */

import { app } from 'electron';

/**
 * Whether the app is running in development mode.
 * Uses app.isPackaged which is false during `npm run dev` and true in packaged builds.
 * Can be overridden by DISABLE_DEV_SANDBOX=true for testing production data in dev.
 */
export function isDevMode(): boolean {
  return !app.isPackaged && process.env.DISABLE_DEV_SANDBOX !== 'true';
}

/**
 * The auto-claude directory name used for project data.
 * - Development: .auto-claude-dev
 * - Production: .auto-claude
 */
export const AUTO_CLAUDE_DIR = isDevMode() ? '.auto-claude-dev' : '.auto-claude';

/**
 * Get the auto-claude directory name.
 * Useful when you need to call this dynamically (e.g., after app ready).
 */
export function getAutoClaudeDir(): string {
  return isDevMode() ? '.auto-claude-dev' : '.auto-claude';
}

/**
 * Log dev mode status (call once at startup)
 */
export function logDevModeStatus(): void {
  if (isDevMode()) {
    console.warn('[DEV] ========================================');
    console.warn('[DEV] Development mode data isolation ENABLED');
    console.warn(`[DEV] Project data directory: ${AUTO_CLAUDE_DIR}`);
    console.warn('[DEV] To use production data, set DISABLE_DEV_SANDBOX=true');
    console.warn('[DEV] ========================================');
  }
}
