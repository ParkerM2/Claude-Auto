"""
Pattern aggregation operations for Graphiti memory.

Aggregates and ranks patterns, gotchas, and improvement suggestions
from historical session data.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .schema import (
    EPISODE_TYPE_GOTCHA,
    EPISODE_TYPE_PATTERN,
    EPISODE_TYPE_TASK_OUTCOME,
)

logger = logging.getLogger(__name__)


class PatternAggregator:
    """
    Aggregates and ranks patterns, gotchas, and improvement suggestions.

    Analyzes historical episodes to identify recurring patterns and insights.
    """

    def __init__(self, client, group_id: str, spec_context_id: str):
        """
        Initialize pattern aggregator.

        Args:
            client: GraphitiClient instance
            group_id: Group ID for memory namespace
            spec_context_id: Spec-specific context ID
        """
        self.client = client
        self.group_id = group_id
        self.spec_context_id = spec_context_id

    async def get_top_patterns(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Get top recurring patterns with frequency and recency.

        Args:
            limit: Maximum number of patterns to return

        Returns:
            List of pattern dicts with keys: content, frequency, last_seen
        """
        try:
            # Search for pattern episodes
            results = await self.client.graphiti.search(
                query="code pattern implementation approach",
                group_ids=[self.group_id],
                num_results=limit * 3,  # Get more to aggregate
            )

            patterns = []
            for result in results:
                content = getattr(result, "content", None) or getattr(
                    result, "fact", None
                )
                if content and EPISODE_TYPE_PATTERN in str(content):
                    try:
                        data = (
                            json.loads(content) if isinstance(content, str) else content
                        )
                        if not isinstance(data, dict):
                            continue
                        if data.get("type") == EPISODE_TYPE_PATTERN:
                            patterns.append(data)
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        continue

            # Aggregate by pattern similarity (simple content matching for now)
            aggregated = self._aggregate_by_content(patterns, "pattern")

            # Sort by frequency (descending) and recency (most recent first)
            sorted_patterns = sorted(
                aggregated,
                key=lambda x: (x["frequency"], x["last_seen"]),
                reverse=True,
            )

            logger.info(
                f"Aggregated {len(sorted_patterns)} patterns from {len(patterns)} raw entries"
            )
            return sorted_patterns[:limit]

        except Exception as e:
            logger.warning(f"Failed to get top patterns: {e}")
            return []

    async def get_common_gotchas(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Get common gotchas/pitfalls with frequency and recency.

        Args:
            limit: Maximum number of gotchas to return

        Returns:
            List of gotcha dicts with keys: content, frequency, last_seen
        """
        try:
            # Search for gotcha episodes
            results = await self.client.graphiti.search(
                query="gotcha pitfall avoid mistake error",
                group_ids=[self.group_id],
                num_results=limit * 3,
            )

            gotchas = []
            for result in results:
                content = getattr(result, "content", None) or getattr(
                    result, "fact", None
                )
                if content and EPISODE_TYPE_GOTCHA in str(content):
                    try:
                        data = (
                            json.loads(content) if isinstance(content, str) else content
                        )
                        if not isinstance(data, dict):
                            continue
                        if data.get("type") == EPISODE_TYPE_GOTCHA:
                            gotchas.append(data)
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        continue

            # Aggregate by gotcha similarity
            aggregated = self._aggregate_by_content(gotchas, "gotcha")

            # Sort by frequency and recency
            sorted_gotchas = sorted(
                aggregated,
                key=lambda x: (x["frequency"], x["last_seen"]),
                reverse=True,
            )

            logger.info(
                f"Aggregated {len(sorted_gotchas)} gotchas from {len(gotchas)} raw entries"
            )
            return sorted_gotchas[:limit]

        except Exception as e:
            logger.warning(f"Failed to get common gotchas: {e}")
            return []

    async def get_improvement_suggestions(
        self, limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Get improvement suggestions based on past task outcomes.

        Analyzes failed or problematic task outcomes to suggest improvements.

        Args:
            limit: Maximum number of suggestions to return

        Returns:
            List of suggestion dicts with keys: content, frequency, last_seen
        """
        try:
            # Search for task outcome episodes, especially failures
            results = await self.client.graphiti.search(
                query="task outcome failure issue problem improvement suggestion",
                group_ids=[self.group_id],
                num_results=limit * 3,
            )

            suggestions = []
            for result in results:
                content = getattr(result, "content", None) or getattr(
                    result, "fact", None
                )
                if content and EPISODE_TYPE_TASK_OUTCOME in str(content):
                    try:
                        data = (
                            json.loads(content) if isinstance(content, str) else content
                        )
                        if not isinstance(data, dict):
                            continue
                        if data.get("type") == EPISODE_TYPE_TASK_OUTCOME:
                            # Extract improvement suggestions from failed outcomes
                            if data.get("success") is False or data.get("issues"):
                                suggestion_text = self._extract_improvement_from_outcome(
                                    data
                                )
                                if suggestion_text:
                                    suggestions.append(
                                        {
                                            **data,
                                            "suggestion": suggestion_text,
                                        }
                                    )
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        continue

            # Aggregate suggestions
            aggregated = self._aggregate_by_content(suggestions, "suggestion")

            # Sort by frequency and recency
            sorted_suggestions = sorted(
                aggregated,
                key=lambda x: (x["frequency"], x["last_seen"]),
                reverse=True,
            )

            logger.info(
                f"Aggregated {len(sorted_suggestions)} suggestions from {len(suggestions)} outcomes"
            )
            return sorted_suggestions[:limit]

        except Exception as e:
            logger.warning(f"Failed to get improvement suggestions: {e}")
            return []

    def _aggregate_by_content(
        self, episodes: list[dict], content_key: str
    ) -> list[dict[str, Any]]:
        """
        Aggregate episodes by content similarity.

        Groups similar content together and counts frequency.

        Args:
            episodes: List of episode dicts
            content_key: Key name containing the content to aggregate

        Returns:
            List of aggregated items with frequency and recency
        """
        # Group by exact content match (simplified aggregation)
        content_map = defaultdict(lambda: {"timestamps": [], "data": None})

        for episode in episodes:
            content = episode.get(content_key)
            if not content:
                continue

            # Normalize content for grouping (lowercase, strip whitespace)
            normalized = content.strip().lower()

            content_map[normalized]["timestamps"].append(
                episode.get("timestamp", datetime.now(timezone.utc).isoformat())
            )
            if content_map[normalized]["data"] is None:
                content_map[normalized]["data"] = episode

        # Convert to aggregated list
        aggregated = []
        for normalized_content, info in content_map.items():
            original_data = info["data"]
            timestamps = info["timestamps"]

            aggregated.append(
                {
                    "content": original_data.get(content_key, ""),
                    "frequency": len(timestamps),
                    "last_seen": max(timestamps),
                    "first_seen": min(timestamps),
                }
            )

        return aggregated

    def _extract_improvement_from_outcome(self, outcome: dict) -> str | None:
        """
        Extract improvement suggestion from a task outcome.

        Args:
            outcome: Task outcome dict

        Returns:
            Improvement suggestion text or None
        """
        # Look for explicit suggestions in outcome data
        if "suggestion" in outcome:
            return outcome["suggestion"]

        # Generate suggestion from issues
        issues = outcome.get("issues", [])
        if issues:
            if isinstance(issues, list) and issues:
                return f"Consider addressing: {issues[0]}"
            elif isinstance(issues, str):
                return f"Consider addressing: {issues}"

        # Generate from failure reason
        if "reason" in outcome:
            return f"Avoid: {outcome['reason']}"

        return None
