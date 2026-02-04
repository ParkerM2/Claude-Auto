import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import { EventEmitter } from 'events';
import * as vscode from 'vscode';
import {
  Spec,
  SpecListItem,
  QAReport,
  WorktreeStatus,
  CLIResponse,
  BackendCommand,
  BackendCommandOptions,
  ProcessOutputData,
  ProcessExitData,
  BuildProgress
} from '../types';

/**
 * Client for communicating with Auto Claude Python backend CLI
 *
 * Follows the pattern from apps/frontend/src/main/agent/agent-process.ts
 * for process spawning and lifecycle management.
 */
export class CLIClient extends EventEmitter {
  private pythonPath: string;
  private backendPath: string;
  private activeProcesses: Map<string, ChildProcess>;
  private outputChannel: vscode.OutputChannel;

  constructor(pythonPath?: string, backendPath?: string) {
    super();

    // Default to system Python if not provided
    this.pythonPath = pythonPath || 'python';

    // Default backend path: apps/backend/run.py relative to workspace root
    this.backendPath = backendPath || this.findBackendPath();

    this.activeProcesses = new Map();
    this.outputChannel = vscode.window.createOutputChannel('Auto Claude');
  }

  /**
   * Find the backend path relative to workspace root
   * Looks for apps/backend/run.py in workspace folders
   */
  private findBackendPath(): string {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
      return path.join('apps', 'backend', 'run.py');
    }
    return path.join(workspaceFolder.uri.fsPath, 'apps', 'backend', 'run.py');
  }

  /**
   * Build command arguments for backend CLI
   */
  private buildCommandArgs(command: BackendCommand, options: BackendCommandOptions = {}): string[] {
    const args: string[] = [this.backendPath];

    // Add command-specific flags
    switch (command) {
      case 'list':
        args.push('--list');
        break;
      case 'run':
        if (options.spec) {
          args.push('--spec', options.spec);
        }
        break;
      case 'review':
        if (options.spec) {
          args.push('--spec', options.spec, '--review');
        }
        break;
      case 'merge':
        if (options.spec) {
          args.push('--spec', options.spec, '--merge');
        }
        break;
      case 'discard':
        if (options.spec) {
          args.push('--spec', options.spec, '--discard');
        }
        break;
      case 'qa':
        if (options.spec) {
          args.push('--spec', options.spec, '--qa');
        }
        break;
      case 'qa-status':
        if (options.spec) {
          args.push('--spec', options.spec, '--qa-status');
        }
        break;
      case 'create-pr':
        if (options.spec) {
          args.push('--spec', options.spec, '--create-pr');
          if (options.prTarget) {
            args.push('--target', options.prTarget);
          }
          if (options.prTitle) {
            args.push('--title', options.prTitle);
          }
          if (options.prDraft) {
            args.push('--draft');
          }
        }
        break;
    }

    // Add common options
    if (options.projectDir) {
      args.push('--project-dir', options.projectDir);
    }
    if (options.model) {
      args.push('--model', options.model);
    }
    if (options.verbose) {
      args.push('--verbose');
    }
    if (options.isolated) {
      args.push('--isolated');
    }
    if (options.direct) {
      args.push('--direct');
    }
    if (options.maxIterations) {
      args.push('--max-iterations', options.maxIterations.toString());
    }

    return args;
  }

  /**
   * Spawn a backend process for the given command
   * Returns a promise that resolves with the process output
   */
  private spawnProcess(
    command: BackendCommand,
    options: BackendCommandOptions = {}
  ): Promise<string> {
    return new Promise((resolve, reject) => {
      const args = this.buildCommandArgs(command, options);
      const specId = options.spec || 'unknown';

      this.outputChannel.appendLine(`[CLI] Executing: ${this.pythonPath} ${args.join(' ')}`);

      const proc = spawn(this.pythonPath, args, {
        cwd: options.projectDir || vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
        env: {
          ...process.env,
          PYTHONUNBUFFERED: '1', // Ensure real-time output
        },
        shell: false,
      });

      // Store active process
      this.activeProcesses.set(specId, proc);

      let stdout = '';
      let stderr = '';

      // Handle stdout
      proc.stdout?.on('data', (data: Buffer) => {
        const output = data.toString();
        stdout += output;

        // Emit output event for real-time updates
        const outputData: ProcessOutputData = {
          specId,
          type: 'stdout',
          data: output,
          timestamp: new Date().toISOString(),
        };
        this.emit('output', outputData);

        this.outputChannel.append(output);

        // Parse progress updates if present
        this.parseProgressUpdates(output, specId);
      });

      // Handle stderr
      proc.stderr?.on('data', (data: Buffer) => {
        const output = data.toString();
        stderr += output;

        const outputData: ProcessOutputData = {
          specId,
          type: 'stderr',
          data: output,
          timestamp: new Date().toISOString(),
        };
        this.emit('output', outputData);

        this.outputChannel.append(`[ERROR] ${output}`);
      });

      // Handle process exit
      proc.on('exit', (code, signal) => {
        this.activeProcesses.delete(specId);

        const exitData: ProcessExitData = {
          specId,
          code,
          signal,
          timestamp: new Date().toISOString(),
        };
        this.emit('exit', exitData);

        if (code === 0) {
          this.outputChannel.appendLine(`[CLI] Process exited successfully`);
          resolve(stdout);
        } else {
          const error = new Error(
            `Process exited with code ${code}\nStderr: ${stderr}\nStdout: ${stdout}`
          );
          this.outputChannel.appendLine(`[CLI] Process failed with code ${code}`);
          reject(error);
        }
      });

      // Handle process error
      proc.on('error', (error) => {
        this.activeProcesses.delete(specId);
        this.outputChannel.appendLine(`[CLI] Process error: ${error.message}`);
        reject(error);
      });
    });
  }

  /**
   * Parse progress updates from stdout
   * Looks for JSON lines with progress information
   */
  private parseProgressUpdates(output: string, specId: string): void {
    // Look for JSON lines in output (backend may emit progress as JSON)
    const lines = output.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
        try {
          const data = JSON.parse(trimmed);
          // Check if this is a progress update
          if (data.type === 'progress' || data.phase) {
            const progress: BuildProgress = {
              specId,
              specName: data.specName || specId,
              phase: data.phase || 'idle',
              phaseProgress: data.phaseProgress || 0,
              overallProgress: data.overallProgress || 0,
              currentSubtask: data.currentSubtask,
              currentSubtaskId: data.currentSubtaskId,
              completedSubtasks: data.completedSubtasks || 0,
              totalSubtasks: data.totalSubtasks || 0,
              message: data.message,
              timestamp: data.timestamp || new Date().toISOString(),
              completedPhases: data.completedPhases,
            };
            this.emit('progress', progress);
          }
        } catch (e) {
          // Not a JSON line, ignore
        }
      }
    }
  }

  /**
   * List all available specs
   */
  async listSpecs(): Promise<SpecListItem[]> {
    try {
      const output = await this.spawnProcess('list');

      // Parse JSON response from backend
      // Backend should return JSON array of specs
      const response: CLIResponse<SpecListItem[]> = JSON.parse(output.trim());

      if (!response.success || !response.data) {
        throw new Error(response.error || 'Failed to list specs');
      }

      return response.data;
    } catch (error) {
      this.outputChannel.appendLine(`[CLI] Failed to list specs: ${error}`);
      throw error;
    }
  }

  /**
   * Run a spec build
   */
  async runSpec(specId: string, options: BackendCommandOptions = {}): Promise<void> {
    try {
      await this.spawnProcess('run', { ...options, spec: specId });
      vscode.window.showInformationMessage(`Build started for spec: ${specId}`);
    } catch (error) {
      this.outputChannel.appendLine(`[CLI] Failed to run spec: ${error}`);
      vscode.window.showErrorMessage(`Failed to run spec ${specId}: ${error}`);
      throw error;
    }
  }

  /**
   * Get QA status for a spec
   */
  async getQAStatus(specId: string, options: BackendCommandOptions = {}): Promise<QAReport> {
    try {
      const output = await this.spawnProcess('qa-status', { ...options, spec: specId });

      const response: CLIResponse<QAReport> = JSON.parse(output.trim());

      if (!response.success || !response.data) {
        throw new Error(response.error || 'Failed to get QA status');
      }

      return response.data;
    } catch (error) {
      this.outputChannel.appendLine(`[CLI] Failed to get QA status: ${error}`);
      throw error;
    }
  }

  /**
   * Review worktree changes
   */
  async reviewWorktree(specId: string, options: BackendCommandOptions = {}): Promise<WorktreeStatus> {
    try {
      const output = await this.spawnProcess('review', { ...options, spec: specId });

      const response: CLIResponse<WorktreeStatus> = JSON.parse(output.trim());

      if (!response.success || !response.data) {
        throw new Error(response.error || 'Failed to review worktree');
      }

      return response.data;
    } catch (error) {
      this.outputChannel.appendLine(`[CLI] Failed to review worktree: ${error}`);
      throw error;
    }
  }

  /**
   * Merge worktree changes into main branch
   */
  async mergeWorktree(specId: string, options: BackendCommandOptions = {}): Promise<void> {
    try {
      await this.spawnProcess('merge', { ...options, spec: specId });
      vscode.window.showInformationMessage(`Worktree merged for spec: ${specId}`);
    } catch (error) {
      this.outputChannel.appendLine(`[CLI] Failed to merge worktree: ${error}`);
      vscode.window.showErrorMessage(`Failed to merge worktree for ${specId}: ${error}`);
      throw error;
    }
  }

  /**
   * Discard worktree changes
   */
  async discardWorktree(specId: string, options: BackendCommandOptions = {}): Promise<void> {
    try {
      await this.spawnProcess('discard', { ...options, spec: specId });
      vscode.window.showInformationMessage(`Worktree discarded for spec: ${specId}`);
    } catch (error) {
      this.outputChannel.appendLine(`[CLI] Failed to discard worktree: ${error}`);
      vscode.window.showErrorMessage(`Failed to discard worktree for ${specId}: ${error}`);
      throw error;
    }
  }

  /**
   * Run QA validation for a spec
   */
  async runQA(specId: string, options: BackendCommandOptions = {}): Promise<QAReport> {
    try {
      const output = await this.spawnProcess('qa', { ...options, spec: specId });

      const response: CLIResponse<QAReport> = JSON.parse(output.trim());

      if (!response.success || !response.data) {
        throw new Error(response.error || 'QA validation failed');
      }

      vscode.window.showInformationMessage(`QA completed for spec: ${specId}`);
      return response.data;
    } catch (error) {
      this.outputChannel.appendLine(`[CLI] Failed to run QA: ${error}`);
      vscode.window.showErrorMessage(`QA failed for ${specId}: ${error}`);
      throw error;
    }
  }

  /**
   * Create a pull request for a spec
   */
  async createPR(specId: string, options: BackendCommandOptions = {}): Promise<void> {
    try {
      await this.spawnProcess('create-pr', { ...options, spec: specId });
      vscode.window.showInformationMessage(`Pull request created for spec: ${specId}`);
    } catch (error) {
      this.outputChannel.appendLine(`[CLI] Failed to create PR: ${error}`);
      vscode.window.showErrorMessage(`Failed to create PR for ${specId}: ${error}`);
      throw error;
    }
  }

  /**
   * Kill a running process for a spec
   */
  killProcess(specId: string): boolean {
    const proc = this.activeProcesses.get(specId);
    if (proc) {
      proc.kill('SIGTERM');
      this.activeProcesses.delete(specId);
      this.outputChannel.appendLine(`[CLI] Killed process for spec: ${specId}`);
      return true;
    }
    return false;
  }

  /**
   * Kill all active processes
   */
  killAllProcesses(): void {
    this.activeProcesses.forEach((proc, specId) => {
      proc.kill('SIGTERM');
      this.outputChannel.appendLine(`[CLI] Killed process for spec: ${specId}`);
    });
    this.activeProcesses.clear();
  }

  /**
   * Check if a process is running for a spec
   */
  isProcessRunning(specId: string): boolean {
    return this.activeProcesses.has(specId);
  }

  /**
   * Show the output channel
   */
  showOutput(): void {
    this.outputChannel.show();
  }

  /**
   * Dispose resources
   */
  dispose(): void {
    this.killAllProcesses();
    this.outputChannel.dispose();
    this.removeAllListeners();
  }
}
