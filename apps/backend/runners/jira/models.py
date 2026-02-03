"""
Jira Data Models

Dataclasses for representing Jira entities like issues, users, and statuses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class JiraUser:
    """Represents a Jira user."""

    account_id: str
    display_name: str
    email_address: str | None = None
    avatar_url: str | None = None
    active: bool = True

    @classmethod
    def from_api(cls, data: dict[str, Any] | None) -> JiraUser | None:
        """Create a JiraUser from API response data."""
        if not data:
            return None
        return cls(
            account_id=data.get("accountId", ""),
            display_name=data.get("displayName", "Unknown"),
            email_address=data.get("emailAddress"),
            avatar_url=data.get("avatarUrls", {}).get("48x48"),
            active=data.get("active", True),
        )


@dataclass
class JiraStatus:
    """Represents a Jira issue status."""

    id: str
    name: str
    category: str  # 'todo', 'in_progress', 'done'

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> JiraStatus:
        """Create a JiraStatus from API response data."""
        status_category = data.get("statusCategory", {})
        category_key = status_category.get("key", "undefined")

        # Map Jira status categories to simplified categories
        category_map = {
            "new": "todo",
            "undefined": "todo",
            "indeterminate": "in_progress",
            "done": "done",
        }

        return cls(
            id=data.get("id", ""),
            name=data.get("name", "Unknown"),
            category=category_map.get(category_key, "todo"),
        )


@dataclass
class JiraPriority:
    """Represents a Jira issue priority."""

    id: str
    name: str
    icon_url: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any] | None) -> JiraPriority | None:
        """Create a JiraPriority from API response data."""
        if not data:
            return None
        return cls(
            id=data.get("id", ""),
            name=data.get("name", "None"),
            icon_url=data.get("iconUrl"),
        )


@dataclass
class JiraProject:
    """Represents a Jira project."""

    id: str
    key: str
    name: str
    avatar_url: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> JiraProject:
        """Create a JiraProject from API response data."""
        return cls(
            id=data.get("id", ""),
            key=data.get("key", ""),
            name=data.get("name", ""),
            avatar_url=data.get("avatarUrls", {}).get("48x48"),
        )


@dataclass
class JiraIssue:
    """Represents a Jira issue/ticket."""

    key: str  # e.g., ES-1234
    id: str
    summary: str
    description: str | None
    status: JiraStatus
    story_points: float | None
    assignee: JiraUser | None
    reporter: JiraUser | None
    priority: JiraPriority | None
    labels: list[str]
    project: JiraProject
    issue_type: str
    url: str
    created_at: str
    updated_at: str

    @classmethod
    def from_api(cls, data: dict[str, Any], base_url: str) -> JiraIssue:
        """Create a JiraIssue from API response data."""
        fields = data.get("fields", {})

        # Extract story points - try common custom field names
        story_points = None
        for field_key in ["customfield_10016", "customfield_10021", "storyPoints"]:
            if field_key in fields and fields[field_key] is not None:
                try:
                    story_points = float(fields[field_key])
                    break
                except (TypeError, ValueError):
                    pass

        # Parse description - handle Atlassian Document Format (ADF)
        description = None
        desc_field = fields.get("description")
        if desc_field:
            if isinstance(desc_field, str):
                description = desc_field
            elif isinstance(desc_field, dict):
                # ADF format - extract text content
                description = cls._extract_adf_text(desc_field)

        key = data.get("key", "")

        return cls(
            key=key,
            id=data.get("id", ""),
            summary=fields.get("summary", ""),
            description=description,
            status=JiraStatus.from_api(fields.get("status", {})),
            story_points=story_points,
            assignee=JiraUser.from_api(fields.get("assignee")),
            reporter=JiraUser.from_api(fields.get("reporter")),
            priority=JiraPriority.from_api(fields.get("priority")),
            labels=fields.get("labels", []),
            project=JiraProject.from_api(fields.get("project", {})),
            issue_type=fields.get("issuetype", {}).get("name", "Task"),
            url=f"{base_url}/browse/{key}",
            created_at=fields.get("created", ""),
            updated_at=fields.get("updated", ""),
        )

    @staticmethod
    def _extract_adf_text(adf: dict[str, Any]) -> str:
        """Extract plain text from Atlassian Document Format (ADF)."""
        content = adf.get("content", [])
        text_parts = []

        for block in content:
            if block.get("type") == "paragraph":
                for inline in block.get("content", []):
                    if inline.get("type") == "text":
                        text_parts.append(inline.get("text", ""))
                text_parts.append("\n")
            elif block.get("type") == "bulletList":
                for item in block.get("content", []):
                    if item.get("type") == "listItem":
                        for para in item.get("content", []):
                            for inline in para.get("content", []):
                                if inline.get("type") == "text":
                                    text_parts.append(f"- {inline.get('text', '')}\n")
            elif block.get("type") == "heading":
                for inline in block.get("content", []):
                    if inline.get("type") == "text":
                        text_parts.append(f"## {inline.get('text', '')}\n")

        return "".join(text_parts).strip()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "key": self.key,
            "id": self.id,
            "summary": self.summary,
            "description": self.description,
            "status": {
                "name": self.status.name,
                "category": self.status.category,
            },
            "storyPoints": self.story_points,
            "assignee": {
                "displayName": self.assignee.display_name,
                "avatarUrl": self.assignee.avatar_url,
            }
            if self.assignee
            else None,
            "reporter": {
                "displayName": self.reporter.display_name,
                "avatarUrl": self.reporter.avatar_url,
            }
            if self.reporter
            else None,
            "priority": {
                "name": self.priority.name,
                "iconUrl": self.priority.icon_url,
            }
            if self.priority
            else None,
            "labels": self.labels,
            "project": {
                "key": self.project.key,
                "name": self.project.name,
            },
            "issueType": self.issue_type,
            "url": self.url,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
