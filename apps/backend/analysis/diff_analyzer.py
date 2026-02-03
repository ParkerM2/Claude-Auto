#!/usr/bin/env python3
"""
Diff Analyzer Module
====================

Parses git diff output to extract detailed line-by-line changes for visualization.
This module is used by the worktree diff viewer to provide structured diff data
with file-level stats, hunks, and individual line changes.

The diff analyzer is used by:
- WorktreeManager: To get detailed diffs for UI visualization
- QA Agent: To analyze changes before approval

Usage:
    from analysis.diff_analyzer import DiffAnalyzer

    analyzer = DiffAnalyzer(project_dir)
    diff_data = analyzer.get_diff(base_ref="main", head_ref="HEAD")

    for file_diff in diff_data.files:
        print(f"{file_diff.change_type}: {file_diff.path}")
        print(f"  +{file_diff.additions} -{file_diff.deletions}")
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# =============================================================================
# ENUMS
# =============================================================================


class ChangeType(str, Enum):
    """Type of change to a file."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class LineType(str, Enum):
    """Type of line in a diff hunk."""

    ADDED = "added"
    DELETED = "deleted"
    CONTEXT = "context"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class DiffLine:
    """
    Represents a single line in a diff hunk.

    Attributes:
        type: Whether this line was added, deleted, or context
        content: The actual line content (without +/- prefix)
        old_line_number: Line number in the old file (None if added)
        new_line_number: Line number in the new file (None if deleted)
    """

    type: LineType
    content: str
    old_line_number: int | None = None
    new_line_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type.value,
            "content": self.content,
            "old_line_number": self.old_line_number,
            "new_line_number": self.new_line_number,
        }


@dataclass
class DiffHunk:
    """
    Represents a hunk (contiguous block of changes) in a diff.

    Attributes:
        old_start: Starting line number in old file
        old_count: Number of lines in old file
        new_start: Starting line number in new file
        new_count: Number of lines in new file
        header: The hunk header (e.g., "@@ -1,5 +1,6 @@")
        lines: List of lines in this hunk
    """

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: list[DiffLine] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "old_start": self.old_start,
            "old_count": self.old_count,
            "new_start": self.new_start,
            "new_count": self.new_count,
            "header": self.header,
            "lines": [line.to_dict() for line in self.lines],
        }


@dataclass
class FileDiff:
    """
    Represents the diff for a single file.

    Attributes:
        path: File path relative to repository root
        old_path: Original path if renamed
        change_type: Type of change (added/modified/deleted/renamed)
        additions: Number of lines added
        deletions: Number of lines deleted
        hunks: List of diff hunks
        is_binary: Whether this is a binary file
        old_mode: File mode in old version
        new_mode: File mode in new version
    """

    path: str
    change_type: ChangeType
    additions: int = 0
    deletions: int = 0
    hunks: list[DiffHunk] = field(default_factory=list)
    old_path: str | None = None
    is_binary: bool = False
    old_mode: str | None = None
    new_mode: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "path": self.path,
            "old_path": self.old_path,
            "change_type": self.change_type.value,
            "additions": self.additions,
            "deletions": self.deletions,
            "hunks": [hunk.to_dict() for hunk in self.hunks],
            "is_binary": self.is_binary,
            "old_mode": self.old_mode,
            "new_mode": self.new_mode,
        }


@dataclass
class DiffResult:
    """
    Complete result of a diff analysis.

    Attributes:
        files: List of file diffs
        total_additions: Total lines added across all files
        total_deletions: Total lines deleted across all files
        files_changed: Number of files changed
        base_ref: Base reference used for diff
        head_ref: Head reference used for diff
        errors: List of errors encountered during parsing
    """

    files: list[FileDiff] = field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0
    files_changed: int = 0
    base_ref: str = ""
    head_ref: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "files": [f.to_dict() for f in self.files],
            "total_additions": self.total_additions,
            "total_deletions": self.total_deletions,
            "files_changed": self.files_changed,
            "base_ref": self.base_ref,
            "head_ref": self.head_ref,
            "errors": self.errors,
        }


# =============================================================================
# DIFF ANALYZER
# =============================================================================


class DiffAnalyzer:
    """
    Analyzes git diffs to extract structured change data.

    This class runs git diff commands and parses the unified diff format
    to extract detailed information about file changes, hunks, and individual
    line modifications.
    """

    # Regex patterns for parsing unified diff format
    FILE_HEADER_PATTERN = re.compile(r"^diff --git a/(.*) b/(.*)$")
    OLD_FILE_PATTERN = re.compile(r"^--- (.*)$")
    NEW_FILE_PATTERN = re.compile(r"^\+\+\+ (.*)$")
    HUNK_HEADER_PATTERN = re.compile(
        r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$"
    )
    RENAME_PATTERN = re.compile(r"^rename from (.*)$")
    RENAME_TO_PATTERN = re.compile(r"^rename to (.*)$")
    MODE_PATTERN = re.compile(r"^(new|deleted|old|new) mode (\d+)$")
    BINARY_PATTERN = re.compile(r"^Binary files .* differ$")

    def __init__(self, project_dir: Path | str):
        """
        Initialize the diff analyzer.

        Args:
            project_dir: Path to the git repository root
        """
        self.project_dir = Path(project_dir).resolve()

    def get_diff(
        self,
        base_ref: str = "main",
        head_ref: str = "HEAD",
        context_lines: int = 3,
        file_paths: list[str] | None = None,
    ) -> DiffResult:
        """
        Get detailed diff between two git references.

        Args:
            base_ref: Base git reference (branch, commit, tag)
            head_ref: Head git reference to compare against base
            context_lines: Number of context lines to include
            file_paths: Optional list of specific file paths to diff

        Returns:
            DiffResult containing all diff information

        Raises:
            subprocess.CalledProcessError: If git command fails
            FileNotFoundError: If project directory doesn't exist
        """
        if not self.project_dir.exists():
            raise FileNotFoundError(f"Project directory not found: {self.project_dir}")

        result = DiffResult(base_ref=base_ref, head_ref=head_ref)

        # Build git diff command
        cmd = [
            "git",
            "diff",
            f"--unified={context_lines}",
            "--no-color",
            "--no-ext-diff",
            "--ignore-submodules",
            f"{base_ref}..{head_ref}",
        ]

        if file_paths:
            cmd.append("--")
            cmd.extend(file_paths)

        try:
            # Run git diff
            process = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse the diff output
            if process.stdout:
                self._parse_diff(process.stdout, result)

        except subprocess.CalledProcessError as e:
            error_msg = f"Git diff failed: {e.stderr}"
            result.errors.append(error_msg)

        return result

    def _parse_diff(self, diff_output: str, result: DiffResult) -> None:
        """
        Parse unified diff output into structured data.

        Args:
            diff_output: Raw git diff output
            result: DiffResult to populate
        """
        lines = diff_output.split("\n")
        current_file: FileDiff | None = None
        current_hunk: DiffHunk | None = None
        old_line_num = 0
        new_line_num = 0

        i = 0
        while i < len(lines):
            line = lines[i]

            # File header: diff --git a/path b/path
            file_match = self.FILE_HEADER_PATTERN.match(line)
            if file_match:
                # Save previous file
                if current_file:
                    result.files.append(current_file)

                old_path = file_match.group(1)
                new_path = file_match.group(2)

                # Determine change type (will be refined below)
                if old_path == new_path:
                    change_type = ChangeType.MODIFIED
                else:
                    change_type = ChangeType.RENAMED

                current_file = FileDiff(path=new_path, change_type=change_type)
                current_hunk = None
                i += 1
                continue

            # Skip if no current file
            if not current_file:
                i += 1
                continue

            # Rename detection
            if line.startswith("rename from "):
                match = self.RENAME_PATTERN.match(line)
                if match:
                    current_file.old_path = match.group(1)
                    current_file.change_type = ChangeType.RENAMED
                i += 1
                continue

            if line.startswith("rename to "):
                match = self.RENAME_TO_PATTERN.match(line)
                if match:
                    current_file.path = match.group(1)
                i += 1
                continue

            # Mode changes
            mode_match = self.MODE_PATTERN.match(line)
            if mode_match:
                mode_type = mode_match.group(1)
                mode_value = mode_match.group(2)
                if mode_type == "new":
                    current_file.new_mode = mode_value
                    if current_file.change_type == ChangeType.MODIFIED:
                        current_file.change_type = ChangeType.ADDED
                elif mode_type == "deleted":
                    current_file.old_mode = mode_value
                    current_file.change_type = ChangeType.DELETED
                elif mode_type == "old":
                    current_file.old_mode = mode_value
                i += 1
                continue

            # Binary file detection
            if self.BINARY_PATTERN.match(line):
                current_file.is_binary = True
                i += 1
                continue

            # Old file marker (---)
            if line.startswith("--- "):
                # Check for /dev/null which indicates a new file
                if "/dev/null" in line or line == "--- /dev/null":
                    if current_file.change_type == ChangeType.MODIFIED:
                        current_file.change_type = ChangeType.ADDED
                i += 1
                continue

            # New file marker (+++)
            if line.startswith("+++ "):
                # Check for /dev/null which indicates a deleted file
                if "/dev/null" in line or line == "+++ /dev/null":
                    if current_file.change_type == ChangeType.MODIFIED:
                        current_file.change_type = ChangeType.DELETED
                i += 1
                continue

            # Hunk header: @@ -old_start,old_count +new_start,new_count @@
            hunk_match = self.HUNK_HEADER_PATTERN.match(line)
            if hunk_match:
                old_start = int(hunk_match.group(1))
                old_count = int(hunk_match.group(2) or "1")
                new_start = int(hunk_match.group(3))
                new_count = int(hunk_match.group(4) or "1")

                current_hunk = DiffHunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    header=line,
                )
                current_file.hunks.append(current_hunk)

                # Initialize line counters
                old_line_num = old_start
                new_line_num = new_start

                i += 1
                continue

            # Skip if no current hunk
            if not current_hunk:
                i += 1
                continue

            # Parse hunk lines
            if line.startswith("+"):
                # Added line
                content = line[1:]
                diff_line = DiffLine(
                    type=LineType.ADDED,
                    content=content,
                    old_line_number=None,
                    new_line_number=new_line_num,
                )
                current_hunk.lines.append(diff_line)
                current_file.additions += 1
                new_line_num += 1

            elif line.startswith("-"):
                # Deleted line
                content = line[1:]
                diff_line = DiffLine(
                    type=LineType.DELETED,
                    content=content,
                    old_line_number=old_line_num,
                    new_line_number=None,
                )
                current_hunk.lines.append(diff_line)
                current_file.deletions += 1
                old_line_num += 1

            elif line.startswith(" "):
                # Context line
                content = line[1:]
                diff_line = DiffLine(
                    type=LineType.CONTEXT,
                    content=content,
                    old_line_number=old_line_num,
                    new_line_number=new_line_num,
                )
                current_hunk.lines.append(diff_line)
                old_line_num += 1
                new_line_num += 1

            i += 1

        # Add the last file
        if current_file:
            result.files.append(current_file)

        # Calculate totals
        result.files_changed = len(result.files)
        result.total_additions = sum(f.additions for f in result.files)
        result.total_deletions = sum(f.deletions for f in result.files)

    def get_diff_stats(
        self, base_ref: str = "main", head_ref: str = "HEAD"
    ) -> dict[str, Any]:
        """
        Get summary statistics about a diff without full line-by-line details.

        Args:
            base_ref: Base git reference
            head_ref: Head git reference

        Returns:
            Dictionary with diff statistics
        """
        cmd = [
            "git",
            "diff",
            "--numstat",
            "--no-color",
            f"{base_ref}..{head_ref}",
        ]

        try:
            process = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            stats = {
                "files_changed": 0,
                "total_additions": 0,
                "total_deletions": 0,
                "files": [],
            }

            for line in process.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("\t")
                if len(parts) != 3:
                    continue

                additions = parts[0]
                deletions = parts[1]
                path = parts[2]

                # Binary files show "-" for additions/deletions
                is_binary = additions == "-" or deletions == "-"

                file_stat = {
                    "path": path,
                    "additions": 0 if is_binary else int(additions),
                    "deletions": 0 if is_binary else int(deletions),
                    "is_binary": is_binary,
                }

                stats["files"].append(file_stat)
                stats["files_changed"] += 1

                if not is_binary:
                    stats["total_additions"] += int(additions)
                    stats["total_deletions"] += int(deletions)

            return stats

        except subprocess.CalledProcessError as e:
            return {
                "error": f"Git diff stats failed: {e.stderr}",
                "files_changed": 0,
                "total_additions": 0,
                "total_deletions": 0,
                "files": [],
            }
