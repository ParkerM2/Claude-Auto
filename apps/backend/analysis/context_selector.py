#!/usr/bin/env python3
"""
Context Selector Module
=======================

Implements relevance-based file selection to prioritize important code
for AI agents working with large codebases.

Usage:
    from analysis.context_selector import ContextSelector

    selector = ContextSelector('.')
    score = selector.score_relevance('auth/login.py', 'implement user authentication')
    relevant_files = selector.select_files('authentication', max_files=100)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .analyzers.base import SKIP_DIRS


class ContextSelector:
    """
    Scores and selects files based on relevance to a task description.

    Uses keyword-based matching with weighted scoring:
    - Path matches (highest weight)
    - Filename matches (medium weight)
    - Content matches (lower weight)
    """

    def __init__(self, path: str | Path):
        """
        Initialize the context selector.

        Args:
            path: Root directory path for the project
        """
        self.path = Path(path).resolve()
        self._cache: dict[str, float] = {}

    def score_relevance(self, file_path: str, task_description: str) -> float:
        """
        Score a file's relevance to a task description.

        Args:
            file_path: Relative or absolute path to the file
            task_description: Description of the task to match against

        Returns:
            Relevance score from 0.0 (not relevant) to 1.0 (highly relevant)
        """
        # Convert to Path object
        target = Path(file_path)
        if not target.is_absolute():
            target = self.path / target

        # Check cache
        cache_key = f"{target}:{task_description}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Extract keywords from task description
        keywords = self._extract_keywords(task_description)
        if not keywords:
            return 0.0

        # Calculate score components
        path_score = self._score_path(target, keywords)
        name_score = self._score_filename(target, keywords)
        content_score = self._score_content(target, keywords)

        # Weighted combination
        # Path matches are most important, then filename, then content
        total_score = (
            path_score * 0.4 +
            name_score * 0.3 +
            content_score * 0.3
        )

        # Normalize to 0.0-1.0 range
        final_score = min(1.0, max(0.0, total_score))

        # Cache result
        self._cache[cache_key] = final_score

        return final_score

    def _extract_keywords(self, text: str) -> list[str]:
        """
        Extract meaningful keywords from text.

        Args:
            text: Text to extract keywords from

        Returns:
            List of normalized keywords
        """
        # Convert to lowercase
        text = text.lower()

        # Split on non-alphanumeric characters
        words = re.findall(r'\b\w+\b', text)

        # Filter out common stop words
        stop_words = {
            'a', 'an', 'and', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'may', 'might', 'must', 'can', 'to', 'of', 'in',
            'on', 'at', 'for', 'with', 'from', 'by', 'as', 'or', 'but', 'not',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
            'we', 'they', 'them', 'my', 'your', 'his', 'her', 'its', 'our',
            'their', 'what', 'which', 'who', 'when', 'where', 'why', 'how',
        }

        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        return keywords

    def _score_path(self, file_path: Path, keywords: list[str]) -> float:
        """
        Score relevance based on path components.

        Args:
            file_path: Path to score
            keywords: List of keywords to match

        Returns:
            Score from 0.0 to 1.0
        """
        path_str = str(file_path).lower()
        path_parts = path_str.split('/')

        matches = 0
        for keyword in keywords:
            # Check each path component
            for part in path_parts:
                if keyword in part:
                    matches += 1
                    break

        # Normalize by number of keywords
        if not keywords:
            return 0.0

        return min(1.0, matches / len(keywords))

    def _score_filename(self, file_path: Path, keywords: list[str]) -> float:
        """
        Score relevance based on filename.

        Args:
            file_path: Path to score
            keywords: List of keywords to match

        Returns:
            Score from 0.0 to 1.0
        """
        filename = file_path.stem.lower()  # Without extension

        matches = 0
        for keyword in keywords:
            if keyword in filename:
                matches += 1

        # Normalize by number of keywords
        if not keywords:
            return 0.0

        return min(1.0, matches / len(keywords))

    def _score_content(self, file_path: Path, keywords: list[str]) -> float:
        """
        Score relevance based on file content.

        Args:
            file_path: Path to score
            keywords: List of keywords to match

        Returns:
            Score from 0.0 to 1.0
        """
        if not file_path.exists() or not file_path.is_file():
            return 0.0

        # Skip binary files and large files
        if file_path.stat().st_size > 1_000_000:  # 1MB limit
            return 0.0

        try:
            content = file_path.read_text(encoding='utf-8').lower()
        except (OSError, UnicodeDecodeError):
            # Can't read file or not text
            return 0.0

        # Count keyword occurrences
        total_matches = 0
        for keyword in keywords:
            # Use word boundaries to avoid partial matches
            pattern = rf'\b{re.escape(keyword)}\b'
            matches = len(re.findall(pattern, content))
            # Diminishing returns for multiple occurrences
            total_matches += min(3, matches) / 3

        # Normalize by number of keywords
        if not keywords:
            return 0.0

        return min(1.0, total_matches / len(keywords))

    def estimate_tokens(self, file_path: Path) -> int:
        """
        Estimate the number of tokens in a file.

        Args:
            file_path: Path to the file

        Returns:
            Estimated token count (0 for unreadable files)
        """
        if not file_path.exists() or not file_path.is_file():
            return 0

        # Skip binary files and large files
        if file_path.stat().st_size > 1_000_000:  # 1MB limit
            return 0

        try:
            content = file_path.read_text(encoding='utf-8')
            # Estimate: 1 token ≈ 4 characters
            return len(content) // 4
        except (OSError, UnicodeDecodeError):
            # Can't read file or not text
            return 0

    def select_files(
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
        # Collect all files with their scores
        scored_files: list[tuple[float, str]] = []

        # Walk the directory tree
        for file_path in self._walk_files():
            # Score the file
            score = self.score_relevance(str(file_path), task_description)

            # Apply minimum score threshold
            if score >= min_score:
                # Store relative path for output
                try:
                    relative_path = file_path.relative_to(self.path)
                    scored_files.append((score, str(relative_path)))
                except ValueError:
                    # File is not under self.path, use absolute path
                    scored_files.append((score, str(file_path)))

        # Sort by score (descending)
        scored_files.sort(reverse=True, key=lambda x: x[0])

        # Apply limits
        result: list[str] = []
        cumulative_tokens = 0

        for score, path in scored_files:
            # Check max_files limit
            if max_files is not None and len(result) >= max_files:
                break

            # Check max_tokens limit
            if max_tokens is not None:
                file_path = self.path / path if not Path(path).is_absolute() else Path(path)
                tokens = self.estimate_tokens(file_path)

                # Would adding this file exceed the limit?
                if cumulative_tokens + tokens > max_tokens:
                    break

                cumulative_tokens += tokens

            result.append(path)

        return result

    def _walk_files(self) -> list[Path]:
        """
        Walk the directory tree and collect all files.

        Returns:
            List of file paths (excludes directories in SKIP_DIRS)
        """
        files: list[Path] = []

        try:
            for item in self.path.rglob('*'):
                # Skip if path contains any skip directory
                if any(skip_dir in item.parts for skip_dir in SKIP_DIRS):
                    continue

                # Only include files, not directories
                if item.is_file():
                    files.append(item)
        except (OSError, PermissionError):
            # Handle permission errors gracefully
            pass

        return files

    def clear_cache(self) -> None:
        """Clear the relevance score cache."""
        self._cache.clear()
