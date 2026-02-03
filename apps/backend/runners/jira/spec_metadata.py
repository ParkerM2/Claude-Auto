"""
Jira Spec Metadata
==================

Manages Jira issue metadata stored in spec directories.

This module provides helper functions to save, load, and query Jira issue
metadata from the jira_issue.json file in spec directories. This metadata
links Auto Claude specs to their originating Jira issues for status updates
and PR linking.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JiraSpecMetadata:
    """
    Jira issue metadata stored with an Auto Claude spec.

    This class represents the data stored in .auto-claude/specs/{spec-id}/jira_issue.json
    """

    def __init__(
        self,
        issue_key: str,
        issue_id: str,
        issue_url: str,
        project_key: str,
        imported_at: str | None = None,
        original_status: str | None = None,
    ):
        """
        Initialize Jira spec metadata.

        Args:
            issue_key: Jira issue key (e.g., "ES-1234")
            issue_id: Jira issue ID
            issue_url: Full URL to Jira issue
            project_key: Jira project key (e.g., "ES")
            imported_at: ISO timestamp of when spec was imported
            original_status: Original Jira status when imported
        """
        self.issue_key = issue_key
        self.issue_id = issue_id
        self.issue_url = issue_url
        self.project_key = project_key
        self.imported_at = imported_at or datetime.now().isoformat()
        self.original_status = original_status

    def to_dict(self) -> dict[str, Any]:
        """
        Convert metadata to dictionary for JSON serialization.

        Returns:
            Dictionary representation of metadata
        """
        return {
            "issue_key": self.issue_key,
            "issue_id": self.issue_id,
            "issue_url": self.issue_url,
            "project_key": self.project_key,
            "imported_at": self.imported_at,
            "original_status": self.original_status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JiraSpecMetadata:
        """
        Create metadata instance from dictionary.

        Args:
            data: Dictionary with metadata fields

        Returns:
            JiraSpecMetadata instance
        """
        return cls(
            issue_key=data["issue_key"],
            issue_id=data["issue_id"],
            issue_url=data["issue_url"],
            project_key=data["project_key"],
            imported_at=data.get("imported_at"),
            original_status=data.get("original_status"),
        )


def save_jira_metadata(spec_dir: Path, metadata: JiraSpecMetadata) -> Path:
    """
    Save Jira issue metadata to spec directory.

    Creates or overwrites the jira_issue.json file in the spec directory
    with the provided metadata.

    Args:
        spec_dir: Path to spec directory (e.g., .auto-claude/specs/001-feature)
        metadata: JiraSpecMetadata instance to save

    Returns:
        Path to created jira_issue.json file

    Raises:
        IOError: If file cannot be written
    """
    metadata_file = spec_dir / "jira_issue.json"

    try:
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        logger.debug(
            f"Saved Jira metadata for issue {metadata.issue_key} to {metadata_file}"
        )
        return metadata_file

    except OSError as e:
        logger.error(f"Failed to save Jira metadata to {metadata_file}: {e}")
        raise


def load_jira_metadata(spec_dir: Path) -> JiraSpecMetadata | None:
    """
    Load Jira issue metadata from spec directory.

    Reads the jira_issue.json file from the spec directory if it exists.

    Args:
        spec_dir: Path to spec directory (e.g., .auto-claude/specs/001-feature)

    Returns:
        JiraSpecMetadata if file exists and is valid, None otherwise
    """
    metadata_file = spec_dir / "jira_issue.json"

    if not metadata_file.exists():
        logger.debug(f"No Jira metadata found at {metadata_file}")
        return None

    try:
        with open(metadata_file, encoding="utf-8") as f:
            data = json.load(f)
            metadata = JiraSpecMetadata.from_dict(data)
            logger.debug(f"Loaded Jira metadata for issue {metadata.issue_key}")
            return metadata

    except (OSError, json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to load Jira metadata from {metadata_file}: {e}")
        return None


def get_issue_key(spec_dir: Path) -> str | None:
    """
    Get Jira issue key from spec metadata.

    Convenience function to quickly get just the issue key without
    loading the full metadata object.

    Args:
        spec_dir: Path to spec directory (e.g., .auto-claude/specs/001-feature)

    Returns:
        Jira issue key (e.g., "ES-1234") if found, None otherwise
    """
    metadata = load_jira_metadata(spec_dir)
    return metadata.issue_key if metadata else None


def is_jira_spec(spec_dir: Path) -> bool:
    """
    Check if a spec is linked to a Jira issue.

    Args:
        spec_dir: Path to spec directory (e.g., .auto-claude/specs/001-feature)

    Returns:
        True if spec has Jira metadata, False otherwise
    """
    metadata_file = spec_dir / "jira_issue.json"
    return metadata_file.exists()


def update_jira_metadata(
    spec_dir: Path,
    **updates: Any,
) -> JiraSpecMetadata | None:
    """
    Update specific fields in Jira metadata.

    Loads existing metadata, updates specified fields, and saves back to disk.

    Args:
        spec_dir: Path to spec directory
        **updates: Keyword arguments with fields to update

    Returns:
        Updated JiraSpecMetadata if successful, None otherwise

    Example:
        update_jira_metadata(spec_dir, original_status="In Progress")
    """
    metadata = load_jira_metadata(spec_dir)
    if not metadata:
        logger.warning(f"Cannot update metadata: no Jira metadata found in {spec_dir}")
        return None

    # Update fields
    for key, value in updates.items():
        if hasattr(metadata, key):
            setattr(metadata, key, value)
        else:
            logger.warning(f"Ignoring unknown metadata field: {key}")

    # Save updated metadata
    save_jira_metadata(spec_dir, metadata)
    return metadata
