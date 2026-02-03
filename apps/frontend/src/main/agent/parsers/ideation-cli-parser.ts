/**
 * Ideation CLI Parser
 * ====================
 * Parses Claude CLI JSON output into typed Idea arrays.
 * Handles various output formats and transforms snake_case to camelCase.
 */

import type {
  Idea,
  IdeationType,
  IdeationStatus,
  CodeImprovementIdea,
  UIUXImprovementIdea,
  DocumentationGapIdea,
  SecurityHardeningIdea,
  PerformanceOptimizationIdea,
  CodeQualityIdea
} from '../../../shared/types';
import { debugLog, debugError } from '../../../shared/utils/debug-logger';

/**
 * Raw idea structure from CLI output (supports both snake_case and camelCase).
 */
export interface RawCLIIdea extends Record<string, unknown> {
  id: string;
  type: string;
  title: string;
  description: string;
  rationale: string;
  status?: string;
  created_at?: string;
  createdAt?: string;

  // Common fields (snake_case from CLI)
  builds_upon?: string[];
  buildsUpon?: string[];
  estimated_effort?: string;
  estimatedEffort?: string;
  affected_files?: string[];
  affectedFiles?: string[];

  // UI/UX specific
  category?: string;
  affected_components?: string[];
  affectedComponents?: string[];
  screenshots?: string[];
  current_state?: string;
  currentState?: string;
  proposed_change?: string;
  proposedChange?: string;
  user_benefit?: string;
  userBenefit?: string;

  // Documentation specific
  target_audience?: string;
  targetAudience?: string;
  affected_areas?: string[];
  affectedAreas?: string[];
  current_documentation?: string;
  currentDocumentation?: string;
  proposed_content?: string;
  proposedContent?: string;
  priority?: string;

  // Security specific
  severity?: string;
  vulnerability?: string;
  current_risk?: string;
  currentRisk?: string;
  remediation?: string;
  references?: string[];
  compliance?: string[];

  // Performance specific
  impact?: string;
  current_metric?: string;
  currentMetric?: string;
  expected_improvement?: string;
  expectedImprovement?: string;
  implementation?: string;
  tradeoffs?: string;

  // Code quality specific
  code_example?: string;
  codeExample?: string;
  best_practice?: string;
  bestPractice?: string;
  metrics?: Record<string, unknown>;
  breaking_change?: boolean;
  breakingChange?: boolean;
  prerequisites?: string[];
}

/**
 * Possible structures of CLI JSON output.
 */
export interface RawCLIOutput {
  ideas?: RawCLIIdea[];
  result?: {
    ideas?: RawCLIIdea[];
  };
  // Direct array case handled separately
}

/**
 * Result of parsing CLI output.
 */
export interface CLIParseResult {
  success: boolean;
  ideas: Idea[];
  error?: string;
  rawOutput?: string;
}

/**
 * Valid ideation types set for validation.
 */
const VALID_IDEATION_TYPES: ReadonlySet<string> = new Set([
  'code_improvements',
  'ui_ux_improvements',
  'documentation_gaps',
  'security_hardening',
  'performance_optimizations',
  'code_quality'
]);

/**
 * Check if a type string is a valid IdeationType.
 */
function isValidIdeationType(type: string): type is IdeationType {
  return VALID_IDEATION_TYPES.has(type);
}

/**
 * Generate a unique ID for an idea if not provided.
 */
function generateIdeaId(type: IdeationType, index: number): string {
  return `${type}-${Date.now()}-${index}`;
}

/**
 * Extract JSON content from raw CLI output.
 *
 * Claude CLI may include extra text before/after JSON, so we need to
 * find and extract just the JSON portion.
 *
 * @param output - Raw CLI stdout
 * @returns Extracted JSON string or null if not found
 */
export function extractJSONFromOutput(output: string): string | null {
  const trimmed = output.trim();

  // Try to find a JSON object
  const objectMatch = trimmed.match(/\{[\s\S]*\}/);
  if (objectMatch) {
    return objectMatch[0];
  }

  // Try to find a JSON array
  const arrayMatch = trimmed.match(/\[[\s\S]*\]/);
  if (arrayMatch) {
    return arrayMatch[0];
  }

  return null;
}

/**
 * Parse JSON string into raw ideas array.
 *
 * Handles multiple response structures:
 * - { "ideas": [...] }
 * - { "result": { "ideas": [...] } }
 * - Direct array [...]
 * - Single idea object { title, description, ... }
 *
 * @param jsonString - JSON string to parse
 * @returns Array of raw ideas
 */
export function parseJSONToRawIdeas(jsonString: string): RawCLIIdea[] {
  const parsed = JSON.parse(jsonString);

  // Handle direct array
  if (Array.isArray(parsed)) {
    return parsed as RawCLIIdea[];
  }

  // Handle { ideas: [...] }
  if (parsed.ideas && Array.isArray(parsed.ideas)) {
    return parsed.ideas as RawCLIIdea[];
  }

  // Handle { result: { ideas: [...] } }
  if (parsed.result && Array.isArray(parsed.result.ideas)) {
    return parsed.result.ideas as RawCLIIdea[];
  }

  // Handle single idea object
  if (parsed.title && parsed.description) {
    return [parsed as RawCLIIdea];
  }

  throw new Error('Unexpected JSON structure: no ideas array found');
}

/**
 * Transform a raw CLI idea into a typed CodeImprovementIdea.
 */
function transformToCodeImprovement(idea: RawCLIIdea, status: IdeationStatus, createdAt: Date): CodeImprovementIdea {
  return {
    id: idea.id,
    type: 'code_improvements',
    title: idea.title,
    description: idea.description,
    rationale: idea.rationale,
    status,
    createdAt,
    buildsUpon: idea.builds_upon || idea.buildsUpon || [],
    estimatedEffort: (idea.estimated_effort || idea.estimatedEffort || 'small') as CodeImprovementIdea['estimatedEffort'],
    affectedFiles: idea.affected_files || idea.affectedFiles || [],
    existingPatterns: (idea as { existing_patterns?: string[]; existingPatterns?: string[] }).existing_patterns ||
                      (idea as { existing_patterns?: string[]; existingPatterns?: string[] }).existingPatterns || [],
    implementationApproach: (idea as { implementation_approach?: string; implementationApproach?: string }).implementation_approach ||
                            (idea as { implementation_approach?: string; implementationApproach?: string }).implementationApproach || ''
  };
}

/**
 * Transform a raw CLI idea into a typed UIUXImprovementIdea.
 */
function transformToUIUXImprovement(idea: RawCLIIdea, status: IdeationStatus, createdAt: Date): UIUXImprovementIdea {
  return {
    id: idea.id,
    type: 'ui_ux_improvements',
    title: idea.title,
    description: idea.description,
    rationale: idea.rationale,
    status,
    createdAt,
    category: (idea.category || 'usability') as UIUXImprovementIdea['category'],
    affectedComponents: idea.affected_components || idea.affectedComponents || [],
    screenshots: idea.screenshots || [],
    currentState: idea.current_state || idea.currentState || '',
    proposedChange: idea.proposed_change || idea.proposedChange || '',
    userBenefit: idea.user_benefit || idea.userBenefit || ''
  };
}

/**
 * Transform a raw CLI idea into a typed DocumentationGapIdea.
 */
function transformToDocumentationGap(idea: RawCLIIdea, status: IdeationStatus, createdAt: Date): DocumentationGapIdea {
  return {
    id: idea.id,
    type: 'documentation_gaps',
    title: idea.title,
    description: idea.description,
    rationale: idea.rationale,
    status,
    createdAt,
    category: (idea.category || 'readme') as DocumentationGapIdea['category'],
    targetAudience: (idea.target_audience || idea.targetAudience || 'developers') as DocumentationGapIdea['targetAudience'],
    affectedAreas: idea.affected_areas || idea.affectedAreas || [],
    currentDocumentation: idea.current_documentation || idea.currentDocumentation || '',
    proposedContent: idea.proposed_content || idea.proposedContent || '',
    priority: (idea.priority || 'medium') as DocumentationGapIdea['priority'],
    estimatedEffort: (idea.estimated_effort || idea.estimatedEffort || 'small') as DocumentationGapIdea['estimatedEffort']
  };
}

/**
 * Transform a raw CLI idea into a typed SecurityHardeningIdea.
 */
function transformToSecurityHardening(idea: RawCLIIdea, status: IdeationStatus, createdAt: Date): SecurityHardeningIdea {
  return {
    id: idea.id,
    type: 'security_hardening',
    title: idea.title,
    description: idea.description,
    rationale: idea.rationale,
    status,
    createdAt,
    category: (idea.category || 'configuration') as SecurityHardeningIdea['category'],
    severity: (idea.severity || 'medium') as SecurityHardeningIdea['severity'],
    affectedFiles: idea.affected_files || idea.affectedFiles || [],
    vulnerability: idea.vulnerability || '',
    currentRisk: idea.current_risk || idea.currentRisk || '',
    remediation: idea.remediation || '',
    references: idea.references || [],
    compliance: idea.compliance || []
  };
}

/**
 * Transform a raw CLI idea into a typed PerformanceOptimizationIdea.
 */
function transformToPerformanceOptimization(idea: RawCLIIdea, status: IdeationStatus, createdAt: Date): PerformanceOptimizationIdea {
  return {
    id: idea.id,
    type: 'performance_optimizations',
    title: idea.title,
    description: idea.description,
    rationale: idea.rationale,
    status,
    createdAt,
    category: (idea.category || 'runtime') as PerformanceOptimizationIdea['category'],
    impact: (idea.impact || 'medium') as PerformanceOptimizationIdea['impact'],
    affectedAreas: idea.affected_areas || idea.affectedAreas || [],
    currentMetric: idea.current_metric || idea.currentMetric || '',
    expectedImprovement: idea.expected_improvement || idea.expectedImprovement || '',
    implementation: idea.implementation || '',
    tradeoffs: idea.tradeoffs || '',
    estimatedEffort: (idea.estimated_effort || idea.estimatedEffort || 'medium') as PerformanceOptimizationIdea['estimatedEffort']
  };
}

/**
 * Transform a raw CLI idea into a typed CodeQualityIdea.
 */
function transformToCodeQuality(idea: RawCLIIdea, status: IdeationStatus, createdAt: Date): CodeQualityIdea {
  return {
    id: idea.id,
    type: 'code_quality',
    title: idea.title,
    description: idea.description,
    rationale: idea.rationale,
    status,
    createdAt,
    category: (idea.category || 'code_smells') as CodeQualityIdea['category'],
    severity: (idea.severity || 'minor') as CodeQualityIdea['severity'],
    affectedFiles: idea.affected_files || idea.affectedFiles || [],
    currentState: idea.current_state || idea.currentState || '',
    proposedChange: idea.proposed_change || idea.proposedChange || '',
    codeExample: idea.code_example || idea.codeExample || '',
    bestPractice: idea.best_practice || idea.bestPractice || '',
    metrics: idea.metrics || {},
    estimatedEffort: (idea.estimated_effort || idea.estimatedEffort || 'medium') as CodeQualityIdea['estimatedEffort'],
    breakingChange: idea.breaking_change ?? idea.breakingChange ?? false,
    prerequisites: idea.prerequisites || []
  };
}

/**
 * Transform a raw CLI idea into a properly typed Idea.
 *
 * @param rawIdea - Raw idea from CLI output
 * @param fallbackType - Type to use if idea doesn't have a valid type
 * @param index - Index for ID generation if needed
 * @returns Typed Idea
 */
export function transformRawIdea(
  rawIdea: RawCLIIdea,
  fallbackType: IdeationType,
  index: number
): Idea {
  const status = (rawIdea.status || 'draft') as IdeationStatus;
  const createdAt = rawIdea.created_at
    ? new Date(rawIdea.created_at)
    : rawIdea.createdAt
      ? new Date(rawIdea.createdAt as string)
      : new Date();

  // Ensure ID exists
  const ideaType = isValidIdeationType(rawIdea.type) ? rawIdea.type : fallbackType;
  const ideaWithId: RawCLIIdea = {
    ...rawIdea,
    id: rawIdea.id || generateIdeaId(ideaType, index)
  };

  // Transform based on type
  switch (ideaType) {
    case 'code_improvements':
      return transformToCodeImprovement(ideaWithId, status, createdAt);

    case 'ui_ux_improvements':
      return transformToUIUXImprovement(ideaWithId, status, createdAt);

    case 'documentation_gaps':
      return transformToDocumentationGap(ideaWithId, status, createdAt);

    case 'security_hardening':
      return transformToSecurityHardening(ideaWithId, status, createdAt);

    case 'performance_optimizations':
      return transformToPerformanceOptimization(ideaWithId, status, createdAt);

    case 'code_quality':
      return transformToCodeQuality(ideaWithId, status, createdAt);

    default:
      // Fallback to code_improvements if type is unknown
      debugLog('[IdeationCLIParser] Unknown idea type, falling back to code_improvements:', rawIdea.type);
      return transformToCodeImprovement(
        { ...ideaWithId, type: 'code_improvements' },
        status,
        createdAt
      );
  }
}

/**
 * Parse Claude CLI output into an array of typed Ideas.
 *
 * This is the main entry point for parsing CLI output.
 *
 * @param output - Raw stdout from Claude CLI
 * @param fallbackType - Type to use for ideas without a valid type
 * @returns Parse result with success status and ideas array
 */
export function parseCLIOutput(
  output: string,
  fallbackType: IdeationType = 'code_improvements'
): CLIParseResult {
  try {
    // Extract JSON from potentially noisy output
    const jsonString = extractJSONFromOutput(output);
    if (!jsonString) {
      return {
        success: false,
        ideas: [],
        error: 'No JSON content found in CLI output',
        rawOutput: output
      };
    }

    // Parse JSON into raw ideas
    const rawIdeas = parseJSONToRawIdeas(jsonString);

    // Validate we got some ideas
    if (rawIdeas.length === 0) {
      return {
        success: false,
        ideas: [],
        error: 'No ideas found in CLI output',
        rawOutput: output
      };
    }

    // Transform raw ideas to typed ideas
    const ideas = rawIdeas.map((rawIdea, index) =>
      transformRawIdea(rawIdea, fallbackType, index)
    );

    debugLog('[IdeationCLIParser] Successfully parsed', ideas.length, 'ideas');

    return {
      success: true,
      ideas,
      rawOutput: output
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown parsing error';
    debugError('[IdeationCLIParser] Parse error:', errorMessage);

    return {
      success: false,
      ideas: [],
      error: errorMessage,
      rawOutput: output
    };
  }
}

/**
 * Validate that an idea has all required base fields.
 *
 * @param idea - Idea to validate
 * @returns true if idea has required fields
 */
export function isValidIdea(idea: unknown): idea is RawCLIIdea {
  if (!idea || typeof idea !== 'object') {
    return false;
  }

  const obj = idea as Record<string, unknown>;
  return (
    typeof obj.title === 'string' &&
    typeof obj.description === 'string' &&
    typeof obj.rationale === 'string'
  );
}

/**
 * Filter and validate an array of potential ideas.
 *
 * @param items - Array of unknown items
 * @returns Array of valid raw ideas
 */
export function filterValidIdeas(items: unknown[]): RawCLIIdea[] {
  const validIdeas: RawCLIIdea[] = [];
  const invalidCount = { count: 0 };

  for (const item of items) {
    if (isValidIdea(item)) {
      validIdeas.push(item);
    } else {
      invalidCount.count++;
    }
  }

  if (invalidCount.count > 0) {
    debugLog('[IdeationCLIParser] Filtered out', invalidCount.count, 'invalid ideas');
  }

  return validIdeas;
}
