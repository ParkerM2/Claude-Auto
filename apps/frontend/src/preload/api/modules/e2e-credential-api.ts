/**
 * E2E Credential API
 *
 * Provides secure credential storage and retrieval for E2E testing
 * authentication flows using Electron's safeStorage API.
 */

import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../../shared/constants/ipc';
import type { IPCResult } from '../../../shared/types/common';

export interface E2ECredentialAPI {
  /**
   * Store an E2E testing credential securely for a project.
   * Uses Electron's safeStorage API for encryption.
   *
   * @param projectPath - The path to the project
   * @param password - The password/credential to store
   * @returns IPCResult indicating success or failure
   */
  e2eStoreCredential: (projectPath: string, password: string) => Promise<IPCResult<boolean>>;

  /**
   * Retrieve a previously stored E2E testing credential for a project.
   * Uses Electron's safeStorage API for decryption.
   *
   * @param projectPath - The path to the project
   * @returns IPCResult with the decrypted credential or null if not found
   */
  e2eRetrieveCredential: (projectPath: string) => Promise<IPCResult<string | null>>;
}

export function createE2ECredentialAPI(): E2ECredentialAPI {
  return {
    e2eStoreCredential: (projectPath: string, password: string) =>
      ipcRenderer.invoke(IPC_CHANNELS.E2E_STORE_CREDENTIAL, projectPath, password),

    e2eRetrieveCredential: (projectPath: string) =>
      ipcRenderer.invoke(IPC_CHANNELS.E2E_RETRIEVE_CREDENTIAL, projectPath),
  };
}
