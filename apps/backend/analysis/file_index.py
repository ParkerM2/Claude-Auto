#!/usr/bin/env python3
"""
File Index Module
=================

Tracks file metadata (mtime, hash, size) for incremental indexing.
Enables efficient detection of changed files in large codebases.

This module provides the core infrastructure for incremental file analysis,
storing metadata to avoid re-analyzing unchanged files.

Usage:
    from file_index import FileIndex

    # Create index for a project directory
    index = FileIndex('/path/to/project')

    # Track a file
    index.track_file('src/main.py')

    # Check if file has changed
    if index.has_changed('src/main.py'):
        print("File has been modified")

    # Save index to disk
    index.save()

    # Load existing index
    index = FileIndex.load('/path/to/project')
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class FileMetadata:
    """Metadata for a tracked file."""

    path: str  # Relative path from project root
    mtime: float  # Modification time (Unix timestamp)
    size: int  # File size in bytes
    hash: str  # SHA-256 hash of file contents
    last_analyzed: float  # Unix timestamp of last analysis

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileMetadata:
        """Create from dictionary loaded from JSON."""
        return cls(
            path=str(data["path"]),
            mtime=float(data["mtime"]),
            size=int(data["size"]),
            hash=str(data["hash"]),
            last_analyzed=float(data["last_analyzed"]),
        )


# =============================================================================
# FILE INDEX
# =============================================================================


class FileIndex:
    """
    Tracks file metadata for incremental indexing.

    The index stores modification times, hashes, and sizes for tracked files,
    enabling efficient detection of changes. The index is persisted to
    .auto-claude/file_index.json for reuse across sessions.
    """

    INDEX_FILENAME = ".auto-claude/file_index.json"

    def __init__(self, project_dir: str | Path) -> None:
        """
        Initialize file index for a project directory.

        Args:
            project_dir: Path to the project root directory
        """
        self.project_dir = Path(project_dir).resolve()
        self._index: dict[str, FileMetadata] = {}
        self._cache: dict[str, bool] = {}  # Cache for has_changed() results
        self._dir_mtimes: dict[
            str, float
        ] = {}  # Track directory mtimes for optimization

    @property
    def index_path(self) -> Path:
        """Get the path to the index file."""
        return self.project_dir / self.INDEX_FILENAME

    def track_file(
        self, file_path: str | Path, compute_hash: bool = False
    ) -> FileMetadata:
        """
        Track a file and store its metadata.

        Args:
            file_path: Path to file (absolute or relative to project_dir)
            compute_hash: If True, compute hash immediately. If False, defer until needed.
                         Hash will be computed later only when needed for verification.

        Returns:
            FileMetadata object for the tracked file

        Raises:
            FileNotFoundError: If file does not exist
        """
        # Convert to absolute path and resolve to handle Windows short paths
        abs_path = Path(file_path)
        if not abs_path.is_absolute():
            abs_path = self.project_dir / file_path
        abs_path = abs_path.resolve()

        if not abs_path.exists():
            raise FileNotFoundError(f"File not found: {abs_path}")

        # Get relative path from project root
        try:
            rel_path = abs_path.relative_to(self.project_dir)
        except ValueError:
            # File is outside project directory, use absolute path
            rel_path = abs_path

        # Get file stats
        stat = abs_path.stat()
        mtime = stat.st_mtime
        size = stat.st_size

        # Only compute hash when explicitly requested or when needed for verification
        if compute_hash:
            file_hash = self._calculate_hash(abs_path)
        else:
            file_hash = ""  # Empty string means "not computed yet"

        # Create metadata
        metadata = FileMetadata(
            path=str(rel_path),
            mtime=mtime,
            size=size,
            hash=file_hash,
            last_analyzed=time.time(),
        )

        # Store in index
        self._index[str(rel_path)] = metadata

        # Clear cache for this file
        self._cache.pop(str(rel_path), None)

        return metadata

    def has_changed(self, file_path: str | Path) -> bool:
        """
        Check if a file has changed since last tracking.

        Uses mtime for quick check, then hash for verification if needed.

        Args:
            file_path: Path to file (absolute or relative to project_dir)

        Returns:
            True if file has changed or is not tracked, False otherwise
        """
        # Convert to relative path, resolving to handle Windows short paths
        abs_path = Path(file_path)
        if not abs_path.is_absolute():
            abs_path = self.project_dir / file_path
        abs_path = abs_path.resolve()

        try:
            rel_path = abs_path.relative_to(self.project_dir)
        except ValueError:
            rel_path = abs_path

        rel_path_str = str(rel_path)

        # Check cache first
        if rel_path_str in self._cache:
            return self._cache[rel_path_str]

        # If not tracked, consider it changed
        if rel_path_str not in self._index:
            self._cache[rel_path_str] = True
            return True

        # Check if file still exists
        if not abs_path.exists():
            self._cache[rel_path_str] = True
            return True

        metadata = self._index[rel_path_str]
        stat = abs_path.stat()

        # Quick check: mtime
        if stat.st_mtime != metadata.mtime:
            # mtime changed, but compute hash to verify actual content change
            # This is when we NEED the hash
            if not metadata.hash:
                # Old hash not computed, must re-track with hash
                self.track_file(abs_path, compute_hash=True)
                self._cache[rel_path_str] = True
                return True

            current_hash = self._calculate_hash(abs_path)
            changed = current_hash != metadata.hash
            self._cache[rel_path_str] = changed
            return changed

        # Size check
        if stat.st_size != metadata.size:
            self._cache[rel_path_str] = True
            return True

        # No change detected
        self._cache[rel_path_str] = False
        return False

    def get_metadata(self, file_path: str | Path) -> FileMetadata | None:
        """
        Get stored metadata for a file.

        Args:
            file_path: Path to file (absolute or relative to project_dir)

        Returns:
            FileMetadata object if tracked, None otherwise
        """
        abs_path = Path(file_path)
        if not abs_path.is_absolute():
            abs_path = self.project_dir / file_path
        abs_path = abs_path.resolve()

        try:
            rel_path = abs_path.relative_to(self.project_dir)
        except ValueError:
            rel_path = abs_path

        return self._index.get(str(rel_path))

    def untrack_file(self, file_path: str | Path) -> bool:
        """
        Remove a file from tracking.

        Args:
            file_path: Path to file (absolute or relative to project_dir)

        Returns:
            True if file was tracked and removed, False otherwise
        """
        abs_path = Path(file_path)
        if not abs_path.is_absolute():
            abs_path = self.project_dir / file_path
        abs_path = abs_path.resolve()

        try:
            rel_path = abs_path.relative_to(self.project_dir)
        except ValueError:
            rel_path = abs_path

        rel_path_str = str(rel_path)

        # Remove from index and cache
        removed = rel_path_str in self._index
        self._index.pop(rel_path_str, None)
        self._cache.pop(rel_path_str, None)

        return removed

    def track_directory(self, dir_path: Path) -> None:
        """
        Track directory mtime for skip-unchanged-dirs optimization.

        Args:
            dir_path: Path to directory (absolute or relative to project_dir)
        """
        abs_dir = Path(dir_path)
        if not abs_dir.is_absolute():
            abs_dir = self.project_dir / dir_path
        abs_dir = abs_dir.resolve()

        if not abs_dir.is_dir():
            return

        try:
            rel_dir = abs_dir.relative_to(self.project_dir)
        except ValueError:
            rel_dir = abs_dir

        rel_dir_str = str(rel_dir)
        self._dir_mtimes[rel_dir_str] = abs_dir.stat().st_mtime

    def dir_has_changed(self, dir_path: Path) -> bool:
        """
        Check if directory or its contents changed.

        Args:
            dir_path: Path to directory (absolute or relative to project_dir)

        Returns:
            True if directory changed or is not tracked, False otherwise
        """
        abs_dir = Path(dir_path)
        if not abs_dir.is_absolute():
            abs_dir = self.project_dir / dir_path
        abs_dir = abs_dir.resolve()

        try:
            rel_dir = abs_dir.relative_to(self.project_dir)
        except ValueError:
            rel_dir = abs_dir

        rel_dir_str = str(rel_dir)

        if rel_dir_str not in self._dir_mtimes:
            return True  # New directory

        if not abs_dir.exists():
            return True  # Deleted

        current_mtime = abs_dir.stat().st_mtime
        return current_mtime != self._dir_mtimes[rel_dir_str]

    def get_files_in_dir(self, dir_path: Path) -> list[str]:
        """
        Get all tracked files in a directory (and subdirectories).

        Args:
            dir_path: Path to directory (absolute or relative to project_dir)

        Returns:
            List of relative file paths in this directory
        """
        abs_dir = Path(dir_path)
        if not abs_dir.is_absolute():
            abs_dir = self.project_dir / dir_path
        abs_dir = abs_dir.resolve()

        try:
            rel_dir = abs_dir.relative_to(self.project_dir)
        except ValueError:
            rel_dir = abs_dir

        rel_dir_str = str(rel_dir)

        # Find all files that start with this directory path
        files = []
        for file_path in self._index.keys():
            if file_path.startswith(rel_dir_str):
                files.append(file_path)

        return files

    def get_tracked_files(self) -> list[str]:
        """
        Get list of all tracked file paths.

        Returns:
            List of relative file paths
        """
        return list(self._index.keys())

    def clear(self) -> None:
        """Clear all tracked files from the index."""
        self._index.clear()
        self._cache.clear()

    def save(self) -> None:
        """
        Save index to disk.

        Creates the .auto-claude directory if it doesn't exist.
        """
        # Ensure directory exists
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to serializable format
        data = {
            "project_dir": str(self.project_dir),
            "files": {
                path: metadata.to_dict() for path, metadata in self._index.items()
            },
            "dir_mtimes": self._dir_mtimes,
            "version": "1.0",
            "created_at": time.time(),
        }

        # Write to file
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, project_dir: str | Path) -> FileIndex:
        """
        Load index from disk.

        Args:
            project_dir: Path to the project root directory

        Returns:
            FileIndex object with loaded data, or empty index if file doesn't exist
        """
        index = cls(project_dir)

        if not index.index_path.exists():
            return index

        try:
            with open(index.index_path, encoding="utf-8") as f:
                data = json.load(f)

            # Validate version (for future compatibility)
            version = data.get("version", "1.0")
            if version != "1.0":
                print(f"Warning: Unknown index version {version}, creating new index")
                return index

            # Load files
            files_data = data.get("files", {})
            for path, metadata_dict in files_data.items():
                try:
                    metadata = FileMetadata.from_dict(metadata_dict)
                    index._index[path] = metadata
                except (KeyError, ValueError, TypeError) as e:
                    print(f"Warning: Failed to load metadata for {path}: {e}")
                    continue

            # Load directory mtimes
            dir_mtimes_data = data.get("dir_mtimes", {})
            index._dir_mtimes = dir_mtimes_data

        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Failed to load index file: {e}")
            # Return empty index on error
            return cls(project_dir)

        return index

    def _calculate_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            Hex string of SHA-256 hash
        """
        sha256 = hashlib.sha256()

        try:
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
        except OSError as e:
            print(f"Warning: Failed to hash file {file_path}: {e}")
            return ""

        return sha256.hexdigest()

    def clear_cache(self) -> None:
        """Clear the internal cache of has_changed() results."""
        self._cache.clear()

    def __len__(self) -> int:
        """Get number of tracked files."""
        return len(self._index)

    def __contains__(self, file_path: str | Path) -> bool:
        """Check if a file is tracked."""
        abs_path = Path(file_path)
        if not abs_path.is_absolute():
            abs_path = self.project_dir / file_path
        abs_path = abs_path.resolve()

        try:
            rel_path = abs_path.relative_to(self.project_dir)
        except ValueError:
            rel_path = abs_path

        return str(rel_path) in self._index


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def load_file_index(project_dir: str | Path) -> FileIndex:
    """
    Convenience function to load a file index.

    Args:
        project_dir: Path to the project root directory

    Returns:
        FileIndex object
    """
    return FileIndex.load(project_dir)


def create_file_index(project_dir: str | Path) -> FileIndex:
    """
    Convenience function to create a new file index.

    Args:
        project_dir: Path to the project root directory

    Returns:
        FileIndex object
    """
    return FileIndex(project_dir)


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="File index management")
    parser.add_argument(
        "project_dir",
        type=Path,
        help="Path to project directory",
    )
    parser.add_argument(
        "--track",
        type=Path,
        help="Track a file",
    )
    parser.add_argument(
        "--check",
        type=Path,
        help="Check if a file has changed",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List tracked files",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save index to disk",
    )

    args = parser.parse_args()

    # Load or create index
    index = FileIndex.load(args.project_dir)
    print(f"Loaded index with {len(index)} tracked files")

    # Handle commands
    if args.track:
        try:
            metadata = index.track_file(args.track)
            print(f"Tracked {metadata.path}")
            print(f"  Size: {metadata.size} bytes")
            print(f"  Hash: {metadata.hash[:16]}...")
            if args.save:
                index.save()
                print(f"Saved to {index.index_path}")
        except FileNotFoundError as e:
            print(f"Error: {e}")

    elif args.check:
        if index.has_changed(args.check):
            print(f"File has changed: {args.check}")
        else:
            print(f"File unchanged: {args.check}")

    elif args.list:
        files = index.get_tracked_files()
        if files:
            print(f"Tracked files ({len(files)}):")
            for file in sorted(files):
                print(f"  {file}")
        else:
            print("No tracked files")


if __name__ == "__main__":
    main()
