import { IPC_CHANNELS } from '../../../shared/constants';
import type { IPCResult } from '../../../shared/types';
import { createIpcListener, invokeIpc, sendIpc, IpcListenerCleanup } from './ipc-utils';

/**
 * CLAUDE.md progress event
 */
export interface ClaudeMdProgressEvent {
  phase: string;
  message: string;
  percent: number;
}

/**
 * Result of checking for CLAUDE.md
 */
export interface ClaudeMdCheckResult {
  exists: boolean;
  path?: string;
}

/**
 * Result of CLAUDE.md generation
 */
export interface ClaudeMdGenerationResult {
  success: boolean;
  outputPath?: string;
  error?: string;
}

/**
 * CLAUDE.md API operations
 */
export interface ClaudeMdAPI {
  // Operations
  /**
   * Check if CLAUDE.md exists in a project
   */
  checkClaudeMd: (projectPath: string) => Promise<IPCResult<ClaudeMdCheckResult>>;

  /**
   * Start CLAUDE.md generation for a project
   */
  generateClaudeMd: (projectPath: string, model?: string) => void;

  // Event Listeners
  /**
   * Listen for generation progress updates
   */
  onProgress: (
    callback: (projectPath: string, progress: ClaudeMdProgressEvent) => void
  ) => IpcListenerCleanup;

  /**
   * Listen for generation completion
   */
  onComplete: (
    callback: (projectPath: string, result: ClaudeMdGenerationResult) => void
  ) => IpcListenerCleanup;

  /**
   * Listen for generation errors
   */
  onError: (callback: (projectPath: string, error: string) => void) => IpcListenerCleanup;
}

/**
 * Creates the CLAUDE.md API implementation
 */
export const createClaudeMdAPI = (): ClaudeMdAPI => ({
  // Operations
  checkClaudeMd: (projectPath: string): Promise<IPCResult<ClaudeMdCheckResult>> =>
    invokeIpc(IPC_CHANNELS.CLAUDE_MD_CHECK, projectPath),

  generateClaudeMd: (projectPath: string, model?: string): void =>
    sendIpc(IPC_CHANNELS.CLAUDE_MD_GENERATE, projectPath, model),

  // Event Listeners
  onProgress: (
    callback: (projectPath: string, progress: ClaudeMdProgressEvent) => void
  ): IpcListenerCleanup => createIpcListener(IPC_CHANNELS.CLAUDE_MD_PROGRESS, callback),

  onComplete: (
    callback: (projectPath: string, result: ClaudeMdGenerationResult) => void
  ): IpcListenerCleanup => createIpcListener(IPC_CHANNELS.CLAUDE_MD_COMPLETE, callback),

  onError: (callback: (projectPath: string, error: string) => void): IpcListenerCleanup =>
    createIpcListener(IPC_CHANNELS.CLAUDE_MD_ERROR, callback),
});
