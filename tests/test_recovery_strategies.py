#!/usr/bin/env python3
"""
Tests for Recovery Strategy System
====================================

Tests the recovery_strategies.py module functionality including:
- Individual strategy classes (SimplifyStrategy, AlternativeLibraryStrategy, etc.)
- Strategy applicability for different failure types
- Strategy guidance generation with context
- StrategyRegistry initialization and management
- Strategy selection and prioritization
- Utility functions for getting strategies
"""

import pytest
from apps.backend.services.recovery_strategies import (
    AlternativeLibraryStrategy,
    DifferentPatternStrategy,
    EscalateStrategy,
    IncrementalStrategy,
    RecoveryStrategy,
    RollbackRetryStrategy,
    SimplifyStrategy,
    SkipSubtaskStrategy,
    Strategy,
    StrategyRegistry,
    StrategyType,
    get_default_registry,
    suggest_strategies,
)


class TestStrategyType:
    """Tests for StrategyType enum."""

    def test_strategy_type_values(self):
        """Verifies all strategy types exist."""
        assert StrategyType.SIMPLIFY.value == "simplify"
        assert StrategyType.ALTERNATIVE_LIBRARY.value == "alternative_library"
        assert StrategyType.DIFFERENT_PATTERN.value == "different_pattern"
        assert StrategyType.INCREMENTAL.value == "incremental"
        assert StrategyType.ROLLBACK_RETRY.value == "rollback_retry"
        assert StrategyType.SKIP_SUBTASK.value == "skip_subtask"
        assert StrategyType.ESCALATE.value == "escalate"


class TestStrategyDataclass:
    """Tests for Strategy dataclass."""

    def test_strategy_creation(self):
        """Creates Strategy with all fields."""
        strategy = Strategy(
            strategy_type=StrategyType.SIMPLIFY,
            name="Test Strategy",
            description="A test strategy",
            guidance="Do this and that",
            priority=8,
            applicable_failures=["broken_build", "verification_failed"],
        )

        assert strategy.strategy_type == StrategyType.SIMPLIFY
        assert strategy.name == "Test Strategy"
        assert strategy.description == "A test strategy"
        assert strategy.guidance == "Do this and that"
        assert strategy.priority == 8
        assert strategy.applicable_failures == ["broken_build", "verification_failed"]

    def test_is_applicable_matching_failure_type(self):
        """Returns True for matching failure type."""
        strategy = Strategy(
            strategy_type=StrategyType.SIMPLIFY,
            name="Test",
            description="Test",
            guidance="Test",
            priority=5,
            applicable_failures=["broken_build", "verification_failed"],
        )

        assert strategy.is_applicable("broken_build") is True
        assert strategy.is_applicable("verification_failed") is True

    def test_is_applicable_non_matching_failure_type(self):
        """Returns False for non-matching failure type."""
        strategy = Strategy(
            strategy_type=StrategyType.SIMPLIFY,
            name="Test",
            description="Test",
            guidance="Test",
            priority=5,
            applicable_failures=["broken_build"],
        )

        assert strategy.is_applicable("circular_fix") is False
        assert strategy.is_applicable("unknown") is False

    def test_is_applicable_with_all_keyword(self):
        """Returns True for any failure type when 'all' is in applicable_failures."""
        strategy = Strategy(
            strategy_type=StrategyType.ESCALATE,
            name="Test",
            description="Test",
            guidance="Test",
            priority=1,
            applicable_failures=["all"],
        )

        assert strategy.is_applicable("broken_build") is True
        assert strategy.is_applicable("verification_failed") is True
        assert strategy.is_applicable("circular_fix") is True
        assert strategy.is_applicable("unknown") is True


class TestSimplifyStrategy:
    """Tests for SimplifyStrategy class."""

    def test_initialization(self):
        """Initializes with correct name, description, and priority."""
        strategy = SimplifyStrategy()
        assert strategy.name == "Simplify Approach"
        assert "smaller" in strategy.description.lower() or "simpler" in strategy.description.lower()
        assert strategy.priority == 8

    def test_get_guidance(self):
        """Returns guidance with breakdown steps."""
        strategy = SimplifyStrategy()
        context = {"error": "SomeError", "subtask_id": "task-1"}
        guidance = strategy.get_guidance(context)

        assert isinstance(guidance, str)
        assert len(guidance) > 0
        assert "step" in guidance.lower() or "mvp" in guidance.lower() or "simpler" in guidance.lower()

    def test_is_applicable_verification_failed(self):
        """Applicable to verification_failed."""
        strategy = SimplifyStrategy()
        assert strategy.is_applicable("verification_failed", {}) is True

    def test_is_applicable_circular_fix(self):
        """Applicable to circular_fix."""
        strategy = SimplifyStrategy()
        assert strategy.is_applicable("circular_fix", {}) is True

    def test_is_applicable_unknown(self):
        """Applicable to unknown failures."""
        strategy = SimplifyStrategy()
        assert strategy.is_applicable("unknown", {}) is True

    def test_not_applicable_broken_build(self):
        """Not applicable to broken_build."""
        strategy = SimplifyStrategy()
        assert strategy.is_applicable("broken_build", {}) is False


class TestAlternativeLibraryStrategy:
    """Tests for AlternativeLibraryStrategy class."""

    def test_initialization(self):
        """Initializes with correct name, description, and priority."""
        strategy = AlternativeLibraryStrategy()
        assert strategy.name == "Alternative Library/Tool"
        assert "library" in strategy.description.lower() or "tool" in strategy.description.lower()
        assert strategy.priority == 7

    def test_get_guidance_with_error(self):
        """Returns guidance including previous error context."""
        strategy = AlternativeLibraryStrategy()
        context = {"error": "ImportError: No module named 'requests'", "subtask_id": "task-1"}
        guidance = strategy.get_guidance(context)

        assert isinstance(guidance, str)
        assert "library" in guidance.lower() or "alternative" in guidance.lower()
        # Should include error context
        assert "previous error" in guidance.lower() or "importerror" in guidance.lower()

    def test_get_guidance_without_error(self):
        """Returns guidance even without error context."""
        strategy = AlternativeLibraryStrategy()
        context = {"subtask_id": "task-1"}
        guidance = strategy.get_guidance(context)

        assert isinstance(guidance, str)
        assert "library" in guidance.lower() or "alternative" in guidance.lower()

    def test_is_applicable_circular_fix(self):
        """Applicable to circular_fix."""
        strategy = AlternativeLibraryStrategy()
        assert strategy.is_applicable("circular_fix", {}) is True

    def test_is_applicable_verification_failed(self):
        """Applicable to verification_failed."""
        strategy = AlternativeLibraryStrategy()
        assert strategy.is_applicable("verification_failed", {}) is True

    def test_not_applicable_broken_build(self):
        """Not applicable to broken_build."""
        strategy = AlternativeLibraryStrategy()
        assert strategy.is_applicable("broken_build", {}) is False


class TestDifferentPatternStrategy:
    """Tests for DifferentPatternStrategy class."""

    def test_initialization(self):
        """Initializes with correct name, description, and priority."""
        strategy = DifferentPatternStrategy()
        assert strategy.name == "Different Implementation Pattern"
        assert "pattern" in strategy.description.lower() or "approach" in strategy.description.lower()
        assert strategy.priority == 8

    def test_get_guidance(self):
        """Returns guidance with pattern alternatives."""
        strategy = DifferentPatternStrategy()
        context = {"error": "Error", "subtask_id": "task-1"}
        guidance = strategy.get_guidance(context)

        assert isinstance(guidance, str)
        assert "pattern" in guidance.lower() or "approach" in guidance.lower()

    def test_is_applicable_circular_fix(self):
        """Applicable to circular_fix."""
        strategy = DifferentPatternStrategy()
        assert strategy.is_applicable("circular_fix", {}) is True

    def test_is_applicable_verification_failed(self):
        """Applicable to verification_failed."""
        strategy = DifferentPatternStrategy()
        assert strategy.is_applicable("verification_failed", {}) is True

    def test_not_applicable_unknown(self):
        """Not applicable to unknown failures."""
        strategy = DifferentPatternStrategy()
        assert strategy.is_applicable("unknown", {}) is False


class TestIncrementalStrategy:
    """Tests for IncrementalStrategy class."""

    def test_initialization(self):
        """Initializes with correct name, description, and priority."""
        strategy = IncrementalStrategy()
        assert strategy.name == "Incremental Implementation"
        assert "incremental" in strategy.description.lower()
        assert strategy.priority == 9  # Highest priority

    def test_get_guidance(self):
        """Returns guidance with incremental steps."""
        strategy = IncrementalStrategy()
        context = {"error": "Error", "subtask_id": "task-1"}
        guidance = strategy.get_guidance(context)

        assert isinstance(guidance, str)
        assert "incremental" in guidance.lower() or "step" in guidance.lower()

    def test_is_applicable_broken_build(self):
        """Applicable to broken_build."""
        strategy = IncrementalStrategy()
        assert strategy.is_applicable("broken_build", {}) is True

    def test_is_applicable_verification_failed(self):
        """Applicable to verification_failed."""
        strategy = IncrementalStrategy()
        assert strategy.is_applicable("verification_failed", {}) is True

    def test_is_applicable_circular_fix(self):
        """Applicable to circular_fix."""
        strategy = IncrementalStrategy()
        assert strategy.is_applicable("circular_fix", {}) is True


class TestRollbackRetryStrategy:
    """Tests for RollbackRetryStrategy class."""

    def test_initialization(self):
        """Initializes with correct name, description, and priority."""
        strategy = RollbackRetryStrategy()
        assert strategy.name == "Rollback and Fresh Approach"
        assert "rollback" in strategy.description.lower()
        assert strategy.priority == 6

    def test_get_guidance_with_commit(self):
        """Returns guidance including last good commit."""
        strategy = RollbackRetryStrategy()
        context = {"last_good_commit": "abc123", "subtask_id": "task-1"}
        guidance = strategy.get_guidance(context)

        assert isinstance(guidance, str)
        assert "rollback" in guidance.lower()
        assert "abc123" in guidance

    def test_get_guidance_without_commit(self):
        """Returns guidance even without last good commit."""
        strategy = RollbackRetryStrategy()
        context = {"subtask_id": "task-1"}
        guidance = strategy.get_guidance(context)

        assert isinstance(guidance, str)
        assert "rollback" in guidance.lower()
        assert "unknown" in guidance.lower()

    def test_is_applicable_with_commit(self):
        """Applicable to broken_build when last_good_commit exists."""
        strategy = RollbackRetryStrategy()
        context = {"last_good_commit": "abc123"}
        assert strategy.is_applicable("broken_build", context) is True

    def test_not_applicable_without_commit(self):
        """Not applicable when last_good_commit is missing."""
        strategy = RollbackRetryStrategy()
        context = {}
        assert strategy.is_applicable("broken_build", context) is False

    def test_not_applicable_other_failure_types(self):
        """Not applicable to non-broken_build failures."""
        strategy = RollbackRetryStrategy()
        context = {"last_good_commit": "abc123"}
        assert strategy.is_applicable("verification_failed", context) is False
        assert strategy.is_applicable("circular_fix", context) is False


class TestSkipSubtaskStrategy:
    """Tests for SkipSubtaskStrategy class."""

    def test_initialization(self):
        """Initializes with correct name, description, and priority."""
        strategy = SkipSubtaskStrategy()
        assert strategy.name == "Skip Subtask"
        assert "skip" in strategy.description.lower()
        assert strategy.priority == 3

    def test_get_guidance_with_context(self):
        """Returns guidance including subtask_id and attempt_count."""
        strategy = SkipSubtaskStrategy()
        context = {"subtask_id": "task-123", "attempt_count": 5}
        guidance = strategy.get_guidance(context)

        assert isinstance(guidance, str)
        assert "task-123" in guidance
        assert "5" in guidance
        assert "skip" in guidance.lower()

    def test_get_guidance_without_context(self):
        """Returns guidance with defaults when context is missing."""
        strategy = SkipSubtaskStrategy()
        context = {}
        guidance = strategy.get_guidance(context)

        assert isinstance(guidance, str)
        assert "unknown" in guidance.lower()
        assert "0" in guidance

    def test_is_applicable_high_attempt_count(self):
        """Applicable when attempt_count >= 3."""
        strategy = SkipSubtaskStrategy()
        assert strategy.is_applicable("any_failure", {"attempt_count": 3}) is True
        assert strategy.is_applicable("any_failure", {"attempt_count": 5}) is True

    def test_not_applicable_low_attempt_count(self):
        """Not applicable when attempt_count < 3."""
        strategy = SkipSubtaskStrategy()
        assert strategy.is_applicable("any_failure", {"attempt_count": 0}) is False
        assert strategy.is_applicable("any_failure", {"attempt_count": 2}) is False

    def test_not_applicable_missing_attempt_count(self):
        """Not applicable when attempt_count is missing."""
        strategy = SkipSubtaskStrategy()
        assert strategy.is_applicable("any_failure", {}) is False


class TestEscalateStrategy:
    """Tests for EscalateStrategy class."""

    def test_initialization(self):
        """Initializes with correct name, description, and priority."""
        strategy = EscalateStrategy()
        assert strategy.name == "Escalate to Human"
        assert "human" in strategy.description.lower() or "escalate" in strategy.description.lower()
        assert strategy.priority == 1  # Lowest priority

    def test_get_guidance_with_full_context(self):
        """Returns guidance with all context information."""
        strategy = EscalateStrategy()
        context = {
            "subtask_id": "task-456",
            "error": "Critical error occurred during execution",
            "attempt_count": 3,
        }
        guidance = strategy.get_guidance(context)

        assert isinstance(guidance, str)
        assert "task-456" in guidance
        assert "3" in guidance
        assert "escalat" in guidance.lower()

    def test_get_guidance_minimal_context(self):
        """Returns guidance with minimal context."""
        strategy = EscalateStrategy()
        context = {}
        guidance = strategy.get_guidance(context)

        assert isinstance(guidance, str)
        assert "unknown" in guidance.lower()

    def test_is_applicable_always(self):
        """Always applicable as last resort."""
        strategy = EscalateStrategy()
        assert strategy.is_applicable("broken_build", {}) is True
        assert strategy.is_applicable("verification_failed", {}) is True
        assert strategy.is_applicable("circular_fix", {}) is True
        assert strategy.is_applicable("unknown", {}) is True


class TestStrategyRegistryInit:
    """Tests for StrategyRegistry initialization."""

    def test_initialization(self):
        """Initializes with default strategies."""
        registry = StrategyRegistry()
        assert len(registry.strategies) > 0
        assert isinstance(registry.strategies, list)

    def test_default_strategies_registered(self):
        """All default strategies are registered."""
        registry = StrategyRegistry()
        strategy_names = [s.name for s in registry.strategies]

        assert "Simplify Approach" in strategy_names
        assert "Alternative Library/Tool" in strategy_names
        assert "Different Implementation Pattern" in strategy_names
        assert "Incremental Implementation" in strategy_names
        assert "Rollback and Fresh Approach" in strategy_names
        assert "Skip Subtask" in strategy_names
        assert "Escalate to Human" in strategy_names

    def test_strategies_sorted_by_priority(self):
        """Strategies are sorted by priority (highest first)."""
        registry = StrategyRegistry()
        priorities = [s.priority for s in registry.strategies]

        # Verify sorted in descending order
        assert priorities == sorted(priorities, reverse=True)


class TestStrategyRegistryRegister:
    """Tests for StrategyRegistry.register_strategy()."""

    def test_register_new_strategy(self):
        """Registers a new strategy."""
        registry = StrategyRegistry()
        initial_count = len(registry.strategies)

        new_strategy = SimplifyStrategy()
        new_strategy.name = "Custom Strategy"
        new_strategy.priority = 10

        registry.register_strategy(new_strategy)

        assert len(registry.strategies) == initial_count + 1
        assert "Custom Strategy" in [s.name for s in registry.strategies]

    def test_register_replaces_existing_strategy(self):
        """Replaces existing strategy with same name."""
        registry = StrategyRegistry()
        initial_count = len(registry.strategies)

        # Create strategy with same name as existing
        new_strategy = SimplifyStrategy()
        new_strategy.priority = 10

        registry.register_strategy(new_strategy)

        # Count should remain the same (replaced, not added)
        assert len(registry.strategies) == initial_count

    def test_register_maintains_priority_order(self):
        """Maintains priority order after registration."""
        registry = StrategyRegistry()

        new_strategy = SimplifyStrategy()
        new_strategy.name = "High Priority Strategy"
        new_strategy.priority = 15

        registry.register_strategy(new_strategy)

        priorities = [s.priority for s in registry.strategies]
        assert priorities == sorted(priorities, reverse=True)


class TestStrategyRegistryGetStrategies:
    """Tests for StrategyRegistry.get_strategies()."""

    def test_get_strategies_verification_failed(self):
        """Returns applicable strategies for verification_failed."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("verification_failed")

        assert len(strategies) > 0
        assert all(isinstance(s, RecoveryStrategy) for s in strategies)

        # Verify all returned strategies are applicable
        for strategy in strategies:
            assert strategy.is_applicable("verification_failed", {})

    def test_get_strategies_broken_build(self):
        """Returns applicable strategies for broken_build."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("broken_build")

        assert len(strategies) > 0
        for strategy in strategies:
            assert strategy.is_applicable("broken_build", {})

    def test_get_strategies_circular_fix(self):
        """Returns applicable strategies for circular_fix."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("circular_fix")

        assert len(strategies) > 0
        for strategy in strategies:
            assert strategy.is_applicable("circular_fix", {})

    def test_get_strategies_with_context(self):
        """Uses context for strategy filtering."""
        registry = StrategyRegistry()
        context = {"attempt_count": 5}
        strategies = registry.get_strategies("unknown", context, top_n=10)

        # SkipSubtaskStrategy should be included (attempt_count >= 3)
        strategy_names = [s.name for s in strategies]
        assert "Skip Subtask" in strategy_names

    def test_get_strategies_top_n_limit(self):
        """Returns only top N strategies."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("verification_failed", top_n=2)

        assert len(strategies) <= 2

    def test_get_strategies_default_top_n(self):
        """Returns default top 3 strategies."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("verification_failed")

        assert len(strategies) <= 3

    def test_get_strategies_ordered_by_priority(self):
        """Returns strategies ordered by priority."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("verification_failed", top_n=5)

        priorities = [s.priority for s in strategies]
        assert priorities == sorted(priorities, reverse=True)


class TestStrategyRegistryGetStrategy:
    """Tests for StrategyRegistry.get_strategy()."""

    def test_get_strategy_by_name_exists(self):
        """Returns strategy when name exists."""
        registry = StrategyRegistry()
        strategy = registry.get_strategy("Incremental Implementation")

        assert strategy is not None
        assert isinstance(strategy, IncrementalStrategy)
        assert strategy.name == "Incremental Implementation"

    def test_get_strategy_by_name_not_exists(self):
        """Returns None when strategy name doesn't exist."""
        registry = StrategyRegistry()
        strategy = registry.get_strategy("Nonexistent Strategy")

        assert strategy is None

    def test_get_strategy_all_defaults(self):
        """Can retrieve all default strategies by name."""
        registry = StrategyRegistry()

        assert registry.get_strategy("Simplify Approach") is not None
        assert registry.get_strategy("Alternative Library/Tool") is not None
        assert registry.get_strategy("Different Implementation Pattern") is not None
        assert registry.get_strategy("Incremental Implementation") is not None
        assert registry.get_strategy("Rollback and Fresh Approach") is not None
        assert registry.get_strategy("Skip Subtask") is not None
        assert registry.get_strategy("Escalate to Human") is not None


class TestStrategyRegistryListStrategies:
    """Tests for StrategyRegistry.list_strategies()."""

    def test_list_strategies(self):
        """Returns list of all strategy names."""
        registry = StrategyRegistry()
        names = registry.list_strategies()

        assert isinstance(names, list)
        assert len(names) > 0
        assert all(isinstance(name, str) for name in names)

    def test_list_strategies_includes_defaults(self):
        """Includes all default strategy names."""
        registry = StrategyRegistry()
        names = registry.list_strategies()

        assert "Simplify Approach" in names
        assert "Alternative Library/Tool" in names
        assert "Incremental Implementation" in names
        assert "Escalate to Human" in names


class TestGetDefaultRegistry:
    """Tests for get_default_registry() utility function."""

    def test_get_default_registry(self):
        """Returns a StrategyRegistry instance."""
        registry = get_default_registry()

        assert isinstance(registry, StrategyRegistry)
        assert len(registry.strategies) > 0

    def test_get_default_registry_has_all_strategies(self):
        """Returns registry with all default strategies."""
        registry = get_default_registry()
        names = registry.list_strategies()

        assert "Simplify Approach" in names
        assert "Alternative Library/Tool" in names
        assert "Different Implementation Pattern" in names
        assert "Incremental Implementation" in names
        assert "Rollback and Fresh Approach" in names
        assert "Skip Subtask" in names
        assert "Escalate to Human" in names


class TestSuggestStrategies:
    """Tests for suggest_strategies() utility function."""

    def test_suggest_strategies_basic(self):
        """Returns list of strategy suggestions."""
        suggestions = suggest_strategies(
            failure_type="verification_failed",
            error="Test failed",
            subtask_id="task-1",
            attempt_count=1,
        )

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert all(isinstance(s, str) for s in suggestions)

    def test_suggest_strategies_includes_strategy_names(self):
        """Suggestions include strategy names."""
        suggestions = suggest_strategies(
            failure_type="verification_failed",
            error="Test failed",
            subtask_id="task-1",
            attempt_count=1,
        )

        combined = " ".join(suggestions)
        # Should include at least some strategy names
        assert any(
            name in combined
            for name in [
                "Simplify",
                "Incremental",
                "Different Pattern",
                "Alternative",
            ]
        )

    def test_suggest_strategies_includes_guidance(self):
        """Suggestions include strategy guidance."""
        suggestions = suggest_strategies(
            failure_type="verification_failed",
            error="ImportError",
            subtask_id="task-1",
            attempt_count=1,
        )

        combined = " ".join(suggestions).lower()
        # Should include guidance keywords
        assert any(
            keyword in combined
            for keyword in [
                "step",
                "approach",
                "pattern",
                "incremental",
                "simpler",
            ]
        )

    def test_suggest_strategies_with_commit(self):
        """Includes rollback strategy when last_good_commit provided."""
        suggestions = suggest_strategies(
            failure_type="broken_build",
            error="Build failed",
            subtask_id="task-1",
            attempt_count=1,
            last_good_commit="abc123",
        )

        combined = " ".join(suggestions)
        # Should include rollback guidance with commit hash
        assert "abc123" in combined

    def test_suggest_strategies_respects_top_n(self):
        """Returns top N strategies (default 3)."""
        suggestions = suggest_strategies(
            failure_type="verification_failed",
            error="Test failed",
            subtask_id="task-1",
            attempt_count=1,
        )

        # Default top_n is 3
        assert len(suggestions) <= 3

    def test_suggest_strategies_high_attempt_count(self):
        """Includes skip/escalate strategies for high attempt count."""
        suggestions = suggest_strategies(
            failure_type="unknown",
            error="Unknown error",
            subtask_id="task-1",
            attempt_count=5,
        )

        combined = " ".join(suggestions).lower()
        # Should include skip or escalate suggestions
        assert "skip" in combined or "escalate" in combined


class TestStrategyApplicability:
    """Tests for strategy applicability across different failure types."""

    def test_verification_failed_strategies(self):
        """Correct strategies are applicable to verification_failed."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("verification_failed", top_n=10)
        strategy_names = [s.name for s in strategies]

        # These should be applicable
        assert "Simplify Approach" in strategy_names
        assert "Incremental Implementation" in strategy_names

    def test_broken_build_strategies(self):
        """Correct strategies are applicable to broken_build."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("broken_build", top_n=10)
        strategy_names = [s.name for s in strategies]

        # Incremental should be applicable
        assert "Incremental Implementation" in strategy_names

    def test_circular_fix_strategies(self):
        """Correct strategies are applicable to circular_fix."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("circular_fix", top_n=10)
        strategy_names = [s.name for s in strategies]

        # These should be applicable
        assert "Simplify Approach" in strategy_names
        assert "Different Implementation Pattern" in strategy_names
        assert "Alternative Library/Tool" in strategy_names

    def test_unknown_failure_strategies(self):
        """Correct strategies are applicable to unknown failures."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("unknown", top_n=10)
        strategy_names = [s.name for s in strategies]

        # Simplify should be applicable to unknown
        assert "Simplify Approach" in strategy_names


class TestStrategyPriority:
    """Tests for strategy priority ordering."""

    def test_incremental_highest_priority(self):
        """IncrementalStrategy has highest priority among defaults."""
        registry = StrategyRegistry()
        incremental = registry.get_strategy("Incremental Implementation")

        # Should be priority 9
        assert incremental.priority == 9

        # Should be highest among applicable strategies
        strategies = registry.get_strategies("verification_failed", top_n=10)
        if incremental in strategies:
            assert incremental.priority >= max(s.priority for s in strategies)

    def test_escalate_lowest_priority(self):
        """EscalateStrategy has lowest priority."""
        registry = StrategyRegistry()
        escalate = registry.get_strategy("Escalate to Human")

        # Should be priority 1
        assert escalate.priority == 1

    def test_priority_affects_order(self):
        """Higher priority strategies appear first."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("verification_failed", top_n=10)

        # Verify descending priority order
        for i in range(len(strategies) - 1):
            assert strategies[i].priority >= strategies[i + 1].priority


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_context(self):
        """Handles empty context dictionary."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("verification_failed", context={})

        assert len(strategies) > 0

    def test_none_context(self):
        """Handles None context."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("verification_failed", context=None)

        assert len(strategies) > 0

    def test_unknown_failure_type(self):
        """Handles unknown failure types gracefully."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("totally_unknown_failure_type")

        # Escalate should always be applicable
        strategy_names = [s.name for s in strategies]
        assert "Escalate to Human" in strategy_names

    def test_top_n_zero(self):
        """Returns empty list when top_n is 0."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("verification_failed", top_n=0)

        assert strategies == []

    def test_top_n_larger_than_available(self):
        """Returns all available strategies when top_n exceeds count."""
        registry = StrategyRegistry()
        strategies = registry.get_strategies("verification_failed", top_n=100)

        # Should return all applicable strategies, not error
        assert len(strategies) > 0

    def test_guidance_with_very_long_error(self):
        """Handles very long error messages."""
        strategy = AlternativeLibraryStrategy()
        long_error = "Error: " + "x" * 10000
        context = {"error": long_error, "subtask_id": "task-1"}
        guidance = strategy.get_guidance(context)

        # Should truncate error in guidance
        assert isinstance(guidance, str)
        assert len(guidance) < len(long_error)

    def test_guidance_with_unicode_error(self):
        """Handles Unicode characters in error messages."""
        strategy = SimplifyStrategy()
        context = {"error": "错误: 导入失败", "subtask_id": "task-1"}
        guidance = strategy.get_guidance(context)

        assert isinstance(guidance, str)
        assert len(guidance) > 0

    def test_suggest_strategies_with_none_commit(self):
        """Handles None last_good_commit gracefully."""
        suggestions = suggest_strategies(
            failure_type="broken_build",
            error="Build failed",
            subtask_id="task-1",
            attempt_count=1,
            last_good_commit=None,
        )

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
