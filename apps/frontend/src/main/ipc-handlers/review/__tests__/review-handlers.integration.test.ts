/**
 * Review Handlers Integration Tests
 *
 * Integration tests for review workflow IPC handlers.
 * Tests file I/O operations and data transformation between frontend and backend formats.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ipcMain } from 'electron';
import { existsSync, mkdirSync, writeFileSync, readFileSync, rmSync } from 'fs';
import path from 'path';
import { registerReviewHandlers } from '../index';
import { IPC_CHANNELS } from '../../../../shared/constants';
import type { ReviewChecklist, ReviewerAssignment, ReviewMetrics } from '../../../../shared/types';

// Mock project store
vi.mock('../../../project-store', () => ({
  projectStore: {
    getProject: vi.fn(() => ({
      id: 'test-project',
      path: '/test/project',
      autoBuildPath: '.auto-claude'
    }))
  }
}));

describe('Review Handlers Integration Tests', () => {
  const testProjectPath = path.join(process.cwd(), 'test-temp-review');
  const testSpecDir = path.join(testProjectPath, '.auto-claude', 'specs', 'test-spec');

  beforeEach(() => {
    // Create test directory
    mkdirSync(testSpecDir, { recursive: true });

    // Clear any existing handlers
    ipcMain.removeAllListeners(IPC_CHANNELS.REVIEW_GET_CHECKLIST);
    ipcMain.removeAllListeners(IPC_CHANNELS.REVIEW_UPDATE_CHECKLIST);
    ipcMain.removeAllListeners(IPC_CHANNELS.REVIEW_GET_REVIEWER_ASSIGNMENT);
    ipcMain.removeAllListeners(IPC_CHANNELS.REVIEW_UPDATE_REVIEWER_ASSIGNMENT);
    ipcMain.removeAllListeners(IPC_CHANNELS.REVIEW_GET_METRICS);

    // Register handlers
    registerReviewHandlers();
  });

  afterEach(() => {
    // Clean up test directory
    if (existsSync(testProjectPath)) {
      rmSync(testProjectPath, { recursive: true, force: true });
    }
  });

  describe('REVIEW_GET_CHECKLIST', () => {
    it('should read review_checklist.json from spec directory', async () => {
      // Create a test checklist file
      const checklistData = {
        items: [
          { id: 'item1', description: 'Test item', completed: false, required: true }
        ],
        updated_at: '2024-01-01T00:00:00Z',
        custom_items_allowed: true
      };

      const checklistPath = path.join(testSpecDir, 'review_checklist.json');
      writeFileSync(checklistPath, JSON.stringify(checklistData, null, 2));

      // Call the handler
      const event = { sender: { send: vi.fn() } };
      const handler = ipcMain.listeners(IPC_CHANNELS.REVIEW_GET_CHECKLIST)[0];
      const result = await handler(event, 'test-project', 'test-spec');

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
      expect(result.data.items).toHaveLength(1);
      expect(result.data.items[0].id).toBe('item1');
    });

    it('should return default checklist when file does not exist', async () => {
      // Do not create the checklist file

      // Call the handler
      const event = { sender: { send: vi.fn() } };
      const handler = ipcMain.listeners(IPC_CHANNELS.REVIEW_GET_CHECKLIST)[0];
      const result = await handler(event, 'test-project', 'test-spec');

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
      expect(result.data.items).toEqual([]);
      expect(result.data.allComplete).toBe(true);
    });
  });

  describe('REVIEW_UPDATE_CHECKLIST', () => {
    it('should write review_checklist.json to spec directory', async () => {
      // Prepare checklist data to update
      const checklist: ReviewChecklist = {
        specId: 'test-spec',
        items: [
          { id: 'item1', label: 'Test item', completed: true, required: true }
        ],
        allComplete: true,
        updatedAt: new Date()
      };

      // Call the handler
      const event = { sender: { send: vi.fn() } };
      const handler = ipcMain.listeners(IPC_CHANNELS.REVIEW_UPDATE_CHECKLIST)[0];
      const result = await handler(event, 'test-project', 'test-spec', checklist);

      expect(result.success).toBe(true);

      // Verify file was created
      const checklistPath = path.join(testSpecDir, 'review_checklist.json');
      expect(existsSync(checklistPath)).toBe(true);

      // Verify file content
      const content = JSON.parse(readFileSync(checklistPath, 'utf-8'));
      expect(content.items).toHaveLength(1);
      expect(content.items[0].id).toBe('item1');
      expect(content.items[0].description).toBe('Test item');
      expect(content.items[0].completed).toBe(true);
    });
  });

  describe('REVIEW_GET_REVIEWER_ASSIGNMENT', () => {
    it('should read reviewer_assignment.json', async () => {
      // Create a test assignment file
      const assignmentData = {
        reviewers: [
          { username: 'alice', email: 'alice@example.com', approved: true, feedback: 'Good' }
        ],
        required_reviewers: [
          { username: 'alice', email: 'alice@example.com', approved: true, feedback: 'Good' }
        ],
        required_approvals: 0,
        updated_at: '2024-01-01T00:00:00Z'
      };

      const assignmentPath = path.join(testSpecDir, 'reviewer_assignment.json');
      writeFileSync(assignmentPath, JSON.stringify(assignmentData, null, 2));

      // Call the handler
      const event = { sender: { send: vi.fn() } };
      const handler = ipcMain.listeners(IPC_CHANNELS.REVIEW_GET_REVIEWER_ASSIGNMENT)[0];
      const result = await handler(event, 'test-project', 'test-spec');

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
      expect(result.data.actual).toHaveLength(1);
      expect(result.data.actual[0].name).toBe('alice');
    });

    it('should return default assignment when file does not exist', async () => {
      // Do not create the assignment file

      // Call the handler
      const event = { sender: { send: vi.fn() } };
      const handler = ipcMain.listeners(IPC_CHANNELS.REVIEW_GET_REVIEWER_ASSIGNMENT)[0];
      const result = await handler(event, 'test-project', 'test-spec');

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
      expect(result.data.required).toEqual([]);
      expect(result.data.actual).toEqual([]);
      expect(result.data.allApproved).toBe(true);
    });
  });

  describe('REVIEW_UPDATE_REVIEWER_ASSIGNMENT', () => {
    it('should write reviewer_assignment.json to spec directory', async () => {
      // Prepare assignment data to update
      const assignment: ReviewerAssignment = {
        specId: 'test-spec',
        required: [
          { id: 'alice', name: 'Alice', email: 'alice@example.com', approved: true }
        ],
        actual: [
          { id: 'alice', name: 'Alice', email: 'alice@example.com', approved: true, comment: 'LGTM' }
        ],
        allApproved: true,
        updatedAt: new Date()
      };

      // Call the handler
      const event = { sender: { send: vi.fn() } };
      const handler = ipcMain.listeners(IPC_CHANNELS.REVIEW_UPDATE_REVIEWER_ASSIGNMENT)[0];
      const result = await handler(event, 'test-project', 'test-spec', assignment);

      expect(result.success).toBe(true);

      // Verify file was created
      const assignmentPath = path.join(testSpecDir, 'reviewer_assignment.json');
      expect(existsSync(assignmentPath)).toBe(true);

      // Verify file content
      const content = JSON.parse(readFileSync(assignmentPath, 'utf-8'));
      expect(content.reviewers).toHaveLength(1);
      expect(content.reviewers[0].username).toBe('Alice');
      expect(content.reviewers[0].approved).toBe(true);
    });
  });

  describe('REVIEW_GET_METRICS', () => {
    it('should read review_metrics.json', async () => {
      // Create a test metrics file
      const metricsData = {
        cycle_time_seconds: 3600,
        iteration_count: 2,
        time_to_approval_seconds: 1800,
        avg_reviewer_response_seconds: 900,
        updated_at: '2024-01-01T00:00:00Z'
      };

      const metricsPath = path.join(testSpecDir, 'review_metrics.json');
      writeFileSync(metricsPath, JSON.stringify(metricsData, null, 2));

      // Call the handler
      const event = { sender: { send: vi.fn() } };
      const handler = ipcMain.listeners(IPC_CHANNELS.REVIEW_GET_METRICS)[0];
      const result = await handler(event, 'test-project', 'test-spec');

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
      expect(result.data.iterationCount).toBe(2);
      expect(result.data.cycleTime).toBe(3600000); // Converted to milliseconds
    });

    it('should return default metrics when file does not exist', async () => {
      // Do not create the metrics file

      // Call the handler
      const event = { sender: { send: vi.fn() } };
      const handler = ipcMain.listeners(IPC_CHANNELS.REVIEW_GET_METRICS)[0];
      const result = await handler(event, 'test-project', 'test-spec');

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
      expect(result.data.iterationCount).toBe(0);
    });
  });

  describe('Error Handling', () => {
    it('should return error for invalid spec paths', async () => {
      // Call handler with non-existent spec
      const event = { sender: { send: vi.fn() } };
      const handler = ipcMain.listeners(IPC_CHANNELS.REVIEW_GET_CHECKLIST)[0];
      const result = await handler(event, 'test-project', 'nonexistent-spec');

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });

    it('should handle invalid JSON gracefully', async () => {
      // Create an invalid JSON file
      const checklistPath = path.join(testSpecDir, 'review_checklist.json');
      writeFileSync(checklistPath, 'invalid json {{{');

      // Call the handler
      const event = { sender: { send: vi.fn() } };
      const handler = ipcMain.listeners(IPC_CHANNELS.REVIEW_GET_CHECKLIST)[0];
      const result = await handler(event, 'test-project', 'test-spec');

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });
  });
});
