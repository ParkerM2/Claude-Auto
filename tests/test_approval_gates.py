#!/usr/bin/env python3
"""
Tests for Approval Gates (can_merge function)
==============================================

Tests for the can_merge() function which enforces approval requirements
before allowing merge operations.
"""

from pathlib import Path

import pytest

from apps.backend.review.reviewer import can_merge
from apps.backend.review.state import ReviewState
from apps.backend.review.checklist import ReviewChecklist
from apps.backend.review.reviewers import ReviewerAssignment


# =============================================================================
# APPROVAL GATES - SUCCESS CASES
# =============================================================================


class TestApprovalGatesSuccess:
    """Tests for can_merge() when all gates are satisfied."""

    def test_can_merge_all_gates_satisfied(self, tmp_path: Path) -> None:
        """can_merge() returns True when all gates pass."""
        # Create approved state
        state = ReviewState()
        state.approve(tmp_path, approved_by="admin")

        # Create complete checklist
        checklist = ReviewChecklist()
        checklist.add_item("test", "Test item", required=True)
        checklist.mark_item_complete("test")
        checklist.save(tmp_path)

        # Create reviewer assignment with approvals
        assignment = ReviewerAssignment(required_approvals=0)
        assignment.add_reviewer("alice")
        assignment.approve_by_reviewer("alice")
        assignment.save(tmp_path)

        # Check can merge
        can_merge_result, blocking_reasons = can_merge(tmp_path)

        assert can_merge_result is True
        assert blocking_reasons == []

    def test_can_merge_no_reviewers_required(self, tmp_path: Path) -> None:
        """can_merge() succeeds when no reviewers assigned."""
        # Create approved state
        state = ReviewState()
        state.approve(tmp_path, approved_by="admin")

        # Create complete checklist
        checklist = ReviewChecklist()
        checklist.add_item("test", "Test", required=True)
        checklist.mark_item_complete("test")
        checklist.save(tmp_path)

        # No reviewer assignment file created

        # Check can merge
        can_merge_result, blocking_reasons = can_merge(tmp_path)

        assert can_merge_result is True
        assert blocking_reasons == []

    def test_can_merge_only_optional_checklist_items(
        self, tmp_path: Path
    ) -> None:
        """can_merge() succeeds with only optional checklist items."""
        # Create approved state
        state = ReviewState()
        state.approve(tmp_path, approved_by="admin")

        # Create checklist with only optional items
        checklist = ReviewChecklist()
        checklist.add_item("opt1", "Optional 1", required=False)
        checklist.add_item("opt2", "Optional 2", required=False)
        checklist.save(tmp_path)

        # Check can merge
        can_merge_result, blocking_reasons = can_merge(tmp_path)

        assert can_merge_result is True
        assert blocking_reasons == []


# =============================================================================
# APPROVAL GATES - BLOCKING CASES
# =============================================================================


class TestApprovalGatesBlocking:
    """Tests for can_merge() when gates are not satisfied."""

    def test_can_merge_blocks_when_not_approved(self, tmp_path: Path) -> None:
        """can_merge() blocks when ReviewState not approved."""
        # Create unapproved state
        state = ReviewState()
        state.save(tmp_path)

        # Create complete checklist
        checklist = ReviewChecklist()
        checklist.add_item("test", "Test", required=True)
        checklist.mark_item_complete("test")
        checklist.save(tmp_path)

        # Check can merge
        can_merge_result, blocking_reasons = can_merge(tmp_path)

        assert can_merge_result is False
        assert any("not approved" in reason.lower() for reason in blocking_reasons)

    def test_can_merge_blocks_when_spec_hash_changed(
        self, tmp_path: Path
    ) -> None:
        """can_merge() blocks when spec changed after approval."""
        # Create spec.md file
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("Original content", encoding="utf-8")

        # Create approved state
        state = ReviewState()
        state.approve(tmp_path, approved_by="admin")

        # Modify spec.md (invalidates approval)
        spec_file.write_text("Modified content", encoding="utf-8")

        # Create complete checklist
        checklist = ReviewChecklist()
        checklist.add_item("test", "Test", required=True)
        checklist.mark_item_complete("test")
        checklist.save(tmp_path)

        # Check can merge
        can_merge_result, blocking_reasons = can_merge(tmp_path)

        assert can_merge_result is False
        assert any(
            "changed since approval" in reason.lower()
            for reason in blocking_reasons
        )

    def test_can_merge_blocks_when_checklist_incomplete(
        self, tmp_path: Path
    ) -> None:
        """can_merge() blocks when checklist incomplete."""
        # Create approved state
        state = ReviewState()
        state.approve(tmp_path, approved_by="admin")

        # Create incomplete checklist
        checklist = ReviewChecklist()
        checklist.add_item("test1", "Test 1", required=True)
        checklist.add_item("test2", "Test 2", required=True)
        checklist.mark_item_complete("test1")
        # test2 not completed
        checklist.save(tmp_path)

        # Check can merge
        can_merge_result, blocking_reasons = can_merge(tmp_path)

        assert can_merge_result is False
        assert any(
            "checklist incomplete" in reason.lower()
            for reason in blocking_reasons
        )
        assert any("1" in reason and "remaining" in reason.lower() for reason in blocking_reasons)

    def test_can_merge_blocks_when_missing_reviewer_approvals(
        self, tmp_path: Path
    ) -> None:
        """can_merge() blocks when reviewers haven't approved."""
        # Create approved state
        state = ReviewState()
        state.approve(tmp_path, approved_by="admin")

        # Create complete checklist
        checklist = ReviewChecklist()
        checklist.add_item("test", "Test", required=True)
        checklist.mark_item_complete("test")
        checklist.save(tmp_path)

        # Create reviewer assignment without approvals
        assignment = ReviewerAssignment(required_approvals=0)
        assignment.add_reviewer("alice")
        assignment.add_reviewer("bob")
        # Neither approved
        assignment.save(tmp_path)

        # Check can merge
        can_merge_result, blocking_reasons = can_merge(tmp_path)

        assert can_merge_result is False
        assert any(
            "missing approvals" in reason.lower()
            for reason in blocking_reasons
        )

    def test_can_merge_blocks_with_multiple_issues(
        self, tmp_path: Path
    ) -> None:
        """can_merge() returns all blocking reasons."""
        # Create unapproved state
        state = ReviewState()
        state.save(tmp_path)

        # Create incomplete checklist
        checklist = ReviewChecklist()
        checklist.add_item("test1", "Test 1", required=True)
        checklist.add_item("test2", "Test 2", required=True)
        checklist.mark_item_complete("test1")
        checklist.save(tmp_path)

        # Create reviewer assignment without approvals
        assignment = ReviewerAssignment(required_approvals=0)
        assignment.add_reviewer("alice")
        assignment.save(tmp_path)

        # Check can merge
        can_merge_result, blocking_reasons = can_merge(tmp_path)

        assert can_merge_result is False
        assert len(blocking_reasons) >= 3
        assert any("not approved" in reason.lower() for reason in blocking_reasons)
        assert any(
            "checklist incomplete" in reason.lower()
            for reason in blocking_reasons
        )
        assert any(
            "missing approvals" in reason.lower()
            for reason in blocking_reasons
        )

    def test_can_merge_handles_missing_files_gracefully(
        self, tmp_path: Path
    ) -> None:
        """can_merge() handles missing review files gracefully."""
        # No state, checklist, or assignment files created

        # Check can merge - should block on unapproved state
        can_merge_result, blocking_reasons = can_merge(tmp_path)

        assert can_merge_result is False
        assert any("not approved" in reason.lower() for reason in blocking_reasons)

    def test_can_merge_provides_correct_blocking_messages(
        self, tmp_path: Path
    ) -> None:
        """can_merge() provides clear, actionable blocking messages."""
        # Create unapproved state
        state = ReviewState()
        state.save(tmp_path)

        # Create incomplete checklist with 2 items remaining
        checklist = ReviewChecklist()
        checklist.add_item("test1", "Test 1", required=True)
        checklist.add_item("test2", "Test 2", required=True)
        checklist.add_item("test3", "Test 3", required=True)
        checklist.mark_item_complete("test1")
        checklist.save(tmp_path)

        # Create reviewer assignment with named reviewers
        assignment = ReviewerAssignment(required_approvals=0)
        assignment.add_reviewer("alice")
        assignment.add_reviewer("bob")
        assignment.save(tmp_path)

        # Check can merge
        can_merge_result, blocking_reasons = can_merge(tmp_path)

        assert can_merge_result is False

        # Check message quality
        messages = " ".join(blocking_reasons)
        assert "Spec not approved" in messages
        assert "2" in messages  # 2 required items remaining
        assert "alice" in messages or "bob" in messages  # Names of pending reviewers
