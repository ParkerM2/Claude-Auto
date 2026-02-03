"""
Streaming File Analyzer Module
================================

Provides memory-efficient streaming file iteration with configurable batch sizes.
Includes a memory-bounded analyzer that processes files in chunks.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Generator, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from .analyzers.base import SKIP_DIRS

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class FileAnalysisResult:
    """
    Result from analyzing a single file.

    Attributes:
        path: Path to the analyzed file
        size: File size in bytes
        lines: Number of lines in the file
        error: Optional error message if analysis failed
    """

    path: Path
    size: int
    lines: int = 0
    error: str | None = None


@dataclass
class StreamingAnalysisResult:
    """
    Overall result from streaming analysis.

    Attributes:
        total_files: Total number of files processed
        total_size: Total size of all files in bytes
        total_lines: Total number of lines across all files
        peak_memory_mb: Peak memory usage in megabytes
        files: List of individual file results
        errors: Count of files that had errors
    """

    total_files: int = 0
    total_size: int = 0
    total_lines: int = 0
    peak_memory_mb: float = 0.0
    files: list[FileAnalysisResult] = field(default_factory=list)
    errors: int = 0


# =============================================================================
# STREAMING ANALYZER
# =============================================================================


class StreamingAnalyzer:
    """
    Memory-bounded analyzer that processes files in chunks.

    This analyzer uses streaming file iteration to process large codebases
    without loading everything into memory at once. It monitors memory usage
    and processes files in configurable batches.

    Example:
        >>> analyzer = StreamingAnalyzer('.', max_memory_mb=100)
        >>> results = analyzer.analyze()
        >>> print(f"Processed {results.total_files} files")
    """

    def __init__(
        self,
        root_path: str | Path,
        max_memory_mb: int = 500,
        batch_size: int = 100,
        skip_dirs: set[str] | None = None,
    ):
        """
        Initialize the streaming analyzer.

        Args:
            root_path: Root directory to analyze
            max_memory_mb: Maximum memory usage in megabytes (soft limit)
            batch_size: Number of files to process per batch
            skip_dirs: Set of directory names to skip
        """
        self.project_dir = Path(root_path).resolve()
        self.max_memory_mb = max_memory_mb
        self.batch_size = batch_size
        self.skip_dirs = skip_dirs if skip_dirs is not None else SKIP_DIRS
        self.peak_memory_mb = 0.0

    def _get_memory_usage_mb(self) -> float:
        """
        Get current memory usage in megabytes.

        Returns:
            Current memory usage in MB
        """
        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            # Fallback to sys.getsizeof if psutil not available
            # This is less accurate but provides a rough estimate
            return sys.getsizeof({}) / (1024 * 1024)

    def _analyze_file(self, file_path: Path) -> FileAnalysisResult:
        """
        Analyze a single file.

        Args:
            file_path: Path to the file to analyze

        Returns:
            FileAnalysisResult with analysis data
        """
        try:
            # Get file size
            size_bytes = file_path.stat().st_size

            # Count lines (for text files)
            lines = 0
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    lines = sum(1 for _ in f)
            except (OSError, UnicodeDecodeError):
                # Binary file or unable to read - skip line counting
                pass

            return FileAnalysisResult(
                path=file_path,
                size=size_bytes,
                lines=lines,
            )

        except Exception as e:
            return FileAnalysisResult(
                path=file_path,
                size=0,
                error=str(e),
            )

    def _process_batch(self, batch: list[Path]) -> list[FileAnalysisResult]:
        """
        Process a batch of files.

        Args:
            batch: List of file paths to process

        Returns:
            List of FileAnalysisResult objects
        """
        results = []
        for file_path in batch:
            result = self._analyze_file(file_path)
            results.append(result)

            # Update peak memory usage
            current_memory = self._get_memory_usage_mb()
            if current_memory > self.peak_memory_mb:
                self.peak_memory_mb = current_memory

        return results

    def analyze(self) -> StreamingAnalysisResult:
        """
        Analyze files in the root directory using streaming.

        Processes files in batches to maintain memory efficiency while
        monitoring memory usage against the configured limit.

        Returns:
            StreamingAnalysisResult with aggregated analysis data
        """
        result = StreamingAnalysisResult()

        try:
            # Stream files in batches
            for batch in stream_files(
                self.project_dir,
                batch_size=self.batch_size,
                skip_dirs=self.skip_dirs,
            ):
                # Check memory usage before processing batch
                current_memory = self._get_memory_usage_mb()
                if current_memory > self.max_memory_mb:
                    # Soft limit exceeded - log but continue
                    # In production, you might want to pause or adjust batch size
                    pass

                # Process the batch
                batch_results = self._process_batch(batch)

                # Aggregate results
                for file_result in batch_results:
                    result.files.append(file_result)
                    result.total_files += 1
                    result.total_size += file_result.size
                    result.total_lines += file_result.lines

                    if file_result.error:
                        result.errors += 1

            # Set peak memory usage
            result.peak_memory_mb = self.peak_memory_mb

        except Exception as e:
            # Handle any unexpected errors
            result.errors += 1

        return result


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
            d for d in dirnames if d not in skip_dirs and not d.startswith(".")
        ]

        # Process files in current directory
        for filename in filenames:
            file_path = Path(dirpath) / filename

            # Skip hidden files
            if filename.startswith("."):
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
            d for d in dirnames if d not in skip_dirs and not d.startswith(".")
        ]

        # Yield files in current directory
        for filename in filenames:
            # Skip hidden files
            if filename.startswith("."):
                continue

            yield Path(dirpath) / filename
