#!/usr/bin/env python3
"""
Tests for ReviewChecklist Data Class
====================================

Comprehensive unit tests for ReviewChecklist and ReviewChecklistItem classes.
Tests cover initialization, item management, completion tracking, and persistence.
"""

import json
from pathlib import Path

import pytest

from apps.backend.review.checklist import (
    ReviewChecklist,
    ReviewChecklistItem,
    REVIEW_CHECKLIST_FILE,
)


# =============================================================================
# REVIEW CHECKLIST ITEM - BASIC FUNCTIONALITY
# =============================================================================


class TestReviewChecklistItemBasics:
    """Tests for ReviewChecklistItem basic functionality."""

    def test_create_item_with_defaults(self) -> None:
        """New ReviewChecklistItem has correct defaults."""
        item = ReviewChecklistItem(id="test", description="Test item")

        assert item.id == "test"
        assert item.description == "Test item"
        assert item.completed is False
        assert item.completed_at == ""
        assert item.completed_by == ""
        assert item.required is True

    def test_create_optional_item(self) -> None:
        """ReviewChecklistItem can be created as optional."""
        item = ReviewChecklistItem(
            id="opt", description="Optional", required=False
        )

        assert item.required is False

    def test_mark_item_complete(self) -> None:
        """mark_complete() sets completion status."""
        item = ReviewChecklistItem(id="test", description="Test")
        item.mark_complete(completed_by="alice")

        assert item.completed is True
        assert item.completed_by == "alice"
        assert item.completed_at != ""  # Should have timestamp

    def test_mark_item_incomplete(self) -> None:
        """mark_incomplete() clears completion status."""
        item = ReviewChecklistItem(id="test", description="Test")
        item.mark_complete(completed_by="alice")
        item.mark_incomplete()

        assert item.completed is False
        assert item.completed_by == ""
        assert item.completed_at == ""

    def test_item_to_dict(self) -> None:
        """to_dict() returns correct dictionary."""
        item = ReviewChecklistItem(
            id="test",
            description="Test item",
            completed=True,
            completed_at="2024-01-01T00:00:00",
            completed_by="bob",
            required=False,
        )

        d = item.to_dict()

        assert d["id"] == "test"
        assert d["description"] == "Test item"
        assert d["completed"] is True
        assert d["completed_at"] == "2024-01-01T00:00:00"
        assert d["completed_by"] == "bob"
        assert d["required"] is False

    def test_item_from_dict(self) -> None:
        """from_dict() creates correct ReviewChecklistItem."""
        data = {
            "id": "test",
            "description": "Test item",
            "completed": True,
            "completed_at": "2024-01-01T00:00:00",
            "completed_by": "charlie",
            "required": False,
        }

        item = ReviewChecklistItem.from_dict(data)

        assert item.id == "test"
        assert item.description == "Test item"
        assert item.completed is True
        assert item.completed_at == "2024-01-01T00:00:00"
        assert item.completed_by == "charlie"
        assert item.required is False


# =============================================================================
# REVIEW CHECKLIST - BASIC FUNCTIONALITY
# =============================================================================


class TestReviewChecklistBasics:
    """Tests for ReviewChecklist basic functionality."""

    def test_create_empty_checklist(self) -> None:
        """New ReviewChecklist has correct defaults."""
        checklist = ReviewChecklist()

        assert checklist.items == []
        assert checklist.created_at != ""
        assert checklist.updated_at != ""
        assert checklist.custom_items_allowed is True

    def test_create_default_checklist(self) -> None:
        """create_default() creates checklist with default items."""
        checklist = ReviewChecklist.create_default()

        assert len(checklist.items) == 5
        assert any(item.id == "code_quality" for item in checklist.items)
        assert any(item.id == "tests_pass" for item in checklist.items)
        assert any(item.id == "documentation" for item in checklist.items)
        assert any(item.id == "security_review" for item in checklist.items)
        assert any(item.id == "performance" for item in checklist.items)

        # Check that performance is optional
        perf_item = next(
            item for item in checklist.items if item.id == "performance"
        )
        assert perf_item.required is False

    def test_add_item(self) -> None:
        """add_item() adds item to checklist."""
        checklist = ReviewChecklist()
        item = checklist.add_item("test", "Test item", required=True)

        assert len(checklist.items) == 1
        assert item.id == "test"
        assert item.description == "Test item"
        assert item.required is True

    def test_add_duplicate_item_raises(self) -> None:
        """add_item() raises ValueError for duplicate ID."""
        checklist = ReviewChecklist()
        checklist.add_item("test", "Test item")

        with pytest.raises(ValueError, match="already exists"):
            checklist.add_item("test", "Duplicate")

    def test_remove_item(self) -> None:
        """remove_item() removes item from checklist."""
        checklist = ReviewChecklist()
        checklist.add_item("test", "Test item")

        result = checklist.remove_item("test")

        assert result is True
        assert len(checklist.items) == 0

    def test_remove_nonexistent_item(self) -> None:
        """remove_item() returns False for nonexistent item."""
        checklist = ReviewChecklist()

        result = checklist.remove_item("nonexistent")

        assert result is False

    def test_get_item(self) -> None:
        """get_item() retrieves item by ID."""
        checklist = ReviewChecklist()
        checklist.add_item("test", "Test item")

        item = checklist.get_item("test")

        assert item is not None
        assert item.id == "test"

    def test_get_nonexistent_item(self) -> None:
        """get_item() returns None for nonexistent item."""
        checklist = ReviewChecklist()

        item = checklist.get_item("nonexistent")

        assert item is None


# =============================================================================
# REVIEW CHECKLIST - COMPLETION TRACKING
# =============================================================================


class TestReviewChecklistCompletion:
    """Tests for ReviewChecklist completion tracking."""

    def test_mark_item_complete(self) -> None:
        """mark_item_complete() marks item as complete."""
        checklist = ReviewChecklist()
        checklist.add_item("test", "Test item")

        result = checklist.mark_item_complete("test", completed_by="alice")

        assert result is True
        item = checklist.get_item("test")
        assert item is not None
        assert item.completed is True
        assert item.completed_by == "alice"

    def test_mark_nonexistent_item_complete(self) -> None:
        """mark_item_complete() returns False for nonexistent item."""
        checklist = ReviewChecklist()

        result = checklist.mark_item_complete("nonexistent")

        assert result is False

    def test_mark_item_incomplete(self) -> None:
        """mark_item_incomplete() marks item as incomplete."""
        checklist = ReviewChecklist()
        checklist.add_item("test", "Test item")
        checklist.mark_item_complete("test")

        result = checklist.mark_item_incomplete("test")

        assert result is True
        item = checklist.get_item("test")
        assert item is not None
        assert item.completed is False

    def test_is_complete_all_required_done(self) -> None:
        """is_complete() returns True when all required items done."""
        checklist = ReviewChecklist()
        checklist.add_item("req1", "Required 1", required=True)
        checklist.add_item("req2", "Required 2", required=True)
        checklist.add_item("opt1", "Optional 1", required=False)

        checklist.mark_item_complete("req1")
        checklist.mark_item_complete("req2")

        assert checklist.is_complete() is True

    def test_is_complete_optional_not_done(self) -> None:
        """is_complete() returns True with optional items incomplete."""
        checklist = ReviewChecklist()
        checklist.add_item("req1", "Required 1", required=True)
        checklist.add_item("opt1", "Optional 1", required=False)

        checklist.mark_item_complete("req1")

        assert checklist.is_complete() is True

    def test_is_complete_required_not_done(self) -> None:
        """is_complete() returns False when required items incomplete."""
        checklist = ReviewChecklist()
        checklist.add_item("req1", "Required 1", required=True)
        checklist.add_item("req2", "Required 2", required=True)

        checklist.mark_item_complete("req1")

        assert checklist.is_complete() is False

    def test_is_complete_empty_checklist(self) -> None:
        """is_complete() returns True for empty checklist."""
        checklist = ReviewChecklist()

        assert checklist.is_complete() is True

    def test_get_completion_status(self) -> None:
        """get_completion_status() returns correct statistics."""
        checklist = ReviewChecklist()
        checklist.add_item("req1", "Required 1", required=True)
        checklist.add_item("req2", "Required 2", required=True)
        checklist.add_item("opt1", "Optional 1", required=False)

        checklist.mark_item_complete("req1")
        checklist.mark_item_complete("opt1")

        status = checklist.get_completion_status()

        assert status["total_items"] == 3
        assert status["total_required"] == 2
        assert status["completed_required"] == 1
        assert status["completed_total"] == 2
        assert status["is_complete"] is False
        assert 60 < status["completion_percentage"] < 70

    def test_reset_checklist(self) -> None:
        """reset() marks all items as incomplete."""
        checklist = ReviewChecklist()
        checklist.add_item("test1", "Test 1")
        checklist.add_item("test2", "Test 2")
        checklist.mark_item_complete("test1")
        checklist.mark_item_complete("test2")

        checklist.reset()

        assert all(not item.completed for item in checklist.items)


# =============================================================================
# REVIEW CHECKLIST - PERSISTENCE
# =============================================================================


class TestReviewChecklistPersistence:
    """Tests for ReviewChecklist load and save operations."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """save() creates review_checklist.json file."""
        checklist = ReviewChecklist()
        checklist.add_item("test", "Test item")

        checklist.save(tmp_path)

        file_path = tmp_path / REVIEW_CHECKLIST_FILE
        assert file_path.exists()

    def test_save_writes_correct_data(self, tmp_path: Path) -> None:
        """save() writes correct JSON data."""
        checklist = ReviewChecklist()
        checklist.add_item("test", "Test item", required=True)
        checklist.mark_item_complete("test", completed_by="alice")

        checklist.save(tmp_path)

        file_path = tmp_path / REVIEW_CHECKLIST_FILE
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "test"
        assert data["items"][0]["description"] == "Test item"
        assert data["items"][0]["completed"] is True
        assert data["items"][0]["completed_by"] == "alice"

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """load() returns empty checklist for nonexistent file."""
        checklist = ReviewChecklist.load(tmp_path)

        assert checklist.items == []
        assert checklist.custom_items_allowed is True

    def test_load_existing_file(self, tmp_path: Path) -> None:
        """load() reads existing checklist file."""
        # Save a checklist
        original = ReviewChecklist()
        original.add_item("test", "Test item", required=True)
        original.mark_item_complete("test", completed_by="bob")
        original.save(tmp_path)

        # Load it back
        loaded = ReviewChecklist.load(tmp_path)

        assert len(loaded.items) == 1
        assert loaded.items[0].id == "test"
        assert loaded.items[0].description == "Test item"
        assert loaded.items[0].completed is True
        assert loaded.items[0].completed_by == "bob"

    def test_to_dict(self) -> None:
        """to_dict() returns correct dictionary."""
        checklist = ReviewChecklist()
        checklist.add_item("test", "Test item")

        d = checklist.to_dict()

        assert "items" in d
        assert "created_at" in d
        assert "updated_at" in d
        assert "custom_items_allowed" in d
        assert len(d["items"]) == 1

    def test_from_dict(self) -> None:
        """from_dict() creates correct ReviewChecklist."""
        data = {
            "items": [
                {
                    "id": "test",
                    "description": "Test item",
                    "completed": True,
                    "completed_at": "2024-01-01T00:00:00",
                    "completed_by": "alice",
                    "required": True,
                }
            ],
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
            "custom_items_allowed": False,
        }

        checklist = ReviewChecklist.from_dict(data)

        assert len(checklist.items) == 1
        assert checklist.items[0].id == "test"
        assert checklist.created_at == "2024-01-01T00:00:00"
        assert checklist.updated_at == "2024-01-02T00:00:00"
        assert checklist.custom_items_allowed is False
