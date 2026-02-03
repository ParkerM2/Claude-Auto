/**
 * CLAUDE.md Generation IPC Handlers
 *
 * Handles checking for CLAUDE.md existence and spawning the Python runner
 * for AI-powered generation of CLAUDE.md files.
 */

import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import { spawn } from 'child_process';
import path from 'path';
import { existsSync } from 'fs';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import { debugLog, debugError } from '../../shared/utils/debug-logger';
import { safeSendToRenderer } from './utils';
import { getConfiguredPythonPath } from '../python-env-manager';
import { getAugmentedEnv } from '../env-utils';
import { isWindows } from '../platform';
import { getEffectiveSourcePath } from '../updater/path-resolver';

export interface ClaudeMdProgressEvent {
  phase: string;
  message: string;
  percent: number;
}

export interface ClaudeMdCheckResult {
  exists: boolean;
  path?: string;
}

export interface ClaudeMdGenerationResult {
  success: boolean;
  outputPath?: string;
  error?: string;
}

/**
 * Register all CLAUDE.md related IPC handlers
 */
export function registerClaudeMdHandlers(getMainWindow: () => BrowserWindow | null): void {
  debugLog('[ClaudeMd Handler] Registering handlers');

  // Check if CLAUDE.md exists in a project directory
  ipcMain.handle(
    IPC_CHANNELS.CLAUDE_MD_CHECK,
    async (_, projectPath: string): Promise<IPCResult<ClaudeMdCheckResult>> => {
      debugLog('[ClaudeMd Handler] Check request:', { projectPath });

      if (!projectPath || typeof projectPath !== 'string') {
        return { success: false, error: 'Invalid project path' };
      }

      const claudeMdPath = path.join(projectPath, 'CLAUDE.md');
      const exists = existsSync(claudeMdPath);

      debugLog('[ClaudeMd Handler] Check result:', { exists, path: claudeMdPath });

      return {
        success: true,
        data: {
          exists,
          path: exists ? claudeMdPath : undefined,
        },
      };
    }
  );

  // Start CLAUDE.md generation using Python runner
  ipcMain.on(IPC_CHANNELS.CLAUDE_MD_GENERATE, (_, projectPath: string, model?: string) => {
    debugLog('[ClaudeMd Handler] Generate request:', { projectPath, model });

    const mainWindow = getMainWindow();
    if (!mainWindow) {
      debugError('[ClaudeMd Handler] No main window available');
      return;
    }

    if (!projectPath || typeof projectPath !== 'string') {
      safeSendToRenderer(
        getMainWindow,
        IPC_CHANNELS.CLAUDE_MD_ERROR,
        projectPath,
        'Invalid project path'
      );
      return;
    }

    // Check if CLAUDE.md already exists
    const claudeMdPath = path.join(projectPath, 'CLAUDE.md');
    if (existsSync(claudeMdPath)) {
      safeSendToRenderer(
        getMainWindow,
        IPC_CHANNELS.CLAUDE_MD_ERROR,
        projectPath,
        'CLAUDE.md already exists'
      );
      return;
    }

    // Get Python path and backend source path
    const pythonPath = getConfiguredPythonPath();
    const backendPath = getEffectiveSourcePath();

    if (!pythonPath) {
      debugError('[ClaudeMd Handler] Python path not configured');
      safeSendToRenderer(
        getMainWindow,
        IPC_CHANNELS.CLAUDE_MD_ERROR,
        projectPath,
        'Python environment not ready'
      );
      return;
    }

    // Validate backend path has the runner
    const runnerPathCheck = path.join(backendPath, 'runners', 'claude_md_runner.py');
    if (!existsSync(runnerPathCheck)) {
      debugError('[ClaudeMd Handler] Backend runner not found:', runnerPathCheck);
      safeSendToRenderer(
        getMainWindow,
        IPC_CHANNELS.CLAUDE_MD_ERROR,
        projectPath,
        'CLAUDE.md generator not available'
      );
      return;
    }

    // Build command arguments
    const runnerPath = path.join(backendPath, 'runners', 'claude_md_runner.py');
    const args = [runnerPath, '--project', projectPath, '--progress'];

    if (model) {
      args.push('--model', model);
    }

    debugLog('[ClaudeMd Handler] Spawning runner:', {
      pythonPath,
      runnerPath,
      args,
    });

    // Build environment with Python paths
    const env = getAugmentedEnv([backendPath]);

    // Spawn the Python process
    const proc = spawn(pythonPath, args, {
      cwd: backendPath,
      env,
      shell: isWindows(),
    });

    let stdout = '';
    let stderr = '';

    proc.stdout?.on('data', (data) => {
      const output = data.toString();
      stdout += output;

      // Parse progress updates
      const lines = output.split('\n');
      for (const line of lines) {
        if (line.startsWith('CLAUDE_MD_PROGRESS:')) {
          try {
            const progressJson = line.slice('CLAUDE_MD_PROGRESS:'.length);
            const progress: ClaudeMdProgressEvent = JSON.parse(progressJson);
            safeSendToRenderer(
              getMainWindow,
              IPC_CHANNELS.CLAUDE_MD_PROGRESS,
              projectPath,
              progress
            );
          } catch (parseError) {
            debugError('[ClaudeMd Handler] Failed to parse progress:', parseError);
          }
        }
      }
    });

    proc.stderr?.on('data', (data) => {
      stderr += data.toString();
      debugLog('[ClaudeMd Handler] stderr:', data.toString());
    });

    proc.on('close', (code) => {
      debugLog('[ClaudeMd Handler] Process exited:', { code, stdout: stdout.slice(-500), stderr });

      if (code === 0) {
        // Check if the file was created
        if (existsSync(claudeMdPath)) {
          safeSendToRenderer(getMainWindow, IPC_CHANNELS.CLAUDE_MD_COMPLETE, projectPath, {
            success: true,
            outputPath: claudeMdPath,
          } as ClaudeMdGenerationResult);
        } else {
          safeSendToRenderer(
            getMainWindow,
            IPC_CHANNELS.CLAUDE_MD_ERROR,
            projectPath,
            'Generation completed but file was not created'
          );
        }
      } else {
        // Extract error message from stderr or stdout
        const errorMessage =
          stderr.trim() || stdout.trim() || `Process exited with code ${code}`;
        safeSendToRenderer(
          getMainWindow,
          IPC_CHANNELS.CLAUDE_MD_ERROR,
          projectPath,
          errorMessage.slice(0, 500) // Truncate to reasonable length
        );
      }
    });

    proc.on('error', (error) => {
      debugError('[ClaudeMd Handler] Process error:', error);
      safeSendToRenderer(
        getMainWindow,
        IPC_CHANNELS.CLAUDE_MD_ERROR,
        projectPath,
        `Failed to start generator: ${error.message}`
      );
    });
  });

  debugLog('[ClaudeMd Handler] Handlers registered');
}
