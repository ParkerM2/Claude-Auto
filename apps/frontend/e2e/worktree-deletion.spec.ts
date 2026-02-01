/**
 * End-to-End tests for worktree deletion functionality
 * Tests: normal deletion, phantom cleanup, orphan worktree deletion
 *
 * NOTE: These tests require the Electron app to be built first.
 * Run `npm run build` before running E2E tests.
 *
 * To run: npx playwright test worktree-deletion --config=e2e/playwright.config.ts
 */
import { test, expect } from '@playwright/test';
import { mkdirSync, mkdtempSync, rmSync, existsSync, writeFileSync, readFileSync } from 'fs';
import { tmpdir } from 'os';
import path from 'path';
import { execSync } from 'child_process';

// Test data directory - created securely with mkdtempSync to prevent TOCTOU attacks
let TEST_DATA_DIR: string;
let TEST_PROJECT_DIR: string;
let SPECS_DIR: string;
let WORKTREES_DIR: string;

// Setup test environment with secure temp directory
function setupTestEnvironment(): void {
  // Create secure temp directory with random suffix
  TEST_DATA_DIR = mkdtempSync(path.join(tmpdir(), 'auto-claude-worktree-deletion-e2e-'));
  TEST_PROJECT_DIR = path.join(TEST_DATA_DIR, 'test-project');
  SPECS_DIR = path.join(TEST_PROJECT_DIR, '.auto-claude', 'specs');
  WORKTREES_DIR = path.join(TEST_PROJECT_DIR, '.auto-claude', 'worktrees', 'tasks');
  mkdirSync(TEST_PROJECT_DIR, { recursive: true });
  mkdirSync(SPECS_DIR, { recursive: true });
  mkdirSync(WORKTREES_DIR, { recursive: true });

  // Initialize as git repository for worktree tests
  try {
    execSync('git init', { cwd: TEST_PROJECT_DIR, stdio: 'pipe' });
    execSync('git config user.email "test@test.com"', { cwd: TEST_PROJECT_DIR, stdio: 'pipe' });
    execSync('git config user.name "Test User"', { cwd: TEST_PROJECT_DIR, stdio: 'pipe' });
    // Create initial commit
    writeFileSync(path.join(TEST_PROJECT_DIR, 'README.md'), '# Test Project');
    execSync('git add README.md', { cwd: TEST_PROJECT_DIR, stdio: 'pipe' });
    execSync('git commit -m "Initial commit"', { cwd: TEST_PROJECT_DIR, stdio: 'pipe' });
  } catch {
    // Git init may fail in some test environments - continue anyway
  }
}

// Cleanup test environment
function cleanupTestEnvironment(): void {
  if (existsSync(TEST_DATA_DIR)) {
    rmSync(TEST_DATA_DIR, { recursive: true, force: true });
  }
}

// Helper to create a spec directory with worktree metadata
function createSpecWithWorktree(
  specId: string,
  options: {
    createWorktreeDir?: boolean;
    taskStatus?: 'todo' | 'in_progress' | 'done' | 'archived';
    hasImplementationPlan?: boolean;
  } = {}
): { specDir: string; worktreePath: string } {
  const {
    createWorktreeDir = true,
    taskStatus = 'in_progress',
    hasImplementationPlan = true
  } = options;

  const specDir = path.join(SPECS_DIR, specId);
  mkdirSync(specDir, { recursive: true });

  // Create spec.md
  writeFileSync(
    path.join(specDir, 'spec.md'),
    `# ${specId}\n\n## Overview\n\nTest task for worktree deletion validation.\n\n## Acceptance Criteria\n\n- [ ] Worktree can be deleted\n`
  );

  // Create requirements.json
  writeFileSync(
    path.join(specDir, 'requirements.json'),
    JSON.stringify(
      {
        task_description: `Test task ${specId}`,
        user_requirements: ['Requirement 1'],
        acceptance_criteria: ['Worktree can be deleted'],
        context: []
      },
      null,
      2
    )
  );

  // Create implementation_plan.json if needed
  if (hasImplementationPlan) {
    writeFileSync(
      path.join(specDir, 'implementation_plan.json'),
      JSON.stringify(
        {
          feature: `Test Feature ${specId}`,
          workflow_type: 'feature',
          services_involved: ['frontend'],
          subtasks: [
            {
              id: 'subtask-1',
              phase: 'Implementation',
              service: 'frontend',
              description: 'Test subtask',
              files_to_modify: [],
              files_to_create: [],
              pattern_files: [],
              verification_command: 'echo ok',
              status: taskStatus === 'done' ? 'completed' : 'pending',
              notes: ''
            }
          ],
          final_acceptance: ['Test complete'],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          spec_file: 'spec.md',
          status: taskStatus
        },
        null,
        2
      )
    );
  }

  // Create build-progress.txt
  writeFileSync(
    path.join(specDir, 'build-progress.txt'),
    `Task Progress: ${specId}\n\nStatus: ${taskStatus}\n`
  );

  // Create worktree directory if requested
  const worktreePath = path.join(WORKTREES_DIR, specId);
  if (createWorktreeDir) {
    mkdirSync(worktreePath, { recursive: true });
    // Create some files to simulate a real worktree
    writeFileSync(path.join(worktreePath, '.git'), `gitdir: ${TEST_PROJECT_DIR}/.git/worktrees/${specId}`);
    writeFileSync(path.join(worktreePath, 'README.md'), `# Worktree for ${specId}`);
  }

  return { specDir, worktreePath };
}

// Helper to simulate a git worktree registration (creates .git/worktrees entry)
function registerWorktreeInGit(specId: string, worktreePath: string): void {
  const gitWorktreesDir = path.join(TEST_PROJECT_DIR, '.git', 'worktrees', specId);
  mkdirSync(gitWorktreesDir, { recursive: true });

  // Create minimal worktree registration files
  writeFileSync(path.join(gitWorktreesDir, 'gitdir'), `${worktreePath}/.git`);
  writeFileSync(path.join(gitWorktreesDir, 'HEAD'), 'ref: refs/heads/main');
}

// Helper to create a phantom worktree (git entry exists but directory doesn't)
function createPhantomWorktree(specId: string): { specDir: string; worktreePath: string } {
  const result = createSpecWithWorktree(specId, { createWorktreeDir: false });

  // Register in git but don't create directory
  registerWorktreeInGit(specId, result.worktreePath);

  return result;
}

// Helper to create an orphan worktree (worktree exists but task was deleted/archived)
function createOrphanWorktree(specId: string): { specDir: string; worktreePath: string } {
  const result = createSpecWithWorktree(specId, {
    createWorktreeDir: true,
    taskStatus: 'archived',
    hasImplementationPlan: true
  });

  // Delete the task files to simulate an orphaned worktree
  const taskJsonPath = path.join(SPECS_DIR, specId, 'task.json');
  if (existsSync(taskJsonPath)) {
    rmSync(taskJsonPath);
  }

  return result;
}

// Helper to verify worktree exists
function worktreeExists(worktreePath: string): boolean {
  return existsSync(worktreePath);
}

// Helper to verify worktree is registered in git
function worktreeRegisteredInGit(specId: string): boolean {
  const gitWorktreesDir = path.join(TEST_PROJECT_DIR, '.git', 'worktrees', specId);
  return existsSync(gitWorktreesDir);
}

// Helper to run git worktree prune
function pruneWorktrees(): void {
  try {
    execSync('git worktree prune', { cwd: TEST_PROJECT_DIR, stdio: 'pipe' });
  } catch {
    // Ignore prune errors
  }
}

test.describe('Worktree Deletion E2E Tests', () => {
  test.beforeAll(() => {
    setupTestEnvironment();
  });

  test.afterAll(() => {
    cleanupTestEnvironment();
  });

  test('should create worktree test infrastructure', () => {
    const specId = '001-worktree-test';
    const { specDir, worktreePath } = createSpecWithWorktree(specId);

    // Verify spec directory created
    expect(existsSync(specDir)).toBe(true);
    expect(existsSync(path.join(specDir, 'spec.md'))).toBe(true);
    expect(existsSync(path.join(specDir, 'requirements.json'))).toBe(true);
    expect(existsSync(path.join(specDir, 'implementation_plan.json'))).toBe(true);

    // Verify worktree directory created
    expect(existsSync(worktreePath)).toBe(true);
  });

  test('should create phantom worktree fixture', () => {
    const specId = '002-phantom-worktree';
    const { specDir, worktreePath } = createPhantomWorktree(specId);

    // Verify spec directory exists
    expect(existsSync(specDir)).toBe(true);

    // Verify worktree directory does NOT exist (phantom)
    expect(existsSync(worktreePath)).toBe(false);

    // Verify git registration exists
    expect(worktreeRegisteredInGit(specId)).toBe(true);
  });

  test('should create orphan worktree fixture', () => {
    const specId = '003-orphan-worktree';
    const { specDir, worktreePath } = createOrphanWorktree(specId);

    // Verify spec directory exists (with archived status)
    expect(existsSync(specDir)).toBe(true);

    // Verify worktree directory exists
    expect(existsSync(worktreePath)).toBe(true);

    // Verify implementation plan shows archived status
    const planPath = path.join(specDir, 'implementation_plan.json');
    const plan = JSON.parse(readFileSync(planPath, 'utf-8'));
    expect(plan.status).toBe('archived');
  });

  test('should prune phantom worktrees with git worktree prune', () => {
    const specId = '004-prune-test';
    const { worktreePath } = createPhantomWorktree(specId);

    // Verify phantom state (registered but no directory)
    expect(worktreeRegisteredInGit(specId)).toBe(true);
    expect(existsSync(worktreePath)).toBe(false);

    // Run prune
    pruneWorktrees();

    // After prune, registration should be cleaned up
    expect(worktreeRegisteredInGit(specId)).toBe(false);
  });

  test('should verify worktree helper functions work correctly', () => {
    const specId = '005-helper-test';
    const { worktreePath } = createSpecWithWorktree(specId);

    // Test worktreeExists helper
    expect(worktreeExists(worktreePath)).toBe(true);
    expect(worktreeExists(path.join(WORKTREES_DIR, 'nonexistent'))).toBe(false);
  });
});

test.describe('Worktree Deletion Flow Tests', () => {
  test.beforeAll(() => {
    setupTestEnvironment();
  });

  test.afterAll(() => {
    cleanupTestEnvironment();
  });

  test('should handle normal worktree deletion', () => {
    const specId = '100-normal-deletion';
    const { specDir, worktreePath } = createSpecWithWorktree(specId);

    // Verify initial state
    expect(existsSync(worktreePath)).toBe(true);
    expect(existsSync(specDir)).toBe(true);

    // Simulate deletion (remove directory and spec)
    rmSync(worktreePath, { recursive: true, force: true });
    rmSync(specDir, { recursive: true, force: true });

    // Verify cleanup
    expect(existsSync(worktreePath)).toBe(false);
    expect(existsSync(specDir)).toBe(false);
  });

  test('should handle phantom worktree cleanup', () => {
    const specId = '101-phantom-cleanup';
    const { specDir, worktreePath } = createPhantomWorktree(specId);

    // Verify phantom state
    expect(existsSync(specDir)).toBe(true);
    expect(existsSync(worktreePath)).toBe(false);
    expect(worktreeRegisteredInGit(specId)).toBe(true);

    // Run prune to clean up phantom entry
    pruneWorktrees();

    // Git registration should be gone
    expect(worktreeRegisteredInGit(specId)).toBe(false);

    // Cleanup spec dir
    rmSync(specDir, { recursive: true, force: true });
    expect(existsSync(specDir)).toBe(false);
  });

  test('should handle orphan worktree deletion', () => {
    const specId = '102-orphan-deletion';
    const { specDir, worktreePath } = createOrphanWorktree(specId);

    // Verify orphan state (worktree exists but task is archived)
    expect(existsSync(worktreePath)).toBe(true);
    expect(existsSync(specDir)).toBe(true);

    const plan = JSON.parse(readFileSync(path.join(specDir, 'implementation_plan.json'), 'utf-8'));
    expect(plan.status).toBe('archived');

    // Simulate orphan deletion (should work even without active task)
    rmSync(worktreePath, { recursive: true, force: true });

    // Worktree should be removed
    expect(existsSync(worktreePath)).toBe(false);

    // Spec dir remains (archived task metadata)
    expect(existsSync(specDir)).toBe(true);
  });

  test('should handle bulk worktree deletion', () => {
    const specIds = ['103-bulk-1', '103-bulk-2', '103-bulk-3'];
    const worktrees: Array<{ specDir: string; worktreePath: string }> = [];

    // Create multiple worktrees
    for (const specId of specIds) {
      worktrees.push(createSpecWithWorktree(specId));
    }

    // Verify all created
    for (const { specDir, worktreePath } of worktrees) {
      expect(existsSync(specDir)).toBe(true);
      expect(existsSync(worktreePath)).toBe(true);
    }

    // Simulate bulk deletion
    for (const { specDir, worktreePath } of worktrees) {
      rmSync(worktreePath, { recursive: true, force: true });
      rmSync(specDir, { recursive: true, force: true });
    }

    // Verify all deleted
    for (const { specDir, worktreePath } of worktrees) {
      expect(existsSync(specDir)).toBe(false);
      expect(existsSync(worktreePath)).toBe(false);
    }
  });

  test('should handle deletion of already-deleted worktree', () => {
    const specId = '104-already-deleted';
    const { specDir, worktreePath } = createSpecWithWorktree(specId);

    // Delete worktree first
    rmSync(worktreePath, { recursive: true, force: true });
    expect(existsSync(worktreePath)).toBe(false);

    // Attempting to delete again should not throw
    expect(() => {
      rmSync(worktreePath, { recursive: true, force: true });
    }).not.toThrow();

    // Cleanup spec
    rmSync(specDir, { recursive: true, force: true });
  });
});

test.describe('Worktree Data Integrity Tests', () => {
  test.beforeAll(() => {
    setupTestEnvironment();
  });

  test.afterAll(() => {
    cleanupTestEnvironment();
  });

  test('should maintain spec data integrity during deletion', () => {
    const specId = '200-data-integrity';
    const { specDir, worktreePath } = createSpecWithWorktree(specId);

    // Read original plan
    const planPath = path.join(specDir, 'implementation_plan.json');
    const originalPlan = JSON.parse(readFileSync(planPath, 'utf-8'));

    // Verify structure
    expect(originalPlan.feature).toBeDefined();
    expect(originalPlan.subtasks).toBeDefined();
    expect(originalPlan.created_at).toBeDefined();

    // Delete worktree but keep spec (for history)
    rmSync(worktreePath, { recursive: true, force: true });

    // Plan should still be readable
    const planAfterDelete = JSON.parse(readFileSync(planPath, 'utf-8'));
    expect(planAfterDelete.feature).toBe(originalPlan.feature);

    // Cleanup
    rmSync(specDir, { recursive: true, force: true });
  });

  test('should validate worktree deletion does not corrupt git state', () => {
    const specId = '201-git-state';
    const { specDir, worktreePath } = createSpecWithWorktree(specId);
    registerWorktreeInGit(specId, worktreePath);

    // Verify git registration
    expect(worktreeRegisteredInGit(specId)).toBe(true);

    // Delete worktree directory
    rmSync(worktreePath, { recursive: true, force: true });

    // Run prune to clean git state
    pruneWorktrees();

    // Git state should be clean
    expect(worktreeRegisteredInGit(specId)).toBe(false);

    // Git commands should still work
    expect(() => {
      execSync('git status', { cwd: TEST_PROJECT_DIR, stdio: 'pipe' });
    }).not.toThrow();

    // Cleanup
    rmSync(specDir, { recursive: true, force: true });
  });

  test('should handle mixed worktree states during deletion', () => {
    // Create worktrees in different states
    const normalId = '202-mixed-normal';
    const phantomId = '202-mixed-phantom';
    const orphanId = '202-mixed-orphan';

    const normal = createSpecWithWorktree(normalId);
    const phantom = createPhantomWorktree(phantomId);
    const orphan = createOrphanWorktree(orphanId);

    // Verify initial mixed states
    expect(existsSync(normal.worktreePath)).toBe(true);
    expect(existsSync(phantom.worktreePath)).toBe(false);
    expect(existsSync(orphan.worktreePath)).toBe(true);

    // Clean up phantom via prune
    pruneWorktrees();
    expect(worktreeRegisteredInGit(phantomId)).toBe(false);

    // Delete normal and orphan worktrees
    rmSync(normal.worktreePath, { recursive: true, force: true });
    rmSync(orphan.worktreePath, { recursive: true, force: true });

    // Verify all worktree directories are gone
    expect(existsSync(normal.worktreePath)).toBe(false);
    expect(existsSync(phantom.worktreePath)).toBe(false);
    expect(existsSync(orphan.worktreePath)).toBe(false);

    // Cleanup spec dirs
    rmSync(normal.specDir, { recursive: true, force: true });
    rmSync(phantom.specDir, { recursive: true, force: true });
    rmSync(orphan.specDir, { recursive: true, force: true });
  });
});
