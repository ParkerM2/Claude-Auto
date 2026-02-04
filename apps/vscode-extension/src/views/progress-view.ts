import * as vscode from 'vscode';
import { CLIClient } from '../backend/cli-client';
import { BuildProgress, ProcessExitData } from '../types';

/**
 * Active progress tracking for a spec
 */
interface ActiveProgress {
  specId: string;
  specName: string;
  progress: vscode.Progress<{ message?: string; increment?: number }>;
  resolve: () => void;
  lastProgress: number;
  startTime: number;
}

/**
 * Progress view for Auto Claude builds
 *
 * Provides real-time progress updates in VS Code UI:
 * - Progress notifications with status updates
 * - Status bar integration
 * - Build phase tracking
 * - Completion notifications
 *
 * Listens to CLIClient events and displays progress using VS Code's progress API.
 */
export class ProgressView implements vscode.Disposable {
  private cliClient: CLIClient;
  private activeProgresses: Map<string, ActiveProgress>;
  private statusBarItem: vscode.StatusBarItem;
  private disposables: vscode.Disposable[] = [];

  constructor(cliClient: CLIClient) {
    this.cliClient = cliClient;
    this.activeProgresses = new Map();

    // Create status bar item
    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      100
    );
    this.statusBarItem.command = 'autoClaude.showOutput';
    this.disposables.push(this.statusBarItem);

    // Register event listeners
    this.registerEventListeners();
  }

  /**
   * Register listeners for CLIClient events
   */
  private registerEventListeners(): void {
    // Listen to progress updates from backend
    this.cliClient.on('progress', (progress: BuildProgress) => {
      this.handleProgressUpdate(progress);
    });

    // Listen to process exit events
    this.cliClient.on('exit', (exitData: ProcessExitData) => {
      this.handleProcessExit(exitData);
    });

    // Listen to output events for additional context
    this.cliClient.on('output', (outputData) => {
      // Update status bar with latest activity
      if (outputData.type === 'stdout' && outputData.data.trim()) {
        this.updateStatusBar(`Auto Claude: Processing ${outputData.specId}...`);
      }
    });
  }

  /**
   * Start progress tracking for a spec build
   */
  async startProgress(specId: string, specName: string): Promise<void> {
    // Check if progress already exists
    if (this.activeProgresses.has(specId)) {
      return;
    }

    // Show progress notification
    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: `Building: ${specName}`,
        cancellable: true,
      },
      async (progress, token) => {
        return new Promise<void>((resolve) => {
          // Store active progress
          const activeProgress: ActiveProgress = {
            specId,
            specName,
            progress,
            resolve,
            lastProgress: 0,
            startTime: Date.now(),
          };
          this.activeProgresses.set(specId, activeProgress);

          // Initial progress update
          progress.report({ message: 'Initializing build...', increment: 0 });

          // Update status bar
          this.updateStatusBar(`Auto Claude: Building ${specName}...`);

          // Handle cancellation
          token.onCancellationRequested(() => {
            this.cancelProgress(specId);
          });
        });
      }
    );
  }

  /**
   * Handle progress update from backend
   */
  private handleProgressUpdate(buildProgress: BuildProgress): void {
    const activeProgress = this.activeProgresses.get(buildProgress.specId);

    if (!activeProgress) {
      // Start progress tracking if not already started
      void this.startProgress(buildProgress.specId, buildProgress.specName);
      return;
    }

    // Calculate progress increment
    const currentProgress = buildProgress.overallProgress;
    const increment = Math.max(0, currentProgress - activeProgress.lastProgress);
    activeProgress.lastProgress = currentProgress;

    // Format progress message
    const message = this.formatProgressMessage(buildProgress);

    // Report progress
    activeProgress.progress.report({
      message,
      increment,
    });

    // Update status bar
    this.updateStatusBar(
      `Auto Claude: ${buildProgress.specName} - ${buildProgress.phase} (${currentProgress}%)`
    );
  }

  /**
   * Format progress message based on build phase and subtask
   */
  private formatProgressMessage(progress: BuildProgress): string {
    const parts: string[] = [];

    // Add phase information
    switch (progress.phase) {
      case 'planning':
        parts.push('🔍 Planning');
        break;
      case 'coding':
        parts.push('⚙️ Coding');
        break;
      case 'qa_review':
        parts.push('✅ QA Review');
        break;
      case 'qa_fixing':
        parts.push('🔧 Fixing Issues');
        break;
      case 'complete':
        parts.push('✨ Complete');
        break;
      case 'failed':
        parts.push('❌ Failed');
        break;
      default:
        parts.push(`${progress.phase}`);
    }

    // Add subtask information
    if (progress.currentSubtask) {
      parts.push(`- ${progress.currentSubtask}`);
    }

    // Add progress percentage
    if (progress.totalSubtasks > 0) {
      parts.push(
        `(${progress.completedSubtasks}/${progress.totalSubtasks} tasks)`
      );
    }

    return parts.join(' ');
  }

  /**
   * Handle process exit event
   */
  private handleProcessExit(exitData: ProcessExitData): void {
    const activeProgress = this.activeProgresses.get(exitData.specId);

    if (!activeProgress) {
      return;
    }

    // Calculate elapsed time
    const elapsedMs = Date.now() - activeProgress.startTime;
    const elapsedSec = Math.round(elapsedMs / 1000);

    // Show completion notification
    if (exitData.code === 0) {
      // Success
      void vscode.window.showInformationMessage(
        `✅ Build completed successfully for ${activeProgress.specName} (${elapsedSec}s)`
      );
      activeProgress.progress.report({
        message: '✨ Complete!',
        increment: 100 - activeProgress.lastProgress,
      });
    } else {
      // Failure
      void vscode.window.showErrorMessage(
        `❌ Build failed for ${activeProgress.specName} (exit code: ${exitData.code})`
      );
      activeProgress.progress.report({
        message: '❌ Build failed',
        increment: 0,
      });
    }

    // Resolve progress and cleanup
    activeProgress.resolve();
    this.activeProgresses.delete(exitData.specId);

    // Clear status bar if no active builds
    if (this.activeProgresses.size === 0) {
      this.statusBarItem.hide();
    }
  }

  /**
   * Cancel progress for a spec
   */
  private cancelProgress(specId: string): void {
    const activeProgress = this.activeProgresses.get(specId);

    if (!activeProgress) {
      return;
    }

    // Kill the backend process
    const killed = this.cliClient.killProcess(specId);

    if (killed) {
      void vscode.window.showWarningMessage(
        `Build cancelled for ${activeProgress.specName}`
      );
    }

    // Resolve progress and cleanup
    activeProgress.resolve();
    this.activeProgresses.delete(specId);

    // Clear status bar if no active builds
    if (this.activeProgresses.size === 0) {
      this.statusBarItem.hide();
    }
  }

  /**
   * Update status bar with current activity
   */
  private updateStatusBar(text: string): void {
    this.statusBarItem.text = `$(sync~spin) ${text}`;
    this.statusBarItem.show();
  }

  /**
   * Get active progress count
   */
  getActiveProgressCount(): number {
    return this.activeProgresses.size;
  }

  /**
   * Check if a spec build is in progress
   */
  isProgressActive(specId: string): boolean {
    return this.activeProgresses.has(specId);
  }

  /**
   * Stop all active progress tracking
   */
  stopAllProgress(): void {
    this.activeProgresses.forEach((progress, specId) => {
      progress.resolve();
      this.cliClient.killProcess(specId);
    });
    this.activeProgresses.clear();
    this.statusBarItem.hide();
  }

  /**
   * Dispose resources
   */
  dispose(): void {
    this.stopAllProgress();
    this.disposables.forEach((d) => d.dispose());
    this.cliClient.removeAllListeners('progress');
    this.cliClient.removeAllListeners('exit');
    this.cliClient.removeAllListeners('output');
  }
}
