/**
 * Review workflow handlers module
 *
 * This module organizes all review-related IPC handlers for the code review workflow.
 * Handles review checklist, reviewer assignment, and review metrics operations.
 *
 * Review data is persisted as JSON files in spec directories:
 * - review_checklist.json - Checklist items and completion status
 * - reviewer_assignment.json - Assigned reviewers and approval status
 * - review_metrics.json - Review cycle time and iteration metrics
 */

import { ipcMain } from 'electron';
import { IPC_CHANNELS, getSpecsDir } from '../../../shared/constants';
import type { IPCResult, ReviewChecklist, ReviewerAssignment, ReviewMetrics } from '../../../shared/types';
import path from 'path';
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { projectStore } from '../../project-store';

// Review data file names (matching backend Python constants)
const REVIEW_CHECKLIST_FILE = 'review_checklist.json';
const REVIEWER_ASSIGNMENT_FILE = 'reviewer_assignment.json';
const REVIEW_METRICS_FILE = 'review_metrics.json';

/**
 * Find spec directory for a given specId and project
 */
function findSpecDir(projectId: string, specId: string): { specDir: string; project: any } | null {
  const project = projectStore.getProject(projectId);
  if (!project) {
    return null;
  }

  const specsBaseDir = getSpecsDir(project.autoBuildPath);
  const specDir = path.join(project.path, specsBaseDir, specId);

  if (!existsSync(specDir)) {
    return null;
  }

  return { specDir, project };
}

/**
 * Register all review workflow IPC handlers
 */
export function registerReviewHandlers(): void {
  /**
   * Get review checklist for a spec
   */
  ipcMain.handle(
    IPC_CHANNELS.REVIEW_GET_CHECKLIST,
    async (_, projectId: string, specId: string): Promise<IPCResult<ReviewChecklist>> => {
      try {
        const result = findSpecDir(projectId, specId);
        if (!result) {
          return { success: false, error: 'Spec not found' };
        }

        const { specDir } = result;
        const checklistPath = path.join(specDir, REVIEW_CHECKLIST_FILE);

        // Return default checklist if file doesn't exist
        if (!existsSync(checklistPath)) {
          const defaultChecklist: ReviewChecklist = {
            specId,
            items: [],
            allComplete: true,
            updatedAt: new Date()
          };
          return { success: true, data: defaultChecklist };
        }

        // Load and parse checklist
        const content = readFileSync(checklistPath, 'utf-8');
        const data = JSON.parse(content);

        const checklist: ReviewChecklist = {
          specId,
          items: data.items || [],
          allComplete: data.items?.every((item: any) => !item.required || item.completed) ?? true,
          updatedAt: new Date(data.updated_at || data.updatedAt || Date.now())
        };

        return { success: true, data: checklist };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to load review checklist'
        };
      }
    }
  );

  /**
   * Update review checklist for a spec
   */
  ipcMain.handle(
    IPC_CHANNELS.REVIEW_UPDATE_CHECKLIST,
    async (_, projectId: string, specId: string, checklist: ReviewChecklist): Promise<IPCResult> => {
      try {
        const result = findSpecDir(projectId, specId);
        if (!result) {
          return { success: false, error: 'Spec not found' };
        }

        const { specDir } = result;
        const checklistPath = path.join(specDir, REVIEW_CHECKLIST_FILE);

        // Ensure spec directory exists
        mkdirSync(specDir, { recursive: true });

        // Convert to backend format
        const data = {
          items: checklist.items.map(item => ({
            id: item.id,
            description: item.label,
            completed: item.completed,
            required: item.required,
            completed_at: item.completed ? new Date().toISOString() : '',
            completed_by: item.completed ? 'user' : ''
          })),
          updated_at: new Date().toISOString(),
          custom_items_allowed: true
        };

        // Write to file
        writeFileSync(checklistPath, JSON.stringify(data, null, 2));

        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to update review checklist'
        };
      }
    }
  );

  /**
   * Get reviewer assignment for a spec
   */
  ipcMain.handle(
    IPC_CHANNELS.REVIEW_GET_REVIEWER_ASSIGNMENT,
    async (_, projectId: string, specId: string): Promise<IPCResult<ReviewerAssignment>> => {
      try {
        const result = findSpecDir(projectId, specId);
        if (!result) {
          return { success: false, error: 'Spec not found' };
        }

        const { specDir } = result;
        const assignmentPath = path.join(specDir, REVIEWER_ASSIGNMENT_FILE);

        // Return default assignment if file doesn't exist
        if (!existsSync(assignmentPath)) {
          const defaultAssignment: ReviewerAssignment = {
            specId,
            required: [],
            actual: [],
            allApproved: true,
            updatedAt: new Date()
          };
          return { success: true, data: defaultAssignment };
        }

        // Load and parse assignment
        const content = readFileSync(assignmentPath, 'utf-8');
        const data = JSON.parse(content);

        const assignment: ReviewerAssignment = {
          specId,
          required: data.required_reviewers?.map((r: any) => ({
            name: r.username || r.name,
            email: r.email || '',
            approved: r.approved || false,
            comment: r.feedback || r.comment || ''
          })) || [],
          actual: data.reviewers?.map((r: any) => ({
            name: r.username || r.name,
            email: r.email || '',
            approved: r.approved || false,
            comment: r.feedback || r.comment || ''
          })) || [],
          allApproved: data.reviewers?.every((r: any) => r.approved) ?? true,
          updatedAt: new Date(data.updated_at || data.updatedAt || Date.now())
        };

        return { success: true, data: assignment };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to load reviewer assignment'
        };
      }
    }
  );

  /**
   * Update reviewer assignment for a spec
   */
  ipcMain.handle(
    IPC_CHANNELS.REVIEW_UPDATE_REVIEWER_ASSIGNMENT,
    async (_, projectId: string, specId: string, assignment: ReviewerAssignment): Promise<IPCResult> => {
      try {
        const result = findSpecDir(projectId, specId);
        if (!result) {
          return { success: false, error: 'Spec not found' };
        }

        const { specDir } = result;
        const assignmentPath = path.join(specDir, REVIEWER_ASSIGNMENT_FILE);

        // Ensure spec directory exists
        mkdirSync(specDir, { recursive: true });

        // Convert to backend format
        const data = {
          reviewers: assignment.actual.map(reviewer => ({
            username: reviewer.name,
            email: reviewer.email || '',
            approved: reviewer.approved || false,
            approved_at: reviewer.approved ? new Date().toISOString() : '',
            feedback: reviewer.comment || '',
            assigned_at: new Date().toISOString(),
            assigned_by: 'user'
          })),
          required_reviewers: assignment.required.map(reviewer => ({
            username: reviewer.name,
            email: reviewer.email || '',
            approved: reviewer.approved || false,
            approved_at: reviewer.approved ? new Date().toISOString() : '',
            feedback: reviewer.comment || ''
          })),
          required_approvals: 0, // 0 means all reviewers must approve
          updated_at: new Date().toISOString(),
          allow_self_approval: false
        };

        // Write to file
        writeFileSync(assignmentPath, JSON.stringify(data, null, 2));

        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to update reviewer assignment'
        };
      }
    }
  );

  /**
   * Get review metrics for a spec
   */
  ipcMain.handle(
    IPC_CHANNELS.REVIEW_GET_METRICS,
    async (_, projectId: string, specId: string): Promise<IPCResult<ReviewMetrics>> => {
      try {
        const result = findSpecDir(projectId, specId);
        if (!result) {
          return { success: false, error: 'Spec not found' };
        }

        const { specDir } = result;
        const metricsPath = path.join(specDir, REVIEW_METRICS_FILE);

        // Return default metrics if file doesn't exist
        if (!existsSync(metricsPath)) {
          const defaultMetrics: ReviewMetrics = {
            specId,
            iterationCount: 0,
            updatedAt: new Date()
          };
          return { success: true, data: defaultMetrics };
        }

        // Load and parse metrics
        const content = readFileSync(metricsPath, 'utf-8');
        const data = JSON.parse(content);

        const metrics: ReviewMetrics = {
          specId,
          cycleTime: data.cycle_time_seconds ? data.cycle_time_seconds * 1000 : undefined,
          iterationCount: data.iteration_count || 0,
          timeToApproval: data.time_to_approval_seconds ? data.time_to_approval_seconds * 1000 : undefined,
          reviewerResponseTime: data.avg_reviewer_response_seconds ? data.avg_reviewer_response_seconds * 1000 : undefined,
          updatedAt: new Date(data.updated_at || data.updatedAt || Date.now())
        };

        return { success: true, data: metrics };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to load review metrics'
        };
      }
    }
  );
}
