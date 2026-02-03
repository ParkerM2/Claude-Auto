#!/usr/bin/env python3
"""
Tests for ReviewMetrics Data Class
===================================

Comprehensive unit tests for ReviewMetrics and ReviewIteration classes.
Tests cover iteration tracking, metrics calculation, and persistence.
"""

import json
import time
from pathlib import Path

import pytest

from apps.backend.review.metrics import (
    ReviewIteration,
    ReviewMetrics,
    REVIEW_METRICS_FILE,
    record_review_iteration,
    get_review_metrics_summary,
)


# =============================================================================
# REVIEW ITERATION - BASIC FUNCTIONALITY
# =============================================================================


class TestReviewIterationBasics:
    """Tests for ReviewIteration basic functionality."""

    def test_create_iteration_with_defaults(self) -> None:
        """New ReviewIteration has correct defaults."""
        iteration = ReviewIteration(
            iteration_number=1, started_at="2024-01-01T00:00:00"
        )

        assert iteration.iteration_number == 1
        assert iteration.started_at == "2024-01-01T00:00:00"
        assert iteration.completed_at == ""
        assert iteration.outcome == "pending"
        assert iteration.reviewer == ""
        assert iteration.duration_seconds == 0.0
        assert iteration.comments_count == 0

    def test_complete_iteration_approved(self) -> None:
        """complete() marks iteration as approved."""
        iteration = ReviewIteration(
            iteration_number=1, started_at="2024-01-01T00:00:00"
        )
        iteration.complete(
            outcome="approved", reviewer="alice", comments_count=3
        )

        assert iteration.outcome == "approved"
        assert iteration.reviewer == "alice"
        assert iteration.comments_count == 3
        assert iteration.completed_at != ""
        assert iteration.duration_seconds > 0

    def test_complete_iteration_rejected(self) -> None:
        """complete() marks iteration as rejected."""
        iteration = ReviewIteration(
            iteration_number=1, started_at="2024-01-01T00:00:00"
        )
        iteration.complete(outcome="rejected", reviewer="bob")

        assert iteration.outcome == "rejected"
        assert iteration.reviewer == "bob"

    def test_get_duration_hours(self) -> None:
        """get_duration_hours() converts seconds to hours."""
        iteration = ReviewIteration(
            iteration_number=1, started_at="2024-01-01T00:00:00"
        )
        iteration.duration_seconds = 7200  # 2 hours

        hours = iteration.get_duration_hours()

        assert hours == 2.0


# =============================================================================
# REVIEW METRICS - BASIC FUNCTIONALITY
# =============================================================================


class TestReviewMetricsBasics:
    """Tests for ReviewMetrics basic functionality."""

    def test_create_empty_metrics(self) -> None:
        """New ReviewMetrics has correct defaults."""
        metrics = ReviewMetrics()

        assert metrics.spec_started_at != ""
        assert metrics.first_review_at == ""
        assert metrics.approved_at == ""
        assert metrics.iterations == []
        assert metrics.total_cycle_time_seconds == 0.0
        assert metrics.total_review_time_seconds == 0.0
        assert metrics.created_at != ""

    def test_start_iteration(self) -> None:
        """start_iteration() creates new iteration."""
        metrics = ReviewMetrics()

        iteration = metrics.start_iteration()

        assert len(metrics.iterations) == 1
        assert iteration.iteration_number == 1
        assert iteration.started_at != ""
        assert metrics.first_review_at != ""

    def test_start_multiple_iterations(self) -> None:
        """start_iteration() increments iteration number."""
        metrics = ReviewMetrics()

        iteration1 = metrics.start_iteration()
        iteration2 = metrics.start_iteration()

        assert iteration1.iteration_number == 1
        assert iteration2.iteration_number == 2
        assert len(metrics.iterations) == 2

    def test_complete_current_iteration_approved(self) -> None:
        """complete_current_iteration() completes latest iteration."""
        metrics = ReviewMetrics()
        metrics.start_iteration()

        result = metrics.complete_current_iteration(
            outcome="approved", reviewer="alice", comments_count=2
        )

        assert result is True
        assert metrics.iterations[0].outcome == "approved"
        assert metrics.iterations[0].reviewer == "alice"
        assert metrics.approved_at != ""

    def test_complete_current_iteration_rejected(self) -> None:
        """complete_current_iteration() with rejection."""
        metrics = ReviewMetrics()
        metrics.start_iteration()

        result = metrics.complete_current_iteration(
            outcome="rejected", reviewer="bob"
        )

        assert result is True
        assert metrics.iterations[0].outcome == "rejected"
        assert metrics.approved_at == ""  # Not approved yet

    def test_complete_no_iteration(self) -> None:
        """complete_current_iteration() returns False when no iteration."""
        metrics = ReviewMetrics()

        result = metrics.complete_current_iteration(outcome="approved")

        assert result is False

    def test_track_multiple_iterations(self) -> None:
        """Track multiple review iterations."""
        metrics = ReviewMetrics()

        # First iteration - rejected
        metrics.start_iteration()
        metrics.complete_current_iteration(
            outcome="rejected", reviewer="alice"
        )

        # Second iteration - rejected again
        metrics.start_iteration()
        metrics.complete_current_iteration(
            outcome="rejected", reviewer="bob"
        )

        # Third iteration - approved
        metrics.start_iteration()
        metrics.complete_current_iteration(
            outcome="approved", reviewer="alice"
        )

        assert len(metrics.iterations) == 3
        assert metrics.iterations[0].outcome == "rejected"
        assert metrics.iterations[1].outcome == "rejected"
        assert metrics.iterations[2].outcome == "approved"
        assert metrics.approved_at != ""


# =============================================================================
# REVIEW METRICS - CALCULATIONS
# =============================================================================


class TestReviewMetricsCalculations:
    """Tests for ReviewMetrics calculations."""

    def test_calculate_cycle_time(self) -> None:
        """Cycle time calculated when approved."""
        metrics = ReviewMetrics()
        metrics.start_iteration()
        time.sleep(0.01)  # Ensure measurable time difference
        metrics.complete_current_iteration(outcome="approved")

        assert metrics.total_cycle_time_seconds > 0

    def test_calculate_review_time(self) -> None:
        """Review time is sum of iteration durations."""
        metrics = ReviewMetrics()

        metrics.start_iteration()
        time.sleep(0.01)  # Ensure measurable time difference
        metrics.complete_current_iteration(outcome="rejected")

        metrics.start_iteration()
        time.sleep(0.01)  # Ensure measurable time difference
        metrics.complete_current_iteration(outcome="approved")

        assert metrics.total_review_time_seconds > 0

    def test_get_iteration_count(self) -> None:
        """get_iteration_count() returns total iterations."""
        metrics = ReviewMetrics()
        metrics.start_iteration()
        metrics.start_iteration()

        assert metrics.get_iteration_count() == 2

    def test_get_completed_iteration_count(self) -> None:
        """get_completed_iteration_count() returns completed count."""
        metrics = ReviewMetrics()
        metrics.start_iteration()
        metrics.complete_current_iteration(outcome="rejected")
        metrics.start_iteration()  # Pending

        assert metrics.get_completed_iteration_count() == 1

    def test_get_approval_iteration(self) -> None:
        """get_approval_iteration() returns approved iteration."""
        metrics = ReviewMetrics()
        metrics.start_iteration()
        metrics.complete_current_iteration(outcome="rejected")
        metrics.start_iteration()
        metrics.complete_current_iteration(outcome="approved")

        approved_iteration = metrics.get_approval_iteration()

        assert approved_iteration is not None
        assert approved_iteration.outcome == "approved"
        assert approved_iteration.iteration_number == 2

    def test_get_reviewer_response_times(self) -> None:
        """get_reviewer_response_times() calculates averages."""
        metrics = ReviewMetrics()

        metrics.start_iteration()
        metrics.complete_current_iteration(outcome="rejected", reviewer="alice")

        metrics.start_iteration()
        metrics.complete_current_iteration(outcome="approved", reviewer="bob")

        response_times = metrics.get_reviewer_response_times()

        assert "alice" in response_times
        assert "bob" in response_times
        # Response times may be 0 or very small since start and complete happen
        # almost instantaneously in tests
        assert response_times["alice"] >= 0
        assert response_times["bob"] >= 0

    def test_get_outcome_stats(self) -> None:
        """get_outcome_stats() returns correct counts."""
        metrics = ReviewMetrics()

        metrics.start_iteration()
        metrics.complete_current_iteration(outcome="rejected")

        metrics.start_iteration()
        metrics.complete_current_iteration(outcome="approved")

        metrics.start_iteration()  # Pending

        stats = metrics.get_outcome_stats()

        assert stats["approved"] == 1
        assert stats["rejected"] == 1
        assert stats["pending"] == 1
        assert stats["total"] == 3

    def test_get_metrics_summary(self) -> None:
        """get_metrics_summary() returns comprehensive summary."""
        metrics = ReviewMetrics()
        metrics.start_iteration()
        metrics.complete_current_iteration(
            outcome="rejected", reviewer="alice"
        )
        metrics.start_iteration()
        metrics.complete_current_iteration(
            outcome="approved", reviewer="bob"
        )

        summary = metrics.get_metrics_summary()

        assert summary["total_iterations"] == 2
        assert summary["completed_iterations"] == 2
        assert summary["approved_count"] == 1
        assert summary["rejected_count"] == 1
        assert summary["is_approved"] is True
        assert summary["unique_reviewers"] == 2

    def test_reset_metrics(self) -> None:
        """reset() clears all metrics."""
        metrics = ReviewMetrics()
        metrics.start_iteration()
        metrics.complete_current_iteration(outcome="approved")

        metrics.reset()

        assert len(metrics.iterations) == 0
        assert metrics.first_review_at == ""
        assert metrics.approved_at == ""
        assert metrics.total_cycle_time_seconds == 0.0


# =============================================================================
# REVIEW METRICS - PERSISTENCE
# =============================================================================


class TestReviewMetricsPersistence:
    """Tests for ReviewMetrics load and save operations."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """save() creates review_metrics.json file."""
        metrics = ReviewMetrics()
        metrics.start_iteration()

        metrics.save(tmp_path)

        file_path = tmp_path / REVIEW_METRICS_FILE
        assert file_path.exists()

    def test_save_writes_correct_data(self, tmp_path: Path) -> None:
        """save() writes correct JSON data."""
        metrics = ReviewMetrics()
        metrics.start_iteration()
        metrics.complete_current_iteration(
            outcome="approved", reviewer="alice"
        )

        metrics.save(tmp_path)

        file_path = tmp_path / REVIEW_METRICS_FILE
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["iterations"]) == 1
        assert data["iterations"][0]["outcome"] == "approved"
        assert data["iterations"][0]["reviewer"] == "alice"
        assert data["approved_at"] != ""

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """load() returns empty metrics for nonexistent file."""
        metrics = ReviewMetrics.load(tmp_path)

        assert metrics.iterations == []
        assert metrics.approved_at == ""

    def test_load_existing_file(self, tmp_path: Path) -> None:
        """load() reads existing metrics file."""
        # Save metrics
        original = ReviewMetrics()
        original.start_iteration()
        original.complete_current_iteration(
            outcome="approved", reviewer="alice"
        )
        original.save(tmp_path)

        # Load it back
        loaded = ReviewMetrics.load(tmp_path)

        assert len(loaded.iterations) == 1
        assert loaded.iterations[0].outcome == "approved"
        assert loaded.iterations[0].reviewer == "alice"
        assert loaded.approved_at != ""

    def test_to_dict(self) -> None:
        """to_dict() returns correct dictionary."""
        metrics = ReviewMetrics()
        metrics.start_iteration()

        d = metrics.to_dict()

        assert "spec_started_at" in d
        assert "iterations" in d
        assert "created_at" in d
        assert len(d["iterations"]) == 1

    def test_from_dict(self) -> None:
        """from_dict() creates correct ReviewMetrics."""
        data = {
            "spec_started_at": "2024-01-01T00:00:00",
            "first_review_at": "2024-01-02T00:00:00",
            "approved_at": "2024-01-03T00:00:00",
            "iterations": [
                {
                    "iteration_number": 1,
                    "started_at": "2024-01-02T00:00:00",
                    "completed_at": "2024-01-03T00:00:00",
                    "outcome": "approved",
                    "reviewer": "alice",
                    "duration_seconds": 3600.0,
                    "comments_count": 2,
                }
            ],
            "total_cycle_time_seconds": 86400.0,
            "total_review_time_seconds": 3600.0,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-03T00:00:00",
        }

        metrics = ReviewMetrics.from_dict(data)

        assert len(metrics.iterations) == 1
        assert metrics.iterations[0].outcome == "approved"
        assert metrics.approved_at == "2024-01-03T00:00:00"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


class TestReviewMetricsUtilities:
    """Tests for utility functions."""

    def test_record_review_iteration(self, tmp_path: Path) -> None:
        """record_review_iteration() convenience function."""
        result = record_review_iteration(
            tmp_path, outcome="approved", reviewer="alice", comments_count=2
        )

        assert result is True

        # Verify it was saved
        metrics = ReviewMetrics.load(tmp_path)
        assert len(metrics.iterations) == 1
        assert metrics.iterations[0].outcome == "approved"

    def test_get_review_metrics_summary(self, tmp_path: Path) -> None:
        """get_review_metrics_summary() utility function."""
        # Create some metrics
        metrics = ReviewMetrics()
        metrics.start_iteration()
        metrics.complete_current_iteration(outcome="approved")
        metrics.save(tmp_path)

        # Get summary
        summary = get_review_metrics_summary(tmp_path)

        assert summary["total_iterations"] == 1
        assert summary["is_approved"] is True
