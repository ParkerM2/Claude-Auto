#!/usr/bin/env python3
"""
Code Quality Tracker Module
============================

Stores and retrieves historical code quality metrics over time.
Provides trend analysis to track code quality improvements or degradation.

This module is used by:
- QA Agent: To verify code quality meets standards
- Coder Agent: To track quality trends during development
- Validation Strategy: To ensure code quality doesn't degrade

Usage:
    from analysis.code_quality_tracker import CodeQualityTracker

    tracker = CodeQualityTracker(spec_dir)
    tracker.save_metrics(metrics_data)

    history = tracker.get_history()
    trends = tracker.get_trends()
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class MetricsSnapshot:
    """
    A snapshot of code quality metrics at a specific point in time.

    Attributes:
        timestamp: ISO 8601 timestamp when metrics were captured
        total_files: Number of files analyzed
        total_lines: Total lines of code
        average_complexity: Average cyclomatic complexity
        average_maintainability: Average maintainability index
        high_complexity_count: Number of functions with complexity > 10
        critical_complexity_count: Number of functions with complexity > 20
        technical_debt_score: Technical debt score (0-100, higher is worse)
    """

    timestamp: str
    total_files: int
    total_lines: int
    average_complexity: float
    average_maintainability: float
    high_complexity_count: int
    critical_complexity_count: int
    technical_debt_score: float


@dataclass
class QualityTrend:
    """
    Trend analysis comparing current metrics to historical data.

    Attributes:
        current: Current metrics snapshot
        previous: Previous metrics snapshot (if available)
        complexity_trend: Trend direction for complexity (improving, stable, degrading)
        maintainability_trend: Trend direction for maintainability
        debt_trend: Trend direction for technical debt
        metrics_delta: Dictionary of metric changes (current - previous)
        recommendations: List of recommendations based on trends
    """

    current: MetricsSnapshot
    previous: MetricsSnapshot | None = None
    complexity_trend: str = "stable"  # improving, stable, degrading
    maintainability_trend: str = "stable"
    debt_trend: str = "stable"
    metrics_delta: dict[str, float] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


# =============================================================================
# CODE QUALITY TRACKER
# =============================================================================


class CodeQualityTracker:
    """
    Tracks code quality metrics over time and provides trend analysis.

    Stores metrics as JSON files in the spec directory, allowing historical
    comparison and trend detection.
    """

    def __init__(self, spec_dir: Path) -> None:
        """
        Initialize the code quality tracker.

        Args:
            spec_dir: Path to the spec directory where metrics will be stored
        """
        self.spec_dir = Path(spec_dir)
        self.metrics_dir = self.spec_dir / "code_quality_metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self._cache: list[MetricsSnapshot] = []

    def save_metrics(self, metrics: dict[str, Any]) -> str:
        """
        Save code quality metrics with timestamp.

        Args:
            metrics: Metrics dictionary from CodeQualityAnalyzer

        Returns:
            Timestamp string of the saved metrics
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        snapshot = MetricsSnapshot(
            timestamp=timestamp,
            total_files=metrics.get("total_files", 0),
            total_lines=metrics.get("total_lines", 0),
            average_complexity=metrics.get("average_complexity", 0.0),
            average_maintainability=metrics.get("average_maintainability", 0.0),
            high_complexity_count=metrics.get("high_complexity_count", 0),
            critical_complexity_count=metrics.get("critical_complexity_count", 0),
            technical_debt_score=metrics.get("technical_debt_score", 0.0),
        )

        # Save to file with timestamp as filename
        safe_timestamp = timestamp.replace(":", "-").replace(".", "-")
        metrics_file = self.metrics_dir / f"metrics_{safe_timestamp}.json"

        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": snapshot.timestamp,
                    "metrics": {
                        "total_files": snapshot.total_files,
                        "total_lines": snapshot.total_lines,
                        "average_complexity": snapshot.average_complexity,
                        "average_maintainability": snapshot.average_maintainability,
                        "high_complexity_count": snapshot.high_complexity_count,
                        "critical_complexity_count": snapshot.critical_complexity_count,
                        "technical_debt_score": snapshot.technical_debt_score,
                    },
                },
                f,
                indent=2,
            )

        # Clear cache to force reload on next access
        self._cache = []

        return timestamp

    def get_history(self, limit: int | None = None) -> list[MetricsSnapshot]:
        """
        Get historical metrics snapshots.

        Args:
            limit: Maximum number of snapshots to return (most recent first)

        Returns:
            List of metrics snapshots ordered by timestamp (newest first)
        """
        if not self._cache:
            self._load_history()

        if limit:
            return self._cache[:limit]
        return self._cache

    def get_latest(self) -> MetricsSnapshot | None:
        """
        Get the most recent metrics snapshot.

        Returns:
            Latest metrics snapshot or None if no history exists
        """
        history = self.get_history(limit=1)
        return history[0] if history else None

    def get_trends(self) -> QualityTrend:
        """
        Analyze trends by comparing current metrics to previous.

        Returns:
            QualityTrend object with trend analysis and recommendations
        """
        history = self.get_history(limit=2)

        if not history:
            # No data available
            return QualityTrend(
                current=MetricsSnapshot(
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    total_files=0,
                    total_lines=0,
                    average_complexity=0.0,
                    average_maintainability=0.0,
                    high_complexity_count=0,
                    critical_complexity_count=0,
                    technical_debt_score=0.0,
                ),
                recommendations=["No historical data available"],
            )

        current = history[0]
        previous = history[1] if len(history) > 1 else None

        trend = QualityTrend(current=current, previous=previous)

        if previous:
            # Calculate deltas
            trend.metrics_delta = {
                "complexity": current.average_complexity - previous.average_complexity,
                "maintainability": current.average_maintainability
                - previous.average_maintainability,
                "technical_debt": current.technical_debt_score
                - previous.technical_debt_score,
                "high_complexity_count": current.high_complexity_count
                - previous.high_complexity_count,
                "critical_complexity_count": current.critical_complexity_count
                - previous.critical_complexity_count,
            }

            # Determine trends (using 5% threshold for significance)
            complexity_change = trend.metrics_delta["complexity"]
            if abs(complexity_change) < 0.5:
                trend.complexity_trend = "stable"
            elif complexity_change < 0:
                trend.complexity_trend = "improving"
            else:
                trend.complexity_trend = "degrading"

            maintainability_change = trend.metrics_delta["maintainability"]
            if abs(maintainability_change) < 2.0:
                trend.maintainability_trend = "stable"
            elif maintainability_change > 0:
                trend.maintainability_trend = "improving"
            else:
                trend.maintainability_trend = "degrading"

            debt_change = trend.metrics_delta["technical_debt"]
            if abs(debt_change) < 2.0:
                trend.debt_trend = "stable"
            elif debt_change < 0:
                trend.debt_trend = "improving"
            else:
                trend.debt_trend = "degrading"

            # Generate recommendations
            trend.recommendations = self._generate_recommendations(trend)

        return trend

    def clear_history(self) -> None:
        """
        Clear all historical metrics data.

        Warning: This will permanently delete all stored metrics.
        """
        if self.metrics_dir.exists():
            for metrics_file in self.metrics_dir.glob("metrics_*.json"):
                metrics_file.unlink()

        self._cache = []

    def _load_history(self) -> None:
        """Load all metrics files from disk and populate cache."""
        metrics_files = sorted(self.metrics_dir.glob("metrics_*.json"), reverse=True)

        snapshots = []
        for metrics_file in metrics_files:
            try:
                with open(metrics_file, encoding="utf-8") as f:
                    data = json.load(f)

                metrics = data.get("metrics", {})
                snapshot = MetricsSnapshot(
                    timestamp=data.get("timestamp", ""),
                    total_files=metrics.get("total_files", 0),
                    total_lines=metrics.get("total_lines", 0),
                    average_complexity=metrics.get("average_complexity", 0.0),
                    average_maintainability=metrics.get("average_maintainability", 0.0),
                    high_complexity_count=metrics.get("high_complexity_count", 0),
                    critical_complexity_count=metrics.get(
                        "critical_complexity_count", 0
                    ),
                    technical_debt_score=metrics.get("technical_debt_score", 0.0),
                )

                snapshots.append(snapshot)

            except (json.JSONDecodeError, KeyError, TypeError):
                # Skip corrupted files
                continue

        self._cache = snapshots

    def _generate_recommendations(self, trend: QualityTrend) -> list[str]:
        """
        Generate recommendations based on trend analysis.

        Args:
            trend: Quality trend object

        Returns:
            List of actionable recommendations
        """
        recommendations = []

        # Complexity recommendations
        if trend.complexity_trend == "degrading":
            recommendations.append(
                "⚠️ Complexity is increasing - consider refactoring complex functions"
            )
        elif trend.complexity_trend == "improving":
            recommendations.append(
                "✅ Complexity is decreasing - code quality improving"
            )

        # Maintainability recommendations
        if trend.maintainability_trend == "degrading":
            recommendations.append(
                "⚠️ Maintainability is decreasing - review code structure and documentation"
            )
        elif trend.maintainability_trend == "improving":
            recommendations.append("✅ Maintainability is improving - good progress")

        # Technical debt recommendations
        if trend.debt_trend == "degrading":
            recommendations.append(
                "⚠️ Technical debt is increasing - allocate time for refactoring"
            )
        elif trend.debt_trend == "improving":
            recommendations.append(
                "✅ Technical debt is decreasing - keep up the good work"
            )

        # Critical complexity warnings
        if (
            trend.current.critical_complexity_count > 0
            and trend.metrics_delta.get("critical_complexity_count", 0) > 0
        ):
            recommendations.append(
                f"🚨 {trend.current.critical_complexity_count} functions with critical complexity (>20) - immediate refactoring recommended"
            )

        # High complexity warnings
        if (
            trend.current.high_complexity_count > 10
            and trend.metrics_delta.get("high_complexity_count", 0) > 0
        ):
            recommendations.append(
                f"⚠️ {trend.current.high_complexity_count} functions with high complexity (>10) - consider simplification"
            )

        # Overall quality assessment
        if trend.current.technical_debt_score > 60:
            recommendations.append(
                "🚨 High technical debt score - significant refactoring needed"
            )
        elif trend.current.technical_debt_score > 40:
            recommendations.append(
                "⚠️ Moderate technical debt - plan for incremental improvements"
            )

        if not recommendations:
            recommendations.append(
                "✅ Code quality is stable - no immediate actions needed"
            )

        return recommendations
