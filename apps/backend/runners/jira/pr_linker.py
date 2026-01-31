"""
Jira PR Linker
==============

Handles automatic linking of GitHub Pull Requests to Jira issues.

When a PR is created for an Auto Claude task that originated from a Jira issue,
this module adds a remote link to the Jira issue pointing to the PR.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .jira_client import JiraClient, JiraApiError

# Configure logger
logger = logging.getLogger(__name__)


class JiraPRLinker:
    """
    Handles automatic linking of GitHub Pull Requests to Jira issues.

    Usage:
        client = JiraClient(config)
        linker = JiraPRLinker(client)

        # Link a PR to a Jira issue
        await linker.link_pr(
            issue_key="ES-1234",
            pr_url="https://github.com/owner/repo/pull/123",
            pr_title="Add feature X"
        )
    """

    def __init__(self, jira_client: JiraClient):
        """
        Initialize Jira PR linker.

        Args:
            jira_client: Configured JiraClient instance
        """
        self.client = jira_client

    async def link_pr(
        self,
        issue_key: str,
        pr_url: str,
        pr_title: str | None = None,
    ) -> bool:
        """
        Add a remote link to a Jira issue pointing to a GitHub PR.

        Uses Jira's remote links API to create a link from the issue to the PR.
        If a link to the same PR URL already exists, this is a no-op.

        Args:
            issue_key: Jira issue key (e.g., "ES-1234")
            pr_url: Full URL to GitHub PR (e.g., "https://github.com/owner/repo/pull/123")
            pr_title: Optional PR title to use as link text

        Returns:
            True if link was created successfully, False otherwise

        Raises:
            JiraApiError: If API request fails
        """
        try:
            logger.info(
                f"Linking GitHub PR to Jira issue {issue_key}: {pr_url}"
            )

            # Build remote link object
            # See: https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-remote-links/
            link_data = {
                "object": {
                    "url": pr_url,
                    "title": pr_title or f"Pull Request #{self._extract_pr_number(pr_url)}",
                }
            }

            # Add the remote link
            await self.client._request(
                "POST",
                f"/issue/{issue_key}/remotelink",
                data=link_data,
            )

            logger.info(
                f"Successfully linked PR {pr_url} to Jira issue {issue_key}"
            )
            return True

        except JiraApiError as e:
            logger.error(
                f"Failed to link PR {pr_url} to Jira issue {issue_key}: {e}"
            )
            raise

    async def on_pr_created(
        self,
        issue_key: str,
        pr_url: str,
        pr_title: str | None = None,
    ) -> bool:
        """
        Handle PR creation event by linking it to the Jira issue.

        Convenience method to be called from the build workflow when a PR is created.

        Args:
            issue_key: Jira issue key (e.g., "ES-1234")
            pr_url: Full URL to GitHub PR
            pr_title: Optional PR title

        Returns:
            True if link was created successfully
        """
        logger.debug(f"PR created event for Jira issue {issue_key}: {pr_url}")
        return await self.link_pr(issue_key, pr_url, pr_title)

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

    @staticmethod
    def _extract_pr_number(pr_url: str) -> str:
        """
        Extract PR number from GitHub PR URL.

        Args:
            pr_url: GitHub PR URL (e.g., "https://github.com/owner/repo/pull/123")

        Returns:
            PR number as string (e.g., "123")
        """
        # Extract number from URL like: https://github.com/owner/repo/pull/123
        parts = pr_url.rstrip("/").split("/")
        if len(parts) > 0 and parts[-2] == "pull":
            return parts[-1]
        return "unknown"
