"""
Base Analyzer Module
====================

Provides common constants, utilities, and base functionality shared across all analyzers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..context_selector import ContextSelector

# Directories to skip during analysis
SKIP_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".env",
    "env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "target",
    "vendor",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    "coverage",
    ".coverage",
    "htmlcov",
    "eggs",
    "*.egg-info",
    ".turbo",
    ".cache",
    ".worktrees",  # Skip git worktrees directory
    ".auto-claude",  # Skip auto-claude metadata directory
}

# Common service directory names
SERVICE_INDICATORS = {
    "backend",
    "frontend",
    "api",
    "web",
    "app",
    "server",
    "client",
    "worker",
    "workers",
    "services",
    "packages",
    "apps",
    "libs",
    "scraper",
    "crawler",
    "proxy",
    "gateway",
    "admin",
    "dashboard",
    "mobile",
    "desktop",
    "cli",
    "sdk",
    "core",
    "shared",
    "common",
}

# Files that indicate a service root
SERVICE_ROOT_FILES = {
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "Gemfile",
    "composer.json",
    "pom.xml",
    "build.gradle",
    "Makefile",
    "Dockerfile",
}


class BaseAnalyzer:
    """Base class with common utilities for all analyzers."""

    def __init__(self, path: Path):
        self.path = path.resolve()
        self._context_selector_instance: ContextSelector | None = None

    def _exists(self, path: str) -> bool:
        """Check if a file exists relative to the analyzer's path."""
        return (self.path / path).exists()

    def _read_file(self, path: str) -> str:
        """Read a file relative to the analyzer's path."""
        try:
            return (self.path / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""

    def _read_json(self, path: str) -> dict | None:
        """Read and parse a JSON file relative to the analyzer's path."""
        content = self._read_file(path)
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None
        return None

    def _infer_env_var_type(self, value: str) -> str:
        """Infer the type of an environment variable from its value."""
        if not value:
            return "string"

        # Boolean
        if value.lower() in ["true", "false", "1", "0", "yes", "no"]:
            return "boolean"

        # Number
        if value.isdigit():
            return "number"

        # URL
        if value.startswith(
            (
                "http://",
                "https://",
                "postgres://",
                "postgresql://",
                "mysql://",
                "mongodb://",
                "redis://",
            )
        ):
            return "url"

        # Email
        if "@" in value and "." in value:
            return "email"

        # Path
        if "/" in value or "\\" in value:
            return "path"

        return "string"

    @property
    def _context_selector(self) -> ContextSelector:
        """
        Lazy-loaded ContextSelector instance.

        Returns:
            ContextSelector instance for this analyzer's path
        """
        if self._context_selector_instance is None:
            # Import here to avoid circular dependency
            from ..context_selector import ContextSelector

            self._context_selector_instance = ContextSelector(self.path)
        return self._context_selector_instance

    def score_file_relevance(self, file_path: str, task_description: str) -> float:
        """
        Score a file's relevance to a task description.

        Args:
            file_path: Relative or absolute path to the file
            task_description: Description of the task to match against

        Returns:
            Relevance score from 0.0 (not relevant) to 1.0 (highly relevant)
        """
        return self._context_selector.score_relevance(file_path, task_description)

    def select_relevant_files(
        self,
        task_description: str,
        max_files: int | None = None,
        max_tokens: int | None = None,
        min_score: float = 0.0,
    ) -> list[str]:
        """
        Select most relevant files based on task description.

        Args:
            task_description: Description of the task to match against
            max_files: Maximum number of files to return (None for unlimited)
            max_tokens: Maximum total tokens across all files (None for unlimited)
            min_score: Minimum relevance score threshold (0.0 to 1.0)

        Returns:
            List of file paths sorted by relevance (highest first)
        """
        return self._context_selector.select_files(
            task_description=task_description,
            max_files=max_files,
            max_tokens=max_tokens,
            min_score=min_score,
        )

    def estimate_file_tokens(self, file_path: str) -> int:
        """
        Estimate the number of tokens in a file.

        Args:
            file_path: Relative or absolute path to the file

        Returns:
            Estimated token count (0 for unreadable files)
        """
        target = Path(file_path)
        if not target.is_absolute():
            target = self.path / target
        return self._context_selector.estimate_tokens(target)

    def clear_context_cache(self) -> None:
        """Clear the context selector's relevance score cache."""
        if self._context_selector_instance is not None:
            self._context_selector_instance.clear_cache()
