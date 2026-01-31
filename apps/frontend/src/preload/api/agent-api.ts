/**
 * Agent API - Aggregates all agent-related API modules
 *
 * This file serves as the main entry point for agent APIs, combining:
 * - Roadmap operations
 * - Ideation operations
 * - Insights operations
 * - Changelog operations
 * - GitHub integration
 * - Shell operations
 */

import { createRoadmapAPI, RoadmapAPI } from './modules/roadmap-api';
import { createIdeationAPI, IdeationAPI } from './modules/ideation-api';
import { createInsightsAPI, InsightsAPI } from './modules/insights-api';
import { createChangelogAPI, ChangelogAPI } from './modules/changelog-api';
import { createGitHubAPI, GitHubAPI } from './modules/github-api';
import { createShellAPI, ShellAPI } from './modules/shell-api';
import { createManagerAPI, ManagerAPI } from './modules/manager-api';

/**
 * Combined Agent API interface
 * Includes all operations from individual API modules
 */
export interface AgentAPI extends
  RoadmapAPI,
  IdeationAPI,
  InsightsAPI,
  ChangelogAPI,
  GitHubAPI,
  ShellAPI,
  ManagerAPI {}

/**
 * Creates the complete Agent API by combining all module APIs
 *
 * @returns Complete AgentAPI with all operations available
 */
export const createAgentAPI = (): AgentAPI => {
  const roadmapAPI = createRoadmapAPI();
  const ideationAPI = createIdeationAPI();
  const insightsAPI = createInsightsAPI();
  const changelogAPI = createChangelogAPI();
  const githubAPI = createGitHubAPI();
  const shellAPI = createShellAPI();
  const managerAPI = createManagerAPI();

  return {
    // Roadmap API
    ...roadmapAPI,

    // Ideation API
    ...ideationAPI,

    // Insights API
    ...insightsAPI,

    // Changelog API
    ...changelogAPI,

    // GitHub Integration API
    ...githubAPI,

    // Shell Operations API
    ...shellAPI,

    // Manager API (PR status monitoring)
    ...managerAPI
  };
};

// Re-export individual API interfaces for consumers who need them
export type {
  RoadmapAPI,
  IdeationAPI,
  InsightsAPI,
  ChangelogAPI,
  GitHubAPI,
  ShellAPI,
  ManagerAPI
};
