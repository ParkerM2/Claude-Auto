"""
Review Checklist Management
============================

Handles configurable review checklists with item tracking and persistence.
Supports customizable checklist items, completion status, and validation.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Checklist file name
REVIEW_CHECKLIST_FILE = "review_checklist.json"


@dataclass
class ReviewChecklistItem:
    """
    A single item in a review checklist.

    Attributes:
        id: Unique identifier for the checklist item
        description: What needs to be checked/verified
        completed: Whether this item has been completed
        completed_at: ISO timestamp when item was completed
        completed_by: Who completed the item (username or 'auto')
        required: Whether this item must be completed for approval
    """

    id: str
    description: str
    completed: bool = False
    completed_at: str = ""
    completed_by: str = ""
    required: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "description": self.description,
            "completed": self.completed,
            "completed_at": self.completed_at,
            "completed_by": self.completed_by,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewChecklistItem":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            description=data.get("description", ""),
            completed=data.get("completed", False),
            completed_at=data.get("completed_at", ""),
            completed_by=data.get("completed_by", ""),
            required=data.get("required", True),
        )

    def mark_complete(self, completed_by: str = "user") -> None:
        """
        Mark this item as completed.

        Args:
            completed_by: Who is marking it complete ('user', 'auto', or username)
        """
        self.completed = True
        self.completed_at = datetime.now().isoformat()
        self.completed_by = completed_by

    def mark_incomplete(self) -> None:
        """Mark this item as incomplete."""
        self.completed = False
        self.completed_at = ""
        self.completed_by = ""


@dataclass
class ReviewChecklist:
    """
    Manages a configurable review checklist for a spec.

    Attributes:
        items: List of checklist items to verify
        created_at: ISO timestamp when checklist was created
        updated_at: ISO timestamp when checklist was last modified
        custom_items_allowed: Whether users can add custom items
    """

    items: list[ReviewChecklistItem] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    custom_items_allowed: bool = True

    def __post_init__(self) -> None:
        """Initialize timestamps if not set."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "items": [item.to_dict() for item in self.items],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "custom_items_allowed": self.custom_items_allowed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewChecklist":
        """Create from dictionary."""
        items_data = data.get("items", [])
        items = [ReviewChecklistItem.from_dict(item) for item in items_data]

        return cls(
            items=items,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            custom_items_allowed=data.get("custom_items_allowed", True),
        )

    def save(self, spec_dir: Path) -> None:
        """
        Save checklist to the spec directory.

        Args:
            spec_dir: Path to the spec directory
        """
        self.updated_at = datetime.now().isoformat()
        checklist_file = Path(spec_dir) / REVIEW_CHECKLIST_FILE

        with open(checklist_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, spec_dir: Path) -> "ReviewChecklist":
        """
        Load checklist from the spec directory.

        Returns a new empty ReviewChecklist if file doesn't exist or is invalid.

        Args:
            spec_dir: Path to the spec directory

        Returns:
            ReviewChecklist instance
        """
        checklist_file = Path(spec_dir) / REVIEW_CHECKLIST_FILE
        if not checklist_file.exists():
            return cls()

        try:
            with open(checklist_file, encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return cls()

    def get_item(self, item_id: str) -> ReviewChecklistItem | None:
        """
        Get a checklist item by ID.

        Args:
            item_id: The item ID to find

        Returns:
            ReviewChecklistItem if found, None otherwise
        """
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def add_item(
        self,
        item_id: str,
        description: str,
        required: bool = True,
        auto_save: bool = False,
        spec_dir: Path | None = None,
    ) -> ReviewChecklistItem:
        """
        Add a new checklist item.

        Args:
            item_id: Unique identifier for the item
            description: Description of what to check
            required: Whether this item is required for approval
            auto_save: Whether to automatically save after adding
            spec_dir: Spec directory path (required if auto_save=True)

        Returns:
            The created ReviewChecklistItem

        Raises:
            ValueError: If item_id already exists
        """
        if self.get_item(item_id):
            raise ValueError(f"Checklist item with id '{item_id}' already exists")

        item = ReviewChecklistItem(
            id=item_id,
            description=description,
            required=required,
        )
        self.items.append(item)

        if auto_save and spec_dir:
            self.save(spec_dir)

        return item

    def remove_item(
        self,
        item_id: str,
        auto_save: bool = False,
        spec_dir: Path | None = None,
    ) -> bool:
        """
        Remove a checklist item by ID.

        Args:
            item_id: The item ID to remove
            auto_save: Whether to automatically save after removing
            spec_dir: Spec directory path (required if auto_save=True)

        Returns:
            True if item was removed, False if not found
        """
        for i, item in enumerate(self.items):
            if item.id == item_id:
                self.items.pop(i)
                if auto_save and spec_dir:
                    self.save(spec_dir)
                return True
        return False

    def mark_item_complete(
        self,
        item_id: str,
        completed_by: str = "user",
        auto_save: bool = False,
        spec_dir: Path | None = None,
    ) -> bool:
        """
        Mark a checklist item as complete.

        Args:
            item_id: The item ID to mark complete
            completed_by: Who is marking it complete
            auto_save: Whether to automatically save after marking
            spec_dir: Spec directory path (required if auto_save=True)

        Returns:
            True if item was found and marked, False otherwise
        """
        item = self.get_item(item_id)
        if item:
            item.mark_complete(completed_by)
            if auto_save and spec_dir:
                self.save(spec_dir)
            return True
        return False

    def mark_item_incomplete(
        self,
        item_id: str,
        auto_save: bool = False,
        spec_dir: Path | None = None,
    ) -> bool:
        """
        Mark a checklist item as incomplete.

        Args:
            item_id: The item ID to mark incomplete
            auto_save: Whether to automatically save after marking
            spec_dir: Spec directory path (required if auto_save=True)

        Returns:
            True if item was found and marked, False otherwise
        """
        item = self.get_item(item_id)
        if item:
            item.mark_incomplete()
            if auto_save and spec_dir:
                self.save(spec_dir)
            return True
        return False

    def is_complete(self) -> bool:
        """
        Check if all required checklist items are completed.

        Returns:
            True if all required items are completed, False otherwise
        """
        required_items = [item for item in self.items if item.required]
        if not required_items:
            # No required items means checklist is complete
            return True
        return all(item.completed for item in required_items)

    def get_completion_status(self) -> dict:
        """
        Get detailed completion status.

        Returns:
            Dictionary with completion statistics
        """
        total_items = len(self.items)
        required_items = [item for item in self.items if item.required]
        total_required = len(required_items)
        completed_required = sum(1 for item in required_items if item.completed)
        completed_total = sum(1 for item in self.items if item.completed)

        return {
            "total_items": total_items,
            "total_required": total_required,
            "completed_required": completed_required,
            "completed_total": completed_total,
            "is_complete": self.is_complete(),
            "completion_percentage": (
                (completed_total / total_items * 100) if total_items > 0 else 100
            ),
        }

    def reset(self, spec_dir: Path | None = None, auto_save: bool = False) -> None:
        """
        Reset all checklist items to incomplete.

        Args:
            spec_dir: Spec directory path (required if auto_save=True)
            auto_save: Whether to automatically save after reset
        """
        for item in self.items:
            item.mark_incomplete()

        if auto_save and spec_dir:
            self.save(spec_dir)

    @classmethod
    def create_default(cls, spec_dir: Path | None = None) -> "ReviewChecklist":
        """
        Create a checklist with default review items.

        Args:
            spec_dir: Optional spec directory to save to

        Returns:
            ReviewChecklist with default items
        """
        checklist = cls()

        # Default checklist items for code review
        default_items = [
            {
                "id": "code_quality",
                "description": "Code follows project style guidelines and best practices",
                "required": True,
            },
            {
                "id": "tests_pass",
                "description": "All tests pass successfully",
                "required": True,
            },
            {
                "id": "documentation",
                "description": "Code is properly documented with comments and docstrings",
                "required": True,
            },
            {
                "id": "security_review",
                "description": "Security considerations have been reviewed",
                "required": True,
            },
            {
                "id": "performance",
                "description": "Performance impact has been considered",
                "required": False,
            },
        ]

        for item_data in default_items:
            checklist.add_item(
                item_id=item_data["id"],
                description=item_data["description"],
                required=item_data["required"],
            )

        if spec_dir:
            checklist.save(spec_dir)

        return checklist
