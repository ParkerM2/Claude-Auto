"""
Streaming File Analyzer Module
================================

Provides memory-efficient streaming file iteration with configurable batch sizes.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator, Iterator

from .analyzers.base import SKIP_DIRS


def stream_files(
    root_path: str | Path,
    batch_size: int = 100,
    skip_dirs: set[str] | None = None,
) -> Generator[list[Path], None, None]:
    """
    Stream files from a directory tree in batches.

    This function uses a generator pattern to yield files in batches, avoiding
    loading all files into memory at once. It respects skip directories and
    provides configurable batch sizing for memory-efficient processing.

    Args:
        root_path: Root directory to scan
        batch_size: Number of files to yield per batch (default: 100)
        skip_dirs: Set of directory names to skip (default: SKIP_DIRS from base.py)

    Yields:
        Lists of Path objects, each list containing up to batch_size files

    Example:
        >>> for batch in stream_files('/project', batch_size=50):
        ...     for file_path in batch:
        ...         process(file_path)
    """
    if skip_dirs is None:
        skip_dirs = SKIP_DIRS

    root = Path(root_path).resolve()
    batch: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out directories to skip (modifies in-place to prevent os.walk from descending)
        dirnames[:] = [
            d for d in dirnames
            if d not in skip_dirs and not d.startswith('.')
        ]

        # Process files in current directory
        for filename in filenames:
            file_path = Path(dirpath) / filename

            # Skip hidden files
            if filename.startswith('.'):
                continue

            batch.append(file_path)

            # Yield batch when it reaches the configured size
            if len(batch) >= batch_size:
                yield batch
                batch = []

    # Yield remaining files in the last batch
    if batch:
        yield batch


def stream_files_iter(
    root_path: str | Path,
    skip_dirs: set[str] | None = None,
) -> Iterator[Path]:
    """
    Stream files one at a time from a directory tree.

    This is a simpler iterator that yields files one by one, useful when you
    need to process files individually without batching.

    Args:
        root_path: Root directory to scan
        skip_dirs: Set of directory names to skip (default: SKIP_DIRS from base.py)

    Yields:
        Path objects for each file

    Example:
        >>> for file_path in stream_files_iter('/project'):
        ...     process(file_path)
    """
    if skip_dirs is None:
        skip_dirs = SKIP_DIRS

    root = Path(root_path).resolve()

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out directories to skip (modifies in-place to prevent os.walk from descending)
        dirnames[:] = [
            d for d in dirnames
            if d not in skip_dirs and not d.startswith('.')
        ]

        # Yield files in current directory
        for filename in filenames:
            # Skip hidden files
            if filename.startswith('.'):
                continue

            yield Path(dirpath) / filename
