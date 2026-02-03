/**
 * Claude CLI-based ideation module.
 *
 * Spawns Claude CLI with print mode (-p) and JSON output format for programmatic
 * ideation generation. Uses OAuth authentication via the user's Claude Pro/Max
 * subscription instead of requiring an API key.
 *
 * @module ideation-cli
 */

import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import { getClaudeCliInvocationAsync, type ClaudeCliInvocation } from '../claude-cli-utils';
import { getProfileEnv, detectRateLimit, detectAuthFailure } from '../rate-limit-detector';
import { getAPIProfileEnv } from '../services/profile';
import { debugLog, debugError } from '../../shared/utils/debug-logger';
import type { IdeationType, IdeationConfig, Idea } from '../../shared/types';

/** Timeout for each ideation type generation (5 minutes) */
const IDEATION_TIMEOUT_MS = 5 * 60 * 1000;

/**
 * Result of spawning a Claude CLI ideation process
 */
export interface IdeationCLIResult {
  /** Whether the CLI completed successfully */
  success: boolean;
  /** The ideation type that was generated */
  type: IdeationType;
  /** Parsed ideas from CLI output (if successful) */
  ideas?: Idea[];
  /** Error message (if failed) */
  error?: string;
  /** Whether the process was rate limited */
  wasRateLimited?: boolean;
  /** Whether the process had an auth failure */
  wasAuthFailure?: boolean;
  /** Raw CLI output for debugging */
  rawOutput?: string;
}

/**
 * Configuration for spawning an ideation CLI process
 */
export interface IdeationCLIConfig {
  /** Project path for context */
  projectPath: string;
  /** The ideation type to generate */
  type: IdeationType;
  /** System prompt content for the ideation type */
  systemPrompt: string;
  /** User prompt with project context */
  userPrompt: string;
  /** Optional max ideas to generate */
  maxIdeas?: number;
  /** Optional model override (opus, sonnet, haiku) */
  model?: string;
}

/**
 * Event types emitted by IdeationCLISpawner
 */
export interface IdeationCLIEvents {
  'cli-started': (type: IdeationType) => void;
  'cli-output': (type: IdeationType, output: string) => void;
  'cli-complete': (result: IdeationCLIResult) => void;
  'cli-error': (type: IdeationType, error: string) => void;
}

/**
 * Spawner class for managing Claude CLI ideation processes.
 *
 * Handles spawning, monitoring, and parsing output from Claude CLI
 * processes for each ideation type.
 */
export class IdeationCLISpawner extends EventEmitter {
  private activeProcesses: Map<IdeationType, ChildProcess> = new Map();
  private processTimeouts: Map<IdeationType, NodeJS.Timeout> = new Map();

  constructor() {
    super();
  }

  /**
   * Build CLI arguments for ideation generation.
   *
   * Uses print mode (-p) with JSON output format for programmatic parsing.
   *
   * @param config - Configuration for the CLI invocation
   * @returns Array of CLI arguments
   */
  buildCLIArgs(config: IdeationCLIConfig): string[] {
    const args: string[] = [
      '-p',  // Print mode - non-interactive, single response
      '--output-format', 'json',  // JSON output for parsing
    ];

    // Add system prompt for ideation context
    if (config.systemPrompt) {
      args.push('--append-system-prompt', config.systemPrompt);
    }

    // Add model override if specified
    if (config.model) {
      args.push('--model', config.model);
    }

    // Add the user prompt as the final argument
    args.push(config.userPrompt);

    return args;
  }

  /**
   * Build environment variables for CLI invocation.
   *
   * Includes OAuth token from profile manager and API profile settings.
   *
   * @param cliInvocation - CLI invocation from getClaudeCliInvocationAsync
   * @returns Environment variables for the process
   */
  async buildCLIEnv(cliInvocation: ClaudeCliInvocation): Promise<Record<string, string>> {
    // Get active Claude profile environment (includes CLAUDE_CONFIG_DIR for fresh tokens)
    const profileEnv = getProfileEnv();

    // Get active API profile environment variables
    const apiProfileEnv = await getAPIProfileEnv();

    // Build final environment with proper precedence:
    // 1. process.env (system)
    // 2. cliInvocation.env (Claude CLI path adjustments)
    // 3. profileEnv (OAuth token / config dir)
    // 4. apiProfileEnv (API profile settings)
    const finalEnv: Record<string, string> = {
      ...process.env as Record<string, string>,
      ...cliInvocation.env,
      ...profileEnv,
      ...apiProfileEnv,
    };

    return finalEnv;
  }

  /**
   * Spawn a Claude CLI process for a single ideation type.
   *
   * @param config - Configuration for the ideation generation
   * @returns Promise that resolves with the result when CLI completes
   */
  async spawnIdeationCLI(config: IdeationCLIConfig): Promise<IdeationCLIResult> {
    debugLog('[IdeationCLI] Starting CLI for type:', config.type);

    try {
      // Get CLI invocation (command and base env)
      const cliInvocation = await getClaudeCliInvocationAsync();
      const cliArgs = this.buildCLIArgs(config);
      const cliEnv = await this.buildCLIEnv(cliInvocation);

      debugLog('[IdeationCLI] CLI command:', cliInvocation.command);
      debugLog('[IdeationCLI] CLI args:', cliArgs.slice(0, -1)); // Don't log full prompt

      return new Promise<IdeationCLIResult>((resolve) => {
        // Spawn the CLI process
        const childProcess = spawn(cliInvocation.command, cliArgs, {
          cwd: config.projectPath,
          env: cliEnv,
          // On Windows, we need shell: true for .cmd files
          shell: process.platform === 'win32',
        });

        // Track active process
        this.activeProcesses.set(config.type, childProcess);
        this.emit('cli-started', config.type);

        // Collect output
        let stdout = '';
        let stderr = '';

        // Set timeout
        const timeoutId = setTimeout(() => {
          debugError('[IdeationCLI] Process timeout for type:', config.type);
          this.killProcess(config.type);
          resolve({
            success: false,
            type: config.type,
            error: `Ideation generation timed out after ${IDEATION_TIMEOUT_MS / 1000 / 60} minutes`,
            rawOutput: stdout + stderr,
          });
        }, IDEATION_TIMEOUT_MS);
        this.processTimeouts.set(config.type, timeoutId);

        // Handle stdout
        childProcess.stdout?.on('data', (data: Buffer) => {
          const chunk = data.toString('utf8');
          stdout += chunk;
          this.emit('cli-output', config.type, chunk);
        });

        // Handle stderr
        childProcess.stderr?.on('data', (data: Buffer) => {
          const chunk = data.toString('utf8');
          stderr += chunk;
          // Stderr might contain progress info or errors
          this.emit('cli-output', config.type, chunk);
        });

        // Handle process exit
        childProcess.on('exit', (code: number | null) => {
          debugLog('[IdeationCLI] Process exited for type:', config.type, 'code:', code);

          // Clean up
          this.clearProcess(config.type);

          const allOutput = stdout + stderr;

          // Check for rate limit
          const rateLimitResult = detectRateLimit(allOutput);
          if (rateLimitResult.isRateLimited) {
            debugLog('[IdeationCLI] Rate limit detected for type:', config.type);
            resolve({
              success: false,
              type: config.type,
              error: `Rate limit reached${rateLimitResult.resetTime ? `. Resets: ${rateLimitResult.resetTime}` : ''}`,
              wasRateLimited: true,
              rawOutput: allOutput,
            });
            return;
          }

          // Check for auth failure
          const authResult = detectAuthFailure(allOutput);
          if (authResult.isAuthFailure) {
            debugLog('[IdeationCLI] Auth failure detected for type:', config.type);
            resolve({
              success: false,
              type: config.type,
              error: authResult.message || 'Authentication failed',
              wasAuthFailure: true,
              rawOutput: allOutput,
            });
            return;
          }

          // Check exit code
          if (code !== 0) {
            debugError('[IdeationCLI] Non-zero exit code for type:', config.type);
            resolve({
              success: false,
              type: config.type,
              error: `CLI exited with code ${code}: ${stderr || 'Unknown error'}`,
              rawOutput: allOutput,
            });
            return;
          }

          // Parse JSON output
          try {
            const parsed = this.parseJSONOutput(stdout, config.type);
            resolve({
              success: true,
              type: config.type,
              ideas: parsed,
              rawOutput: stdout,
            });
          } catch (parseError) {
            debugError('[IdeationCLI] JSON parse error for type:', config.type, parseError);
            resolve({
              success: false,
              type: config.type,
              error: `Failed to parse CLI output: ${parseError instanceof Error ? parseError.message : 'Unknown error'}`,
              rawOutput: stdout,
            });
          }
        });

        // Handle process error (spawn failure)
        childProcess.on('error', (err: Error) => {
          debugError('[IdeationCLI] Process error for type:', config.type, err.message);
          this.clearProcess(config.type);

          // Check if Claude CLI is not found
          if (err.message.includes('ENOENT') || err.message.includes('not found')) {
            resolve({
              success: false,
              type: config.type,
              error: 'Claude CLI not found. Please install Claude CLI and ensure it is in your PATH.',
            });
            return;
          }

          resolve({
            success: false,
            type: config.type,
            error: `Process error: ${err.message}`,
          });
        });
      });
    } catch (err) {
      debugError('[IdeationCLI] Failed to spawn CLI for type:', config.type, err);
      return {
        success: false,
        type: config.type,
        error: `Failed to spawn CLI: ${err instanceof Error ? err.message : 'Unknown error'}`,
      };
    }
  }

  /**
   * Spawn CLI processes for multiple ideation types in parallel.
   *
   * @param configs - Array of configurations for each type
   * @returns Promise that resolves with results for all types
   */
  async spawnParallel(configs: IdeationCLIConfig[]): Promise<IdeationCLIResult[]> {
    debugLog('[IdeationCLI] Starting parallel CLI for', configs.length, 'types');

    const promises = configs.map((config) => this.spawnIdeationCLI(config));
    const results = await Promise.all(promises);

    debugLog('[IdeationCLI] Parallel CLI complete:', {
      total: results.length,
      successful: results.filter((r) => r.success).length,
      failed: results.filter((r) => !r.success).length,
    });

    return results;
  }

  /**
   * Parse JSON output from Claude CLI into Idea array.
   *
   * The CLI outputs JSON when using --output-format json.
   * Expected format: { "ideas": [...] } or { "result": { "ideas": [...] } }
   *
   * @param output - Raw stdout from CLI
   * @param type - The ideation type for context
   * @returns Array of parsed ideas
   */
  private parseJSONOutput(output: string, type: IdeationType): Idea[] {
    // Trim and find JSON content
    const trimmed = output.trim();

    // Try to find JSON object in output (might have extra text before/after)
    const jsonMatch = trimmed.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      throw new Error('No JSON object found in output');
    }

    const parsed = JSON.parse(jsonMatch[0]);

    // Handle different response structures
    let ideas: unknown[];
    if (Array.isArray(parsed.ideas)) {
      ideas = parsed.ideas;
    } else if (parsed.result && Array.isArray(parsed.result.ideas)) {
      ideas = parsed.result.ideas;
    } else if (Array.isArray(parsed)) {
      ideas = parsed;
    } else {
      // If we get a single object that looks like an idea, wrap it
      if (parsed.title && parsed.description) {
        ideas = [parsed];
      } else {
        throw new Error('Unexpected JSON structure: missing ideas array');
      }
    }

    // Note: Full transformation is done by ideation-cli-parser.ts
    // Here we just return the raw parsed data with type annotation
    return ideas.map((item: unknown) => {
      const idea = item as Record<string, unknown>;
      return {
        ...idea,
        type: idea.type || type,
      };
    }) as unknown as Idea[];
  }

  /**
   * Kill an active ideation process.
   *
   * @param type - The ideation type to kill
   * @returns true if a process was killed
   */
  killProcess(type: IdeationType): boolean {
    const process = this.activeProcesses.get(type);
    if (process) {
      debugLog('[IdeationCLI] Killing process for type:', type);
      process.kill('SIGTERM');
      this.clearProcess(type);
      return true;
    }
    return false;
  }

  /**
   * Kill all active ideation processes.
   */
  killAll(): void {
    debugLog('[IdeationCLI] Killing all processes');
    // Use Array.from to avoid downlevelIteration requirement
    const types = Array.from(this.activeProcesses.keys());
    for (const type of types) {
      this.killProcess(type);
    }
  }

  /**
   * Check if a process is running for a type.
   *
   * @param type - The ideation type to check
   * @returns true if a process is active
   */
  isRunning(type: IdeationType): boolean {
    return this.activeProcesses.has(type);
  }

  /**
   * Get count of active processes.
   */
  getActiveCount(): number {
    return this.activeProcesses.size;
  }

  /**
   * Clear process tracking for a type.
   *
   * @param type - The ideation type to clear
   */
  private clearProcess(type: IdeationType): void {
    this.activeProcesses.delete(type);

    const timeout = this.processTimeouts.get(type);
    if (timeout) {
      clearTimeout(timeout);
      this.processTimeouts.delete(type);
    }
  }
}

/**
 * Build the user prompt for ideation generation.
 *
 * Combines project context with ideation-specific instructions.
 *
 * @param type - The ideation type
 * @param projectPath - Path to the project
 * @param config - Ideation configuration
 * @returns User prompt string
 */
export function buildIdeationUserPrompt(
  type: IdeationType,
  projectPath: string,
  config: IdeationConfig
): string {
  const maxIdeas = config.maxIdeasPerType || 5;

  const contextParts: string[] = [
    `Analyze the codebase at: ${projectPath}`,
    `Generate up to ${maxIdeas} ${formatIdeationType(type)} ideas.`,
  ];

  // Add context flags
  if (config.includeRoadmapContext) {
    contextParts.push('Consider the project roadmap when generating ideas.');
  }
  if (config.includeKanbanContext) {
    contextParts.push('Consider existing kanban tasks when generating ideas.');
  }

  contextParts.push(
    'Return a JSON object with an "ideas" array containing the generated ideas.',
    'Each idea should have: id, title, description, rationale, and type-specific fields.'
  );

  return contextParts.join('\n');
}

/**
 * Format ideation type for display.
 *
 * @param type - The ideation type
 * @returns Human-readable type name
 */
function formatIdeationType(type: IdeationType): string {
  const typeNames: Record<IdeationType, string> = {
    'code_improvements': 'code improvement',
    'ui_ux_improvements': 'UI/UX improvement',
    'documentation_gaps': 'documentation gap',
    'security_hardening': 'security hardening',
    'performance_optimizations': 'performance optimization',
    'code_quality': 'code quality',
  };
  return typeNames[type] || type;
}

// Export a singleton instance for convenient use
export const ideationCLISpawner = new IdeationCLISpawner();
