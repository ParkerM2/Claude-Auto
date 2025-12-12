import { EventEmitter } from 'events';
import path from 'path';
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { spawn, ChildProcess } from 'child_process';
import { app } from 'electron';
import type {
  InsightsSession,
  InsightsChatMessage,
  InsightsChatStatus,
  InsightsStreamChunk
} from '../shared/types';

const INSIGHTS_DIR = 'auto-claude/insights';
const SESSION_FILE = 'session.json';

/**
 * Service for AI-powered codebase insights chat
 */
export class InsightsService extends EventEmitter {
  private pythonPath: string = 'python3';
  private autoBuildSourcePath: string = '';
  private activeSessions: Map<string, ChildProcess> = new Map();
  private sessions: Map<string, InsightsSession> = new Map();

  constructor() {
    super();
  }

  /**
   * Configure paths for Python and auto-claude source
   */
  configure(pythonPath?: string, autoBuildSourcePath?: string): void {
    if (pythonPath) {
      this.pythonPath = pythonPath;
    }
    if (autoBuildSourcePath) {
      this.autoBuildSourcePath = autoBuildSourcePath;
    }
  }

  /**
   * Get the auto-claude source path (detects automatically if not configured)
   */
  private getAutoBuildSourcePath(): string | null {
    if (this.autoBuildSourcePath && existsSync(this.autoBuildSourcePath)) {
      return this.autoBuildSourcePath;
    }

    const possiblePaths = [
      path.resolve(__dirname, '..', '..', '..', 'auto-claude'),
      path.resolve(app.getAppPath(), '..', 'auto-claude'),
      path.resolve(process.cwd(), 'auto-claude')
    ];

    for (const p of possiblePaths) {
      if (existsSync(p) && existsSync(path.join(p, 'VERSION'))) {
        return p;
      }
    }
    return null;
  }

  /**
   * Load environment variables from auto-claude .env file
   */
  private loadAutoBuildEnv(): Record<string, string> {
    const autoBuildSource = this.getAutoBuildSourcePath();
    if (!autoBuildSource) return {};

    const envPath = path.join(autoBuildSource, '.env');
    if (!existsSync(envPath)) return {};

    try {
      const envContent = readFileSync(envPath, 'utf-8');
      const envVars: Record<string, string> = {};

      for (const line of envContent.split('\n')) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) continue;

        const eqIndex = trimmed.indexOf('=');
        if (eqIndex > 0) {
          const key = trimmed.substring(0, eqIndex).trim();
          let value = trimmed.substring(eqIndex + 1).trim();

          if ((value.startsWith('"') && value.endsWith('"')) ||
              (value.startsWith("'") && value.endsWith("'"))) {
            value = value.slice(1, -1);
          }

          envVars[key] = value;
        }
      }

      return envVars;
    } catch {
      return {};
    }
  }

  /**
   * Get insights directory path for a project
   */
  private getInsightsDir(projectPath: string): string {
    return path.join(projectPath, INSIGHTS_DIR);
  }

  /**
   * Get session file path for a project
   */
  private getSessionPath(projectPath: string): string {
    return path.join(this.getInsightsDir(projectPath), SESSION_FILE);
  }

  /**
   * Load session from disk
   */
  loadSession(projectId: string, projectPath: string): InsightsSession | null {
    // Check in-memory cache first
    if (this.sessions.has(projectId)) {
      return this.sessions.get(projectId)!;
    }

    const sessionPath = this.getSessionPath(projectPath);
    if (!existsSync(sessionPath)) {
      return null;
    }

    try {
      const content = readFileSync(sessionPath, 'utf-8');
      const session = JSON.parse(content) as InsightsSession;
      // Convert date strings back to Date objects
      session.createdAt = new Date(session.createdAt);
      session.updatedAt = new Date(session.updatedAt);
      session.messages = session.messages.map(m => ({
        ...m,
        timestamp: new Date(m.timestamp)
      }));
      this.sessions.set(projectId, session);
      return session;
    } catch {
      return null;
    }
  }

  /**
   * Save session to disk
   */
  private saveSession(projectPath: string, session: InsightsSession): void {
    const insightsDir = this.getInsightsDir(projectPath);
    if (!existsSync(insightsDir)) {
      mkdirSync(insightsDir, { recursive: true });
    }

    const sessionPath = this.getSessionPath(projectPath);
    writeFileSync(sessionPath, JSON.stringify(session, null, 2));
    this.sessions.set(session.projectId, session);
  }

  /**
   * Clear session
   */
  clearSession(projectId: string, projectPath: string): void {
    this.sessions.delete(projectId);
    const sessionPath = this.getSessionPath(projectPath);
    if (existsSync(sessionPath)) {
      try {
        // Just reset the session file, not the directory
        writeFileSync(sessionPath, JSON.stringify({
          id: `session-${Date.now()}`,
          projectId,
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date()
        }, null, 2));
      } catch {
        // Ignore errors
      }
    }
  }

  /**
   * Send a message and get AI response
   */
  async sendMessage(projectId: string, projectPath: string, message: string): Promise<void> {
    // Cancel any existing session for this project
    if (this.activeSessions.has(projectId)) {
      const existingProcess = this.activeSessions.get(projectId);
      existingProcess?.kill();
      this.activeSessions.delete(projectId);
    }

    const autoBuildSource = this.getAutoBuildSourcePath();
    if (!autoBuildSource) {
      this.emit('error', projectId, 'Auto Claude source not found');
      return;
    }

    // Load or create session
    let session = this.loadSession(projectId, projectPath);
    if (!session) {
      session = {
        id: `session-${Date.now()}`,
        projectId,
        messages: [],
        createdAt: new Date(),
        updatedAt: new Date()
      };
    }

    // Add user message
    const userMessage: InsightsChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date()
    };
    session.messages.push(userMessage);
    session.updatedAt = new Date();
    this.saveSession(projectPath, session);

    // Emit thinking status
    this.emit('status', projectId, {
      phase: 'thinking',
      message: 'Processing your message...'
    } as InsightsChatStatus);

    // Load environment
    const envVars = this.loadAutoBuildEnv();

    // Build conversation history for context
    const conversationHistory = session.messages.map(m => ({
      role: m.role,
      content: m.content
    }));

    // Create the insights runner script path
    const runnerPath = path.join(autoBuildSource, 'insights_runner.py');

    // Check if runner exists
    if (!existsSync(runnerPath)) {
      this.emit('error', projectId, 'insights_runner.py not found in auto-claude directory');
      return;
    }

    // Spawn Python process
    const proc = spawn(this.pythonPath, [
      runnerPath,
      '--project-dir', projectPath,
      '--message', message,
      '--history', JSON.stringify(conversationHistory)
    ], {
      cwd: autoBuildSource,
      env: {
        ...process.env,
        ...envVars,
        PYTHONUNBUFFERED: '1'
      }
    });

    this.activeSessions.set(projectId, proc);

    let fullResponse = '';
    let suggestedTask: InsightsChatMessage['suggestedTask'] | undefined;

    proc.stdout?.on('data', (data: Buffer) => {
      const text = data.toString();

      // Check for special markers
      const lines = text.split('\n');
      for (const line of lines) {
        if (line.startsWith('__TASK_SUGGESTION__:')) {
          try {
            const taskJson = line.substring('__TASK_SUGGESTION__:'.length);
            suggestedTask = JSON.parse(taskJson);
            this.emit('stream-chunk', projectId, {
              type: 'task_suggestion',
              suggestedTask
            } as InsightsStreamChunk);
          } catch {
            // Not valid JSON, treat as normal text
            fullResponse += line + '\n';
            this.emit('stream-chunk', projectId, {
              type: 'text',
              content: line + '\n'
            } as InsightsStreamChunk);
          }
        } else if (line.startsWith('__TOOL_START__:')) {
          // Tool execution started
          try {
            const toolJson = line.substring('__TOOL_START__:'.length);
            const toolData = JSON.parse(toolJson);
            this.emit('stream-chunk', projectId, {
              type: 'tool_start',
              tool: {
                name: toolData.name,
                input: toolData.input
              }
            } as InsightsStreamChunk);
          } catch {
            // Ignore parse errors for tool markers
          }
        } else if (line.startsWith('__TOOL_END__:')) {
          // Tool execution finished
          try {
            const toolJson = line.substring('__TOOL_END__:'.length);
            const toolData = JSON.parse(toolJson);
            this.emit('stream-chunk', projectId, {
              type: 'tool_end',
              tool: {
                name: toolData.name
              }
            } as InsightsStreamChunk);
          } catch {
            // Ignore parse errors for tool markers
          }
        } else if (line.trim()) {
          fullResponse += line + '\n';
          this.emit('stream-chunk', projectId, {
            type: 'text',
            content: line + '\n'
          } as InsightsStreamChunk);
        }
      }
    });

    proc.stderr?.on('data', (data: Buffer) => {
      const text = data.toString();
      console.error('[Insights]', text);
    });

    proc.on('close', (code) => {
      this.activeSessions.delete(projectId);

      if (code === 0) {
        // Add assistant message to session
        const assistantMessage: InsightsChatMessage = {
          id: `msg-${Date.now()}`,
          role: 'assistant',
          content: fullResponse.trim(),
          timestamp: new Date(),
          suggestedTask
        };

        session!.messages.push(assistantMessage);
        session!.updatedAt = new Date();
        this.saveSession(projectPath, session!);

        this.emit('stream-chunk', projectId, {
          type: 'done'
        } as InsightsStreamChunk);

        this.emit('status', projectId, {
          phase: 'complete'
        } as InsightsChatStatus);
      } else {
        this.emit('stream-chunk', projectId, {
          type: 'error',
          error: `Process exited with code ${code}`
        } as InsightsStreamChunk);

        this.emit('error', projectId, `Process exited with code ${code}`);
      }
    });

    proc.on('error', (err) => {
      this.activeSessions.delete(projectId);
      this.emit('error', projectId, err.message);
    });
  }

}

// Singleton instance
export const insightsService = new InsightsService();
