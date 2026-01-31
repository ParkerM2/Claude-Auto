"""
Jira Spec Importer
==================

Converts Jira issues to Auto Claude spec.md format.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import JiraIssue
from .spec_metadata import JiraSpecMetadata, save_jira_metadata


class JiraSpecImporter:
    """
    Converts Jira issues to Auto Claude spec format.

    Usage:
        importer = JiraSpecImporter(specs_dir=Path(".auto-claude/specs"))
        spec_dir = await importer.import_issue(jira_issue, spec_name="001-feature")
    """

    def __init__(self, specs_dir: Path):
        """
        Initialize the spec importer.

        Args:
            specs_dir: Directory to create specs in (e.g., .auto-claude/specs/)
        """
        self.specs_dir = Path(specs_dir)

    def import_issue(
        self, issue: JiraIssue, spec_name: str | None = None
    ) -> Path:
        """
        Import a Jira issue as an Auto Claude spec.

        Args:
            issue: JiraIssue object to import
            spec_name: Optional spec name (e.g., "001-feature"). If None,
                      generates from issue key

        Returns:
            Path to created spec directory

        Raises:
            ValueError: If spec directory already exists
        """
        # Generate spec name from issue key if not provided
        if not spec_name:
            spec_name = self._generate_spec_name(issue)

        # Create spec directory
        spec_dir = self.specs_dir / spec_name
        if spec_dir.exists():
            raise ValueError(
                f"Spec directory already exists: {spec_dir}. "
                "Choose a different spec name."
            )

        spec_dir.mkdir(parents=True, exist_ok=False)

        # Create spec.md
        self._create_spec_md(spec_dir, issue)

        # Create requirements.json
        self._create_requirements_json(spec_dir, issue)

        # Create jira_issue.json (metadata linking spec to Jira)
        self._create_jira_metadata(spec_dir, issue)

        return spec_dir

    def _generate_spec_name(self, issue: JiraIssue) -> str:
        """
        Generate spec name from issue key.

        Args:
            issue: JiraIssue object

        Returns:
            Spec name (e.g., "ES-1234-feature-name")
        """
        # Sanitize summary for use in directory name
        sanitized_summary = issue.summary.lower()
        # Replace spaces and special chars with hyphens
        sanitized_summary = "".join(
            c if c.isalnum() or c in (" ", "-") else "" for c in sanitized_summary
        )
        sanitized_summary = "-".join(sanitized_summary.split())
        # Limit length
        if len(sanitized_summary) > 40:
            sanitized_summary = sanitized_summary[:40].rstrip("-")

        return f"{issue.key.lower()}-{sanitized_summary}"

    def _create_spec_md(self, spec_dir: Path, issue: JiraIssue) -> Path:
        """
        Create spec.md file from Jira issue.

        Args:
            spec_dir: Spec directory path
            issue: JiraIssue object

        Returns:
            Path to created spec.md file
        """
        spec_file = spec_dir / "spec.md"

        # Build spec content
        content_parts = [
            f"# {issue.summary}",
            "",
            self._format_description(issue),
            "",
        ]

        # Add issue metadata section
        content_parts.extend([
            "## Issue Details",
            "",
            f"- **Jira Issue:** [{issue.key}]({issue.url})",
            f"- **Type:** {issue.issue_type}",
            f"- **Status:** {issue.status.name}",
            f"- **Priority:** {issue.priority.name if issue.priority else 'None'}",
        ])

        if issue.story_points:
            content_parts.append(f"- **Story Points:** {issue.story_points}")

        if issue.assignee:
            content_parts.append(f"- **Assignee:** {issue.assignee.display_name}")

        if issue.labels:
            content_parts.append(f"- **Labels:** {', '.join(issue.labels)}")

        content_parts.extend(["", ""])

        # Extract acceptance criteria from description if present
        acceptance_criteria = self._extract_acceptance_criteria(issue)
        if acceptance_criteria:
            content_parts.extend([
                "## Acceptance Criteria",
                "",
                *acceptance_criteria,
                "",
            ])

        # Write spec file
        with open(spec_file, "w", encoding="utf-8") as f:
            f.write("\n".join(content_parts))

        return spec_file

    def _format_description(self, issue: JiraIssue) -> str:
        """
        Format issue description for spec.md.

        Args:
            issue: JiraIssue object

        Returns:
            Formatted description text
        """
        if not issue.description:
            return "No description provided."

        # Remove acceptance criteria section if present (we extract it separately)
        description = issue.description
        lines = description.split("\n")
        filtered_lines = []
        in_acceptance_criteria = False

        for line in lines:
            lower_line = line.lower().strip()
            if any(
                marker in lower_line
                for marker in [
                    "acceptance criteria",
                    "acceptance criterion",
                    "definition of done",
                ]
            ):
                in_acceptance_criteria = True
                continue
            if in_acceptance_criteria and line.strip().startswith(("- ", "* ", "• ")):
                continue
            if in_acceptance_criteria and not line.strip():
                in_acceptance_criteria = False
                continue

            if not in_acceptance_criteria:
                filtered_lines.append(line)

        return "\n".join(filtered_lines).strip()

    def _extract_acceptance_criteria(self, issue: JiraIssue) -> list[str]:
        """
        Extract acceptance criteria from issue description.

        Args:
            issue: JiraIssue object

        Returns:
            List of acceptance criteria lines
        """
        if not issue.description:
            return []

        lines = issue.description.split("\n")
        criteria = []
        in_criteria_section = False

        for line in lines:
            lower_line = line.lower().strip()

            # Check if we're entering acceptance criteria section
            if any(
                marker in lower_line
                for marker in [
                    "acceptance criteria",
                    "acceptance criterion",
                    "definition of done",
                ]
            ):
                in_criteria_section = True
                continue

            # If we're in the section, collect bullet points
            if in_criteria_section:
                stripped = line.strip()
                if stripped.startswith(("- ", "* ", "• ")):
                    # Convert to markdown checkbox format
                    text = stripped[2:].strip()
                    criteria.append(f"- [ ] {text}")
                elif not stripped:
                    # Empty line ends the section
                    break

        return criteria

    def _create_requirements_json(self, spec_dir: Path, issue: JiraIssue) -> Path:
        """
        Create requirements.json from Jira issue.

        Args:
            spec_dir: Spec directory path
            issue: JiraIssue object

        Returns:
            Path to created requirements.json file
        """
        requirements_file = spec_dir / "requirements.json"

        # Determine workflow type from issue type
        workflow_map = {
            "Bug": "bugfix",
            "Story": "feature",
            "Task": "feature",
            "Epic": "feature",
            "Improvement": "refactor",
            "Sub-task": "feature",
        }
        workflow_type = workflow_map.get(issue.issue_type, "feature")

        requirements = {
            "task_description": issue.summary,
            "workflow_type": workflow_type,
            "services_involved": [],  # AI will discover during planning
            "additional_context": issue.description,
            "created_at": datetime.now().isoformat(),
            "imported_from_jira": True,
            "jira_issue_key": issue.key,
        }

        with open(requirements_file, "w", encoding="utf-8") as f:
            json.dump(requirements, f, indent=2)

        return requirements_file

    def _create_jira_metadata(self, spec_dir: Path, issue: JiraIssue) -> Path:
        """
        Create jira_issue.json metadata file.

        This file stores the link between the spec and the Jira issue,
        allowing status updates and PR linking later.

        Args:
            spec_dir: Spec directory path
            issue: JiraIssue object

        Returns:
            Path to created jira_issue.json file
        """
        metadata = JiraSpecMetadata(
            issue_key=issue.key,
            issue_id=issue.id,
            issue_url=issue.url,
            project_key=issue.project.key,
            imported_at=datetime.now().isoformat(),
            original_status=issue.status.name,
        )

        return save_jira_metadata(spec_dir, metadata)
