"""
Reviewer Assignment Management
===============================

Handles reviewer assignments for specs with approval tracking and persistence.
Supports multiple reviewers, assignment status, and approval state management.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Reviewer assignment file name
REVIEWER_ASSIGNMENT_FILE = "reviewer_assignment.json"


@dataclass
class ReviewerInfo:
    """
    Information about a single reviewer assigned to a spec.

    Attributes:
        username: Reviewer's username or identifier
        assigned_at: ISO timestamp when reviewer was assigned
        assigned_by: Who assigned this reviewer
        approved: Whether this reviewer has approved the spec
        approved_at: ISO timestamp when reviewer approved
        feedback: Optional feedback/comments from reviewer
    """

    username: str
    assigned_at: str = ""
    assigned_by: str = ""
    approved: bool = False
    approved_at: str = ""
    feedback: str = ""

    def __post_init__(self) -> None:
        """Initialize timestamps if not set."""
        if not self.assigned_at:
            self.assigned_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "username": self.username,
            "assigned_at": self.assigned_at,
            "assigned_by": self.assigned_by,
            "approved": self.approved,
            "approved_at": self.approved_at,
            "feedback": self.feedback,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewerInfo":
        """Create from dictionary."""
        return cls(
            username=data.get("username", ""),
            assigned_at=data.get("assigned_at", ""),
            assigned_by=data.get("assigned_by", ""),
            approved=data.get("approved", False),
            approved_at=data.get("approved_at", ""),
            feedback=data.get("feedback", ""),
        )

    def approve(self, feedback: str = "") -> None:
        """
        Mark this reviewer as having approved.

        Args:
            feedback: Optional feedback from the reviewer
        """
        self.approved = True
        self.approved_at = datetime.now().isoformat()
        if feedback:
            self.feedback = feedback

    def revoke_approval(self) -> None:
        """Revoke this reviewer's approval."""
        self.approved = False
        self.approved_at = ""


@dataclass
class ReviewerAssignment:
    """
    Manages reviewer assignments for a spec.

    Attributes:
        reviewers: List of assigned reviewers
        required_approvals: Number of approvals required (0 = all reviewers must approve)
        created_at: ISO timestamp when assignment was created
        updated_at: ISO timestamp when assignment was last modified
        allow_self_approval: Whether spec author can approve their own work
    """

    reviewers: list[ReviewerInfo] = field(default_factory=list)
    required_approvals: int = 0
    created_at: str = ""
    updated_at: str = ""
    allow_self_approval: bool = False

    def __post_init__(self) -> None:
        """Initialize timestamps if not set."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "reviewers": [reviewer.to_dict() for reviewer in self.reviewers],
            "required_approvals": self.required_approvals,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "allow_self_approval": self.allow_self_approval,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewerAssignment":
        """Create from dictionary."""
        reviewers_data = data.get("reviewers", [])
        reviewers = [ReviewerInfo.from_dict(r) for r in reviewers_data]

        return cls(
            reviewers=reviewers,
            required_approvals=data.get("required_approvals", 0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            allow_self_approval=data.get("allow_self_approval", False),
        )

    def save(self, spec_dir: Path) -> None:
        """
        Save reviewer assignment to the spec directory.

        Args:
            spec_dir: Path to the spec directory
        """
        self.updated_at = datetime.now().isoformat()
        assignment_file = Path(spec_dir) / REVIEWER_ASSIGNMENT_FILE

        with open(assignment_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, spec_dir: Path) -> "ReviewerAssignment":
        """
        Load reviewer assignment from the spec directory.

        Returns a new empty ReviewerAssignment if file doesn't exist or is invalid.

        Args:
            spec_dir: Path to the spec directory

        Returns:
            ReviewerAssignment instance
        """
        assignment_file = Path(spec_dir) / REVIEWER_ASSIGNMENT_FILE
        if not assignment_file.exists():
            return cls()

        try:
            with open(assignment_file, encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return cls()

    def get_reviewer(self, username: str) -> ReviewerInfo | None:
        """
        Get a reviewer by username.

        Args:
            username: The reviewer's username to find

        Returns:
            ReviewerInfo if found, None otherwise
        """
        for reviewer in self.reviewers:
            if reviewer.username == username:
                return reviewer
        return None

    def add_reviewer(
        self,
        username: str,
        assigned_by: str = "user",
        auto_save: bool = False,
        spec_dir: Path | None = None,
    ) -> ReviewerInfo:
        """
        Add a new reviewer to the assignment.

        Args:
            username: Username of the reviewer to add
            assigned_by: Who is assigning this reviewer
            auto_save: Whether to automatically save after adding
            spec_dir: Spec directory path (required if auto_save=True)

        Returns:
            The created ReviewerInfo

        Raises:
            ValueError: If reviewer is already assigned
        """
        if self.get_reviewer(username):
            raise ValueError(f"Reviewer '{username}' is already assigned")

        reviewer = ReviewerInfo(
            username=username,
            assigned_by=assigned_by,
        )
        self.reviewers.append(reviewer)

        if auto_save and spec_dir:
            self.save(spec_dir)

        return reviewer

    def remove_reviewer(
        self,
        username: str,
        auto_save: bool = False,
        spec_dir: Path | None = None,
    ) -> bool:
        """
        Remove a reviewer from the assignment.

        Args:
            username: The reviewer's username to remove
            auto_save: Whether to automatically save after removing
            spec_dir: Spec directory path (required if auto_save=True)

        Returns:
            True if reviewer was removed, False if not found
        """
        for i, reviewer in enumerate(self.reviewers):
            if reviewer.username == username:
                self.reviewers.pop(i)
                if auto_save and spec_dir:
                    self.save(spec_dir)
                return True
        return False

    def approve_by_reviewer(
        self,
        username: str,
        feedback: str = "",
        auto_save: bool = False,
        spec_dir: Path | None = None,
    ) -> bool:
        """
        Mark a reviewer's approval.

        Args:
            username: The reviewer's username
            feedback: Optional feedback from the reviewer
            auto_save: Whether to automatically save after approval
            spec_dir: Spec directory path (required if auto_save=True)

        Returns:
            True if reviewer was found and marked, False otherwise
        """
        reviewer = self.get_reviewer(username)
        if reviewer:
            reviewer.approve(feedback)
            if auto_save and spec_dir:
                self.save(spec_dir)
            return True
        return False

    def revoke_approval_by_reviewer(
        self,
        username: str,
        auto_save: bool = False,
        spec_dir: Path | None = None,
    ) -> bool:
        """
        Revoke a reviewer's approval.

        Args:
            username: The reviewer's username
            auto_save: Whether to automatically save after revoking
            spec_dir: Spec directory path (required if auto_save=True)

        Returns:
            True if reviewer was found and revoked, False otherwise
        """
        reviewer = self.get_reviewer(username)
        if reviewer:
            reviewer.revoke_approval()
            if auto_save and spec_dir:
                self.save(spec_dir)
            return True
        return False

    def get_approval_count(self) -> int:
        """
        Get the number of reviewers who have approved.

        Returns:
            Count of approved reviewers
        """
        return sum(1 for reviewer in self.reviewers if reviewer.approved)

    def get_required_approval_count(self) -> int:
        """
        Get the number of approvals required.

        Returns:
            Number of required approvals (total reviewers if required_approvals=0)
        """
        if self.required_approvals <= 0:
            # 0 means all reviewers must approve
            return len(self.reviewers)
        return min(self.required_approvals, len(self.reviewers))

    def has_required_approvals(self) -> bool:
        """
        Check if the required number of approvals has been met.

        Returns:
            True if approval requirement is satisfied, False otherwise
        """
        if not self.reviewers:
            # No reviewers means no approval requirement
            return True

        approval_count = self.get_approval_count()
        required_count = self.get_required_approval_count()

        return approval_count >= required_count

    def get_approval_status(self) -> dict:
        """
        Get detailed approval status.

        Returns:
            Dictionary with approval statistics
        """
        total_reviewers = len(self.reviewers)
        approved_count = self.get_approval_count()
        required_count = self.get_required_approval_count()
        pending_reviewers = [r.username for r in self.reviewers if not r.approved]
        approved_reviewers = [r.username for r in self.reviewers if r.approved]

        return {
            "total_reviewers": total_reviewers,
            "approved_count": approved_count,
            "required_count": required_count,
            "has_required_approvals": self.has_required_approvals(),
            "pending_reviewers": pending_reviewers,
            "approved_reviewers": approved_reviewers,
            "approval_percentage": (
                (approved_count / total_reviewers * 100) if total_reviewers > 0 else 100
            ),
        }

    def reset_approvals(
        self,
        spec_dir: Path | None = None,
        auto_save: bool = False,
    ) -> None:
        """
        Reset all reviewer approvals (e.g., when spec changes).

        Args:
            spec_dir: Spec directory path (required if auto_save=True)
            auto_save: Whether to automatically save after reset
        """
        for reviewer in self.reviewers:
            reviewer.revoke_approval()

        if auto_save and spec_dir:
            self.save(spec_dir)

    def clear_reviewers(
        self,
        spec_dir: Path | None = None,
        auto_save: bool = False,
    ) -> None:
        """
        Remove all reviewers from the assignment.

        Args:
            spec_dir: Spec directory path (required if auto_save=True)
            auto_save: Whether to automatically save after clearing
        """
        self.reviewers.clear()

        if auto_save and spec_dir:
            self.save(spec_dir)
