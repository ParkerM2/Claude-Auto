/**
 * Manager API Module
 *
 * Preload API for the Manager agent that monitors PR status
 * for tasks with linked PRs.
 */

import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../../shared/constants/ipc';
import type { IPCResult } from '../../../shared/types';
import type { PRStatusInfo } from '../../../shared/types/task';

/**
 * PR status update event data
 */
export interface PRStatusUpdateEvent {
  taskId: string;
  prStatus: PRStatusInfo;
}

/**
 * Manager API interface
 */
export interface ManagerAPI {
  // Manager control
  startManager: () => Promise<IPCResult<void>>;
  stopManager: () => Promise<IPCResult<void>>;

  // Task monitoring
  managerAddTask: (taskId: string, prUrl: string) => Promise<IPCResult<void>>;
  managerRemoveTask: (taskId: string) => Promise<IPCResult<void>>;
  managerRefreshTask: (taskId: string) => Promise<IPCResult<void>>;

  // Task activity notification (renderer -> main)
  notifyTaskActivity: (taskId: string) => void;

  // Event listeners
  onPRStatusUpdate: (callback: (event: PRStatusUpdateEvent) => void) => () => void;
}

/**
 * Create the Manager API
 */
export const createManagerAPI = (): ManagerAPI => ({
  // Manager control
  startManager: () => ipcRenderer.invoke(IPC_CHANNELS.MANAGER_START),
  stopManager: () => ipcRenderer.invoke(IPC_CHANNELS.MANAGER_STOP),

  // Task monitoring
  managerAddTask: (taskId: string, prUrl: string) =>
    ipcRenderer.invoke(IPC_CHANNELS.MANAGER_ADD_TASK, taskId, prUrl),
  managerRemoveTask: (taskId: string) =>
    ipcRenderer.invoke(IPC_CHANNELS.MANAGER_REMOVE_TASK, taskId),
  managerRefreshTask: (taskId: string) =>
    ipcRenderer.invoke(IPC_CHANNELS.MANAGER_REFRESH_TASK, taskId),

  // Task activity notification
  notifyTaskActivity: (taskId: string) => {
    ipcRenderer.send(IPC_CHANNELS.MANAGER_TASK_ACTIVITY, taskId);
  },

  // Event listeners
  onPRStatusUpdate: (callback: (event: PRStatusUpdateEvent) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, data: PRStatusUpdateEvent) => {
      callback(data);
    };
    ipcRenderer.on(IPC_CHANNELS.MANAGER_PR_STATUS_UPDATE, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.MANAGER_PR_STATUS_UPDATE, handler);
    };
  }
});
