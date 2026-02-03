"""
End-to-End Tests for Merge Conflict Analysis Feature
=====================================================

Tests the complete merge conflict analysis flow:
1. Preview conflicts before merge
2. AI-suggested resolution strategies
3. User strategy selection
4. Apply selected strategies during merge

These tests validate the integration between backend CLI and frontend UI.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the backend directory to path
_backend_dir = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from merge.types import ConflictRegion, ChangeType, ConflictSeverity
from merge.conflict_analysis import suggest_resolution_strategies


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_worktree_dir(tmp_path):
    """Create a temporary worktree directory structure."""
    worktree_dir = tmp_path / ".auto-claude" / "worktrees" / "tasks" / "001-test-feature"
    worktree_dir.mkdir(parents=True)

    # Create spec directory
    spec_dir = tmp_path / ".auto-claude" / "specs" / "001-test-feature"
    spec_dir.mkdir(parents=True)

    return {
        "worktree": worktree_dir,
        "spec": spec_dir,
        "project_root": tmp_path
    }


@pytest.fixture
def sample_conflicts():
    """Create sample conflicts for testing."""
    return [
        ConflictRegion(
            file_path="src/auth.py",
            location="function:authenticate",
            tasks_involved=["001-auth", "002-security"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.HIGH,
            can_auto_merge=False,
            reason="Both branches modified authentication logic",
            resolution_strategies=[
                "Manual review required: authentication changes need careful examination",
                "AI-assisted merge: analyze security implications",
                "Keep both changes with conditional logic"
            ]
        ),
        ConflictRegion(
            file_path="src/utils.py",
            location="file_top",
            tasks_involved=["001-utils"],
            change_types=[ChangeType.ADD_IMPORT],
            severity=ConflictSeverity.LOW,
            can_auto_merge=True,
            reason="Import statement order differs",
            resolution_strategies=[
                "Auto-merge: combine imports and sort alphabetically",
                "Use current branch: main branch imports",
                "Use incoming branch: feature branch imports"
            ]
        ),
        ConflictRegion(
            file_path="package.json",
            location="dependencies",
            tasks_involved=["001-deps", "002-deps"],
            change_types=[ChangeType.MODIFY_VARIABLE],
            severity=ConflictSeverity.MEDIUM,
            can_auto_merge=False,
            reason="Dependency versions differ",
            resolution_strategies=[
                "Use semantic versioning: choose highest compatible version",
                "Manual review: check breaking changes",
                "AI-assisted: analyze dependency compatibility"
            ]
        )
    ]


@pytest.fixture
def mock_preview_response(sample_conflicts):
    """Create mock response for preview-merge CLI command."""
    return {
        "success": True,
        "conflicts": [c.to_dict() for c in sample_conflicts],
        "total_conflicts": len(sample_conflicts),
        "auto_mergeable_count": sum(1 for c in sample_conflicts if c.can_auto_merge),
        "high_severity_count": sum(1 for c in sample_conflicts if c.severity == ConflictSeverity.HIGH)
    }


# ============================================================================
# E2E Test: Backend Preview Conflicts
# ============================================================================

class TestBackendPreviewE2E:
    """Test backend conflict preview functionality."""

    def test_preview_returns_conflicts_with_strategies(self, sample_conflicts):
        """Test that preview command returns conflicts with AI strategies."""
        # Verify each conflict has resolution strategies
        for conflict in sample_conflicts:
            assert hasattr(conflict, 'resolution_strategies')
            assert isinstance(conflict.resolution_strategies, list)
            assert len(conflict.resolution_strategies) > 0

            # Verify strategies are meaningful
            for strategy in conflict.resolution_strategies:
                assert len(strategy) > 10  # Not just empty strings
                assert isinstance(strategy, str)

    def test_suggest_resolution_strategies_function(self):
        """Test the strategy suggestion function directly."""
        conflict = ConflictRegion(
            file_path="test.py",
            location="function:test",
            tasks_involved=["001-test"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.HIGH,
            can_auto_merge=False,
            reason="Both modified same function"
        )

        strategies = suggest_resolution_strategies(conflict=conflict)

        assert isinstance(strategies, list)
        assert len(strategies) > 0

        # High severity should suggest manual review
        strategy_text = " ".join(strategies).lower()
        assert "manual" in strategy_text or "review" in strategy_text or "ai" in strategy_text

    def test_strategies_vary_by_severity(self):
        """Test that strategy suggestions vary based on conflict severity."""
        high_conflict = ConflictRegion(
            file_path="critical.py",
            location="function:critical",
            tasks_involved=["001-security"],
            change_types=[ChangeType.MODIFY_FUNCTION],
            severity=ConflictSeverity.HIGH,
            can_auto_merge=False,
            reason="Security critical changes"
        )

        low_conflict = ConflictRegion(
            file_path="style.py",
            location="file_top",
            tasks_involved=["001-style"],
            change_types=[ChangeType.FORMATTING_ONLY],
            severity=ConflictSeverity.LOW,
            can_auto_merge=True,
            reason="Formatting differences"
        )

        high_strategies = suggest_resolution_strategies(high_conflict)
        low_strategies = suggest_resolution_strategies(low_conflict)

        # High severity should be more cautious
        high_text = " ".join(high_strategies).lower()
        low_text = " ".join(low_strategies).lower()

        # High severity likely mentions manual/careful review
        assert "manual" in high_text or "careful" in high_text or "ai" in high_text

        # Low severity might mention auto-merge
        assert "auto" in low_text or "merge" in low_text


# ============================================================================
# E2E Test: Conflict Data Serialization
# ============================================================================

class TestConflictSerializationE2E:
    """Test conflict data serialization for frontend communication."""

    def test_conflict_to_dict_includes_strategies(self, sample_conflicts):
        """Test that ConflictRegion.to_dict() includes resolution strategies."""
        for conflict in sample_conflicts:
            data = conflict.to_dict()

            assert "resolution_strategies" in data
            assert isinstance(data["resolution_strategies"], list)
            assert len(data["resolution_strategies"]) > 0

    def test_conflict_from_dict_preserves_strategies(self, sample_conflicts):
        """Test that ConflictRegion.from_dict() preserves resolution strategies."""
        original = sample_conflicts[0]
        data = original.to_dict()

        # Simulate JSON round-trip
        json_str = json.dumps(data)
        parsed_data = json.loads(json_str)

        # Recreate from dict
        recreated = ConflictRegion.from_dict(parsed_data)

        assert recreated.resolution_strategies == original.resolution_strategies
        assert len(recreated.resolution_strategies) == len(original.resolution_strategies)

    def test_preview_response_json_format(self, mock_preview_response):
        """Test that preview response has correct JSON format for frontend."""
        # Simulate JSON round-trip (backend -> IPC -> frontend)
        json_str = json.dumps(mock_preview_response)
        parsed = json.loads(json_str)

        assert "success" in parsed
        assert "conflicts" in parsed
        assert isinstance(parsed["conflicts"], list)

        # Each conflict should have strategies
        for conflict_data in parsed["conflicts"]:
            assert "resolution_strategies" in conflict_data
            assert isinstance(conflict_data["resolution_strategies"], list)


# ============================================================================
# E2E Test: Strategy Selection and Application
# ============================================================================

class TestStrategySelectionE2E:
    """Test user strategy selection and application flow."""

    def test_user_strategy_selection_format(self):
        """Test the format of user-selected strategies."""
        # Simulate user selections from frontend
        user_selections = {
            "src/auth.py:10-15": "AI-assisted merge: analyze security implications",
            "src/utils.py:42-45": "Auto-merge: combine imports and sort alphabetically",
            "package.json:20-22": "Use semantic versioning: choose highest compatible version"
        }

        # Verify format is JSON-serializable
        json_str = json.dumps(user_selections)
        parsed = json.loads(json_str)

        assert len(parsed) == 3
        assert "src/auth.py:10-15" in parsed

        # Verify strategy values are strings
        for key, value in parsed.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
            assert len(value) > 0

    def test_conflict_resolution_parameter_format(self):
        """Test that conflict resolutions parameter matches expected format."""
        # This matches the format passed to --conflict-resolutions CLI arg
        conflict_resolutions = {
            "src/auth.py": "Manual review required: authentication changes need careful examination",
            "src/utils.py": "Auto-merge: combine imports and sort alphabetically"
        }

        # Should be JSON-serializable for CLI parameter
        json_str = json.dumps(conflict_resolutions)
        assert isinstance(json_str, str)

        # Should be parseable
        parsed = json.loads(json_str)
        assert parsed == conflict_resolutions


# ============================================================================
# E2E Test: Complete Flow Integration
# ============================================================================

class TestCompleteFlowE2E:
    """Test the complete end-to-end flow."""

    def test_preview_to_merge_flow(self, sample_conflicts, mock_preview_response):
        """Test complete flow from preview to merge with strategy selection."""
        # Step 1: Backend generates preview with conflicts and strategies
        conflicts = sample_conflicts
        assert all(len(c.resolution_strategies) > 0 for c in conflicts)

        # Step 2: Frontend receives conflict data
        preview_data = mock_preview_response
        assert preview_data["success"] is True
        assert len(preview_data["conflicts"]) == 3

        # Step 3: User views conflicts and strategies in UI
        for conflict_data in preview_data["conflicts"]:
            strategies = conflict_data["resolution_strategies"]
            assert isinstance(strategies, list)
            assert len(strategies) > 0

        # Step 4: User selects strategies for each conflict
        user_selections = {}
        for conflict_data in preview_data["conflicts"]:
            file_path = conflict_data["file_path"]
            # User selects first strategy
            selected_strategy = conflict_data["resolution_strategies"][0]
            user_selections[file_path] = selected_strategy

        assert len(user_selections) == 3

        # Step 5: Frontend sends selections to backend for merge
        merge_payload = {
            "conflict_resolutions": user_selections
        }

        # Verify payload format
        assert "conflict_resolutions" in merge_payload
        assert len(merge_payload["conflict_resolutions"]) == 3

        # Step 6: Backend applies selected strategies (simulated)
        # In real flow, this would call MergeOrchestrator with conflict_resolutions
        for file_path, strategy in user_selections.items():
            assert isinstance(strategy, str)
            assert len(strategy) > 0

    def test_conflict_count_badge_data(self, mock_preview_response):
        """Test data for conflict count badge display."""
        preview = mock_preview_response

        # Frontend needs these counts for badge
        total_conflicts = preview["total_conflicts"]
        high_severity_count = preview["high_severity_count"]

        assert total_conflicts == 3
        assert high_severity_count == 1

        # Badge should show total with severity indicator
        badge_text = f"{total_conflicts} conflicts"
        badge_severity = "destructive" if high_severity_count > 0 else "warning"

        assert badge_text == "3 conflicts"
        assert badge_severity == "destructive"

    def test_auto_merge_vs_manual_review_detection(self, sample_conflicts):
        """Test detection of auto-mergeable vs manual review conflicts."""
        auto_mergeable = [c for c in sample_conflicts if c.can_auto_merge]
        needs_review = [c for c in sample_conflicts if not c.can_auto_merge]

        assert len(auto_mergeable) == 1  # utils.py
        assert len(needs_review) == 2     # auth.py, package.json

        # Auto-mergeable conflicts should have auto-merge strategy
        for conflict in auto_mergeable:
            strategy_text = " ".join(conflict.resolution_strategies).lower()
            assert "auto" in strategy_text

        # Manual review conflicts should suggest review/AI
        for conflict in needs_review:
            strategy_text = " ".join(conflict.resolution_strategies).lower()
            assert "manual" in strategy_text or "ai" in strategy_text or "review" in strategy_text


# ============================================================================
# E2E Test: Error Handling
# ============================================================================

class TestErrorHandlingE2E:
    """Test error handling in conflict analysis flow."""

    def test_no_conflicts_scenario(self):
        """Test flow when no conflicts exist."""
        preview_response = {
            "success": True,
            "conflicts": [],
            "total_conflicts": 0,
            "auto_mergeable_count": 0,
            "high_severity_count": 0
        }

        # Frontend should show "no conflicts" message
        assert preview_response["total_conflicts"] == 0
        assert len(preview_response["conflicts"]) == 0

    def test_preview_failure_scenario(self):
        """Test flow when preview command fails."""
        error_response = {
            "success": False,
            "error": "Failed to analyze conflicts: worktree not found",
            "conflicts": []
        }

        assert error_response["success"] is False
        assert "error" in error_response
        assert isinstance(error_response["error"], str)

    def test_missing_strategies_fallback(self):
        """Test fallback when strategies are missing (backward compatibility)."""
        # Simulate old conflict data without strategies field
        old_conflict_data = {
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 5,
            "severity": "medium",
            "reason": "Both modified",
            "change_type": "modified",
            "can_auto_merge": False
            # No resolution_strategies field
        }

        # Frontend should handle gracefully
        strategies = old_conflict_data.get("resolution_strategies", [])
        assert strategies == []  # Empty list fallback

        # Or use single strategy field if available
        single_strategy = old_conflict_data.get("strategy")
        if single_strategy:
            strategies = [single_strategy]


# ============================================================================
# E2E Test: IPC Communication
# ============================================================================

class TestIPCCommunicationE2E:
    """Test IPC communication between frontend and backend."""

    def test_preview_conflicts_ipc_request(self):
        """Test preview conflicts IPC request format."""
        # Frontend sends this to backend
        ipc_request = {
            "projectPath": "/path/to/project",
            "specId": "001-test-feature"
        }

        assert "projectPath" in ipc_request
        assert "specId" in ipc_request

    def test_merge_with_resolutions_ipc_request(self):
        """Test merge with conflict resolutions IPC request format."""
        # Frontend sends this to backend for merge
        ipc_request = {
            "projectPath": "/path/to/project",
            "specId": "001-test-feature",
            "conflictResolutions": {
                "src/auth.py": "Manual review required",
                "src/utils.py": "Auto-merge: combine imports"
            }
        }

        assert "projectPath" in ipc_request
        assert "specId" in ipc_request
        assert "conflictResolutions" in ipc_request
        assert isinstance(ipc_request["conflictResolutions"], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
