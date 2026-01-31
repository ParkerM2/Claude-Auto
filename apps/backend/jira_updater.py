"""
Jira Updater
============

Provides helper functions to update Jira ticket status based on Auto Claude task lifecycle.

This module wraps the JiraStatusUpdater class to provide simple functions that can be
called from the coder agent at key lifecycle events (task started, completed, failed).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from runners.jira.jira_client import JiraClient, JiraApiError
from runners.jira.models import JiraConfig
from runners.jira.status_updater import JiraStatusUpdater

logger = logging.getLogger(__name__)


def is_jira_enabled() -> bool:
    """
    Check if Jira integration is enabled via environment variables.

    Returns:
        True if Jira is configured, False otherwise
    """
    required_vars = ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"]
    return all(os.getenv(var) for var in required_vars)


def _get_jira_config() -> JiraConfig | None:
    """
    Get Jira configuration from environment variables.

    Returns:
        JiraConfig if all required env vars are set, None otherwise
    """
    if not is_jira_enabled():
        return None

    return JiraConfig(
        base_url=os.getenv("JIRA_BASE_URL", ""),
        email=os.getenv("JIRA_EMAIL", ""),
        api_token=os.getenv("JIRA_API_TOKEN", ""),
        project_key=os.getenv("JIRA_PROJECT_KEY"),
    )


def _get_jira_updater() -> JiraStatusUpdater | None:
    """
    Create a JiraStatusUpdater instance.

    Returns:
        JiraStatusUpdater if Jira is enabled, None otherwise
    """
    config = _get_jira_config()
    if not config:
        return None

    client = JiraClient(config)
    return JiraStatusUpdater(client)


async def jira_task_started(spec_dir: Path) -> bool:
    """
    Update Jira ticket status to "In Progress" when Auto Claude task starts.

    Args:
        spec_dir: Path to spec directory (e.g., .auto-claude/specs/001-feature)

    Returns:
        True if status updated successfully, False otherwise
    """
    if not is_jira_enabled():
        logger.debug("Jira integration not enabled, skipping status update")
        return False

    updater = _get_jira_updater()
    if not updater:
        logger.warning("Failed to create Jira updater")
        return False

    # Get issue key from spec metadata
    issue_key = updater.get_issue_key_from_spec(spec_dir)
    if not issue_key:
        logger.debug(f"No Jira issue associated with spec {spec_dir.name}")
        return False

    try:
        logger.info(f"Updating Jira issue {issue_key} status to 'In Progress'")
        return await updater.on_task_started(issue_key)
    except JiraApiError as e:
        logger.error(f"Failed to update Jira issue {issue_key} status: {e}")
        return False


async def jira_build_complete(spec_dir: Path) -> bool:
    """
    Update Jira ticket status to "Done" when Auto Claude build completes.

    Args:
        spec_dir: Path to spec directory (e.g., .auto-claude/specs/001-feature)

    Returns:
        True if status updated successfully, False otherwise
    """
    if not is_jira_enabled():
        logger.debug("Jira integration not enabled, skipping status update")
        return False

    updater = _get_jira_updater()
    if not updater:
        logger.warning("Failed to create Jira updater")
        return False

    # Get issue key from spec metadata
    issue_key = updater.get_issue_key_from_spec(spec_dir)
    if not issue_key:
        logger.debug(f"No Jira issue associated with spec {spec_dir.name}")
        return False

    try:
        logger.info(f"Updating Jira issue {issue_key} status to 'Done'")
        return await updater.on_task_completed(issue_key)
    except JiraApiError as e:
        logger.error(f"Failed to update Jira issue {issue_key} status: {e}")
        return False


async def jira_task_stuck(
    spec_dir: Path,
    subtask_id: str,
    attempt_count: int,
) -> bool:
    """
    Update Jira ticket status to "To Do" when Auto Claude task gets stuck.

    This reverts the issue back to "To Do" status so the work can be retried or
    reassigned. Also adds a comment to the Jira issue with details about the failure.

    Args:
        spec_dir: Path to spec directory (e.g., .auto-claude/specs/001-feature)
        subtask_id: ID of the stuck subtask
        attempt_count: Number of failed attempts

    Returns:
        True if status updated successfully, False otherwise
    """
    if not is_jira_enabled():
        logger.debug("Jira integration not enabled, skipping status update")
        return False

    updater = _get_jira_updater()
    if not updater:
        logger.warning("Failed to create Jira updater")
        return False

    # Get issue key from spec metadata
    issue_key = updater.get_issue_key_from_spec(spec_dir)
    if not issue_key:
        logger.debug(f"No Jira issue associated with spec {spec_dir.name}")
        return False

    try:
        logger.warning(
            f"Auto Claude subtask {subtask_id} is stuck after {attempt_count} attempts. "
            f"Reverting Jira issue {issue_key} to 'To Do'"
        )
        return await updater.on_task_failed(issue_key)
    except JiraApiError as e:
        logger.error(f"Failed to update Jira issue {issue_key} status: {e}")
        return False
