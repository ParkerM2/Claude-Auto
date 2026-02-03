"""
Review Metrics Tracking System
===============================

Tracks review cycle time, iteration count, time-to-approval, and reviewer
response time. Provides analytics for review workflow performance.
"""

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Metrics file name
REVIEW_METRICS_FILE = "review_metrics.json"


# =============================================================================
# REVIEW ITERATION TRACKING
# =============================================================================


@dataclass
class ReviewIteration:
    """
    Represents a single review iteration/cycle.

    Attributes:
        iteration_number: Sequential iteration number (1, 2, 3, ...)
        started_at: ISO timestamp when iteration started
        completed_at: ISO timestamp when iteration completed
        outcome: "approved", "rejected", or "pending"
        reviewer: Username of reviewer who performed this iteration
        duration_seconds: Duration of this iteration in seconds
        comments_count: Number of feedback comments in this iteration
    """

    iteration_number: int
    started_at: str
    completed_at: str = ""
    outcome: str = "pending"
    reviewer: str = ""
    duration_seconds: float = 0.0
    comments_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "iteration_number": self.iteration_number,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "outcome": self.outcome,
            "reviewer": self.reviewer,
            "duration_seconds": round(self.duration_seconds, 2),
            "comments_count": self.comments_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewIteration":
        """Create from dictionary."""
        return cls(
            iteration_number=data.get("iteration_number", 0),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            outcome=data.get("outcome", "pending"),
            reviewer=data.get("reviewer", ""),
            duration_seconds=data.get("duration_seconds", 0.0),
            comments_count=data.get("comments_count", 0),
        )

    def complete(
        self,
        outcome: str,
        reviewer: str = "",
        comments_count: int = 0,
    ) -> None:
        """
        Mark this iteration as complete.

        Args:
            outcome: "approved" or "rejected"
            reviewer: Username of reviewer
            comments_count: Number of feedback comments
        """
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.outcome = outcome
        self.reviewer = reviewer
        self.comments_count = comments_count

        # Calculate duration
        if self.started_at and self.completed_at:
            try:
                start = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
                end = datetime.fromisoformat(self.completed_at.replace("Z", "+00:00"))
                # Ensure both datetimes are timezone-aware (assume UTC if naive)
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                self.duration_seconds = (end - start).total_seconds()
            except (ValueError, AttributeError):
                self.duration_seconds = 0.0

    def get_duration_hours(self) -> float:
        """Get duration in hours."""
        return round(self.duration_seconds / 3600, 2)


# =============================================================================
# REVIEW METRICS
# =============================================================================


@dataclass
class ReviewMetrics:
    """
    Tracks review workflow metrics for a spec.

    Attributes:
        spec_started_at: ISO timestamp when spec was created
        first_review_at: ISO timestamp of first review iteration
        approved_at: ISO timestamp when finally approved
        iterations: List of review iterations/cycles
        total_cycle_time_seconds: Total time from spec creation to approval
        total_review_time_seconds: Total time spent in review iterations
        created_at: ISO timestamp when metrics tracking started
        updated_at: ISO timestamp when metrics were last updated
    """

    spec_started_at: str = ""
    first_review_at: str = ""
    approved_at: str = ""
    iterations: list[ReviewIteration] = field(default_factory=list)
    total_cycle_time_seconds: float = 0.0
    total_review_time_seconds: float = 0.0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        """Initialize timestamps if not set."""
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.spec_started_at:
            self.spec_started_at = self.created_at

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "spec_started_at": self.spec_started_at,
            "first_review_at": self.first_review_at,
            "approved_at": self.approved_at,
            "iterations": [iteration.to_dict() for iteration in self.iterations],
            "total_cycle_time_seconds": round(self.total_cycle_time_seconds, 2),
            "total_review_time_seconds": round(self.total_review_time_seconds, 2),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewMetrics":
        """Create from dictionary."""
        iterations_data = data.get("iterations", [])
        iterations = [ReviewIteration.from_dict(it) for it in iterations_data]

        return cls(
            spec_started_at=data.get("spec_started_at", ""),
            first_review_at=data.get("first_review_at", ""),
            approved_at=data.get("approved_at", ""),
            iterations=iterations,
            total_cycle_time_seconds=data.get("total_cycle_time_seconds", 0.0),
            total_review_time_seconds=data.get("total_review_time_seconds", 0.0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def save(self, spec_dir: Path) -> None:
        """
        Save metrics to the spec directory.

        Args:
            spec_dir: Path to the spec directory
        """
        self.updated_at = datetime.now(timezone.utc).isoformat()
        metrics_file = Path(spec_dir) / REVIEW_METRICS_FILE

        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, spec_dir: Path) -> "ReviewMetrics":
        """
        Load metrics from the spec directory.

        Returns a new empty ReviewMetrics if file doesn't exist or is invalid.

        Args:
            spec_dir: Path to the spec directory

        Returns:
            ReviewMetrics instance
        """
        metrics_file = Path(spec_dir) / REVIEW_METRICS_FILE
        if not metrics_file.exists():
            return cls()

        try:
            with open(metrics_file, encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return cls()

    def start_iteration(
        self,
        auto_save: bool = False,
        spec_dir: Path | None = None,
    ) -> ReviewIteration:
        """
        Start a new review iteration.

        Args:
            auto_save: Whether to automatically save after starting
            spec_dir: Spec directory path (required if auto_save=True)

        Returns:
            The created ReviewIteration
        """
        iteration_number = len(self.iterations) + 1
        iteration = ReviewIteration(
            iteration_number=iteration_number,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self.iterations.append(iteration)

        # Track first review timestamp
        if iteration_number == 1 and not self.first_review_at:
            self.first_review_at = iteration.started_at

        if auto_save and spec_dir:
            self.save(spec_dir)

        return iteration

    def complete_current_iteration(
        self,
        outcome: str,
        reviewer: str = "",
        comments_count: int = 0,
        auto_save: bool = False,
        spec_dir: Path | None = None,
    ) -> bool:
        """
        Complete the current (latest) review iteration.

        Args:
            outcome: "approved" or "rejected"
            reviewer: Username of reviewer
            comments_count: Number of feedback comments
            auto_save: Whether to automatically save after completion
            spec_dir: Spec directory path (required if auto_save=True)

        Returns:
            True if iteration was completed, False if no pending iteration
        """
        if not self.iterations:
            return False

        current = self.iterations[-1]
        if current.outcome != "pending":
            # Current iteration already completed
            return False

        current.complete(outcome, reviewer, comments_count)

        # If approved, record final approval time
        if outcome == "approved":
            self.approved_at = current.completed_at
            self._calculate_cycle_time()

        self._calculate_review_time()

        if auto_save and spec_dir:
            self.save(spec_dir)

        return True

    def _calculate_cycle_time(self) -> None:
        """
        Calculate total cycle time from spec creation to approval.
        Only called when spec is approved.
        """
        if not self.spec_started_at or not self.approved_at:
            return

        try:
            start = datetime.fromisoformat(self.spec_started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(self.approved_at.replace("Z", "+00:00"))
            self.total_cycle_time_seconds = (end - start).total_seconds()
        except (ValueError, AttributeError):
            self.total_cycle_time_seconds = 0.0

    def _calculate_review_time(self) -> None:
        """
        Calculate total time spent in review iterations.
        Sum of all completed iteration durations.
        """
        total = sum(
            iteration.duration_seconds
            for iteration in self.iterations
            if iteration.outcome != "pending"
        )
        self.total_review_time_seconds = total

    def get_iteration_count(self) -> int:
        """Get the total number of review iterations."""
        return len(self.iterations)

    def get_completed_iteration_count(self) -> int:
        """Get the number of completed review iterations."""
        return sum(1 for it in self.iterations if it.outcome != "pending")

    def get_approval_iteration(self) -> ReviewIteration | None:
        """
        Get the iteration where spec was approved (if any).

        Returns:
            ReviewIteration if approved, None otherwise
        """
        for iteration in reversed(self.iterations):
            if iteration.outcome == "approved":
                return iteration
        return None

    def get_average_iteration_time_seconds(self) -> float:
        """
        Get average time per review iteration.

        Returns:
            Average duration in seconds
        """
        completed = [it for it in self.iterations if it.outcome != "pending"]
        if not completed:
            return 0.0

        total_time = sum(it.duration_seconds for it in completed)
        return round(total_time / len(completed), 2)

    def get_time_to_first_review_seconds(self) -> float:
        """
        Get time from spec creation to first review.

        Returns:
            Duration in seconds
        """
        if not self.spec_started_at or not self.first_review_at:
            return 0.0

        try:
            start = datetime.fromisoformat(self.spec_started_at.replace("Z", "+00:00"))
            first = datetime.fromisoformat(self.first_review_at.replace("Z", "+00:00"))
            return round((first - start).total_seconds(), 2)
        except (ValueError, AttributeError):
            return 0.0

    def get_reviewer_response_times(self) -> dict[str, float]:
        """
        Get average response time per reviewer.

        Returns:
            Dictionary mapping reviewer username to average response time (seconds)
        """
        reviewer_times: dict[str, list[float]] = {}

        for iteration in self.iterations:
            if iteration.outcome != "pending" and iteration.reviewer:
                if iteration.reviewer not in reviewer_times:
                    reviewer_times[iteration.reviewer] = []
                reviewer_times[iteration.reviewer].append(iteration.duration_seconds)

        # Calculate averages
        return {
            reviewer: round(sum(times) / len(times), 2)
            for reviewer, times in reviewer_times.items()
        }

    def get_outcome_stats(self) -> dict[str, int]:
        """
        Get statistics on iteration outcomes.

        Returns:
            Dictionary with counts of approved, rejected, pending iterations
        """
        outcomes = Counter(it.outcome for it in self.iterations)
        return {
            "approved": outcomes.get("approved", 0),
            "rejected": outcomes.get("rejected", 0),
            "pending": outcomes.get("pending", 0),
            "total": len(self.iterations),
        }

    def get_metrics_summary(self) -> dict[str, Any]:
        """
        Get a comprehensive summary of all metrics.

        Returns:
            Dictionary with all calculated metrics
        """
        outcome_stats = self.get_outcome_stats()
        reviewer_times = self.get_reviewer_response_times()

        return {
            # Timestamps
            "spec_started_at": self.spec_started_at,
            "first_review_at": self.first_review_at,
            "approved_at": self.approved_at,
            # Iteration counts
            "total_iterations": self.get_iteration_count(),
            "completed_iterations": self.get_completed_iteration_count(),
            "approved_count": outcome_stats["approved"],
            "rejected_count": outcome_stats["rejected"],
            "pending_count": outcome_stats["pending"],
            # Time metrics (seconds)
            "total_cycle_time_seconds": round(self.total_cycle_time_seconds, 2),
            "total_review_time_seconds": round(self.total_review_time_seconds, 2),
            "average_iteration_time_seconds": self.get_average_iteration_time_seconds(),
            "time_to_first_review_seconds": self.get_time_to_first_review_seconds(),
            # Time metrics (hours, for readability)
            "total_cycle_time_hours": round(self.total_cycle_time_seconds / 3600, 2),
            "total_review_time_hours": round(self.total_review_time_seconds / 3600, 2),
            "average_iteration_time_hours": round(
                self.get_average_iteration_time_seconds() / 3600, 2
            ),
            "time_to_first_review_hours": round(
                self.get_time_to_first_review_seconds() / 3600, 2
            ),
            # Reviewer metrics
            "reviewer_response_times": reviewer_times,
            "unique_reviewers": len(reviewer_times),
            # Status
            "is_approved": bool(self.approved_at),
            "is_in_review": outcome_stats["pending"] > 0,
        }

    def reset(
        self,
        spec_dir: Path | None = None,
        auto_save: bool = False,
    ) -> None:
        """
        Reset all metrics (e.g., when spec changes after approval).

        Args:
            spec_dir: Spec directory path (required if auto_save=True)
            auto_save: Whether to automatically save after reset
        """
        self.first_review_at = ""
        self.approved_at = ""
        self.iterations.clear()
        self.total_cycle_time_seconds = 0.0
        self.total_review_time_seconds = 0.0

        if auto_save and spec_dir:
            self.save(spec_dir)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def record_review_iteration(
    spec_dir: Path,
    outcome: str,
    reviewer: str = "",
    comments_count: int = 0,
) -> bool:
    """
    Convenience function to record a review iteration.

    Loads metrics, starts/completes iteration, and saves.

    Args:
        spec_dir: Spec directory path
        outcome: "approved" or "rejected"
        reviewer: Username of reviewer
        comments_count: Number of feedback comments

    Returns:
        True if recorded successfully
    """
    metrics = ReviewMetrics.load(spec_dir)

    # If there's no pending iteration, start one
    if not metrics.iterations or metrics.iterations[-1].outcome != "pending":
        metrics.start_iteration()

    success = metrics.complete_current_iteration(
        outcome=outcome,
        reviewer=reviewer,
        comments_count=comments_count,
    )

    if success:
        metrics.save(spec_dir)

    return success


def get_review_metrics_summary(spec_dir: Path) -> dict[str, Any]:
    """
    Get metrics summary for a spec.

    Args:
        spec_dir: Spec directory path

    Returns:
        Metrics summary dictionary
    """
    metrics = ReviewMetrics.load(spec_dir)
    return metrics.get_metrics_summary()
