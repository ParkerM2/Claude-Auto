"""
Jira Integration Module

Provides async Jira REST API client for fetching issues, users, and projects.
"""

from .jira_client import JiraClient, JiraTimeoutError, JiraAuthError, JiraApiError
from .models import JiraIssue, JiraUser, JiraStatus, JiraProject

__all__ = [
    "JiraClient",
    "JiraTimeoutError",
    "JiraAuthError",
    "JiraApiError",
    "JiraIssue",
    "JiraUser",
    "JiraStatus",
    "JiraProject",
]
