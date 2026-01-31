/**
 * Manager Process Manager
 *
 * Manages the lifecycle of the Manager agent subprocess that monitors
 * PR status for tasks with linked PRs.
 *
 * The manager agent runs as a long-lived background process that:
 * - Polls GitHub PRs for status changes
 * - Emits status updates via stdout using __MANAGER_EVENT__:{json} protocol
 * - Receives commands via stdin (JSON-lines format)
 */

import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import { EventEmitter } from 'events';
import { parsePythonCommand } from '../python-detector';
import { getConfiguredPythonPath } from '../python-env-manager';
import { killProcessGracefully, isWindows } from '../platform';
import type { PRStatusInfo } from '../../shared/types/task';

// ESM-compatible __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Monitored task info for tracking
 */
interface MonitoredTask {
  taskId: string;
  prUrl: string;
}

/**
 * Event types emitted by the ManagerProcessManager
 */
export interface ManagerEvents {
  'pr-status-update': (taskId: string, prStatus: PRStatusInfo) => void;
  'manager-started': () => void;
  'manager-stopped': () => void;
  'manager-error': (error: string) => void;
}

/**
 * Manager Process Manager
 *
 * Handles spawning, communication, and lifecycle of the Manager agent
 * Python subprocess.
 */
export class ManagerProcessManager extends EventEmitter {
  private process: ChildProcess | null = null;
  private monitoredTasks: Map<string, MonitoredTask> = new Map();
  private isStarted = false;
  private projectPath: string | null = null;
  private backendPath: string | null = null;
  private stdoutBuffer = '';

  constructor() {
    super();
  }

  /**
   * Configure the manager with paths
   */
  configure(projectPath: string, backendPath: string): void {
    this.projectPath = projectPath;
    this.backendPath = backendPath;
  }

  /**
   * Start the manager subprocess
   */
  async start(): Promise<boolean> {
    if (this.isStarted || this.process) {
      console.log('[ManagerProcess] Already running');
      return true;
    }

    if (!this.backendPath) {
      console.error('[ManagerProcess] Backend path not configured');
      return false;
    }

    const managerScript = path.join(this.backendPath, 'agents', 'manager.py');
    const pythonPath = getConfiguredPythonPath();

    try {
      const [pythonCommand, pythonBaseArgs] = parsePythonCommand(pythonPath);
      const args = [
        ...pythonBaseArgs,
        managerScript,
        '--project', this.projectPath || '.',
        '--poll-interval', '60'
      ];

      console.log('[ManagerProcess] Starting manager subprocess:', pythonCommand, args.join(' '));

      this.process = spawn(pythonCommand, args, {
        cwd: this.backendPath,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: {
          ...process.env,
          PYTHONUNBUFFERED: '1',
          PYTHONIOENCODING: 'utf-8'
        }
      });

      this.setupProcessHandlers();
      this.isStarted = true;

      // Send any pending tasks to monitor
      for (const task of this.monitoredTasks.values()) {
        this.sendCommand({ type: 'add_task', taskId: task.taskId, prUrl: task.prUrl });
      }

      console.log('[ManagerProcess] Manager subprocess started, PID:', this.process.pid);
      return true;

    } catch (error) {
      console.error('[ManagerProcess] Failed to start manager:', error);
      this.emit('manager-error', error instanceof Error ? error.message : String(error));
      return false;
    }
  }

  /**
   * Stop the manager subprocess gracefully
   */
  stop(): void {
    if (!this.process) {
      console.log('[ManagerProcess] Not running');
      return;
    }

    console.log('[ManagerProcess] Stopping manager subprocess');

    // Send stop command first
    this.sendCommand({ type: 'stop' });

    // Give it a moment to clean up, then force kill
    setTimeout(() => {
      if (this.process) {
        killProcessGracefully(this.process, {
          debugPrefix: '[ManagerProcess]',
          debug: process.env.DEBUG === 'true'
        });
        this.process = null;
      }
    }, 1000);

    this.isStarted = false;
    this.emit('manager-stopped');
  }

  /**
   * Add a task to monitoring
   */
  addTask(taskId: string, prUrl: string): void {
    this.monitoredTasks.set(taskId, { taskId, prUrl });
    console.log('[ManagerProcess] Added task to monitoring:', taskId, prUrl);

    if (this.isStarted && this.process) {
      this.sendCommand({ type: 'add_task', taskId, prUrl });
    }
  }

  /**
   * Remove a task from monitoring
   */
  removeTask(taskId: string): void {
    this.monitoredTasks.delete(taskId);
    console.log('[ManagerProcess] Removed task from monitoring:', taskId);

    if (this.isStarted && this.process) {
      this.sendCommand({ type: 'remove_task', taskId });
    }
  }

  /**
   * Force immediate refresh of a task's PR status
   */
  refreshTask(taskId: string): void {
    if (this.isStarted && this.process) {
      this.sendCommand({ type: 'refresh_task', taskId });
    }
  }

  /**
   * Get the list of monitored tasks
   */
  getMonitoredTasks(): MonitoredTask[] {
    return Array.from(this.monitoredTasks.values());
  }

  /**
   * Check if manager is running
   */
  isRunning(): boolean {
    return this.isStarted && this.process !== null;
  }

  /**
   * Send a command to the manager subprocess via stdin
   */
  private sendCommand(cmd: Record<string, unknown>): void {
    if (!this.process || !this.process.stdin) {
      console.warn('[ManagerProcess] Cannot send command, process not running');
      return;
    }

    try {
      const line = JSON.stringify(cmd) + '\n';
      this.process.stdin.write(line);
    } catch (error) {
      console.error('[ManagerProcess] Failed to send command:', error);
    }
  }

  /**
   * Setup event handlers for the subprocess
   */
  private setupProcessHandlers(): void {
    if (!this.process) return;

    this.process.stdout?.on('data', (data: Buffer) => {
      this.handleStdout(data.toString('utf8'));
    });

    this.process.stderr?.on('data', (data: Buffer) => {
      // Log stderr but don't treat as error - manager logs to stderr
      const text = data.toString('utf8');
      console.log('[ManagerProcess:stderr]', text.trim());
    });

    this.process.on('exit', (code: number | null) => {
      console.log('[ManagerProcess] Process exited with code:', code);
      this.process = null;
      this.isStarted = false;
      this.emit('manager-stopped');
    });

    this.process.on('error', (err: Error) => {
      console.error('[ManagerProcess] Process error:', err.message);
      this.emit('manager-error', err.message);
    });
  }

  /**
   * Handle stdout data from the subprocess
   */
  private handleStdout(data: string): void {
    this.stdoutBuffer += data;

    // Process complete lines
    const lines = this.stdoutBuffer.split('\n');
    this.stdoutBuffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim()) continue;

      // Check for manager event protocol
      if (line.includes('__MANAGER_EVENT__:')) {
        const jsonStart = line.indexOf('__MANAGER_EVENT__:') + '__MANAGER_EVENT__:'.length;
        const jsonStr = line.slice(jsonStart).trim();

        try {
          const event = JSON.parse(jsonStr);
          this.handleManagerEvent(event);
        } catch (e) {
          console.warn('[ManagerProcess] Failed to parse event JSON:', jsonStr);
        }
      }
    }
  }

  /**
   * Handle a manager event from the subprocess
   */
  private handleManagerEvent(event: Record<string, unknown>): void {
    const eventType = event.type as string;

    switch (eventType) {
      case 'pr_status': {
        const taskId = event.taskId as string;
        const prStatusRaw = event.prStatus as Record<string, unknown>;

        // Convert snake_case to camelCase
        const prStatus: PRStatusInfo = {
          prNumber: prStatusRaw.pr_number as number,
          state: prStatusRaw.state as PRStatusInfo['state'],
          reviewDecision: prStatusRaw.review_decision as PRStatusInfo['reviewDecision'],
          ciStatus: prStatusRaw.ci_status as PRStatusInfo['ciStatus'],
          isDraft: prStatusRaw.is_draft as boolean,
          mergeable: prStatusRaw.mergeable as PRStatusInfo['mergeable'],
          lastUpdated: prStatusRaw.last_updated as string
        };

        console.log('[ManagerProcess] PR status update for task:', taskId, prStatus);
        this.emit('pr-status-update', taskId, prStatus);
        break;
      }

      case 'started':
        console.log('[ManagerProcess] Manager agent started');
        this.emit('manager-started');
        break;

      case 'stopped':
        console.log('[ManagerProcess] Manager agent stopped');
        break;

      case 'pong':
        console.log('[ManagerProcess] Pong received');
        break;

      default:
        console.log('[ManagerProcess] Unknown event type:', eventType);
    }
  }
}

// Singleton instance
let managerProcessInstance: ManagerProcessManager | null = null;

/**
 * Get the singleton ManagerProcessManager instance
 */
export function getManagerProcess(): ManagerProcessManager {
  if (!managerProcessInstance) {
    managerProcessInstance = new ManagerProcessManager();
  }
  return managerProcessInstance;
}

/**
 * Initialize the manager process with project and backend paths
 */
export function initializeManagerProcess(projectPath: string, backendPath: string): ManagerProcessManager {
  const manager = getManagerProcess();
  manager.configure(projectPath, backendPath);
  return manager;
}
