"""
Jira Status Updater
===================

Handles automatic Jira ticket status updates based on Auto Claude task progress.

Maps Auto Claude task lifecycle events to Jira status transitions:
- Task started → "In Progress"
- Task completed → "Done"
- Task failed → "To Do" (reverted)
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Any

from .jira_client import JiraClient, JiraApiError

# Configure logger
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Auto Claude task status states."""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class JiraStatusUpdater:
    """
    Handles automatic Jira ticket status updates based on Auto Claude task progress.

    Usage:
        client = JiraClient(config)
        updater = JiraStatusUpdater(client)

        # Update status when task starts
        await updater.on_task_started("ES-1234")

        # Update status when task completes
        await updater.on_task_completed("ES-1234")

        # Revert status if task fails
        await updater.on_task_failed("ES-1234")
    """

    # Default status transition mapping
    # Maps Auto Claude task states to Jira status names
    DEFAULT_STATUS_MAP = {
        TaskStatus.STARTED: "In Progress",
        TaskStatus.COMPLETED: "Done",
        TaskStatus.FAILED: "To Do",
    }

    def __init__(
        self,
        jira_client: JiraClient,
        status_map: dict[TaskStatus, str] | None = None,
    ):
        """
        Initialize Jira status updater.

        Args:
            jira_client: Configured JiraClient instance
            status_map: Optional custom status mapping (defaults to DEFAULT_STATUS_MAP)
        """
        self.client = jira_client
        self.status_map = status_map or self.DEFAULT_STATUS_MAP

    async def update_status(
        self,
        issue_key: str,
        task_status: TaskStatus,
    ) -> bool:
        """
        Update Jira issue status based on Auto Claude task status.

        Args:
            issue_key: Jira issue key (e.g., "ES-1234")
            task_status: Auto Claude task status

        Returns:
            True if status updated successfully, False otherwise

        Raises:
            JiraApiError: If API request fails
        """
        target_status = self.status_map.get(task_status)
        if not target_status:
            logger.warning(
                f"No status mapping for task status: {task_status}. "
                "Using default mapping."
            )
            target_status = self.DEFAULT_STATUS_MAP.get(task_status)
            if not target_status:
                raise ValueError(f"Unknown task status: {task_status}")

        try:
            logger.info(
                f"Updating Jira issue {issue_key} status to '{target_status}' "
                f"(task status: {task_status.value})"
            )

            # Call JiraClient.update_status() to perform the transition
            await self.client.update_status(issue_key, target_status)

            return True

        except JiraApiError as e:
            logger.error(f"Failed to update Jira issue {issue_key} status: {e}")
            raise

    async def on_task_started(self, issue_key: str) -> bool:
        """
        Update Jira status when Auto Claude task starts.

        Args:
            issue_key: Jira issue key (e.g., "ES-1234")

        Returns:
            True if status updated successfully
        """
        logger.debug(f"Task started event for Jira issue {issue_key}")
        return await self.update_status(issue_key, TaskStatus.STARTED)

    async def on_task_completed(self, issue_key: str) -> bool:
        """
        Update Jira status when Auto Claude task completes.

        Args:
            issue_key: Jira issue key (e.g., "ES-1234")

        Returns:
            True if status updated successfully
        """
        logger.debug(f"Task completed event for Jira issue {issue_key}")
        return await self.update_status(issue_key, TaskStatus.COMPLETED)

    async def on_task_failed(self, issue_key: str) -> bool:
        """
        Update Jira status when Auto Claude task fails.

        Reverts the issue to "To Do" status so work can be retried.

        Args:
            issue_key: Jira issue key (e.g., "ES-1234")

        Returns:
            True if status updated successfully
        """
        logger.debug(f"Task failed event for Jira issue {issue_key}")
        return await self.update_status(issue_key, TaskStatus.FAILED)

    def get_issue_key_from_spec(self, spec_dir: Path) -> str | None:
        """
        Extract Jira issue key from spec metadata.

        Reads the jira_issue.json file created during spec import
        to get the associated Jira issue key.

        Args:
            spec_dir: Path to spec directory (e.g., .auto-claude/specs/001-feature)

        Returns:
            Jira issue key if found, None otherwise
        """
        from .spec_metadata import get_issue_key

        return get_issue_key(spec_dir)
