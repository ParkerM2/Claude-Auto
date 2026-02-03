/**
 * Preload script type definitions
 *
 * This file provides TypeScript declarations for the electronAPI methods
 * exposed via the preload script to the renderer process.
 */

import type { IPCResult } from '../shared/types';

/**
 * E2E Testing Credential API
 *
 * Provides secure credential storage and retrieval for E2E testing
 * authentication flows using Electron's safeStorage API.
 */
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

// Re-export the main ElectronAPI type for convenience
export type { ElectronAPI } from './api';
