"""
Conflict Analysis
=================

Core logic for detecting and analyzing conflicts between task changes.

This module contains:
- Conflict detection algorithms
- Severity assessment logic
- Implicit conflict detection
- Range overlap checking
"""

from __future__ import annotations

import logging
from collections import defaultdict

from .compatibility_rules import CompatibilityRule
from .types import (
    ChangeType,
    ConflictRegion,
    ConflictSeverity,
    FileAnalysis,
    MergeStrategy,
    SemanticChange,
)

# Import debug utilities
try:
    from debug import debug, debug_detailed, debug_verbose
except ImportError:

    def debug(*args, **kwargs):
        pass

    def debug_detailed(*args, **kwargs):
        pass

    def debug_verbose(*args, **kwargs):
        pass


logger = logging.getLogger(__name__)
MODULE = "merge.conflict_analysis"


def detect_conflicts(
    task_analyses: dict[str, FileAnalysis],
    rule_index: dict[tuple[ChangeType, ChangeType], CompatibilityRule],
) -> list[ConflictRegion]:
    """
    Detect conflicts between multiple task changes to the same file.

    Args:
        task_analyses: Map of task_id -> FileAnalysis
        rule_index: Indexed compatibility rules for fast lookup

    Returns:
        List of detected conflict regions
    """
    task_ids = list(task_analyses.keys())
    debug(
        MODULE,
        f"Detecting conflicts between {len(task_analyses)} tasks",
        tasks=task_ids,
    )

    if len(task_analyses) <= 1:
        debug(MODULE, "No conflicts possible with 0-1 tasks")
        return []  # No conflicts possible with 0-1 tasks

    conflicts: list[ConflictRegion] = []

    # Group changes by location
    location_changes: dict[str, list[tuple[str, SemanticChange]]] = defaultdict(list)

    for task_id, analysis in task_analyses.items():
        debug_detailed(
            MODULE,
            f"Processing task {task_id}",
            changes_count=len(analysis.changes),
            file=analysis.file_path,
        )
        for change in analysis.changes:
            location_changes[change.location].append((task_id, change))

    debug_detailed(MODULE, f"Grouped changes into {len(location_changes)} locations")

    # Analyze each location for conflicts
    for location, task_changes in location_changes.items():
        if len(task_changes) <= 1:
            continue  # No conflict at this location

        debug_verbose(
            MODULE,
            f"Checking location {location}",
            task_changes_count=len(task_changes),
        )

        file_path = next(iter(task_analyses.values())).file_path
        conflict = analyze_location_conflict(
            file_path, location, task_changes, rule_index
        )
        if conflict:
            debug_detailed(
                MODULE,
                f"Conflict detected at {location}",
                severity=conflict.severity.value,
                can_auto_merge=conflict.can_auto_merge,
                tasks=conflict.tasks_involved,
            )
            conflicts.append(conflict)

    # Also check for implicit conflicts (e.g., changes to related code)
    implicit_conflicts = detect_implicit_conflicts(task_analyses)
    if implicit_conflicts:
        debug_detailed(MODULE, f"Found {len(implicit_conflicts)} implicit conflicts")
    conflicts.extend(implicit_conflicts)

    return conflicts


def analyze_location_conflict(
    file_path: str,
    location: str,
    task_changes: list[tuple[str, SemanticChange]],
    rule_index: dict[tuple[ChangeType, ChangeType], CompatibilityRule],
) -> ConflictRegion | None:
    """
    Analyze changes at a specific location for conflicts.

    Args:
        file_path: Path to the file being analyzed
        location: Location identifier (e.g., "function:main")
        task_changes: List of (task_id, change) tuples for this location
        rule_index: Indexed compatibility rules

    Returns:
        ConflictRegion if conflicts exist, None otherwise
    """
    tasks = [tc[0] for tc in task_changes]
    changes = [tc[1] for tc in task_changes]
    change_types = [c.change_type for c in changes]

    # Check if all changes target the same thing
    targets = {c.target for c in changes}
    if len(targets) > 1:
        # Different targets at same location - likely compatible
        # (e.g., adding two different functions)
        return None

    # Check pairwise compatibility
    all_compatible = True
    final_strategy: MergeStrategy | None = None
    reasons = []

    for i, (type_a, change_a) in enumerate(zip(change_types, changes)):
        for type_b, change_b in zip(change_types[i + 1 :], changes[i + 1 :]):
            rule = rule_index.get((type_a, type_b))

            if rule:
                if not rule.compatible:
                    all_compatible = False
                    reasons.append(rule.reason)
                elif rule.strategy:
                    final_strategy = rule.strategy
            else:
                # No rule - conservative default
                all_compatible = False
                reasons.append(f"No rule for {type_a.value} + {type_b.value}")

    # Determine severity
    if all_compatible:
        severity = ConflictSeverity.NONE
    else:
        severity = assess_severity(change_types, changes)

    return ConflictRegion(
        file_path=file_path,
        location=location,
        tasks_involved=tasks,
        change_types=change_types,
        severity=severity,
        can_auto_merge=all_compatible,
        merge_strategy=final_strategy if all_compatible else MergeStrategy.AI_REQUIRED,
        reason=" | ".join(reasons) if reasons else "Changes are compatible",
    )


def assess_severity(
    change_types: list[ChangeType],
    changes: list[SemanticChange],
) -> ConflictSeverity:
    """
    Assess the severity of a conflict.

    Args:
        change_types: List of change types involved
        changes: List of semantic changes

    Returns:
        Assessed conflict severity level
    """
    # Critical: Both tasks modify core logic
    modify_types = {
        ChangeType.MODIFY_FUNCTION,
        ChangeType.MODIFY_METHOD,
        ChangeType.MODIFY_CLASS,
    }
    modify_count = sum(1 for ct in change_types if ct in modify_types)

    if modify_count >= 2:
        # Check if they modify the exact same lines
        line_ranges = [(c.line_start, c.line_end) for c in changes]
        if ranges_overlap(line_ranges):
            return ConflictSeverity.CRITICAL

    # High: Structural changes that could break compilation
    structural_types = {
        ChangeType.WRAP_JSX,
        ChangeType.UNWRAP_JSX,
        ChangeType.REMOVE_FUNCTION,
        ChangeType.REMOVE_CLASS,
    }
    if any(ct in structural_types for ct in change_types):
        return ConflictSeverity.HIGH

    # Medium: Modifications to same function/method
    if modify_count >= 1:
        return ConflictSeverity.MEDIUM

    # Low: Likely resolvable with AI
    return ConflictSeverity.LOW


def ranges_overlap(ranges: list[tuple[int, int]]) -> bool:
    """
    Check if any line ranges overlap.

    Args:
        ranges: List of (start_line, end_line) tuples

    Returns:
        True if any ranges overlap, False otherwise
    """
    sorted_ranges = sorted(ranges)
    for i in range(len(sorted_ranges) - 1):
        if sorted_ranges[i][1] >= sorted_ranges[i + 1][0]:
            return True
    return False


def detect_implicit_conflicts(
    task_analyses: dict[str, FileAnalysis],
) -> list[ConflictRegion]:
    """
    Detect implicit conflicts not caught by location analysis.

    This includes conflicts like:
    - Function rename + function call changes
    - Import removal + usage
    - Variable rename + references

    Args:
        task_analyses: Map of task_id -> FileAnalysis

    Returns:
        List of implicit conflict regions

    Note:
        These advanced checks are currently TODO.
        The main location-based detection handles most cases.
    """
    conflicts = []

    # Check for function rename + function call changes
    # (If task A renames a function and task B calls the old name)

    # Check for import removal + usage
    # (If task A removes an import and task B uses it)

    # For now, these advanced checks are TODO
    # The main location-based detection handles most cases

    return conflicts


def suggest_resolution_strategies(conflict: ConflictRegion) -> list[str]:
    """
    Generate AI-suggested resolution strategies for a conflict.

    Analyzes the conflict characteristics and suggests practical approaches
    for resolving it based on severity, change types, and merge strategy.

    Args:
        conflict: The conflict region to analyze

    Returns:
        List of human-readable resolution strategy suggestions
    """
    strategies = []

    debug_detailed(
        MODULE,
        f"Generating strategies for conflict at {conflict.location}",
        severity=conflict.severity.value,
        can_auto_merge=conflict.can_auto_merge,
        tasks=conflict.tasks_involved,
    )

    # If auto-mergeable, explain the automatic strategy
    if conflict.can_auto_merge and conflict.merge_strategy:
        if conflict.merge_strategy == MergeStrategy.COMBINE_IMPORTS:
            strategies.append(
                "Auto-merge: Combine all imports from both tasks into a single import list"
            )
        elif conflict.merge_strategy == MergeStrategy.HOOKS_FIRST:
            strategies.append(
                "Auto-merge: Add React hooks at function start, followed by other changes"
            )
        elif conflict.merge_strategy == MergeStrategy.APPEND_FUNCTIONS:
            strategies.append(
                "Auto-merge: Append all new functions after existing code"
            )
        elif conflict.merge_strategy == MergeStrategy.APPEND_METHODS:
            strategies.append(
                "Auto-merge: Add all new methods to the class in order"
            )
        elif conflict.merge_strategy == MergeStrategy.COMBINE_PROPS:
            strategies.append(
                "Auto-merge: Merge JSX/object properties from both tasks"
            )
        else:
            strategies.append(
                f"Auto-merge: Apply {conflict.merge_strategy.value} strategy"
            )
        return strategies

    # Generate strategies based on severity
    if conflict.severity == ConflictSeverity.CRITICAL:
        strategies.append(
            "Manual review: Both tasks modify the same code lines - requires careful human review"
        )
        strategies.append(
            "Use git diff: Compare both versions and manually combine the logic"
        )
        strategies.append(
            f"Coordinate with task owners: Review intent of tasks {' and '.join(conflict.tasks_involved)}"
        )

    elif conflict.severity == ConflictSeverity.HIGH:
        strategies.append(
            "AI-assisted merge: Use AI to intelligently combine structural changes"
        )
        strategies.append(
            "Sequential merge: Apply one task first, then manually apply the second"
        )
        strategies.append(
            "Refactor approach: Consider redesigning the affected code to accommodate both changes"
        )

    elif conflict.severity == ConflictSeverity.MEDIUM:
        strategies.append(
            "AI merge: Let AI analyze and combine the function/method modifications"
        )
        strategies.append(
            "Manual merge: Review and combine changes while preserving both functionalities"
        )

    else:  # LOW severity
        strategies.append(
            "AI auto-merge: Low-risk conflict that AI can likely resolve automatically"
        )
        strategies.append(
            "Quick review: Verify merged result maintains both task intents"
        )

    # Add change-type specific strategies
    change_types_set = set(conflict.change_types)

    if ChangeType.REMOVE_FUNCTION in change_types_set or ChangeType.REMOVE_CLASS in change_types_set:
        strategies.append(
            "Conflict resolution: One task removes code another modifies - determine if removal is still valid"
        )

    if ChangeType.RENAME_FUNCTION in change_types_set:
        strategies.append(
            "Update references: Ensure function calls use the correct name after merge"
        )

    if {ChangeType.WRAP_JSX, ChangeType.UNWRAP_JSX} & change_types_set:
        strategies.append(
            "JSX structure: Carefully review JSX nesting changes to maintain valid structure"
        )

    if {ChangeType.ADD_IMPORT, ChangeType.REMOVE_IMPORT} & change_types_set:
        strategies.append(
            "Import cleanup: Ensure imports match the actual usage in merged code"
        )

    # If no strategies generated yet, provide generic fallback
    if not strategies:
        strategies.append(
            "Manual review: Carefully examine both changes and combine them appropriately"
        )
        strategies.append(
            "AI assistance: Use AI to suggest a merged version incorporating both changes"
        )

    debug_detailed(
        MODULE,
        f"Generated {len(strategies)} strategies for conflict",
        location=conflict.location,
    )

    return strategies


def analyze_compatibility(
    change_a: SemanticChange,
    change_b: SemanticChange,
    rule_index: dict[tuple[ChangeType, ChangeType], CompatibilityRule],
) -> tuple[bool, MergeStrategy | None, str]:
    """
    Analyze compatibility between two specific changes.

    Args:
        change_a: First semantic change
        change_b: Second semantic change
        rule_index: Indexed compatibility rules

    Returns:
        Tuple of (compatible, strategy, reason)
    """
    rule = rule_index.get((change_a.change_type, change_b.change_type))

    if rule:
        return (rule.compatible, rule.strategy, rule.reason)
    else:
        return (False, MergeStrategy.AI_REQUIRED, "No compatibility rule defined")
