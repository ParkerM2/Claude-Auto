import { spawn } from 'child_process';
import path from 'path';
import { existsSync, promises as fsPromises } from 'fs';
import { EventEmitter } from 'events';
import { AgentState } from './agent-state';
import { AgentEvents } from './agent-events';
import { AgentProcessManager } from './agent-process';
import { RoadmapConfig } from './types';
import type { IdeationConfig, Idea } from '../../shared/types';
import { detectRateLimit, createSDKRateLimitInfo, getProfileEnv } from '../rate-limit-detector';
import { getAPIProfileEnv } from '../services/profile';
import { getOAuthModeClearVars } from './env-utils';
import { debugLog, debugError } from '../../shared/utils/debug-logger';
import { stripAnsiCodes } from '../../shared/utils/ansi-sanitizer';
import { parsePythonCommand } from '../python-detector';
import { pythonEnvManager } from '../python-env-manager';
import { transformIdeaFromSnakeCase, transformSessionFromSnakeCase } from '../ipc-handlers/ideation/transformers';
import { transformRoadmapFromSnakeCase } from '../ipc-handlers/roadmap/transformers';
import type { RawIdea } from '../ipc-handlers/ideation/types';
import {
  IdeationCLISpawner,
  buildIdeationUserPrompt,
  type IdeationCLIConfig,
  type IdeationCLIResult
} from './ideation-cli';
import { parseCLIOutput } from './parsers/ideation-cli-parser';
import type { IdeationType } from '../../shared/types';

/** Maximum length for status messages displayed in progress UI */
const STATUS_MESSAGE_MAX_LENGTH = 200;

/**
 * Formats a raw log line for display as a status message.
 * Strips ANSI escape codes, extracts the first line, and truncates to max length.
 *
 * @param log - Raw log output from backend process
 * @returns Formatted status message safe for UI display
 */
function formatStatusMessage(log: string): string {
  if (!log) return '';
  return stripAnsiCodes(log.trim()).split('\n')[0].substring(0, STATUS_MESSAGE_MAX_LENGTH);
}

/**
 * Queue management for ideation and roadmap generation
 */
export class AgentQueueManager {
  private state: AgentState;
  private events: AgentEvents;
  private processManager: AgentProcessManager;
  private emitter: EventEmitter;
  private ideationCLISpawner: IdeationCLISpawner;

  constructor(
    state: AgentState,
    events: AgentEvents,
    processManager: AgentProcessManager,
    emitter: EventEmitter
  ) {
    this.state = state;
    this.events = events;
    this.processManager = processManager;
    this.emitter = emitter;
    this.ideationCLISpawner = new IdeationCLISpawner();
    this.setupCLISpawnerEvents();
  }

  /**
   * Set up event listeners for the CLI spawner.
   * Forwards CLI events to the main emitter with appropriate transformations.
   */
  private setupCLISpawnerEvents(): void {
    // Forward CLI output as log messages
    this.ideationCLISpawner.on('cli-output', (type: IdeationType, output: string) => {
      debugLog('[Agent Queue] CLI output for type:', type);
      // Output is logged for debugging but not emitted as logs to avoid noise
    });

    // Forward CLI errors
    this.ideationCLISpawner.on('cli-error', (type: IdeationType, error: string) => {
      debugError('[Agent Queue] CLI error for type:', type, error);
    });
  }

  /**
   * Ensure Python environment is ready before spawning processes.
   * Prevents the race condition where generation starts before dependencies are installed,
   * which would cause it to fall back to system Python and fail with ModuleNotFoundError.
   *
   * Delegates to AgentProcessManager.ensurePythonEnvReady() for the actual initialization.
   *
   * @param projectId - The project ID for error event emission
   * @param eventType - The error event type to emit on failure
   * @returns true if environment is ready, false if initialization failed (error already emitted)
   */
  private async ensurePythonEnvReady(
    projectId: string,
    eventType: 'ideation-error' | 'roadmap-error'
  ): Promise<boolean> {
    const status = await this.processManager.ensurePythonEnvReady('AgentQueue');
    if (!status.ready) {
      this.emitter.emit(eventType, projectId, `Python environment not ready: ${status.error || 'initialization failed'}`);
      return false;
    }
    return true;
  }

  /**
   * Start roadmap generation process
   *
   * @param refreshCompetitorAnalysis - Force refresh competitor analysis even if it exists.
   *   This allows refreshing competitor data independently of the general roadmap refresh.
   *   Use when user explicitly wants new competitor research.
   */
  async startRoadmapGeneration(
    projectId: string,
    projectPath: string,
    refresh: boolean = false,
    enableCompetitorAnalysis: boolean = false,
    refreshCompetitorAnalysis: boolean = false,
    config?: RoadmapConfig
  ): Promise<void> {
    debugLog('[Agent Queue] Starting roadmap generation:', {
      projectId,
      projectPath,
      refresh,
      enableCompetitorAnalysis,
      refreshCompetitorAnalysis,
      config
    });

    const autoBuildSource = this.processManager.getAutoBuildSourcePath();

    if (!autoBuildSource) {
      debugError('[Agent Queue] Auto-build source path not found');
      this.emitter.emit('roadmap-error', projectId, 'Auto-build source path not found. Please configure it in App Settings.');
      return;
    }

    const roadmapRunnerPath = path.join(autoBuildSource, 'runners', 'roadmap_runner.py');

    if (!existsSync(roadmapRunnerPath)) {
      debugError('[Agent Queue] Roadmap runner not found at:', roadmapRunnerPath);
      this.emitter.emit('roadmap-error', projectId, `Roadmap runner not found at: ${roadmapRunnerPath}`);
      return;
    }

    const args = [roadmapRunnerPath, '--project', projectPath];

    if (refresh) {
      args.push('--refresh');
    }

    // Add competitor analysis flag if enabled
    if (enableCompetitorAnalysis) {
      args.push('--competitor-analysis');
    }

    // Add refresh competitor analysis flag if user wants fresh competitor data
    if (refreshCompetitorAnalysis) {
      args.push('--refresh-competitor-analysis');
    }

    // Add model and thinking level from config
    // Pass shorthand (opus/sonnet/haiku) - backend resolves using API profile env vars
    if (config?.model) {
      args.push('--model', config.model);
    }
    if (config?.thinkingLevel) {
      args.push('--thinking-level', config.thinkingLevel);
    }

    debugLog('[Agent Queue] Spawning roadmap process with args:', args);

    // Use projectId as taskId for roadmap operations
    await this.spawnRoadmapProcess(projectId, projectPath, args);
  }

  /**
   * Start ideation generation process using Claude CLI.
   *
   * Uses Claude CLI with print mode (-p) and JSON output for programmatic
   * ideation generation. This replaces the Python-based approach to work
   * with OAuth authentication (Claude Pro/Max subscription).
   *
   * @param projectId - The project ID for event emission
   * @param projectPath - Path to the project
   * @param config - Ideation configuration
   * @param _refresh - Unused, kept for API compatibility
   */
  async startIdeationGeneration(
    projectId: string,
    projectPath: string,
    config: IdeationConfig,
    _refresh: boolean = false
  ): Promise<void> {
    debugLog('[Agent Queue] Starting CLI-based ideation generation:', {
      projectId,
      projectPath,
      config
    });

    // Validate enabled types
    if (!config.enabledTypes || config.enabledTypes.length === 0) {
      debugError('[Agent Queue] No ideation types enabled');
      this.emitter.emit('ideation-error', projectId, 'No ideation types selected. Please select at least one type.');
      return;
    }

    // Use CLI-based ideation spawning
    await this.spawnIdeationCLIProcess(projectId, projectPath, config);
  }

  /**
   * Spawn a Python process for ideation generation
   */
  private async spawnIdeationProcess(
    projectId: string,
    projectPath: string,
    args: string[]
  ): Promise<void> {
    debugLog('[Agent Queue] Spawning ideation process:', { projectId, projectPath });

    // Run from auto-claude source directory so imports work correctly
    const autoBuildSource = this.processManager.getAutoBuildSourcePath();
    const cwd = autoBuildSource || process.cwd();

    // Ensure Python environment is ready before spawning
    if (!await this.ensurePythonEnvReady(projectId, 'ideation-error')) {
      return;
    }

    // Kill existing process for this project if any
    const wasKilled = this.processManager.killProcess(projectId);
    if (wasKilled) {
      debugLog('[Agent Queue] Killed existing process for project:', projectId);
    }

    // Generate unique spawn ID for this process instance
    const spawnId = this.state.generateSpawnId();
    debugLog('[Agent Queue] Generated spawn ID:', spawnId);


    // Get combined environment variables
    const combinedEnv = this.processManager.getCombinedEnv(projectPath);

    // Get active Claude profile environment (CLAUDE_CODE_OAUTH_TOKEN if not default)
    const profileEnv = getProfileEnv();

    // Get active API profile environment variables
    const apiProfileEnv = await getAPIProfileEnv();

    // Get OAuth mode clearing vars (clears stale ANTHROPIC_* vars when in OAuth mode)
    const oauthModeClearVars = getOAuthModeClearVars(apiProfileEnv);

    // Get Python path from process manager (uses venv if configured)
    const pythonPath = this.processManager.getPythonPath();

    // Get Python environment from pythonEnvManager (includes bundled site-packages)
    const pythonEnv = pythonEnvManager.getPythonEnv();

    // Build PYTHONPATH: bundled site-packages (if any) + autoBuildSource for local imports
    const pythonPathParts: string[] = [];
    if (pythonEnv.PYTHONPATH) {
      pythonPathParts.push(pythonEnv.PYTHONPATH);
    }
    if (autoBuildSource) {
      pythonPathParts.push(autoBuildSource);
    }
    const combinedPythonPath = pythonPathParts.join(process.platform === 'win32' ? ';' : ':');

    // Build final environment with proper precedence:
    // 1. process.env (system)
    // 2. pythonEnv (bundled packages environment)
    // 3. combinedEnv (auto-claude/.env for CLI usage)
    // 4. oauthModeClearVars (clear stale ANTHROPIC_* vars when in OAuth mode)
    // 5. profileEnv (Electron app OAuth token)
    // 6. apiProfileEnv (Active API profile config - highest priority for ANTHROPIC_* vars)
    // 7. Our specific overrides
    const finalEnv = {
      ...process.env,
      ...pythonEnv,
      ...combinedEnv,
      ...oauthModeClearVars,
      ...profileEnv,
      ...apiProfileEnv,
      PYTHONPATH: combinedPythonPath,
      PYTHONUNBUFFERED: '1',
      PYTHONUTF8: '1'
    };

    // Debug: Show OAuth token source (token values intentionally omitted for security - AC4)
    const tokenSource = profileEnv['CLAUDE_CODE_OAUTH_TOKEN']
      ? 'Electron app profile'
      : (combinedEnv['CLAUDE_CODE_OAUTH_TOKEN'] ? 'auto-claude/.env' : 'not found');
    const hasToken = !!(finalEnv as Record<string, string | undefined>)['CLAUDE_CODE_OAUTH_TOKEN'];
    debugLog('[Agent Queue] OAuth token status:', {
      source: tokenSource,
      hasToken
    });

    // Parse Python command to handle space-separated commands like "py -3"
    const [pythonCommand, pythonBaseArgs] = parsePythonCommand(pythonPath);
    const childProcess = spawn(pythonCommand, [...pythonBaseArgs, ...args], {
      cwd,
      env: finalEnv
    });

    this.state.addProcess(projectId, {
      taskId: projectId,
      process: childProcess,
      startedAt: new Date(),
      projectPath, // Store project path for loading session on completion
      spawnId,
      queueProcessType: 'ideation'
    });

    // Track progress through output
    let progressPhase = 'analyzing';
    let progressPercent = 10;
    // Collect output for rate limit detection
    let allOutput = '';

    // Helper to emit logs - split multi-line output into individual log lines
    const emitLogs = (log: string) => {
      const lines = log.split('\n').filter(line => line.trim().length > 0);
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.length > 0) {
          this.emitter.emit('ideation-log', projectId, trimmed);
        }
      }
    };

    // Track completed types for progress calculation
    const completedTypes = new Set<string>();
    const totalTypes = 7; // Default all types

    // Handle stdout - explicitly decode as UTF-8 for cross-platform Unicode support
    childProcess.stdout?.on('data', (data: Buffer) => {
      const log = data.toString('utf8');
      // Collect output for rate limit detection (keep last 10KB)
      allOutput = (allOutput + log).slice(-10000);

      // Emit all log lines for the activity log
      emitLogs(log);

      const typeCompleteMatch = log.match(/IDEATION_TYPE_COMPLETE:(\w+):(\d+)/);
      if (typeCompleteMatch) {
        const [, ideationType, ideasCount] = typeCompleteMatch;
        completedTypes.add(ideationType);

        debugLog('[Agent Queue] Ideation type completed:', {
          projectId,
          ideationType,
          ideasCount: parseInt(ideasCount, 10),
          totalCompleted: completedTypes.size
        });

        const typeFilePath = path.join(
          projectPath,
          '.auto-claude',
          'ideation',
          `${ideationType}_ideas.json`
        );

        const loadIdeationType = async (): Promise<void> => {
          try {
            const content = await fsPromises.readFile(typeFilePath, 'utf-8');
            const data: Record<string, RawIdea[]> = JSON.parse(content);
            const rawIdeas: RawIdea[] = data[ideationType] || [];
            const ideas: Idea[] = rawIdeas.map(transformIdeaFromSnakeCase);
            debugLog('[Agent Queue] Loaded ideas for type:', {
              ideationType,
              loadedCount: ideas.length,
              filePath: typeFilePath
            });
            this.emitter.emit('ideation-type-complete', projectId, ideationType, ideas);
          } catch (err) {
            if ((err as NodeJS.ErrnoException).code === 'ENOENT') {
              debugError('[Agent Queue] Ideas file not found:', typeFilePath);
            } else {
              debugError('[Agent Queue] Failed to load ideas for type:', ideationType, err);
            }
            this.emitter.emit('ideation-type-complete', projectId, ideationType, []);
          }
        };
        loadIdeationType().catch((err: unknown) => {
          debugError('[Agent Queue] Unhandled error in ideation type handler (event already emitted):', {
            ideationType,
            projectId,
            typeFilePath
          }, err);
        });
      }

      const typeFailedMatch = log.match(/IDEATION_TYPE_FAILED:(\w+)/);
      if (typeFailedMatch) {
        const [, ideationType] = typeFailedMatch;
        completedTypes.add(ideationType);

        debugError('[Agent Queue] Ideation type failed:', { projectId, ideationType });
        this.emitter.emit('ideation-type-failed', projectId, ideationType);
      }

      // Parse progress using AgentEvents
      const progressUpdate = this.events.parseIdeationProgress(
        log,
        progressPhase,
        progressPercent,
        completedTypes,
        totalTypes
      );
      progressPhase = progressUpdate.phase;
      progressPercent = progressUpdate.progress;

      // Emit progress update with a clean message for the status bar
      const statusMessage = formatStatusMessage(log);
      this.emitter.emit('ideation-progress', projectId, {
        phase: progressPhase,
        progress: progressPercent,
        message: statusMessage,
        completedTypes: Array.from(completedTypes)
      });
    });

    // Handle stderr - also emit as logs, explicitly decode as UTF-8
    childProcess.stderr?.on('data', (data: Buffer) => {
      const log = data.toString('utf8');
      // Collect stderr for rate limit detection too
      allOutput = (allOutput + log).slice(-10000);
      console.error('[Ideation STDERR]', log);
      emitLogs(log);
      this.emitter.emit('ideation-progress', projectId, {
        phase: progressPhase,
        progress: progressPercent,
        message: formatStatusMessage(log)
      });
    });

    // Handle process exit
    childProcess.on('exit', (code: number | null) => {
      debugLog('[Agent Queue] Ideation process exited:', { projectId, code, spawnId });

      // Check if this process was intentionally stopped by the user
      const wasIntentionallyStopped = this.state.wasSpawnKilled(spawnId);
      if (wasIntentionallyStopped) {
        debugLog('[Agent Queue] Ideation process was intentionally stopped, ignoring exit');
        this.state.clearKilledSpawn(spawnId);
        // Note: Don't call deleteProcess here - killProcess() already deleted it.
        // A new process with the same projectId may have been started.
        // Emit stopped event to ensure UI updates
        this.emitter.emit('ideation-stopped', projectId);
        return;
      }

      // Get the stored project path before deleting from map
      const processInfo = this.state.getProcess(projectId);
      const storedProjectPath = processInfo?.projectPath;
      this.state.deleteProcess(projectId);

      // Check for rate limit if process failed
      if (code !== 0) {
        debugLog('[Agent Queue] Checking for rate limit (non-zero exit)');
        const rateLimitDetection = detectRateLimit(allOutput);
        if (rateLimitDetection.isRateLimited) {
          debugLog('[Agent Queue] Rate limit detected for ideation');
          const rateLimitInfo = createSDKRateLimitInfo('ideation', rateLimitDetection, {
            projectId
          });
          this.emitter.emit('sdk-rate-limit', rateLimitInfo);
        }
      }

      if (code === 0) {
        debugLog('[Agent Queue] Ideation generation completed successfully');
        this.emitter.emit('ideation-progress', projectId, {
          phase: 'complete',
          progress: 100,
          message: 'Ideation generation complete'
        });

        // Load and emit the complete ideation session
        if (storedProjectPath) {
          try {
            const ideationFilePath = path.join(
              storedProjectPath,
              '.auto-claude',
              'ideation',
              'ideation.json'
            );
            debugLog('[Agent Queue] Loading ideation session from:', ideationFilePath);
            if (existsSync(ideationFilePath)) {
              const loadSession = async (): Promise<void> => {
                try {
                  const content = await fsPromises.readFile(ideationFilePath, 'utf-8');
                  const rawSession = JSON.parse(content);
                  const session = transformSessionFromSnakeCase(rawSession, projectId);
                  debugLog('[Agent Queue] Loaded ideation session:', {
                    totalIdeas: session.ideas?.length || 0
                  });
                  this.emitter.emit('ideation-complete', projectId, session);
                } catch (err) {
                  debugError('[Ideation] Failed to load ideation session:', err);
                  this.emitter.emit('ideation-error', projectId,
                    `Failed to load ideation session: ${err instanceof Error ? err.message : 'Unknown error'}`);
                }
              };
              loadSession().catch((err: unknown) => {
                debugError('[Agent Queue] Unhandled error loading ideation session:', err);
              });
            } else {
              debugError('[Ideation] ideation.json not found at:', ideationFilePath);
              this.emitter.emit('ideation-error', projectId,
                'Ideation completed but session file not found. Ideas may have been saved to individual type files.');
            }
          } catch (err) {
            debugError('[Ideation] Unexpected error in ideation completion:', err);
            this.emitter.emit('ideation-error', projectId,
              `Failed to load ideation session: ${err instanceof Error ? err.message : 'Unknown error'}`);
          }
        } else {
          debugError('[Ideation] No project path available to load session');
          this.emitter.emit('ideation-error', projectId,
            'Ideation completed but project path unavailable');
        }
      } else {
        debugError('[Agent Queue] Ideation generation failed:', { projectId, code });
        this.emitter.emit('ideation-error', projectId, `Ideation generation failed with exit code ${code}`);
      }
    });

    // Handle process error
    childProcess.on('error', (err: Error) => {
      console.error('[Ideation] Process error:', err.message);
      this.state.deleteProcess(projectId);
      this.emitter.emit('ideation-error', projectId, err.message);
    });
  }

  /**
   * Spawn Claude CLI processes for ideation generation.
   *
   * Uses the Claude CLI with print mode (-p) and JSON output format for each
   * enabled ideation type. Processes run in parallel for efficiency.
   *
   * This method is designed to replace Python-based ideation with CLI-based
   * approach that uses OAuth authentication (Claude Pro/Max subscription).
   *
   * @param projectId - The project ID for event emission
   * @param projectPath - Path to the project for context
   * @param config - Ideation configuration with enabled types
   * @returns Promise that resolves when all CLI processes complete
   */
  async spawnIdeationCLIProcess(
    projectId: string,
    projectPath: string,
    config: IdeationConfig
  ): Promise<void> {
    debugLog('[Agent Queue] Spawning CLI-based ideation:', {
      projectId,
      projectPath,
      enabledTypes: config.enabledTypes
    });

    // Kill any existing CLI processes for this project
    this.ideationCLISpawner.killAll();

    // Build CLI configs for each enabled type
    const cliConfigs: IdeationCLIConfig[] = config.enabledTypes.map((type) => ({
      projectPath,
      type,
      // System prompt will be loaded from prompts module in phase 4
      // For now, use a basic prompt that instructs JSON output
      systemPrompt: this.buildIdeationSystemPrompt(type),
      userPrompt: buildIdeationUserPrompt(type, projectPath, config),
      maxIdeas: config.maxIdeasPerType,
      model: config.model
    }));

    // Track progress
    const totalTypes = cliConfigs.length;
    const completedTypes = new Set<IdeationType>();
    let allIdeas: Idea[] = [];

    // Emit initial progress
    this.emitter.emit('ideation-progress', projectId, {
      phase: 'generating',
      progress: 5,
      message: `Starting ideation for ${totalTypes} types...`,
      completedTypes: []
    });

    // Spawn all CLI processes in parallel
    const results = await this.ideationCLISpawner.spawnParallel(cliConfigs);

    // Process results
    for (const result of results) {
      if (result.success && result.ideas) {
        // Parse and transform the ideas using the proper parser
        const parseResult = parseCLIOutput(result.rawOutput || '', result.type);

        if (parseResult.success) {
          completedTypes.add(result.type);
          allIdeas = allIdeas.concat(parseResult.ideas);

          debugLog('[Agent Queue] CLI ideation type complete:', {
            type: result.type,
            ideasCount: parseResult.ideas.length
          });

          // Emit per-type completion event
          this.emitter.emit('ideation-type-complete', projectId, result.type, parseResult.ideas);

          // Emit progress update
          const progressPercent = Math.round((completedTypes.size / totalTypes) * 90) + 5;
          this.emitter.emit('ideation-progress', projectId, {
            phase: 'generating',
            progress: progressPercent,
            message: `Completed ${result.type}`,
            completedTypes: Array.from(completedTypes)
          });
        } else {
          debugError('[Agent Queue] CLI ideation parse failed:', {
            type: result.type,
            error: parseResult.error
          });
          this.emitter.emit('ideation-type-failed', projectId, result.type);
        }
      } else {
        // Handle failure
        debugError('[Agent Queue] CLI ideation type failed:', {
          type: result.type,
          error: result.error,
          wasRateLimited: result.wasRateLimited,
          wasAuthFailure: result.wasAuthFailure
        });

        // Emit type failure event
        this.emitter.emit('ideation-type-failed', projectId, result.type);

        // Handle rate limit - use detectRateLimit on rawOutput to get full detection details
        if (result.wasRateLimited && result.rawOutput) {
          const rateLimitDetection = detectRateLimit(result.rawOutput);
          const rateLimitInfo = createSDKRateLimitInfo('ideation', rateLimitDetection, {
            projectId
          });
          this.emitter.emit('sdk-rate-limit', rateLimitInfo);
        } else if (result.wasRateLimited) {
          // Fallback if no rawOutput available
          const rateLimitInfo = createSDKRateLimitInfo('ideation', {
            isRateLimited: true
          }, { projectId });
          this.emitter.emit('sdk-rate-limit', rateLimitInfo);
        }

        // Handle auth failure - emit error immediately
        if (result.wasAuthFailure) {
          this.emitter.emit('ideation-error', projectId,
            'Authentication failed. Please ensure you are logged in to Claude CLI.');
          return;
        }
      }
    }

    // Determine final outcome
    const successfulTypes = results.filter((r) => r.success).length;

    if (successfulTypes === 0) {
      // All types failed
      this.emitter.emit('ideation-error', projectId,
        'All ideation types failed. Check logs for details.');
      return;
    }

    // Emit completion
    this.emitter.emit('ideation-progress', projectId, {
      phase: 'complete',
      progress: 100,
      message: 'Ideation generation complete',
      completedTypes: Array.from(completedTypes)
    });

    // Build a session-like structure for compatibility
    const session = {
      projectId,
      ideas: allIdeas,
      generatedAt: new Date().toISOString(),
      enabledTypes: Array.from(completedTypes)
    };

    debugLog('[Agent Queue] CLI ideation complete:', {
      totalIdeas: allIdeas.length,
      successfulTypes,
      failedTypes: totalTypes - successfulTypes
    });

    this.emitter.emit('ideation-complete', projectId, session);
  }

  /**
   * Build the system prompt for a specific ideation type.
   *
   * Note: In phase 4, this will be replaced with loading prompts from
   * apps/backend/prompts/ideation_*.md files.
   *
   * @param type - The ideation type
   * @returns System prompt string
   */
  private buildIdeationSystemPrompt(type: IdeationType): string {
    const prompts: Record<IdeationType, string> = {
      'code_improvements': `You are a senior software engineer analyzing code for improvements.
Identify opportunities to improve code quality, readability, and maintainability.
Return a JSON object with an "ideas" array where each idea has:
- id: unique string
- type: "code_improvements"
- title: short descriptive title
- description: detailed description of the improvement
- rationale: why this improvement is valuable
- estimatedEffort: "small" | "medium" | "large"
- affectedFiles: array of file paths affected`,

      'ui_ux_improvements': `You are a UX expert analyzing the application for user experience improvements.
Identify opportunities to improve usability, accessibility, and user delight.
Return a JSON object with an "ideas" array where each idea has:
- id: unique string
- type: "ui_ux_improvements"
- title: short descriptive title
- description: detailed description of the improvement
- rationale: why this improvement is valuable
- category: "usability" | "accessibility" | "visual" | "interaction" | "navigation"
- affectedComponents: array of component names affected
- userBenefit: expected benefit to users`,

      'documentation_gaps': `You are a technical writer analyzing documentation gaps.
Identify missing or incomplete documentation that would help developers.
Return a JSON object with an "ideas" array where each idea has:
- id: unique string
- type: "documentation_gaps"
- title: short descriptive title
- description: what documentation is missing
- rationale: why this documentation is needed
- targetAudience: "developers" | "users" | "contributors"
- priority: "low" | "medium" | "high"`,

      'security_hardening': `You are a security expert analyzing the codebase for vulnerabilities.
Identify security improvements and potential vulnerabilities to address.
Return a JSON object with an "ideas" array where each idea has:
- id: unique string
- type: "security_hardening"
- title: short descriptive title
- description: the security issue or improvement
- rationale: why this is important
- severity: "low" | "medium" | "high" | "critical"
- affectedFiles: array of file paths affected
- remediation: how to fix the issue`,

      'performance_optimizations': `You are a performance engineer analyzing the codebase.
Identify opportunities to improve application performance.
Return a JSON object with an "ideas" array where each idea has:
- id: unique string
- type: "performance_optimizations"
- title: short descriptive title
- description: the performance issue or optimization
- rationale: why this matters
- impact: "low" | "medium" | "high"
- expectedImprovement: what improvement to expect`,

      'code_quality': `You are a code quality expert analyzing the codebase.
Identify code smells, anti-patterns, and quality improvements.
Return a JSON object with an "ideas" array where each idea has:
- id: unique string
- type: "code_quality"
- title: short descriptive title
- description: the quality issue
- rationale: why this matters
- category: "code_smells" | "anti_patterns" | "testing" | "architecture"
- severity: "minor" | "moderate" | "major"
- affectedFiles: array of file paths affected`
    };

    return prompts[type] || prompts['code_improvements'];
  }

  /**
   * Stop CLI-based ideation for a project.
   *
   * @param projectId - The project ID (used for event emission)
   * @returns true if processes were killed
   */
  stopIdeationCLI(projectId: string): boolean {
    debugLog('[Agent Queue] Stopping CLI ideation for project:', projectId);

    const activeCount = this.ideationCLISpawner.getActiveCount();
    if (activeCount > 0) {
      this.ideationCLISpawner.killAll();
      this.emitter.emit('ideation-stopped', projectId);
      return true;
    }

    return false;
  }

  /**
   * Check if CLI-based ideation is running.
   *
   * @returns true if any CLI processes are active
   */
  isIdeationCLIRunning(): boolean {
    return this.ideationCLISpawner.getActiveCount() > 0;
  }

  /**
   * Spawn a Python process for roadmap generation
   */
  private async spawnRoadmapProcess(
    projectId: string,
    projectPath: string,
    args: string[]
  ): Promise<void> {
    debugLog('[Agent Queue] Spawning roadmap process:', { projectId, projectPath });

    // Run from auto-claude source directory so imports work correctly
    const autoBuildSource = this.processManager.getAutoBuildSourcePath();
    const cwd = autoBuildSource || process.cwd();

    // Ensure Python environment is ready before spawning
    if (!await this.ensurePythonEnvReady(projectId, 'roadmap-error')) {
      return;
    }

    // Kill existing process for this project if any
    const wasKilled = this.processManager.killProcess(projectId);
    if (wasKilled) {
      debugLog('[Agent Queue] Killed existing roadmap process for project:', projectId);
    }

    // Generate unique spawn ID for this process instance
    const spawnId = this.state.generateSpawnId();
    debugLog('[Agent Queue] Generated roadmap spawn ID:', spawnId);


    // Get combined environment variables
    const combinedEnv = this.processManager.getCombinedEnv(projectPath);

    // Get active Claude profile environment (CLAUDE_CODE_OAUTH_TOKEN if not default)
    const profileEnv = getProfileEnv();

    // Get active API profile environment variables
    const apiProfileEnv = await getAPIProfileEnv();

    // Get OAuth mode clearing vars (clears stale ANTHROPIC_* vars when in OAuth mode)
    const oauthModeClearVars = getOAuthModeClearVars(apiProfileEnv);

    // Get Python path from process manager (uses venv if configured)
    const pythonPath = this.processManager.getPythonPath();

    // Get Python environment from pythonEnvManager (includes bundled site-packages)
    const pythonEnv = pythonEnvManager.getPythonEnv();

    // Build PYTHONPATH: bundled site-packages (if any) + autoBuildSource for local imports
    const pythonPathParts: string[] = [];
    if (pythonEnv.PYTHONPATH) {
      pythonPathParts.push(pythonEnv.PYTHONPATH);
    }
    if (autoBuildSource) {
      pythonPathParts.push(autoBuildSource);
    }
    const combinedPythonPath = pythonPathParts.join(process.platform === 'win32' ? ';' : ':');

    // Build final environment with proper precedence:
    // 1. process.env (system)
    // 2. pythonEnv (bundled packages environment)
    // 3. combinedEnv (auto-claude/.env for CLI usage)
    // 4. oauthModeClearVars (clear stale ANTHROPIC_* vars when in OAuth mode)
    // 5. profileEnv (Electron app OAuth token)
    // 6. apiProfileEnv (Active API profile config - highest priority for ANTHROPIC_* vars)
    // 7. Our specific overrides
    const finalEnv = {
      ...process.env,
      ...pythonEnv,
      ...combinedEnv,
      ...oauthModeClearVars,
      ...profileEnv,
      ...apiProfileEnv,
      PYTHONPATH: combinedPythonPath,
      PYTHONUNBUFFERED: '1',
      PYTHONUTF8: '1'
    };

    // Debug: Show OAuth token source (token values intentionally omitted for security - AC4)
    const tokenSource = profileEnv['CLAUDE_CODE_OAUTH_TOKEN']
      ? 'Electron app profile'
      : (combinedEnv['CLAUDE_CODE_OAUTH_TOKEN'] ? 'auto-claude/.env' : 'not found');
    const hasToken = !!(finalEnv as Record<string, string | undefined>)['CLAUDE_CODE_OAUTH_TOKEN'];
    debugLog('[Agent Queue] OAuth token status:', {
      source: tokenSource,
      hasToken
    });

    // Parse Python command to handle space-separated commands like "py -3"
    const [pythonCommand, pythonBaseArgs] = parsePythonCommand(pythonPath);
    const childProcess = spawn(pythonCommand, [...pythonBaseArgs, ...args], {
      cwd,
      env: finalEnv
    });

    this.state.addProcess(projectId, {
      taskId: projectId,
      process: childProcess,
      startedAt: new Date(),
      projectPath, // Store project path for loading roadmap on completion
      spawnId,
      queueProcessType: 'roadmap'
    });

    // Track progress through output
    let progressPhase = 'analyzing';
    let progressPercent = 10;
    // Collect output for rate limit detection
    let allRoadmapOutput = '';

    // Helper to emit logs - split multi-line output into individual log lines
    const emitLogs = (log: string) => {
      const lines = log.split('\n').filter(line => line.trim().length > 0);
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.length > 0) {
          this.emitter.emit('roadmap-log', projectId, trimmed);
        }
      }
    };

    // Handle stdout - explicitly decode as UTF-8 for cross-platform Unicode support
    childProcess.stdout?.on('data', (data: Buffer) => {
      const log = data.toString('utf8');
      // Collect output for rate limit detection (keep last 10KB)
      allRoadmapOutput = (allRoadmapOutput + log).slice(-10000);

      // Emit all log lines for debugging
      emitLogs(log);

      // Parse progress using AgentEvents
      const progressUpdate = this.events.parseRoadmapProgress(log, progressPhase, progressPercent);
      progressPhase = progressUpdate.phase;
      progressPercent = progressUpdate.progress;

      // Emit progress update
      this.emitter.emit('roadmap-progress', projectId, {
        phase: progressPhase,
        progress: progressPercent,
        message: formatStatusMessage(log)
      });
    });

    // Handle stderr - explicitly decode as UTF-8
    childProcess.stderr?.on('data', (data: Buffer) => {
      const log = data.toString('utf8');
      // Collect stderr for rate limit detection too
      allRoadmapOutput = (allRoadmapOutput + log).slice(-10000);
      console.error('[Roadmap STDERR]', log);
      emitLogs(log);
      this.emitter.emit('roadmap-progress', projectId, {
        phase: progressPhase,
        progress: progressPercent,
        message: formatStatusMessage(log)
      });
    });

    // Handle process exit
    childProcess.on('exit', (code: number | null) => {
      debugLog('[Agent Queue] Roadmap process exited:', { projectId, code, spawnId });

      // Check if this process was intentionally stopped by the user
      const wasIntentionallyStopped = this.state.wasSpawnKilled(spawnId);
      if (wasIntentionallyStopped) {
        debugLog('[Agent Queue] Roadmap process was intentionally stopped, ignoring exit');
        this.state.clearKilledSpawn(spawnId);
        // Note: Don't call deleteProcess here - killProcess() already deleted it.
        // A new process with the same projectId may have been started.
        return;
      }

      // Get the stored project path before deleting from map
      const processInfo = this.state.getProcess(projectId);
      const storedProjectPath = processInfo?.projectPath;
      this.state.deleteProcess(projectId);

      // Check for rate limit if process failed
      if (code !== 0) {
        debugLog('[Agent Queue] Checking for rate limit (non-zero exit)');
        const rateLimitDetection = detectRateLimit(allRoadmapOutput);
        if (rateLimitDetection.isRateLimited) {
          debugLog('[Agent Queue] Rate limit detected for roadmap');
          const rateLimitInfo = createSDKRateLimitInfo('roadmap', rateLimitDetection, {
            projectId
          });
          this.emitter.emit('sdk-rate-limit', rateLimitInfo);
        }
      }

      if (code === 0) {
        debugLog('[Agent Queue] Roadmap generation completed successfully');
        this.emitter.emit('roadmap-progress', projectId, {
          phase: 'complete',
          progress: 100,
          message: 'Roadmap generation complete'
        });

        // Load and emit the complete roadmap
        if (storedProjectPath) {
          try {
            const roadmapFilePath = path.join(
              storedProjectPath,
              '.auto-claude',
              'roadmap',
              'roadmap.json'
            );
            debugLog('[Agent Queue] Loading roadmap from:', roadmapFilePath);
            if (existsSync(roadmapFilePath)) {
              const loadRoadmap = async (): Promise<void> => {
                try {
                  const content = await fsPromises.readFile(roadmapFilePath, 'utf-8');
                  const rawRoadmap = JSON.parse(content);
                  const transformedRoadmap = transformRoadmapFromSnakeCase(rawRoadmap, projectId);
                  debugLog('[Agent Queue] Loaded roadmap:', {
                    featuresCount: transformedRoadmap.features?.length || 0,
                    phasesCount: transformedRoadmap.phases?.length || 0
                  });
                  this.emitter.emit('roadmap-complete', projectId, transformedRoadmap);
                } catch (err) {
                  debugError('[Roadmap] Failed to load roadmap:', err);
                  this.emitter.emit('roadmap-error', projectId,
                    `Failed to load roadmap: ${err instanceof Error ? err.message : 'Unknown error'}`);
                }
              };
              loadRoadmap().catch((err: unknown) => {
                debugError('[Agent Queue] Unhandled error loading roadmap:', err);
              });
            } else {
              debugError('[Roadmap] roadmap.json not found at:', roadmapFilePath);
              this.emitter.emit('roadmap-error', projectId,
                'Roadmap completed but file not found.');
            }
          } catch (err) {
            debugError('[Roadmap] Unexpected error in roadmap completion:', err);
            this.emitter.emit('roadmap-error', projectId,
              `Unexpected error: ${err instanceof Error ? err.message : 'Unknown error'}`);
          }
        } else {
          debugError('[Roadmap] No project path available for roadmap completion');
          this.emitter.emit('roadmap-error', projectId, 'Roadmap completed but project path not found.');
        }
      } else {
        debugError('[Agent Queue] Roadmap generation failed:', { projectId, code });
        this.emitter.emit('roadmap-error', projectId, `Roadmap generation failed with exit code ${code}`);
      }
    });

    // Handle process error
    childProcess.on('error', (err: Error) => {
      console.error('[Roadmap] Process error:', err.message);
      this.state.deleteProcess(projectId);
      this.emitter.emit('roadmap-error', projectId, err.message);
    });
  }

  /**
   * Stop ideation generation for a project
   */
  stopIdeation(projectId: string): boolean {
    debugLog('[Agent Queue] Stop ideation requested:', { projectId });

    const processInfo = this.state.getProcess(projectId);
    const isIdeation = processInfo?.queueProcessType === 'ideation';
    debugLog('[Agent Queue] Process running?', { projectId, isIdeation, processType: processInfo?.queueProcessType });

    if (isIdeation) {
      debugLog('[Agent Queue] Killing ideation process:', projectId);
      this.processManager.killProcess(projectId);
      this.emitter.emit('ideation-stopped', projectId);
      return true;
    }
    debugLog('[Agent Queue] No running ideation process found for:', projectId);
    return false;
  }

  /**
   * Check if ideation is running for a project
   */
  isIdeationRunning(projectId: string): boolean {
    const processInfo = this.state.getProcess(projectId);
    return processInfo?.queueProcessType === 'ideation';
  }

  /**
   * Stop roadmap generation for a project
   */
  stopRoadmap(projectId: string): boolean {
    debugLog('[Agent Queue] Stop roadmap requested:', { projectId });

    const processInfo = this.state.getProcess(projectId);
    const isRoadmap = processInfo?.queueProcessType === 'roadmap';
    debugLog('[Agent Queue] Roadmap process running?', { projectId, isRoadmap, processType: processInfo?.queueProcessType });

    if (isRoadmap) {
      debugLog('[Agent Queue] Killing roadmap process:', projectId);
      this.processManager.killProcess(projectId);
      this.emitter.emit('roadmap-stopped', projectId);
      return true;
    }
    debugLog('[Agent Queue] No running roadmap process found for:', projectId);
    return false;
  }

  /**
   * Check if roadmap is running for a project
   */
  isRoadmapRunning(projectId: string): boolean {
    const processInfo = this.state.getProcess(projectId);
    return processInfo?.queueProcessType === 'roadmap';
  }
}
