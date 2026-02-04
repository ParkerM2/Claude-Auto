import { EventEmitter } from 'events';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { ChildProcess } from 'child_process';
import {
  BuildProgress,
  ProcessOutputData,
  QAReport,
  WorktreeStatus,
  CLIResponse,
  SpecListItem
} from '../types';

/**
 * Output line types that can be parsed from backend
 */
export type OutputLineType =
  | 'progress'
  | 'error'
  | 'warning'
  | 'info'
  | 'debug'
  | 'json'
  | 'plain';

/**
 * Parsed output line with type and content
 */
export interface ParsedOutputLine {
  type: OutputLineType;
  content: string;
  timestamp: Date;
  data?: unknown;
}

/**
 * Process health status
 */
export interface ProcessHealth {
  isRunning: boolean;
  specId: string;
  startTime: Date;
  lastOutput?: Date;
  pid?: number;
  isHealthy: boolean;
  stallDuration?: number; // milliseconds since last output
}

/**
 * Backend configuration options
 */
export interface BackendConfig {
  pythonPath?: string;
  backendPath?: string;
  workspaceRoot?: string;
  autoClaudeDir?: string;
  environmentVariables?: Record<string, string>;
  healthCheckInterval?: number; // milliseconds
  stallThreshold?: number; // milliseconds to consider process stalled
}

/**
 * Process manager for backend lifecycle and output parsing
 *
 * Manages:
 * - Backend process environment setup
 * - Python path detection and validation
 * - Sophisticated output parsing (JSON, progress, errors)
 * - Process health monitoring
 * - Environment variable configuration
 *
 * Pattern from: apps/frontend/src/main/agent/agent-process.ts
 */
export class ProcessManager extends EventEmitter {
  private config: BackendConfig;
  private processHealth: Map<string, ProcessHealth>;
  private healthCheckTimer?: NodeJS.Timeout;
  private outputBuffers: Map<string, string>;

  constructor(config: BackendConfig = {}) {
    super();
    this.config = {
      healthCheckInterval: 5000, // 5 seconds
      stallThreshold: 60000, // 60 seconds
      ...config
    };
    this.processHealth = new Map();
    this.outputBuffers = new Map();
  }

  /**
   * Configure the process manager
   */
  configure(config: Partial<BackendConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Get Python path with fallback detection
   * Tries: configured path → system python → python3
   */
  getPythonPath(): string {
    if (this.config.pythonPath && this.validatePythonPath(this.config.pythonPath)) {
      return this.config.pythonPath;
    }

    // Try common Python executable names
    const pythonNames = process.platform === 'win32'
      ? ['python', 'python3', 'py']
      : ['python3', 'python'];

    for (const name of pythonNames) {
      if (this.commandExists(name)) {
        return name;
      }
    }

    // Fallback to 'python' - will fail later if not found
    return 'python';
  }

  /**
   * Validate that a Python path exists and is executable
   */
  private validatePythonPath(pythonPath: string): boolean {
    try {
      // Check if it's an absolute path that exists
      if (path.isAbsolute(pythonPath)) {
        return fs.existsSync(pythonPath);
      }
      // Check if it's a command in PATH
      return this.commandExists(pythonPath);
    } catch {
      return false;
    }
  }

  /**
   * Check if a command exists in PATH
   */
  private commandExists(command: string): boolean {
    try {
      const { execSync } = require('child_process');
      const checkCommand = process.platform === 'win32'
        ? `where ${command}`
        : `which ${command}`;
      execSync(checkCommand, { stdio: 'ignore' });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get backend CLI path
   * Resolves to apps/backend/run.py relative to workspace
   */
  getBackendPath(): string {
    if (this.config.backendPath) {
      return this.config.backendPath;
    }

    const workspaceRoot = this.config.workspaceRoot || process.cwd();
    return path.join(workspaceRoot, 'apps', 'backend', 'run.py');
  }

  /**
   * Get .auto-claude directory path
   */
  getAutoClaudeDir(): string {
    if (this.config.autoClaudeDir) {
      return this.config.autoClaudeDir;
    }

    const workspaceRoot = this.config.workspaceRoot || process.cwd();
    return path.join(workspaceRoot, '.auto-claude');
  }

  /**
   * Setup process environment variables
   * Includes Python unbuffered mode, PATH augmentation, etc.
   */
  setupEnvironment(extraEnv: Record<string, string> = {}): NodeJS.ProcessEnv {
    const env: NodeJS.ProcessEnv = {
      ...process.env,
      ...this.config.environmentVariables,
      ...extraEnv
    };

    // Ensure unbuffered output for real-time streaming
    env.PYTHONUNBUFFERED = '1';

    // Set Auto Claude directory
    env.AUTO_CLAUDE_DIR = this.getAutoClaudeDir();

    // Add workspace root
    if (this.config.workspaceRoot) {
      env.WORKSPACE_ROOT = this.config.workspaceRoot;
    }

    return env;
  }

  /**
   * Register a process for health monitoring
   */
  registerProcess(specId: string, proc: ChildProcess): void {
    const health: ProcessHealth = {
      isRunning: true,
      specId,
      startTime: new Date(),
      lastOutput: new Date(),
      pid: proc.pid,
      isHealthy: true
    };

    this.processHealth.set(specId, health);
    this.outputBuffers.set(specId, '');

    // Start health monitoring if not already running
    if (!this.healthCheckTimer) {
      this.startHealthMonitoring();
    }

    // Update health on process exit
    proc.on('exit', () => {
      const h = this.processHealth.get(specId);
      if (h) {
        h.isRunning = false;
        this.processHealth.set(specId, h);
      }
    });
  }

  /**
   * Unregister a process from health monitoring
   */
  unregisterProcess(specId: string): void {
    this.processHealth.delete(specId);
    this.outputBuffers.delete(specId);

    // Stop health monitoring if no processes remain
    if (this.processHealth.size === 0 && this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = undefined;
    }
  }

  /**
   * Update process health when output is received
   */
  updateProcessOutput(specId: string): void {
    const health = this.processHealth.get(specId);
    if (health) {
      health.lastOutput = new Date();
      health.isHealthy = true;
      health.stallDuration = 0;
      this.processHealth.set(specId, health);
    }
  }

  /**
   * Get health status for a process
   */
  getProcessHealth(specId: string): ProcessHealth | undefined {
    return this.processHealth.get(specId);
  }

  /**
   * Start periodic health monitoring
   */
  private startHealthMonitoring(): void {
    if (this.healthCheckTimer) {
      return;
    }

    this.healthCheckTimer = setInterval(() => {
      const now = Date.now();

      this.processHealth.forEach((health, specId) => {
        if (!health.isRunning) {
          return;
        }

        const timeSinceOutput = health.lastOutput
          ? now - health.lastOutput.getTime()
          : now - health.startTime.getTime();

        health.stallDuration = timeSinceOutput;

        // Check if process has stalled
        const threshold = this.config.stallThreshold || 60000;
        if (timeSinceOutput > threshold) {
          health.isHealthy = false;
          this.emit('process-stalled', {
            specId,
            stallDuration: timeSinceOutput,
            health
          });
        }

        this.processHealth.set(specId, health);
      });
    }, this.config.healthCheckInterval || 5000);
  }

  /**
   * Parse output line by line, identifying type and extracting data
   */
  parseOutputLine(line: string): ParsedOutputLine {
    const trimmed = line.trim();
    const timestamp = new Date();

    // Try to parse as JSON first
    if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
      try {
        const data = JSON.parse(trimmed);

        // Check for progress updates
        if (data.type === 'progress' || data.phase) {
          return {
            type: 'progress',
            content: trimmed,
            timestamp,
            data
          };
        }

        // Generic JSON data
        return {
          type: 'json',
          content: trimmed,
          timestamp,
          data
        };
      } catch {
        // Not valid JSON, continue with other checks
      }
    }

    // Check for error patterns
    if (trimmed.match(/^(ERROR|Error|error):/i)) {
      return {
        type: 'error',
        content: trimmed,
        timestamp
      };
    }

    // Check for warning patterns
    if (trimmed.match(/^(WARNING|Warning|warning):/i)) {
      return {
        type: 'warning',
        content: trimmed,
        timestamp
      };
    }

    // Check for debug patterns
    if (trimmed.match(/^(DEBUG|Debug|debug):/i)) {
      return {
        type: 'debug',
        content: trimmed,
        timestamp
      };
    }

    // Check for info patterns
    if (trimmed.match(/^(INFO|Info|info):/i)) {
      return {
        type: 'info',
        content: trimmed,
        timestamp
      };
    }

    // Default to plain text
    return {
      type: 'plain',
      content: trimmed,
      timestamp
    };
  }

  /**
   * Parse output stream with buffering for incomplete lines
   * Returns complete lines and updates buffer
   */
  parseOutputStream(specId: string, data: string): ParsedOutputLine[] {
    // Get existing buffer
    const buffer = this.outputBuffers.get(specId) || '';

    // Combine buffer with new data
    const combined = buffer + data;

    // Split into lines
    const lines = combined.split('\n');

    // Last element might be incomplete - keep it in buffer
    const incomplete = lines.pop() || '';
    this.outputBuffers.set(specId, incomplete);

    // Parse complete lines
    return lines
      .filter(line => line.trim().length > 0)
      .map(line => this.parseOutputLine(line));
  }

  /**
   * Parse progress update from JSON data
   */
  parseProgressUpdate(specId: string, data: unknown): BuildProgress | null {
    if (!data || typeof data !== 'object') {
      return null;
    }

    const obj = data as Record<string, unknown>;

    // Check if this looks like a progress update
    if (!obj.phase && obj.type !== 'progress') {
      return null;
    }

    try {
      const progress: BuildProgress = {
        specId,
        specName: (obj.specName as string) || specId,
        phase: (obj.phase as BuildProgress['phase']) || 'idle',
        phaseProgress: (obj.phaseProgress as number) || 0,
        overallProgress: (obj.overallProgress as number) || 0,
        currentSubtask: obj.currentSubtask as string | undefined,
        currentSubtaskId: obj.currentSubtaskId as string | undefined,
        completedSubtasks: (obj.completedSubtasks as number) || 0,
        totalSubtasks: (obj.totalSubtasks as number) || 0,
        message: obj.message as string | undefined,
        timestamp: (obj.timestamp as string) || new Date().toISOString(),
        completedPhases: obj.completedPhases as string[] | undefined
      };

      return progress;
    } catch {
      return null;
    }
  }

  /**
   * Parse CLI response from JSON output
   */
  parseCliResponse<T>(output: string): CLIResponse<T> | null {
    try {
      const lines = output.trim().split('\n');

      // Look for JSON response (usually the last complete JSON object)
      for (let i = lines.length - 1; i >= 0; i--) {
        const line = lines[i].trim();
        if (line.startsWith('{') && line.endsWith('}')) {
          const response = JSON.parse(line) as CLIResponse<T>;
          if ('success' in response) {
            return response;
          }
        }
      }

      return null;
    } catch {
      return null;
    }
  }

  /**
   * Extract error message from output
   */
  extractErrorMessage(output: string): string {
    const lines = output.split('\n');

    // Look for error lines
    const errorLines = lines.filter(line =>
      line.match(/^(ERROR|Error|error|Exception|Traceback):/i)
    );

    if (errorLines.length > 0) {
      return errorLines.join('\n');
    }

    // If no explicit errors, return last few lines
    return lines.slice(-5).join('\n');
  }

  /**
   * Check if output contains an error
   */
  hasError(output: string): boolean {
    return output.match(/(ERROR|Error|error|Exception|Traceback|Failed|failed)/i) !== null;
  }

  /**
   * Get system information for debugging
   */
  getSystemInfo(): Record<string, string> {
    return {
      platform: process.platform,
      arch: process.arch,
      nodeVersion: process.version,
      pythonPath: this.getPythonPath(),
      backendPath: this.getBackendPath(),
      autoClaudeDir: this.getAutoClaudeDir(),
      workspaceRoot: this.config.workspaceRoot || process.cwd(),
      homeDir: os.homedir(),
      tmpDir: os.tmpdir()
    };
  }

  /**
   * Dispose resources and stop monitoring
   */
  dispose(): void {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = undefined;
    }

    this.processHealth.clear();
    this.outputBuffers.clear();
    this.removeAllListeners();
  }
}
