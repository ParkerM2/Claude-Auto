"""
Pattern Detection for Self-Healing Agents
==========================================

Detects stuck patterns in autonomous builds to enable intelligent recovery.
Identifies loops, thrashing, and repeated failures before they waste time/context.

Key Features:
- Loop detection (same approach tried repeatedly)
- Thrashing detection (alternating between a few approaches)
- Repeated failure detection (same error multiple times)
- Time-based timeout detection
- Configurable thresholds for pattern recognition
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class PatternType(Enum):
    """Types of stuck patterns that can be detected."""

    LOOP = "loop"  # Same approach attempted multiple times
    THRASHING = "thrashing"  # Alternating between 2-3 approaches repeatedly
    REPEATED_FAILURE = "repeated_failure"  # Same error occurring multiple times
    TIMEOUT = "timeout"  # Subtask taking too long
    CONTEXT_EXHAUSTION = "context_exhaustion"  # Running out of context tokens
    NO_PATTERN = "no_pattern"  # No stuck pattern detected


@dataclass
class PatternMatch:
    """Represents a detected pattern."""

    pattern_type: PatternType
    confidence: float  # 0.0 to 1.0
    evidence: str  # Human-readable explanation
    recommendation: str  # Suggested recovery action
    metadata: dict[str, Any]  # Additional pattern-specific data


class PatternDetector:
    """
    Detects stuck patterns in autonomous agent builds.

    Analyzes attempt history to identify:
    - Loops (same fix attempted N times)
    - Thrashing (cycling between 2-3 approaches)
    - Repeated failures (same error N times)
    - Timeouts (subtask exceeding time limit)

    Used by RecoveryManager to determine when to escalate or change strategy.
    """

    def __init__(
        self,
        loop_threshold: int = 3,
        thrashing_threshold: int = 4,
        repeated_failure_threshold: int = 3,
        timeout_minutes: int = 30,
    ):
        """
        Initialize pattern detector.

        Args:
            loop_threshold: Number of identical attempts before detecting a loop
            thrashing_threshold: Number of alternating attempts before detecting thrashing
            repeated_failure_threshold: Number of same errors before detecting repeated failure
            timeout_minutes: Minutes before a subtask is considered timed out
        """
        self.loop_threshold = loop_threshold
        self.thrashing_threshold = thrashing_threshold
        self.repeated_failure_threshold = repeated_failure_threshold
        self.timeout_minutes = timeout_minutes

    def detect_patterns(
        self,
        attempt_history: list[dict[str, Any]],
        subtask_start_time: str | None = None,
    ) -> list[PatternMatch]:
        """
        Detect all patterns in the attempt history.

        Args:
            attempt_history: List of attempt records with fields:
                - approach: str describing the approach taken
                - error: str error message if failed
                - timestamp: str ISO format timestamp
            subtask_start_time: ISO timestamp when subtask started (for timeout detection)

        Returns:
            List of detected patterns, ordered by confidence (highest first)
        """
        patterns = []

        # Detect loop pattern
        loop_pattern = self._detect_loop(attempt_history)
        if loop_pattern:
            patterns.append(loop_pattern)

        # Detect thrashing pattern
        thrashing_pattern = self._detect_thrashing(attempt_history)
        if thrashing_pattern:
            patterns.append(thrashing_pattern)

        # Detect repeated failure pattern
        repeated_failure_pattern = self._detect_repeated_failure(attempt_history)
        if repeated_failure_pattern:
            patterns.append(repeated_failure_pattern)

        # Detect timeout pattern
        if subtask_start_time:
            timeout_pattern = self._detect_timeout(attempt_history, subtask_start_time)
            if timeout_pattern:
                patterns.append(timeout_pattern)

        # Detect context exhaustion
        context_pattern = self._detect_context_exhaustion(attempt_history)
        if context_pattern:
            patterns.append(context_pattern)

        # Sort by confidence (highest first)
        patterns.sort(key=lambda p: p.confidence, reverse=True)

        return patterns

    def _detect_loop(
        self, attempt_history: list[dict[str, Any]]
    ) -> PatternMatch | None:
        """
        Detect if the same approach is being tried repeatedly.

        Returns:
            PatternMatch if loop detected, None otherwise
        """
        if len(attempt_history) < self.loop_threshold:
            return None

        # Look at the last N attempts
        recent_attempts = attempt_history[-self.loop_threshold :]

        # Get approaches (normalize by lowercasing and removing extra whitespace)
        approaches = [
            self._normalize_approach(a.get("approach", "")) for a in recent_attempts
        ]

        # Check if all approaches are the same
        if len(set(approaches)) == 1 and approaches[0]:
            confidence = min(1.0, len(attempt_history) / (self.loop_threshold * 2))
            return PatternMatch(
                pattern_type=PatternType.LOOP,
                confidence=confidence,
                evidence=f"Same approach attempted {len(attempt_history)} times: '{approaches[0][:100]}'",
                recommendation="Try a completely different approach or escalate to human",
                metadata={
                    "approach": approaches[0],
                    "attempt_count": len(attempt_history),
                    "threshold": self.loop_threshold,
                },
            )

        return None

    def _detect_thrashing(
        self, attempt_history: list[dict[str, Any]]
    ) -> PatternMatch | None:
        """
        Detect if agent is cycling between 2-3 different approaches.

        Returns:
            PatternMatch if thrashing detected, None otherwise
        """
        if len(attempt_history) < self.thrashing_threshold:
            return None

        # Look at recent attempts
        recent_attempts = attempt_history[-self.thrashing_threshold :]
        approaches = [
            self._normalize_approach(a.get("approach", "")) for a in recent_attempts
        ]

        # Count unique approaches
        unique_approaches = set(approaches)

        # Thrashing = cycling between 2-3 approaches
        if 2 <= len(unique_approaches) <= 3:
            # Check if there's actually cycling (not just trying 3 different things once)
            approach_counts = {
                approach: approaches.count(approach) for approach in unique_approaches
            }

            # If each approach tried at least twice, it's thrashing
            if all(count >= 2 for count in approach_counts.values()):
                confidence = min(
                    1.0, len(attempt_history) / (self.thrashing_threshold * 1.5)
                )
                approach_list = list(unique_approaches)
                return PatternMatch(
                    pattern_type=PatternType.THRASHING,
                    confidence=confidence,
                    evidence=f"Cycling between {len(unique_approaches)} approaches: "
                    f"{', '.join([f'"{a[:50]}..."' for a in approach_list])}",
                    recommendation="Break the cycle by trying a fundamentally different strategy",
                    metadata={
                        "approaches": approach_list,
                        "attempt_count": len(attempt_history),
                        "cycle_count": min(approach_counts.values()),
                    },
                )

        return None

    def _detect_repeated_failure(
        self, attempt_history: list[dict[str, Any]]
    ) -> PatternMatch | None:
        """
        Detect if the same error is occurring repeatedly.

        Returns:
            PatternMatch if repeated failure detected, None otherwise
        """
        if len(attempt_history) < self.repeated_failure_threshold:
            return None

        # Extract and normalize errors
        errors = [
            self._normalize_error(a.get("error", ""))
            for a in attempt_history
            if a.get("error")
        ]

        if not errors:
            return None

        # Find most common error
        error_counts = {}
        for error in errors:
            error_counts[error] = error_counts.get(error, 0) + 1

        # Find the most repeated error
        max_count = max(error_counts.values())
        most_common_error = [e for e, c in error_counts.items() if c == max_count][0]

        if max_count >= self.repeated_failure_threshold:
            confidence = min(1.0, max_count / (self.repeated_failure_threshold * 2))
            return PatternMatch(
                pattern_type=PatternType.REPEATED_FAILURE,
                confidence=confidence,
                evidence=f"Same error occurred {max_count} times: '{most_common_error[:100]}'",
                recommendation="The current approach cannot fix this error. Try a different solution",
                metadata={
                    "error": most_common_error,
                    "occurrence_count": max_count,
                    "threshold": self.repeated_failure_threshold,
                },
            )

        return None

    def _detect_timeout(
        self, attempt_history: list[dict[str, Any]], subtask_start_time: str
    ) -> PatternMatch | None:
        """
        Detect if the subtask has exceeded the time limit.

        Args:
            attempt_history: List of attempts
            subtask_start_time: ISO timestamp when subtask started

        Returns:
            PatternMatch if timeout detected, None otherwise
        """
        try:
            start_time = datetime.fromisoformat(
                subtask_start_time.replace("Z", "+00:00")
            )
            current_time = (
                datetime.now(start_time.tzinfo) if start_time.tzinfo else datetime.now()
            )
            elapsed = current_time - start_time

            if elapsed > timedelta(minutes=self.timeout_minutes):
                confidence = min(
                    1.0, elapsed.total_seconds() / (self.timeout_minutes * 60 * 2)
                )
                return PatternMatch(
                    pattern_type=PatternType.TIMEOUT,
                    confidence=confidence,
                    evidence=f"Subtask has been running for {elapsed.total_seconds() / 60:.1f} minutes "
                    f"(limit: {self.timeout_minutes} minutes)",
                    recommendation="Skip this subtask and move to next, or escalate to human",
                    metadata={
                        "elapsed_minutes": elapsed.total_seconds() / 60,
                        "timeout_minutes": self.timeout_minutes,
                        "attempt_count": len(attempt_history),
                    },
                )
        except (ValueError, AttributeError, TypeError):
            # Invalid timestamp format
            pass

        return None

    def _detect_context_exhaustion(
        self, attempt_history: list[dict[str, Any]]
    ) -> PatternMatch | None:
        """
        Detect if context exhaustion is occurring.

        Returns:
            PatternMatch if context exhaustion detected, None otherwise
        """
        # Check if any recent errors mention context/token limits
        context_keywords = [
            "context",
            "token limit",
            "maximum length",
            "too long",
            "context window",
        ]

        recent_errors = [
            a.get("error", "").lower() for a in attempt_history[-3:] if a.get("error")
        ]

        context_error_count = sum(
            1
            for error in recent_errors
            if any(keyword in error for keyword in context_keywords)
        )

        if context_error_count >= 2:
            return PatternMatch(
                pattern_type=PatternType.CONTEXT_EXHAUSTION,
                confidence=0.9,
                evidence=f"Context/token limit errors in {context_error_count} recent attempts",
                recommendation="Break subtask into smaller pieces or use fresh agent session",
                metadata={
                    "context_error_count": context_error_count,
                    "total_attempts": len(attempt_history),
                },
            )

        return None

    def _normalize_approach(self, approach: str) -> str:
        """
        Normalize an approach string for comparison.

        Args:
            approach: Raw approach string

        Returns:
            Normalized lowercase string with extra whitespace removed
        """
        return " ".join(approach.lower().strip().split())

    def _normalize_error(self, error: str) -> str:
        """
        Normalize an error string for comparison.

        Removes dynamic parts like timestamps, file paths, line numbers.

        Args:
            error: Raw error string

        Returns:
            Normalized error string
        """
        import re

        # Remove timestamps
        normalized = re.sub(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", "", error)

        # Remove file paths (Unix and Windows)
        normalized = re.sub(r"[/\\][\w/\\.-]+\.(py|js|ts|tsx|jsx)", "", normalized)

        # Remove line numbers (e.g., "line 42", ":42:")
        normalized = re.sub(r"line \d+|:\d+:", "", normalized)

        # Remove hex addresses (e.g., "0x7f8b3c4a5e10")
        normalized = re.sub(r"0x[0-9a-fA-F]+", "", normalized)

        # Normalize whitespace
        normalized = " ".join(normalized.lower().strip().split())

        return normalized

    def get_strongest_pattern(
        self,
        attempt_history: list[dict[str, Any]],
        subtask_start_time: str | None = None,
    ) -> PatternMatch | None:
        """
        Get the most confident pattern match.

        Args:
            attempt_history: List of attempt records
            subtask_start_time: ISO timestamp when subtask started

        Returns:
            Strongest PatternMatch or None if no patterns detected
        """
        patterns = self.detect_patterns(attempt_history, subtask_start_time)
        return patterns[0] if patterns else None
