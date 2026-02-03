"""
Recovery Strategy System
========================

Provides alternative recovery strategies for different failure types.
Enables automatic retry with different approaches based on failure patterns.

Key Features:
- Strategy registry for different failure types
- Context-aware strategy selection
- Strategy prioritization based on success rates
- Customizable recovery approaches
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class StrategyType(Enum):
    """Types of recovery strategies."""

    SIMPLIFY = "simplify"  # Break down into simpler steps
    ALTERNATIVE_LIBRARY = "alternative_library"  # Try different library/tool
    DIFFERENT_PATTERN = "different_pattern"  # Use different implementation pattern
    INCREMENTAL = "incremental"  # Implement incrementally with tests
    ROLLBACK_RETRY = "rollback_retry"  # Rollback and try fresh approach
    SKIP_SUBTASK = "skip_subtask"  # Skip and move to next
    ESCALATE = "escalate"  # Escalate to human


@dataclass
class Strategy:
    """
    Represents a recovery strategy.

    Attributes:
        strategy_type: Type of strategy
        name: Human-readable strategy name
        description: What the strategy does
        guidance: Detailed guidance for implementing the strategy
        priority: Priority level (1-10, higher = more preferred)
        applicable_failures: List of failure types this strategy works for
    """

    strategy_type: StrategyType
    name: str
    description: str
    guidance: str
    priority: int
    applicable_failures: List[str]

    def is_applicable(self, failure_type: str) -> bool:
        """
        Check if this strategy is applicable to a failure type.

        Args:
            failure_type: Type of failure (e.g., "broken_build", "verification_failed")

        Returns:
            True if strategy is applicable, False otherwise
        """
        return failure_type in self.applicable_failures or "all" in self.applicable_failures


class RecoveryStrategy(ABC):
    """
    Abstract base class for recovery strategies.

    Subclasses implement specific recovery approaches for different failure types.
    """

    def __init__(self, name: str, description: str, priority: int = 5):
        """
        Initialize recovery strategy.

        Args:
            name: Strategy name
            description: What the strategy does
            priority: Priority level (1-10, higher = more preferred)
        """
        self.name = name
        self.description = description
        self.priority = priority

    @abstractmethod
    def get_guidance(self, context: Dict) -> str:
        """
        Get strategy-specific guidance based on failure context.

        Args:
            context: Dictionary with failure context (error, subtask_id, history, etc.)

        Returns:
            Detailed guidance string
        """
        pass

    @abstractmethod
    def is_applicable(self, failure_type: str, context: Dict) -> bool:
        """
        Check if strategy is applicable to this failure.

        Args:
            failure_type: Type of failure
            context: Failure context

        Returns:
            True if applicable, False otherwise
        """
        pass


class SimplifyStrategy(RecoveryStrategy):
    """Strategy: Break down into simpler steps."""

    def __init__(self):
        super().__init__(
            name="Simplify Approach",
            description="Break down the task into smaller, simpler steps",
            priority=8,
        )

    def get_guidance(self, context: Dict) -> str:
        return """
Break down the subtask into smaller steps:
1. Identify the minimal working implementation (MVP)
2. Implement the simplest version first
3. Test that minimal version works
4. Add complexity incrementally
5. Test after each addition

Example: If implementing a complex API endpoint, start with:
- Basic route handler that returns static data
- Add parameter parsing
- Add database query
- Add error handling
- Add validation
"""

    def is_applicable(self, failure_type: str, context: Dict) -> bool:
        # Applicable to verification failures and circular fixes
        return failure_type in ["verification_failed", "circular_fix", "unknown"]


class AlternativeLibraryStrategy(RecoveryStrategy):
    """Strategy: Try a different library or tool."""

    def __init__(self):
        super().__init__(
            name="Alternative Library/Tool",
            description="Use a different library or tool to accomplish the task",
            priority=7,
        )

    def get_guidance(self, context: Dict) -> str:
        error = context.get("error", "")
        return f"""
Try a different library or tool approach:
1. Identify what libraries/tools were used in previous attempts
2. Research alternatives that solve the same problem
3. Consider more mature/stable alternatives
4. Look at what the project already uses

Common alternatives:
- HTTP: requests → httpx, urllib3
- Testing: pytest → unittest, nose2
- Async: asyncio → trio, curio
- CLI: argparse → click, typer
- Database: SQLAlchemy → peewee, django ORM

Previous error: {error[:200] if error else 'N/A'}
"""

    def is_applicable(self, failure_type: str, context: Dict) -> bool:
        # Applicable when previous attempts failed, especially circular fixes
        return failure_type in ["circular_fix", "verification_failed", "unknown"]


class DifferentPatternStrategy(RecoveryStrategy):
    """Strategy: Use a different implementation pattern."""

    def __init__(self):
        super().__init__(
            name="Different Implementation Pattern",
            description="Use a fundamentally different approach or design pattern",
            priority=8,
        )

    def get_guidance(self, context: Dict) -> str:
        return """
Try a different implementation pattern:
1. Review previous attempts to identify the pattern used
2. Choose a fundamentally different approach
3. Consider trade-offs (performance vs simplicity, etc.)

Pattern alternatives:
- OOP → Functional approach
- Synchronous → Asynchronous
- Class-based → Function-based
- Imperative → Declarative
- Monolithic → Modular
- Direct implementation → Use existing utility/helper

Example: If class-based state management failed, try:
- Simple function with closure
- Context manager
- Global state with locks
- Database-backed state
"""

    def is_applicable(self, failure_type: str, context: Dict) -> bool:
        # Especially useful for circular fixes and repeated failures
        return failure_type in ["circular_fix", "verification_failed"]


class IncrementalStrategy(RecoveryStrategy):
    """Strategy: Implement incrementally with tests."""

    def __init__(self):
        super().__init__(
            name="Incremental Implementation",
            description="Build incrementally, testing each piece before moving forward",
            priority=9,
        )

    def get_guidance(self, context: Dict) -> str:
        return """
Implement incrementally with validation at each step:
1. Start with the smallest possible change
2. Verify it works (run tests, manual check, etc.)
3. Commit the working change
4. Add the next small piece
5. Verify again
6. Repeat until complete

Benefits:
- Easier to debug (know exactly what broke)
- Can recover to last working state
- Builds confidence incrementally
- Prevents large changes that are hard to fix

Red flags to avoid:
- Making multiple changes at once
- Not testing until "everything is done"
- Skipping intermediate validation steps
"""

    def is_applicable(self, failure_type: str, context: Dict) -> bool:
        # Useful for broken builds and verification failures
        return failure_type in ["broken_build", "verification_failed", "circular_fix"]


class RollbackRetryStrategy(RecoveryStrategy):
    """Strategy: Rollback to last good state and try fresh approach."""

    def __init__(self):
        super().__init__(
            name="Rollback and Fresh Approach",
            description="Rollback to last working state and start over with a new strategy",
            priority=6,
        )

    def get_guidance(self, context: Dict) -> str:
        last_good_commit = context.get("last_good_commit", "unknown")
        return f"""
Rollback to last working state and start fresh:
1. Rollback to last good commit: {last_good_commit}
2. Review what went wrong in previous attempts
3. Choose a COMPLETELY different approach
4. Document why the new approach should work better
5. Implement with incremental testing

Key: Don't just try the same thing again. Think about:
- Why did previous approaches fail?
- What assumption was wrong?
- Is there a simpler path?
- What would an expert do differently?
"""

    def is_applicable(self, failure_type: str, context: Dict) -> bool:
        # Most useful for broken builds
        return failure_type == "broken_build" and context.get("last_good_commit") is not None


class SkipSubtaskStrategy(RecoveryStrategy):
    """Strategy: Skip subtask and move to next."""

    def __init__(self):
        super().__init__(
            name="Skip Subtask",
            description="Skip this subtask and move to the next one",
            priority=3,
        )

    def get_guidance(self, context: Dict) -> str:
        subtask_id = context.get("subtask_id", "unknown")
        attempt_count = context.get("attempt_count", 0)
        return f"""
Skip subtask {subtask_id} and continue with next:
- Attempts made: {attempt_count}
- Subtask will be marked as 'stuck' for human review
- Other subtasks can still be completed
- Return to this later with fresh perspective or more context

Consider: Is this subtask blocking other work?
- If yes: Try once more with minimal implementation
- If no: Safe to skip and continue
"""

    def is_applicable(self, failure_type: str, context: Dict) -> bool:
        # Applicable when we've exhausted other options
        attempt_count = context.get("attempt_count", 0)
        return attempt_count >= 3


class EscalateStrategy(RecoveryStrategy):
    """Strategy: Escalate to human intervention."""

    def __init__(self):
        super().__init__(
            name="Escalate to Human",
            description="Mark for human intervention due to unrecoverable issue",
            priority=1,
        )

    def get_guidance(self, context: Dict) -> str:
        subtask_id = context.get("subtask_id", "unknown")
        error = context.get("error", "")
        return f"""
Escalating subtask {subtask_id} to human intervention:

Issue: {error[:300] if error else 'Multiple recovery attempts failed'}

Next steps:
1. Document all attempted approaches
2. Mark subtask as 'needs_human'
3. Continue with other subtasks if possible
4. Human will review and provide guidance

Information for human:
- Subtask ID: {subtask_id}
- Attempts made: {context.get('attempt_count', 0)}
- Error summary: {error[:200] if error else 'N/A'}
"""

    def is_applicable(self, failure_type: str, context: Dict) -> bool:
        # Always applicable as last resort
        return True


class StrategyRegistry:
    """
    Registry of available recovery strategies.

    Manages strategy selection based on failure type and context.
    Tracks strategy effectiveness for learning.
    """

    def __init__(self):
        """Initialize registry with default strategies."""
        self.strategies: List[RecoveryStrategy] = []
        self._register_default_strategies()

    def _register_default_strategies(self) -> None:
        """Register all default recovery strategies."""
        default_strategies = [
            IncrementalStrategy(),
            SimplifyStrategy(),
            DifferentPatternStrategy(),
            AlternativeLibraryStrategy(),
            RollbackRetryStrategy(),
            SkipSubtaskStrategy(),
            EscalateStrategy(),
        ]

        for strategy in default_strategies:
            self.register_strategy(strategy)

    def register_strategy(self, strategy: RecoveryStrategy) -> None:
        """
        Register a new recovery strategy.

        Args:
            strategy: RecoveryStrategy instance to register
        """
        # Check if strategy with same name already exists
        existing = [s for s in self.strategies if s.name == strategy.name]
        if existing:
            # Replace existing strategy
            self.strategies = [s for s in self.strategies if s.name != strategy.name]

        self.strategies.append(strategy)

        # Sort by priority (highest first)
        self.strategies.sort(key=lambda s: s.priority, reverse=True)

    def get_strategies(
        self, failure_type: str, context: Optional[Dict] = None, top_n: int = 3
    ) -> List[RecoveryStrategy]:
        """
        Get applicable strategies for a failure type.

        Args:
            failure_type: Type of failure (e.g., "broken_build", "verification_failed")
            context: Optional failure context for more specific strategy selection
            top_n: Number of top strategies to return (default: 3)

        Returns:
            List of applicable strategies, ordered by priority
        """
        if context is None:
            context = {}

        # Filter to applicable strategies
        applicable = [s for s in self.strategies if s.is_applicable(failure_type, context)]

        # Return top N strategies
        return applicable[:top_n]

    def get_strategy(self, strategy_name: str) -> Optional[RecoveryStrategy]:
        """
        Get a specific strategy by name.

        Args:
            strategy_name: Name of the strategy

        Returns:
            RecoveryStrategy instance or None if not found
        """
        for strategy in self.strategies:
            if strategy.name == strategy_name:
                return strategy
        return None

    def list_strategies(self) -> List[str]:
        """
        List all registered strategy names.

        Returns:
            List of strategy names
        """
        return [s.name for s in self.strategies]


# Utility functions


def get_default_registry() -> StrategyRegistry:
    """
    Get a registry with default strategies.

    Returns:
        StrategyRegistry instance with all default strategies
    """
    return StrategyRegistry()


def suggest_strategies(
    failure_type: str, error: str, subtask_id: str, attempt_count: int, last_good_commit: Optional[str] = None
) -> List[str]:
    """
    Get strategy suggestions for a failure.

    Args:
        failure_type: Type of failure
        error: Error message
        subtask_id: ID of failed subtask
        attempt_count: Number of attempts so far
        last_good_commit: Last known good commit hash

    Returns:
        List of strategy guidance strings
    """
    registry = get_default_registry()
    context = {
        "error": error,
        "subtask_id": subtask_id,
        "attempt_count": attempt_count,
        "last_good_commit": last_good_commit,
    }

    strategies = registry.get_strategies(failure_type, context, top_n=3)
    suggestions = []

    for strategy in strategies:
        suggestions.append(f"### {strategy.name}\n{strategy.description}\n{strategy.get_guidance(context)}")

    return suggestions
