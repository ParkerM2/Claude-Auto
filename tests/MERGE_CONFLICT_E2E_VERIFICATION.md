# Merge Conflict Analysis E2E Verification Guide

## Overview
This document provides manual verification steps for the merge conflict analysis feature end-to-end flow.

## Automated Test Coverage

The automated E2E test suite in `test_merge_conflict_analysis_e2e.py` covers:

### 1. Backend Preview Conflicts
- ✅ Preview returns conflicts with AI-suggested strategies
- ✅ Strategy suggestion function generates meaningful strategies
- ✅ Strategies vary based on conflict severity (HIGH → manual review, LOW → auto-merge)

### 2. Conflict Data Serialization
- ✅ ConflictRegion.to_dict() includes resolution_strategies field
- ✅ ConflictRegion.from_dict() preserves strategies through JSON round-trip
- ✅ Preview response has correct JSON format for IPC communication

### 3. Strategy Selection and Application
- ✅ User strategy selection format (file_path:line_range → strategy)
- ✅ Conflict resolutions parameter format for CLI (--conflict-resolutions JSON)
- ✅ JSON serialization/deserialization works correctly

### 4. Complete Flow Integration
- ✅ Preview → display → select → merge flow
- ✅ Conflict count badge data calculation
- ✅ Auto-merge vs manual review detection

### 5. Error Handling
- ✅ No conflicts scenario (empty list)
- ✅ Preview failure scenario (error message)
- ✅ Missing strategies fallback (backward compatibility)

### 6. IPC Communication
- ✅ Preview conflicts IPC request format
- ✅ Merge with resolutions IPC request format

## Manual Verification Steps

### Prerequisites
1. Electron app built and running: `npm run dev`
2. Test project with a task in `human_review` status
3. Task has an associated git worktree with potential merge conflicts

### Step 1: Preview Conflicts
**Action:** Open task detail, navigate to Review tab

**Expected:**
- Preview loads automatically when tab opens
- Loading indicator appears during analysis
- Conflict count badge appears on merge button if conflicts exist
- Badge shows total conflict count with destructive (red) or warning (yellow) color

**Verify:**
```
✓ Auto-preview triggered on Review tab open
✓ Conflict count badge visible
✓ Badge color matches severity (high severity = red)
```

### Step 2: View Conflict Details
**Action:** Click "View Details" button to open ConflictDetailsDialog

**Expected:**
- Dialog opens showing list of all detected conflicts
- Each conflict displays:
  - File path and line range
  - Conflict reason/description
  - Severity indicator
  - AI-suggested resolution strategies (3-4 options)
- Strategies displayed as radio buttons for selection
- Auto-mergeable conflicts clearly indicated

**Verify:**
```
✓ Dialog shows all conflicts
✓ AI strategies visible for each conflict (3-4 options)
✓ Radio buttons allow selecting one strategy per conflict
✓ Auto-merge badge shown for auto-mergeable conflicts
✓ Internationalization works (English/French)
```

### Step 3: Select Resolution Strategies
**Action:** Select a strategy for each conflict using radio buttons

**Expected:**
- Only one strategy can be selected per conflict
- Selected strategy is highlighted
- Selection persists when scrolling through conflicts
- No visual glitches or layout issues

**Verify:**
```
✓ Radio button selection works correctly
✓ One strategy selected per conflict
✓ Visual feedback shows selected state
✓ Selections persist while dialog is open
```

### Step 4: Initiate Merge with Selected Strategies
**Action:** Close dialog, click merge button

**Expected:**
- Merge process starts
- Backend receives conflict resolutions as JSON parameter
- Selected strategies are applied during merge
- Progress shown in UI

**Verify:**
```
✓ Merge button triggers merge with conflict resolutions
✓ Backend receives --conflict-resolutions parameter
✓ Selected strategies logged/applied
✓ Progress indicator visible
```

### Step 5: Verify Merge Result
**Action:** Check merge completion status

**Expected:**
- Merge completes successfully
- Changes applied according to selected strategies
- Task status updates appropriately
- No errors in console logs

**Verify:**
```
✓ Merge completes without errors
✓ Changes reflect selected strategies
✓ Task status updated
✓ No console errors
```

## Edge Cases to Test

### No Conflicts
- Task with no merge conflicts
- Preview should show "No conflicts detected"
- Merge button should work without opening conflict dialog

### All Auto-Mergeable
- All conflicts can be auto-merged
- Badge should show count but with lower severity color
- Dialog should clearly indicate auto-merge capability

### High Severity Conflicts
- Conflicts marked as HIGH or CRITICAL severity
- Badge should be red (destructive variant)
- Strategies should emphasize manual review/AI assistance

### Mixed Conflicts
- Combination of auto-mergeable and manual review conflicts
- Badge shows total count with highest severity color
- Dialog clearly distinguishes between types

### Preview Failure
- Worktree doesn't exist or other error
- Error message displayed to user
- Graceful degradation (can still attempt merge)

## Test Execution Commands

```bash
# Run automated E2E tests
cd apps/backend
python -m pytest ../../tests/test_merge_conflict_analysis_e2e.py -v

# Run all merge-related tests
python -m pytest ../../tests/test_merge_*.py -v

# Type check frontend
cd ../frontend
npm run type-check

# Run frontend unit tests
npm test -- --run
```

## Success Criteria

All automated tests pass:
- ✅ 15+ test cases in test_merge_conflict_analysis_e2e.py
- ✅ Conflict data serialization works
- ✅ Strategy suggestion function works
- ✅ IPC communication format validated

Manual verification complete:
- ✅ Preview loads automatically
- ✅ Conflict details dialog shows strategies
- ✅ User can select strategies
- ✅ Merge applies selected strategies
- ✅ UI properly internationalized
- ✅ Error handling works

## Known Limitations

1. **Strategy Application**: The backend accepts user-selected strategies but the actual conflict resolution still uses git's merge algorithms. The strategies serve as guidance for the merge orchestrator.

2. **Real-time Updates**: Conflict preview is triggered on tab open, not in real-time as commits are made to the base branch.

3. **Offline Mode**: Conflict analysis requires git access and may fail if git is not available.

## Related Files

- Test Suite: `tests/test_merge_conflict_analysis_e2e.py`
- Backend Types: `apps/backend/merge/types.py`
- Conflict Analysis: `apps/backend/merge/conflict_analysis.py`
- Frontend Dialog: `apps/frontend/src/renderer/components/task-detail/task-review/ConflictDetailsDialog.tsx`
- IPC Handlers: `apps/frontend/src/main/ipc-handlers/task/worktree-handlers.ts`
- i18n Keys: `apps/frontend/src/shared/i18n/locales/{en,fr}/dialogs.json`

## Notes for QA

This feature adds proactive conflict detection without changing the actual merge behavior. It provides visibility and user control over conflict resolution strategies, but the underlying git merge mechanics remain the same.

The AI-suggested strategies are generated based on:
- Conflict severity (CRITICAL/HIGH/MEDIUM/LOW)
- Change types (MODIFIED/ADDED/DELETED)
- Auto-merge capability
- File types and patterns
- Merge strategy (recursive/ours/theirs)

Strategy suggestions are heuristic-based, not AI-model-generated (no LLM calls during preview for performance).
