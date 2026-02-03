#!/usr/bin/env python3
"""
Incremental Indexer Module
===========================

Detects file changes by comparing current filesystem state with stored index.
Uses mtime for quick checks and hashes for verification to avoid false positives.

This module builds on FileIndex to provide efficient change detection for large
codebases, enabling incremental analysis that only processes modified files.

Usage:
    from incremental_indexer import IncrementalIndexer

    # Create indexer for a project
    indexer = IncrementalIndexer('/path/to/project')

    # Detect all changes
    changes = indexer.detect_changes()
    print(f"Added: {len(changes['added'])}")
    print(f"Modified: {len(changes['modified'])}")
    print(f"Deleted: {len(changes['deleted'])}")

    # Update index with current state
    indexer.update_index()
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .file_index import FileIndex

# =============================================================================
# CONSTANTS
# =============================================================================

# Directories to skip during scanning (same as BaseAnalyzer)
SKIP_DIRS = {
    "node_modules",
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "target",
    "vendor",
    ".idea",
    ".vscode",
    ".auto-claude",
}

# File extensions to index (source code files)
INDEX_EXTENSIONS = {
    # JavaScript/TypeScript
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    # Python
    ".py",
    ".pyi",
    # Web
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    # Config
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    # Documentation
    ".md",
    ".rst",
    ".txt",
    # Rust
    ".rs",
    # Go
    ".go",
    # C/C++
    ".c",
    ".cpp",
    ".cc",
    ".h",
    ".hpp",
    # Java/Kotlin
    ".java",
    ".kt",
    ".kts",
    # C#
    ".cs",
    # Ruby
    ".rb",
    # PHP
    ".php",
    # Swift
    ".swift",
    # Dart
    ".dart",
    # Shell
    ".sh",
    ".bash",
    ".zsh",
    # Other
    ".sql",
    ".graphql",
    ".proto",
}


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class ChangeSet:
    """Represents detected changes in the filesystem."""

    added: list[str]  # New files not in index
    modified: list[str]  # Existing files with changed content
    deleted: list[str]  # Files in index but missing from filesystem
    unchanged: list[str]  # Files with no changes

    def __len__(self) -> int:
        """Total number of changed files."""
        return len(self.added) + len(self.modified) + len(self.deleted)

    def has_changes(self) -> bool:
        """Check if any changes were detected."""
        return bool(self.added or self.modified or self.deleted)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "added": self.added,
            "modified": self.modified,
            "deleted": self.deleted,
            "unchanged": self.unchanged,
            "total_changed": len(self),
        }


# =============================================================================
# INCREMENTAL INDEXER
# =============================================================================


class IncrementalIndexer:
    """
    Detects file changes by comparing filesystem state with stored index.

    Scans the project directory for relevant source files, compares against
    the stored FileIndex, and returns lists of added, modified, and deleted
    files. Uses mtime for quick detection and hashes for verification.
    """

    def __init__(
        self,
        project_dir: str | Path,
        extensions: set[str] | None = None,
        skip_dirs: set[str] | None = None,
    ) -> None:
        """
        Initialize incremental indexer.

        Args:
            project_dir: Path to the project root directory
            extensions: Set of file extensions to index (default: INDEX_EXTENSIONS)
            skip_dirs: Set of directories to skip (default: SKIP_DIRS)
        """
        self.project_dir = Path(project_dir).resolve()
        self.extensions = extensions or INDEX_EXTENSIONS
        self.skip_dirs = skip_dirs or SKIP_DIRS
        self.file_index = FileIndex.load(project_dir)
        self._cache: dict[str, Any] = {}

    def _should_index(self, file_path: Path) -> bool:
        """
        Check if a file should be indexed.

        Args:
            file_path: Path to the file

        Returns:
            True if file should be indexed, False otherwise
        """
        # Skip if extension not in whitelist
        if file_path.suffix.lower() not in self.extensions:
            return False

        # Skip if in a skipped directory
        for part in file_path.parts:
            if part in self.skip_dirs:
                return False

        return True

    def _scan_directory(self) -> set[str]:
        """
        Scan project directory for indexable files.

        Returns:
            Set of relative file paths
        """
        files = set()

        try:
            for item in self.project_dir.rglob("*"):
                # Skip directories
                if item.is_dir():
                    continue

                # Skip files in excluded directories
                if not self._should_index(item):
                    continue

                # Get relative path
                try:
                    rel_path = item.relative_to(self.project_dir)
                    files.add(str(rel_path))
                except (ValueError, OSError):
                    # Skip files outside project or with permission errors
                    continue

        except (OSError, PermissionError) as e:
            print(f"Warning: Error scanning directory {self.project_dir}: {e}")

        return files

    def get_cached_result(self, file_path: str) -> Any | None:
        """
        Get cached analysis result for a file.

        Args:
            file_path: Relative path to the file

        Returns:
            Cached result if available, None otherwise
        """
        cache_key = str(Path(file_path).as_posix())
        return self._cache.get(cache_key)

    def set_cached_result(self, file_path: str, result: Any) -> None:
        """
        Store analysis result in cache.

        Args:
            file_path: Relative path to the file
            result: Analysis result to cache
        """
        cache_key = str(Path(file_path).as_posix())
        self._cache[cache_key] = result

    def invalidate_cache(self, file_path: str) -> None:
        """
        Invalidate cached result for a file.

        Args:
            file_path: Relative path to the file
        """
        cache_key = str(Path(file_path).as_posix())
        self._cache.pop(cache_key, None)

    def clear_cache(self) -> None:
        """Clear all cached results."""
        self._cache.clear()

    def detect_changes(self) -> ChangeSet:
        """
        Detect changes between filesystem and stored index.

        Uses directory-level mtime optimization to skip unchanged directories,
        significantly improving performance when most files haven't changed.

        Returns:
            ChangeSet object with lists of changed files
        """
        current_files = set()
        added = []
        modified = []
        deleted = []
        unchanged = []

        # Get tracked files from index
        tracked_files = set(self.file_index.get_tracked_files())

        # Walk filesystem with directory-level optimization
        for root, dirs, files in os.walk(self.project_dir):
            root_path = Path(root)

            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.skip_dirs]

            # Check if directory changed
            if not self.file_index.dir_has_changed(root_path):
                # Directory unchanged, skip scanning files
                # Just mark all files in this dir as unchanged
                for rel_path in self.file_index.get_files_in_dir(root_path):
                    current_files.add(rel_path)
                    unchanged.append(rel_path)

                # Don't descend into subdirectories
                dirs.clear()
                continue

            # Directory changed, track it and scan files normally
            self.file_index.track_directory(root_path)

            for file_name in files:
                file_path = root_path / file_name

                # Skip if not indexable
                if not self._should_index(file_path):
                    continue

                # Get relative path
                try:
                    rel_path = file_path.relative_to(self.project_dir)
                    rel_path_str = str(rel_path)
                except (ValueError, OSError):
                    # Skip files outside project or with permission errors
                    continue

                current_files.add(rel_path_str)

                # Check if file changed
                if rel_path_str not in tracked_files:
                    # New file
                    added.append(rel_path_str)
                elif self.file_index.has_changed(file_path):
                    # Modified file
                    modified.append(rel_path_str)
                else:
                    # Unchanged file
                    unchanged.append(rel_path_str)

        # Find deleted files (in index but not in filesystem)
        for file_path in sorted(tracked_files):
            if file_path not in current_files:
                deleted.append(file_path)

        return ChangeSet(
            added=sorted(added),
            modified=sorted(modified),
            deleted=sorted(deleted),
            unchanged=sorted(unchanged),
        )

    def update_index(self, changes: ChangeSet | None = None) -> int:
        """
        Update the index with current filesystem state.

        Args:
            changes: Optional ChangeSet from detect_changes(). If None, will
                    detect changes first.

        Returns:
            Number of files updated in the index
        """
        if changes is None:
            changes = self.detect_changes()

        updated_count = 0

        # Track added files and invalidate cache (don't compute hash during bulk indexing)
        for file_path in changes.added:
            try:
                self.file_index.track_file(file_path, compute_hash=False)
                self.invalidate_cache(file_path)
                updated_count += 1
            except (FileNotFoundError, OSError) as e:
                print(f"Warning: Failed to track {file_path}: {e}")

        # Update modified files and invalidate cache (don't compute hash during bulk indexing)
        for file_path in changes.modified:
            try:
                self.file_index.track_file(file_path, compute_hash=False)
                self.invalidate_cache(file_path)
                updated_count += 1
            except (FileNotFoundError, OSError) as e:
                print(f"Warning: Failed to update {file_path}: {e}")

        # Remove deleted files and invalidate cache
        for file_path in changes.deleted:
            self.file_index.untrack_file(file_path)
            self.invalidate_cache(file_path)
            updated_count += 1

        # Save updated index
        if updated_count > 0:
            self.file_index.save()

        return updated_count

    def get_changed_files(self) -> list[str]:
        """
        Get list of all changed files (added + modified).

        Returns:
            List of relative file paths that have changed
        """
        changes = self.detect_changes()
        return changes.added + changes.modified

    def rebuild_index(self) -> int:
        """
        Rebuild the entire index from scratch.

        Scans all files and updates the index, removing stale entries.

        Returns:
            Number of files in the rebuilt index
        """
        # Clear existing index and cache
        self.file_index.clear()
        self.clear_cache()

        # Scan and track all files (don't compute hash during bulk rebuild)
        current_files = self._scan_directory()

        for file_path in sorted(current_files):
            try:
                self.file_index.track_file(file_path, compute_hash=False)
            except (FileNotFoundError, OSError) as e:
                print(f"Warning: Failed to track {file_path}: {e}")

        # Save rebuilt index
        self.file_index.save()

        return len(self.file_index)

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about the index.

        Returns:
            Dictionary with index statistics
        """
        changes = self.detect_changes()

        return {
            "total_tracked": len(self.file_index),
            "total_current": len(self._scan_directory()),
            "added": len(changes.added),
            "modified": len(changes.modified),
            "deleted": len(changes.deleted),
            "unchanged": len(changes.unchanged),
            "total_changed": len(changes),
            "has_changes": changes.has_changes(),
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def detect_changes(
    project_dir: str | Path,
    extensions: set[str] | None = None,
    skip_dirs: set[str] | None = None,
) -> ChangeSet:
    """
    Convenience function to detect changes in a project.

    Args:
        project_dir: Path to the project root directory
        extensions: Set of file extensions to index
        skip_dirs: Set of directories to skip

    Returns:
        ChangeSet object with detected changes
    """
    indexer = IncrementalIndexer(project_dir, extensions, skip_dirs)
    return indexer.detect_changes()


def update_index(
    project_dir: str | Path,
    extensions: set[str] | None = None,
    skip_dirs: set[str] | None = None,
) -> int:
    """
    Convenience function to update index with current state.

    Args:
        project_dir: Path to the project root directory
        extensions: Set of file extensions to index
        skip_dirs: Set of directories to skip

    Returns:
        Number of files updated
    """
    indexer = IncrementalIndexer(project_dir, extensions, skip_dirs)
    return indexer.update_index()


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    """CLI entry point for testing."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Incremental indexer for change detection")
    parser.add_argument(
        "project_dir",
        type=Path,
        help="Path to project directory",
    )
    parser.add_argument(
        "--detect",
        action="store_true",
        help="Detect changes",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update index with current state",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild index from scratch",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show index statistics",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    args = parser.parse_args()

    # Create indexer
    indexer = IncrementalIndexer(args.project_dir)

    # Handle commands
    if args.rebuild:
        count = indexer.rebuild_index()
        if args.json:
            print(json.dumps({"rebuilt": True, "files": count}))
        else:
            print(f"Rebuilt index with {count} files")

    elif args.update:
        count = indexer.update_index()
        if args.json:
            print(json.dumps({"updated": count}))
        else:
            print(f"Updated {count} files in index")

    elif args.stats:
        stats = indexer.get_stats()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print("Index Statistics:")
            print(f"  Total tracked: {stats['total_tracked']}")
            print(f"  Total current: {stats['total_current']}")
            print(f"  Added: {stats['added']}")
            print(f"  Modified: {stats['modified']}")
            print(f"  Deleted: {stats['deleted']}")
            print(f"  Unchanged: {stats['unchanged']}")
            print(f"  Total changed: {stats['total_changed']}")

    else:  # Default to detect
        changes = indexer.detect_changes()
        if args.json:
            print(json.dumps(changes.to_dict(), indent=2))
        else:
            print("Changes detected:")
            print(f"  Added: {len(changes.added)} files")
            if changes.added:
                for file in changes.added[:10]:  # Show first 10
                    print(f"    + {file}")
                if len(changes.added) > 10:
                    print(f"    ... and {len(changes.added) - 10} more")

            print(f"  Modified: {len(changes.modified)} files")
            if changes.modified:
                for file in changes.modified[:10]:
                    print(f"    M {file}")
                if len(changes.modified) > 10:
                    print(f"    ... and {len(changes.modified) - 10} more")

            print(f"  Deleted: {len(changes.deleted)} files")
            if changes.deleted:
                for file in changes.deleted[:10]:
                    print(f"    - {file}")
                if len(changes.deleted) > 10:
                    print(f"    ... and {len(changes.deleted) - 10} more")

            print(f"  Unchanged: {len(changes.unchanged)} files")


if __name__ == "__main__":
    main()
