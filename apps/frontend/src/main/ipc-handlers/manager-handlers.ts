/**
 * Manager IPC Handlers
 *
 * Handles IPC communication for the Manager agent that monitors
 * PR status for tasks with linked PRs.
 */

import { ipcMain, BrowserWindow } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import { getManagerProcess, initializeManagerProcess } from '../manager';
import type { PRStatusInfo } from '../../shared/types/task';

/**
 * Initialize the manager process and setup event forwarding
 */
export function initializeManager(
  getMainWindow: () => BrowserWindow | null,
  backendPath: string,
  projectPath: string
): void {
  const manager = initializeManagerProcess(projectPath, backendPath);

  // Forward PR status updates to renderer
  manager.on('pr-status-update', (taskId: string, prStatus: PRStatusInfo) => {
    const mainWindow = getMainWindow();
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send(IPC_CHANNELS.MANAGER_PR_STATUS_UPDATE, {
        taskId,
        prStatus
      });
    }
  });

  // Forward manager lifecycle events
  manager.on('manager-started', () => {
    console.log('[ManagerHandlers] Manager started');
  });

  manager.on('manager-stopped', () => {
    console.log('[ManagerHandlers] Manager stopped');
  });

  manager.on('manager-error', (error: string) => {
    console.error('[ManagerHandlers] Manager error:', error);
  });
}

/**
 * Register manager IPC handlers
 */
export function registerManagerHandlers(
  getMainWindow: () => BrowserWindow | null
): void {
  // Start the manager
  ipcMain.handle(IPC_CHANNELS.MANAGER_START, async () => {
    const manager = getManagerProcess();
    const success = await manager.start();
    return { success };
  });

  // Stop the manager
  ipcMain.handle(IPC_CHANNELS.MANAGER_STOP, () => {
    const manager = getManagerProcess();
    manager.stop();
    return { success: true };
  });

  // Add a task to monitoring
  ipcMain.handle(IPC_CHANNELS.MANAGER_ADD_TASK, (_event, taskId: string, prUrl: string) => {
    const manager = getManagerProcess();
    manager.addTask(taskId, prUrl);
    return { success: true };
  });

  // Remove a task from monitoring
  ipcMain.handle(IPC_CHANNELS.MANAGER_REMOVE_TASK, (_event, taskId: string) => {
    const manager = getManagerProcess();
    manager.removeTask(taskId);
    return { success: true };
  });

  // Force refresh a task's PR status
  ipcMain.handle(IPC_CHANNELS.MANAGER_REFRESH_TASK, (_event, taskId: string) => {
    const manager = getManagerProcess();
    manager.refreshTask(taskId);
    return { success: true };
  });

  // Handle task activity from renderer (user interaction)
  ipcMain.on(IPC_CHANNELS.MANAGER_TASK_ACTIVITY, (_event, taskId: string) => {
    // When user interacts with a task, refresh its PR status
    const manager = getManagerProcess();
    if (manager.isRunning()) {
      manager.refreshTask(taskId);
    }
  });

  console.log('[ManagerHandlers] IPC handlers registered');
}

/**
 * Cleanup manager handlers on app quit
 */
export function cleanupManagerHandlers(): void {
  const manager = getManagerProcess();
  manager.stop();
}
