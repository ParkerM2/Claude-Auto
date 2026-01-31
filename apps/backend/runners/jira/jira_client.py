"""
Jira REST API Client with Timeout and Retry Logic
==================================================

Async client for Jira Cloud REST API that provides:
- Basic authentication with email + API token
- Configurable timeouts (default 30s)
- Exponential backoff retry (3 attempts)
- Structured error handling

Authentication uses Jira Cloud's standard Basic auth:
  - Email: Your Atlassian account email
  - API Token: Generated at https://id.atlassian.com/manage-profile/security/api-tokens
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp

from .models import JiraIssue, JiraUser, JiraProject
from .spec_importer import JiraSpecImporter

# Configure logger
logger = logging.getLogger(__name__)


class JiraTimeoutError(Exception):
    """Raised when Jira API request times out after all retry attempts."""

    pass


class JiraAuthError(Exception):
    """Raised when authentication fails (invalid credentials)."""

    pass


class JiraApiError(Exception):
    """Raised when Jira API returns an error."""

    pass


@dataclass
class JiraConfig:
    """Configuration for Jira client."""

    base_url: str  # e.g., https://company.atlassian.net
    email: str
    api_token: str
    project_key: str | None = None  # e.g., ES


class JiraClient:
    """
    Async client for Jira Cloud REST API.

    Usage:
        config = JiraConfig(
            base_url="https://company.atlassian.net",
            email="user@company.com",
            api_token="your-api-token",
            project_key="ES"
        )
        client = JiraClient(config)

        # Get current user
        user = await client.get_current_user()

        # Get issues assigned to current user
        issues = await client.get_my_issues()

        # Get specific issue
        issue = await client.get_issue("ES-1234")
    """

    def __init__(
        self,
        config: JiraConfig,
        default_timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize Jira client.

        Args:
            config: Jira configuration with credentials
            default_timeout: Default timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.config = config
        self.default_timeout = default_timeout
        self.max_retries = max_retries

        # Build auth header
        credentials = f"{config.email}:{config.api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self._auth_header = f"Basic {encoded}"

        # API base URL
        self._api_url = f"{config.base_url.rstrip('/')}/rest/api/3"

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Make an authenticated request to Jira API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., /myself)
            params: Query parameters
            data: Request body data
            timeout: Request timeout in seconds

        Returns:
            JSON response data

        Raises:
            JiraTimeoutError: If request times out
            JiraAuthError: If authentication fails
            JiraApiError: If API returns an error
        """
        timeout = timeout or self.default_timeout
        url = f"{self._api_url}{endpoint}"

        headers = {
            "Authorization": self._auth_header,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(
                    f"Jira API request (attempt {attempt}/{self.max_retries}): "
                    f"{method} {endpoint}"
                )

                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method,
                        url,
                        headers=headers,
                        params=params,
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=timeout),
                    ) as response:
                        response_text = await response.text()

                        # Handle authentication errors
                        if response.status == 401:
                            raise JiraAuthError(
                                "Authentication failed. Check your email and API token."
                            )
                        if response.status == 403:
                            raise JiraAuthError(
                                "Access forbidden. Check your permissions."
                            )

                        # Handle other errors
                        if response.status >= 400:
                            error_msg = response_text
                            try:
                                error_data = json.loads(response_text)
                                if "errorMessages" in error_data:
                                    error_msg = "; ".join(error_data["errorMessages"])
                                elif "message" in error_data:
                                    error_msg = error_data["message"]
                            except json.JSONDecodeError:
                                pass
                            raise JiraApiError(
                                f"Jira API error ({response.status}): {error_msg}"
                            )

                        # Parse successful response
                        if response_text:
                            return json.loads(response_text)
                        return {}

            except asyncio.TimeoutError:
                backoff_delay = 2 ** (attempt - 1)
                logger.warning(
                    f"Jira API request timed out after {timeout}s "
                    f"(attempt {attempt}/{self.max_retries})"
                )

                if attempt < self.max_retries:
                    logger.info(f"Retrying in {backoff_delay}s...")
                    await asyncio.sleep(backoff_delay)
                    continue
                else:
                    raise JiraTimeoutError(
                        f"Jira API request timed out after {self.max_retries} attempts"
                    )

            except (JiraAuthError, JiraApiError):
                # Don't retry auth or API errors
                raise

            except aiohttp.ClientError as e:
                backoff_delay = 2 ** (attempt - 1)
                logger.warning(f"Jira API connection error: {e}")

                if attempt < self.max_retries:
                    logger.info(f"Retrying in {backoff_delay}s...")
                    await asyncio.sleep(backoff_delay)
                    continue
                else:
                    raise JiraApiError(f"Connection error: {e}")

        # Should never reach here
        raise JiraApiError("Unexpected error in Jira client")

    async def get_current_user(self) -> JiraUser:
        """
        Get the currently authenticated user.

        Returns:
            JiraUser representing the authenticated user
        """
        data = await self._request("GET", "/myself")
        user = JiraUser.from_api(data)
        if not user:
            raise JiraApiError("Failed to parse user data")
        return user

    async def get_issue(self, issue_key: str) -> JiraIssue:
        """
        Get a single issue by its key.

        Args:
            issue_key: Issue key (e.g., ES-1234)

        Returns:
            JiraIssue object
        """
        data = await self._request(
            "GET",
            f"/issue/{issue_key}",
            params={
                "fields": "summary,description,status,priority,assignee,reporter,"
                "labels,project,issuetype,created,updated,"
                "customfield_10016,customfield_10021"  # Story points
            },
        )
        return JiraIssue.from_api(data, self.config.base_url)

    async def get_my_issues(
        self,
        project_key: str | None = None,
        max_results: int = 50,
    ) -> list[JiraIssue]:
        """
        Get issues assigned to the current user.

        Args:
            project_key: Optional project key to filter by (defaults to config)
            max_results: Maximum number of results

        Returns:
            List of JiraIssue objects
        """
        project = project_key or self.config.project_key

        # Build JQL query
        jql_parts = ["assignee = currentUser()"]
        if project:
            jql_parts.append(f"project = {project}")
        jql_parts.append("ORDER BY updated DESC")

        jql = " AND ".join(jql_parts[:2]) + " " + jql_parts[2]

        return await self.search_issues(jql, max_results)

    async def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        start_at: int = 0,
    ) -> list[JiraIssue]:
        """
        Search for issues using JQL.

        Args:
            jql: JQL query string
            max_results: Maximum number of results per page
            start_at: Starting index for pagination

        Returns:
            List of JiraIssue objects
        """
        data = await self._request(
            "GET",
            "/search",
            params={
                "jql": jql,
                "maxResults": max_results,
                "startAt": start_at,
                "fields": "summary,description,status,priority,assignee,reporter,"
                "labels,project,issuetype,created,updated,"
                "customfield_10016,customfield_10021",  # Story points
            },
        )

        issues = []
        for issue_data in data.get("issues", []):
            issues.append(JiraIssue.from_api(issue_data, self.config.base_url))

        return issues

    async def get_project(self, project_key: str) -> JiraProject:
        """
        Get project details by key.

        Args:
            project_key: Project key (e.g., ES)

        Returns:
            JiraProject object
        """
        data = await self._request("GET", f"/project/{project_key}")
        return JiraProject.from_api(data)

    async def test_connection(self) -> dict[str, Any]:
        """
        Test the connection and return status info.

        Returns:
            Dict with connection status
        """
        try:
            user = await self.get_current_user()
            return {
                "connected": True,
                "user": user.display_name,
                "email": user.email_address,
            }
        except JiraAuthError as e:
            return {
                "connected": False,
                "error": str(e),
            }
        except Exception as e:
            return {
                "connected": False,
                "error": f"Connection failed: {e}",
            }

    async def update_status(
        self,
        issue_key: str,
        target_status: str,
    ) -> bool:
        """
        Update the status of a Jira issue by transitioning to a new status.

        Finds the appropriate transition ID for the target status and executes it.
        If multiple transitions lead to the same status, uses the first match.

        Args:
            issue_key: Jira issue key (e.g., "ES-1234")
            target_status: Target status name (e.g., "In Progress", "Done")

        Returns:
            True if status transition was successful

        Raises:
            JiraApiError: If transition fails or target status is not available
        """
        # Get available transitions for this issue
        logger.debug(f"Fetching available transitions for issue {issue_key}")
        transitions_data = await self._request(
            "GET",
            f"/issue/{issue_key}/transitions",
        )

        transitions = transitions_data.get("transitions", [])
        if not transitions:
            raise JiraApiError(
                f"No transitions available for issue {issue_key}. "
                "The issue may be in a terminal state or you lack permissions."
            )

        # Find transition ID for target status
        # Match case-insensitively for better UX
        target_status_lower = target_status.lower()
        transition_id = None

        for transition in transitions:
            to_status = transition.get("to", {}).get("name", "")
            if to_status.lower() == target_status_lower:
                transition_id = transition.get("id")
                logger.debug(
                    f"Found transition ID {transition_id} for status '{to_status}'"
                )
                break

        if not transition_id:
            available_statuses = [
                t.get("to", {}).get("name", "Unknown") for t in transitions
            ]
            raise JiraApiError(
                f"Status '{target_status}' is not available for issue {issue_key}. "
                f"Available transitions: {', '.join(available_statuses)}"
            )

        # Execute the transition
        logger.info(
            f"Transitioning issue {issue_key} to status '{target_status}' "
            f"(transition ID: {transition_id})"
        )
        await self._request(
            "POST",
            f"/issue/{issue_key}/transitions",
            data={"transition": {"id": transition_id}},
        )

        logger.info(f"Successfully transitioned issue {issue_key} to '{target_status}'")
        return True

    async def link_pr(
        self,
        issue_key: str,
        pr_url: str,
        pr_title: str,
    ) -> dict[str, Any]:
        """
        Add a remote link to a Pull Request on a Jira issue.

        Creates a remote link on the issue pointing to the PR URL,
        making it easy to navigate between Jira and GitHub.

        Args:
            issue_key: Jira issue key (e.g., "ES-1234")
            pr_url: Full URL of the pull request
            pr_title: Title/description of the pull request

        Returns:
            Dict containing the created remote link data

        Raises:
            JiraApiError: If link creation fails
        """
        logger.info(f"Adding PR link to issue {issue_key}: {pr_url}")

        # Build remote link payload
        # Follows Jira Cloud REST API v3 remote link schema
        payload = {
            "object": {
                "url": pr_url,
                "title": pr_title,
            }
        }

        # Create the remote link
        response = await self._request(
            "POST",
            f"/issue/{issue_key}/remotelink",
            data=payload,
        )

        logger.info(f"Successfully linked PR to issue {issue_key}")
        return response

    async def import_issue(
        self,
        issue_key: str,
        specs_dir: Path,
        spec_name: str | None = None,
    ) -> Path:
        """
        Import a Jira issue as an Auto Claude spec.

        Fetches the issue from Jira and creates a spec directory with:
        - spec.md (formatted issue content)
        - requirements.json (structured requirements)
        - jira_issue.json (metadata linking spec to Jira)

        Args:
            issue_key: Jira issue key (e.g., "ES-1234")
            specs_dir: Directory to create specs in (e.g., Path(".auto-claude/specs"))
            spec_name: Optional spec name (e.g., "001-feature"). If None,
                      generates from issue key

        Returns:
            Path to created spec directory

        Raises:
            JiraApiError: If issue fetch fails
            ValueError: If spec directory already exists
        """
        # Fetch the issue from Jira
        issue = await self.get_issue(issue_key)

        # Use JiraSpecImporter to create the spec
        importer = JiraSpecImporter(specs_dir)
        spec_dir = importer.import_issue(issue, spec_name)

        logger.info(f"Successfully imported Jira issue {issue_key} to {spec_dir}")
        return spec_dir
