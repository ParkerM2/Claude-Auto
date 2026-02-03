"""
Recovery Learning System
========================

Learns from successful recoveries to improve future recovery attempts.
Stores patterns in Graphiti memory for cross-session learning.

Key Features:
- Track successful recovery patterns
- Store recovery outcomes in Graphiti
- Retrieve similar past recoveries
- Provide learned insights for recovery hints
- Learn which strategies work for which failure types
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RecoveryPattern:
    """
    Represents a learned recovery pattern.

    Attributes:
        failure_type: Type of failure that occurred
        strategy_used: Strategy that was successful
        subtask_description: Description of the subtask
        success_count: Number of times this pattern led to success
        last_used: Timestamp of last successful use
    """

    failure_type: str
    strategy_used: str
    subtask_description: str
    success_count: int = 1
    last_used: str = ""


class RecoveryLearner:
    """
    Manages learning from successful recoveries.

    Responsibilities:
    - Record successful recovery attempts
    - Store patterns in Graphiti for persistence
    - Retrieve similar past recoveries
    - Provide learned insights for recovery hints
    - Track which strategies work best for different failure types
    """

    def __init__(self, spec_dir: Path, project_dir: Path | None = None):
        """
        Initialize recovery learner.

        Args:
            spec_dir: Spec directory containing memory/
            project_dir: Optional project root directory (for Graphiti)
        """
        self.spec_dir = spec_dir
        self.project_dir = project_dir or spec_dir
        self.memory_dir = spec_dir / "memory"
        self.patterns_file = self.memory_dir / "recovery_patterns.json"

        # Graphiti memory integration (optional)
        self._graphiti_memory = None
        self._graphiti_available = False

        # Ensure memory directory exists
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Initialize patterns file if it doesn't exist
        if not self.patterns_file.exists():
            self._init_patterns_file()

        # Initialize Graphiti if available
        self._init_graphiti()

    def _init_patterns_file(self) -> None:
        """Initialize the recovery patterns file."""
        initial_data = {
            "patterns": [],
            "strategy_success_rates": {},
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
            },
        }
        with open(self.patterns_file, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=2)

    def _init_graphiti(self) -> None:
        """Initialize Graphiti memory integration if available."""
        try:
            from integrations.graphiti.memory import (
                get_graphiti_memory,
                is_graphiti_enabled,
            )

            if is_graphiti_enabled():
                self._graphiti_memory = get_graphiti_memory(
                    self.spec_dir,
                    self.project_dir,
                    group_id_mode="project",  # Use project-wide learning
                )
                self._graphiti_available = self._graphiti_memory.is_enabled

                if self._graphiti_available:
                    logger.info("RecoveryLearner: Graphiti integration enabled")
            else:
                logger.debug("RecoveryLearner: Graphiti not enabled")

        except ImportError:
            logger.debug("RecoveryLearner: Graphiti not available (import failed)")
        except Exception as e:
            logger.warning(f"RecoveryLearner: Failed to initialize Graphiti: {e}")

    def _load_patterns(self) -> dict:
        """Load recovery patterns from JSON file."""
        try:
            with open(self.patterns_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            self._init_patterns_file()
            with open(self.patterns_file, encoding="utf-8") as f:
                return json.load(f)

    def _save_patterns(self, data: dict) -> None:
        """Save recovery patterns to JSON file."""
        data["metadata"]["last_updated"] = datetime.now().isoformat()
        with open(self.patterns_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def record_successful_recovery(
        self,
        subtask_id: str,
        subtask_description: str,
        failure_type: str,
        strategy_used: str,
        attempts_before_success: int,
        error_message: str | None = None,
    ) -> None:
        """
        Record a successful recovery for learning.

        Args:
            subtask_id: ID of the subtask
            subtask_description: Description of the subtask
            failure_type: Type of failure that occurred
            strategy_used: Strategy that led to success
            attempts_before_success: Number of attempts before success
            error_message: Optional error message that was resolved
        """
        # Save to local JSON
        patterns = self._load_patterns()

        # Add pattern entry
        pattern_entry = {
            "subtask_id": subtask_id,
            "subtask_description": subtask_description,
            "failure_type": failure_type,
            "strategy_used": strategy_used,
            "attempts_before_success": attempts_before_success,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat(),
        }
        patterns["patterns"].append(pattern_entry)

        # Update strategy success rates
        if strategy_used not in patterns["strategy_success_rates"]:
            patterns["strategy_success_rates"][strategy_used] = {
                "success_count": 0,
                "total_attempts": 0,
                "failure_types": {},
            }

        strategy_stats = patterns["strategy_success_rates"][strategy_used]
        strategy_stats["success_count"] += 1
        strategy_stats["total_attempts"] += attempts_before_success

        # Track which failure types this strategy works for
        if failure_type not in strategy_stats["failure_types"]:
            strategy_stats["failure_types"][failure_type] = 0
        strategy_stats["failure_types"][failure_type] += 1

        self._save_patterns(patterns)

        logger.info(
            f"RecoveryLearner: Recorded successful recovery - "
            f"subtask={subtask_id}, strategy={strategy_used}, "
            f"attempts={attempts_before_success}"
        )

        # Save to Graphiti asynchronously if available
        if self._graphiti_available and self._graphiti_memory:
            asyncio.create_task(
                self._save_to_graphiti(
                    subtask_id,
                    subtask_description,
                    failure_type,
                    strategy_used,
                    attempts_before_success,
                    error_message,
                )
            )

    async def _save_to_graphiti(
        self,
        subtask_id: str,
        subtask_description: str,
        failure_type: str,
        strategy_used: str,
        attempts_before_success: int,
        error_message: str | None = None,
    ) -> None:
        """
        Save successful recovery to Graphiti memory.

        Args:
            subtask_id: ID of the subtask
            subtask_description: Description of the subtask
            failure_type: Type of failure that occurred
            strategy_used: Strategy that led to success
            attempts_before_success: Number of attempts before success
            error_message: Optional error message that was resolved
        """
        try:
            if not self._graphiti_memory:
                return

            # Save as task outcome
            outcome_text = (
                f"Successfully recovered from {failure_type} using {strategy_used} "
                f"strategy after {attempts_before_success} attempts. "
                f"Subtask: {subtask_description}"
            )

            metadata = {
                "failure_type": failure_type,
                "strategy_used": strategy_used,
                "attempts_before_success": attempts_before_success,
                "error_message": error_message,
            }

            await self._graphiti_memory.save_task_outcome(
                task_id=f"recovery_{subtask_id}",
                success=True,
                outcome=outcome_text,
                metadata=metadata,
            )

            logger.info(f"RecoveryLearner: Saved to Graphiti - {subtask_id}")

        except Exception as e:
            logger.warning(f"RecoveryLearner: Failed to save to Graphiti: {e}")

    def get_learned_insights(
        self,
        failure_type: str,
        subtask_description: str | None = None,
        limit: int = 5,
    ) -> list[str]:
        """
        Get learned insights based on failure type and context.

        Args:
            failure_type: Type of failure
            subtask_description: Optional description for similarity matching
            limit: Maximum number of insights to return

        Returns:
            List of insight strings
        """
        insights = []

        # Load local patterns
        patterns = self._load_patterns()

        # Filter patterns by failure type
        matching_patterns = [
            p for p in patterns["patterns"] if p["failure_type"] == failure_type
        ]

        if not matching_patterns:
            insights.append(f"No learned patterns yet for failure type: {failure_type}")
            return insights

        # Add strategy recommendations based on success rates
        strategy_stats = patterns["strategy_success_rates"]
        relevant_strategies = [
            (strategy, stats)
            for strategy, stats in strategy_stats.items()
            if failure_type in stats.get("failure_types", {})
        ]

        # Sort by success count for this failure type
        relevant_strategies.sort(
            key=lambda x: x[1]["failure_types"].get(failure_type, 0), reverse=True
        )

        if relevant_strategies:
            insights.append("\n📚 Learned Strategies (most successful first):")
            for strategy, stats in relevant_strategies[:limit]:
                success_count = stats["failure_types"].get(failure_type, 0)
                total_attempts = stats["total_attempts"]
                success_rate = (
                    stats["success_count"] / total_attempts * 100
                    if total_attempts > 0
                    else 0
                )
                insights.append(
                    f"  • {strategy}: {success_count} successful recoveries "
                    f"({success_rate:.0f}% success rate overall)"
                )

        # Add specific examples from recent patterns
        recent_patterns = sorted(
            matching_patterns, key=lambda x: x.get("timestamp", ""), reverse=True
        )[:3]

        if recent_patterns:
            insights.append("\n💡 Recent Successful Recoveries:")
            for pattern in recent_patterns:
                insights.append(
                    f"  • {pattern['strategy_used']} worked after "
                    f"{pattern['attempts_before_success']} attempts"
                )
                if pattern.get("subtask_description"):
                    insights.append(
                        f"    Context: {pattern['subtask_description'][:80]}..."
                    )

        # Try to get insights from Graphiti if available
        if self._graphiti_available and self._graphiti_memory and subtask_description:
            try:
                graphiti_insights = asyncio.run(
                    self._get_graphiti_insights(subtask_description, limit)
                )
                if graphiti_insights:
                    insights.append("\n🧠 Similar Past Recoveries (Graphiti):")
                    insights.extend(graphiti_insights)
            except Exception as e:
                logger.debug(f"RecoveryLearner: Graphiti insights failed: {e}")

        return insights

    async def _get_graphiti_insights(
        self,
        subtask_description: str,
        limit: int = 5,
    ) -> list[str]:
        """
        Get insights from Graphiti memory.

        Args:
            subtask_description: Description for similarity search
            limit: Maximum number of insights

        Returns:
            List of insight strings
        """
        if not self._graphiti_memory:
            return []

        try:
            # Search for similar task outcomes
            similar_outcomes = await self._graphiti_memory.get_similar_task_outcomes(
                subtask_description, limit=limit
            )

            insights = []
            for outcome in similar_outcomes:
                content = outcome.get("content", "")
                metadata = outcome.get("metadata", {})

                strategy = metadata.get("strategy_used", "unknown")
                attempts = metadata.get("attempts_before_success", "?")

                insights.append(
                    f"  • {strategy} (after {attempts} attempts) - {content[:100]}..."
                )

            return insights

        except Exception as e:
            logger.debug(f"RecoveryLearner: Graphiti search failed: {e}")
            return []

    def get_best_strategy(
        self,
        failure_type: str,
    ) -> str | None:
        """
        Get the best strategy based on past success for a failure type.

        Args:
            failure_type: Type of failure

        Returns:
            Strategy name or None if no data available
        """
        patterns = self._load_patterns()
        strategy_stats = patterns["strategy_success_rates"]

        # Find strategies that have worked for this failure type
        relevant_strategies = [
            (strategy, stats["failure_types"].get(failure_type, 0))
            for strategy, stats in strategy_stats.items()
            if failure_type in stats.get("failure_types", {})
        ]

        if not relevant_strategies:
            return None

        # Return strategy with most successes for this failure type
        best_strategy = max(relevant_strategies, key=lambda x: x[1])
        return best_strategy[0]

    def get_statistics(self) -> dict:
        """
        Get learning statistics.

        Returns:
            Dictionary with statistics
        """
        patterns = self._load_patterns()

        total_patterns = len(patterns["patterns"])
        total_strategies = len(patterns["strategy_success_rates"])

        # Calculate average attempts before success
        attempts = [
            p["attempts_before_success"]
            for p in patterns["patterns"]
            if p.get("attempts_before_success")
        ]
        avg_attempts = sum(attempts) / len(attempts) if attempts else 0

        # Count patterns by failure type
        failure_type_counts = {}
        for pattern in patterns["patterns"]:
            ft = pattern.get("failure_type", "unknown")
            failure_type_counts[ft] = failure_type_counts.get(ft, 0) + 1

        return {
            "total_learned_patterns": total_patterns,
            "total_strategies_tracked": total_strategies,
            "average_attempts_before_success": round(avg_attempts, 2),
            "patterns_by_failure_type": failure_type_counts,
            "graphiti_enabled": self._graphiti_available,
        }
