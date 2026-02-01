/**
 * Review workflow handlers - Main entry point
 *
 * This file serves as the main entry point for all review workflow IPC handlers.
 * The actual implementation is organized in the review/ module:
 *
 * - review/index.ts - Review checklist, reviewer assignment, and metrics handlers
 *
 * This modular structure improves:
 * - Code maintainability and readability
 * - Testability of individual components
 * - Separation of concerns
 * - Developer experience when working with the codebase
 */

// Re-export the main registration function from the review module
export { registerReviewHandlers } from './review';
