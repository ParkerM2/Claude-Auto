#!/usr/bin/env python3
"""
Tests for ReviewerAssignment Data Class
========================================

Comprehensive unit tests for ReviewerAssignment and ReviewerInfo classes.
Tests cover reviewer management, approval tracking, and persistence.
"""

import json
from pathlib import Path

import pytest

from apps.backend.review.reviewers import (
    ReviewerAssignment,
    ReviewerInfo,
    REVIEWER_ASSIGNMENT_FILE,
)


# =============================================================================
# REVIEWER INFO - BASIC FUNCTIONALITY
# =============================================================================


class TestReviewerInfoBasics:
    """Tests for ReviewerInfo basic functionality."""

    def test_create_reviewer_with_defaults(self) -> None:
        """New ReviewerInfo has correct defaults."""
        reviewer = ReviewerInfo(username="alice")

        assert reviewer.username == "alice"
        assert reviewer.assigned_at != ""
        assert reviewer.assigned_by == ""
        assert reviewer.approved is False
        assert reviewer.approved_at == ""
        assert reviewer.feedback == ""

    def test_approve_reviewer(self) -> None:
        """approve() sets approval status."""
        reviewer = ReviewerInfo(username="bob")
        reviewer.approve(feedback="Looks good!")

        assert reviewer.approved is True
        assert reviewer.approved_at != ""
        assert reviewer.feedback == "Looks good!"

    def test_revoke_approval(self) -> None:
        """revoke_approval() clears approval status."""
        reviewer = ReviewerInfo(username="charlie")
        reviewer.approve(feedback="Good")
        reviewer.revoke_approval()

        assert reviewer.approved is False
        assert reviewer.approved_at == ""

    def test_reviewer_to_dict(self) -> None:
        """to_dict() returns correct dictionary."""
        reviewer = ReviewerInfo(
            username="dave",
            assigned_at="2024-01-01T00:00:00",
            assigned_by="alice",
            approved=True,
            approved_at="2024-01-02T00:00:00",
            feedback="LGTM",
        )

        d = reviewer.to_dict()

        assert d["username"] == "dave"
        assert d["assigned_at"] == "2024-01-01T00:00:00"
        assert d["assigned_by"] == "alice"
        assert d["approved"] is True
        assert d["approved_at"] == "2024-01-02T00:00:00"
        assert d["feedback"] == "LGTM"

    def test_reviewer_from_dict(self) -> None:
        """from_dict() creates correct ReviewerInfo."""
        data = {
            "username": "eve",
            "assigned_at": "2024-01-01T00:00:00",
            "assigned_by": "bob",
            "approved": True,
            "approved_at": "2024-01-02T00:00:00",
            "feedback": "Approved",
        }

        reviewer = ReviewerInfo.from_dict(data)

        assert reviewer.username == "eve"
        assert reviewer.assigned_at == "2024-01-01T00:00:00"
        assert reviewer.assigned_by == "bob"
        assert reviewer.approved is True
        assert reviewer.approved_at == "2024-01-02T00:00:00"
        assert reviewer.feedback == "Approved"


# =============================================================================
# REVIEWER ASSIGNMENT - BASIC FUNCTIONALITY
# =============================================================================


class TestReviewerAssignmentBasics:
    """Tests for ReviewerAssignment basic functionality."""

    def test_create_empty_assignment(self) -> None:
        """New ReviewerAssignment has correct defaults."""
        assignment = ReviewerAssignment()

        assert assignment.reviewers == []
        assert assignment.required_approvals == 0
        assert assignment.created_at != ""
        assert assignment.updated_at != ""
        assert assignment.allow_self_approval is False

    def test_add_reviewer(self) -> None:
        """add_reviewer() adds reviewer to assignment."""
        assignment = ReviewerAssignment()
        reviewer = assignment.add_reviewer("alice", assigned_by="admin")

        assert len(assignment.reviewers) == 1
        assert reviewer.username == "alice"
        assert reviewer.assigned_by == "admin"

    def test_add_duplicate_reviewer_raises(self) -> None:
        """add_reviewer() raises ValueError for duplicate username."""
        assignment = ReviewerAssignment()
        assignment.add_reviewer("alice")

        with pytest.raises(ValueError, match="already assigned"):
            assignment.add_reviewer("alice")

    def test_remove_reviewer(self) -> None:
        """remove_reviewer() removes reviewer from assignment."""
        assignment = ReviewerAssignment()
        assignment.add_reviewer("alice")

        result = assignment.remove_reviewer("alice")

        assert result is True
        assert len(assignment.reviewers) == 0

    def test_remove_nonexistent_reviewer(self) -> None:
        """remove_reviewer() returns False for nonexistent reviewer."""
        assignment = ReviewerAssignment()

        result = assignment.remove_reviewer("nonexistent")

        assert result is False

    def test_get_reviewer(self) -> None:
        """get_reviewer() retrieves reviewer by username."""
        assignment = ReviewerAssignment()
        assignment.add_reviewer("alice")

        reviewer = assignment.get_reviewer("alice")

        assert reviewer is not None
        assert reviewer.username == "alice"

    def test_get_nonexistent_reviewer(self) -> None:
        """get_reviewer() returns None for nonexistent reviewer."""
        assignment = ReviewerAssignment()

        reviewer = assignment.get_reviewer("nonexistent")

        assert reviewer is None


# =============================================================================
# REVIEWER ASSIGNMENT - APPROVAL TRACKING
# =============================================================================


class TestReviewerAssignmentApprovals:
    """Tests for ReviewerAssignment approval tracking."""

    def test_approve_by_reviewer(self) -> None:
        """approve_by_reviewer() marks reviewer as approved."""
        assignment = ReviewerAssignment()
        assignment.add_reviewer("alice")

        result = assignment.approve_by_reviewer(
            "alice", feedback="Looks good"
        )

        assert result is True
        reviewer = assignment.get_reviewer("alice")
        assert reviewer is not None
        assert reviewer.approved is True
        assert reviewer.feedback == "Looks good"

    def test_approve_nonexistent_reviewer(self) -> None:
        """approve_by_reviewer() returns False for nonexistent reviewer."""
        assignment = ReviewerAssignment()

        result = assignment.approve_by_reviewer("nonexistent")

        assert result is False

    def test_revoke_approval_by_reviewer(self) -> None:
        """revoke_approval_by_reviewer() revokes approval."""
        assignment = ReviewerAssignment()
        assignment.add_reviewer("alice")
        assignment.approve_by_reviewer("alice")

        result = assignment.revoke_approval_by_reviewer("alice")

        assert result is True
        reviewer = assignment.get_reviewer("alice")
        assert reviewer is not None
        assert reviewer.approved is False

    def test_get_approval_count(self) -> None:
        """get_approval_count() returns correct count."""
        assignment = ReviewerAssignment()
        assignment.add_reviewer("alice")
        assignment.add_reviewer("bob")
        assignment.add_reviewer("charlie")

        assignment.approve_by_reviewer("alice")
        assignment.approve_by_reviewer("charlie")

        assert assignment.get_approval_count() == 2

    def test_has_required_approvals_all_must_approve(self) -> None:
        """has_required_approvals() with required_approvals=0."""
        assignment = ReviewerAssignment(required_approvals=0)
        assignment.add_reviewer("alice")
        assignment.add_reviewer("bob")

        # Not all approved yet
        assignment.approve_by_reviewer("alice")
        assert assignment.has_required_approvals() is False

        # Now all approved
        assignment.approve_by_reviewer("bob")
        assert assignment.has_required_approvals() is True

    def test_has_required_approvals_partial(self) -> None:
        """has_required_approvals() with partial approval requirement."""
        assignment = ReviewerAssignment(required_approvals=2)
        assignment.add_reviewer("alice")
        assignment.add_reviewer("bob")
        assignment.add_reviewer("charlie")

        # One approval - not enough
        assignment.approve_by_reviewer("alice")
        assert assignment.has_required_approvals() is False

        # Two approvals - enough
        assignment.approve_by_reviewer("bob")
        assert assignment.has_required_approvals() is True

    def test_has_required_approvals_no_reviewers(self) -> None:
        """has_required_approvals() returns True when no reviewers."""
        assignment = ReviewerAssignment()

        assert assignment.has_required_approvals() is True

    def test_get_approval_status(self) -> None:
        """get_approval_status() returns correct statistics."""
        assignment = ReviewerAssignment(required_approvals=2)
        assignment.add_reviewer("alice")
        assignment.add_reviewer("bob")
        assignment.add_reviewer("charlie")

        assignment.approve_by_reviewer("alice")
        assignment.approve_by_reviewer("bob")

        status = assignment.get_approval_status()

        assert status["total_reviewers"] == 3
        assert status["approved_count"] == 2
        assert status["required_count"] == 2
        assert status["has_required_approvals"] is True
        assert status["pending_reviewers"] == ["charlie"]
        assert set(status["approved_reviewers"]) == {"alice", "bob"}

    def test_reset_approvals(self) -> None:
        """reset_approvals() clears all approvals."""
        assignment = ReviewerAssignment()
        assignment.add_reviewer("alice")
        assignment.add_reviewer("bob")
        assignment.approve_by_reviewer("alice")
        assignment.approve_by_reviewer("bob")

        assignment.reset_approvals()

        assert all(not r.approved for r in assignment.reviewers)

    def test_clear_reviewers(self) -> None:
        """clear_reviewers() removes all reviewers."""
        assignment = ReviewerAssignment()
        assignment.add_reviewer("alice")
        assignment.add_reviewer("bob")

        assignment.clear_reviewers()

        assert len(assignment.reviewers) == 0


# =============================================================================
# REVIEWER ASSIGNMENT - PERSISTENCE
# =============================================================================


class TestReviewerAssignmentPersistence:
    """Tests for ReviewerAssignment load and save operations."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """save() creates reviewer_assignment.json file."""
        assignment = ReviewerAssignment()
        assignment.add_reviewer("alice")

        assignment.save(tmp_path)

        file_path = tmp_path / REVIEWER_ASSIGNMENT_FILE
        assert file_path.exists()

    def test_save_writes_correct_data(self, tmp_path: Path) -> None:
        """save() writes correct JSON data."""
        assignment = ReviewerAssignment(required_approvals=2)
        assignment.add_reviewer("alice", assigned_by="admin")
        assignment.approve_by_reviewer("alice", feedback="Good")

        assignment.save(tmp_path)

        file_path = tmp_path / REVIEWER_ASSIGNMENT_FILE
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["reviewers"]) == 1
        assert data["reviewers"][0]["username"] == "alice"
        assert data["reviewers"][0]["approved"] is True
        assert data["reviewers"][0]["feedback"] == "Good"
        assert data["required_approvals"] == 2

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """load() returns empty assignment for nonexistent file."""
        assignment = ReviewerAssignment.load(tmp_path)

        assert assignment.reviewers == []
        assert assignment.required_approvals == 0

    def test_load_existing_file(self, tmp_path: Path) -> None:
        """load() reads existing assignment file."""
        # Save an assignment
        original = ReviewerAssignment(required_approvals=2)
        original.add_reviewer("alice", assigned_by="admin")
        original.approve_by_reviewer("alice", feedback="LGTM")
        original.save(tmp_path)

        # Load it back
        loaded = ReviewerAssignment.load(tmp_path)

        assert len(loaded.reviewers) == 1
        assert loaded.reviewers[0].username == "alice"
        assert loaded.reviewers[0].approved is True
        assert loaded.reviewers[0].feedback == "LGTM"
        assert loaded.required_approvals == 2

    def test_to_dict(self) -> None:
        """to_dict() returns correct dictionary."""
        assignment = ReviewerAssignment()
        assignment.add_reviewer("alice")

        d = assignment.to_dict()

        assert "reviewers" in d
        assert "required_approvals" in d
        assert "created_at" in d
        assert "updated_at" in d
        assert "allow_self_approval" in d
        assert len(d["reviewers"]) == 1

    def test_from_dict(self) -> None:
        """from_dict() creates correct ReviewerAssignment."""
        data = {
            "reviewers": [
                {
                    "username": "alice",
                    "assigned_at": "2024-01-01T00:00:00",
                    "assigned_by": "admin",
                    "approved": True,
                    "approved_at": "2024-01-02T00:00:00",
                    "feedback": "Approved",
                }
            ],
            "required_approvals": 1,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
            "allow_self_approval": True,
        }

        assignment = ReviewerAssignment.from_dict(data)

        assert len(assignment.reviewers) == 1
        assert assignment.reviewers[0].username == "alice"
        assert assignment.required_approvals == 1
        assert assignment.allow_self_approval is True
