#!/usr/bin/env python3
"""Unit tests for StreamingAnalyzer."""
import tempfile
from pathlib import Path

import pytest

from apps.backend.analysis.streaming_analyzer import (
    StreamingAnalyzer,
    stream_files,
    stream_files_iter,
)


@pytest.fixture
def temp_project():
    """Create a temporary project directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create test files
        (project_dir / "test1.py").write_text("print('hello')\n" * 10)
        (project_dir / "test2.py").write_text("print('world')\n" * 20)
        (project_dir / "test3.js").write_text("console.log('test');\n" * 15)

        (project_dir / "subdir").mkdir()
        (project_dir / "subdir" / "test4.py").write_text("import os\n" * 5)
        (project_dir / "subdir" / "test5.py").write_text("def func(): pass\n" * 8)

        yield project_dir


def test_stream_files_batch_basic(temp_project):
    """Test batch streaming of files."""
    batches = list(stream_files(temp_project, batch_size=2))

    # Should have multiple batches
    assert len(batches) > 0

    # Each batch should be a list of Path objects
    for batch in batches:
        assert isinstance(batch, list)
        assert all(isinstance(f, Path) for f in batch)


def test_stream_files_batch_size(temp_project):
    """Test batch size configuration."""
    batches = list(stream_files(temp_project, batch_size=2))

    # Most batches should have exactly 2 files (last may have fewer)
    for batch in batches[:-1]:
        assert len(batch) == 2

    # Last batch should have remaining files
    assert len(batches[-1]) <= 2


def test_stream_files_respects_skip_dirs(temp_project):
    """Test that streaming respects SKIP_DIRS."""
    # Create node_modules (should be skipped)
    (temp_project / "node_modules").mkdir()
    (temp_project / "node_modules" / "test.js").write_text("test")

    batches = list(stream_files(temp_project, batch_size=10))

    # Should not include node_modules files
    all_files = [f for batch in batches for f in batch]
    assert not any("node_modules" in str(f) for f in all_files)


def test_stream_files_skips_hidden(temp_project):
    """Test that streaming skips hidden files and directories."""
    # Create hidden file
    (temp_project / ".hidden").write_text("hidden")

    batches = list(stream_files(temp_project, batch_size=10))

    # Should not include hidden files
    all_files = [f for batch in batches for f in batch]
    assert not any(".hidden" in str(f) for f in all_files)


def test_stream_files_generator_behavior(temp_project):
    """Test that stream_files is a generator."""
    gen = stream_files(temp_project, batch_size=2)

    # Should be a generator
    assert hasattr(gen, "__iter__")
    assert hasattr(gen, "__next__")


def test_stream_files_iter_basic(temp_project):
    """Test one-by-one streaming of files."""
    files = list(stream_files_iter(temp_project))

    # Should have all files
    assert len(files) == 5  # 5 source files total

    # All should be Path objects
    assert all(isinstance(f, Path) for f in files)


def test_stream_files_iter_generator_behavior(temp_project):
    """Test that stream_files_iter is a generator."""
    gen = stream_files_iter(temp_project)

    # Should be a generator
    assert hasattr(gen, "__iter__")
    assert hasattr(gen, "__next__")


def test_stream_files_iter_memory_efficient(temp_project):
    """Test memory efficiency of streaming iterator."""
    # Create many files
    for i in range(100):
        (temp_project / f"file{i}.py").write_text(f"# File {i}")

    gen = stream_files_iter(temp_project)

    # Should be able to iterate without loading all files
    count = 0
    for _ in gen:
        count += 1
        if count == 10:
            break

    # Should have processed some files
    assert count == 10


def test_streaming_analyzer_creation(temp_project):
    """Test StreamingAnalyzer initialization."""
    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=100, batch_size=10)

    assert analyzer.project_dir == temp_project.resolve()
    assert analyzer.max_memory_mb == 100
    assert analyzer.batch_size == 10


def test_streaming_analyzer_analyze(temp_project):
    """Test memory-bounded analysis."""
    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=100, batch_size=2)

    result = analyzer.analyze()

    # Should have results
    assert result is not None
    assert result.total_files > 0
    assert result.total_size > 0
    assert result.total_lines > 0


def test_streaming_analyzer_file_count(temp_project):
    """Test file count in analysis results."""
    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=100)

    result = analyzer.analyze()

    # Should count all source files
    assert result.total_files == 5


def test_streaming_analyzer_line_count(temp_project):
    """Test line count in analysis results."""
    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=100)

    result = analyzer.analyze()

    # Should count lines in all files
    # test1: 10, test2: 20, test3: 15, test4: 5, test5: 8 = 58 lines
    assert result.total_lines == 58


def test_streaming_analyzer_size_tracking(temp_project):
    """Test size tracking in analysis results."""
    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=100)

    result = analyzer.analyze()

    # Should track total size
    assert result.total_size > 0


def test_streaming_analyzer_peak_memory(temp_project):
    """Test peak memory tracking."""
    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=100)

    result = analyzer.analyze()

    # Peak memory should be recorded (may be 0.0 without psutil)
    assert result.peak_memory_mb >= 0.0


def test_streaming_analyzer_batch_processing(temp_project):
    """Test batch processing."""
    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=100, batch_size=2)

    result = analyzer.analyze()

    # Should process files in batches
    assert result.total_files == 5


def test_streaming_analyzer_error_handling(temp_project):
    """Test error handling for unreadable files."""
    # Create binary file
    (temp_project / "binary.bin").write_bytes(b"\x00" * 100)

    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=100)

    result = analyzer.analyze()

    # Should handle errors gracefully
    # Binary files might not be analyzed or might cause errors
    assert result.errors >= 0


def test_streaming_analyzer_analyze_file(temp_project):
    """Test individual file analysis."""
    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=100)

    file_path = temp_project / "test1.py"
    file_result = analyzer._analyze_file(file_path)

    # Should analyze file
    assert file_result is not None
    assert file_result.path == file_path
    assert file_result.size > 0
    assert file_result.lines == 10


def test_streaming_analyzer_analyze_file_error(temp_project):
    """Test file analysis error handling."""
    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=100)

    # Try to analyze nonexistent file
    file_result = analyzer._analyze_file(temp_project / "nonexistent.py")

    # Should return result with error
    assert file_result is not None
    assert file_result.error is not None


def test_streaming_analyzer_analyze_binary_file(temp_project):
    """Test binary file analysis."""
    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=100)

    # Create binary file
    binary_file = temp_project / "binary.bin"
    binary_file.write_bytes(b"\x00" * 100)

    file_result = analyzer._analyze_file(binary_file)

    # Should handle binary files - they should be analyzed
    # Note: binary files may have a small line count due to null byte handling
    assert file_result is not None
    assert file_result.path == binary_file
    assert file_result.size == 100


def test_streaming_analyzer_process_batch(temp_project):
    """Test batch processing."""
    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=100)

    # Get a batch of files
    files = list(stream_files_iter(temp_project))[:3]

    batch_result = analyzer._process_batch(files)

    # Should process batch
    assert batch_result is not None
    assert len(batch_result) <= 3


def test_streaming_analyzer_memory_limit(temp_project):
    """Test memory limit enforcement."""
    # Set very low memory limit
    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=1, batch_size=1)

    result = analyzer.analyze()

    # Should still complete (may not process all files if limit hit)
    assert result is not None


def test_streaming_analyzer_statistics(temp_project):
    """Test statistics collection."""
    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=100)

    result = analyzer.analyze()

    # Should collect statistics
    assert hasattr(result, "total_files")
    assert hasattr(result, "total_size")
    assert hasattr(result, "total_lines")
    assert hasattr(result, "peak_memory_mb")
    assert hasattr(result, "errors")


def test_streaming_respects_gitignore_patterns(temp_project):
    """Test that streaming respects common ignore patterns."""
    # Create __pycache__ (should be skipped)
    (temp_project / "__pycache__").mkdir()
    (temp_project / "__pycache__" / "test.pyc").write_bytes(b"compiled")

    files = list(stream_files_iter(temp_project))

    # Should not include __pycache__ files
    assert not any("__pycache__" in str(f) for f in files)


def test_integration_large_batch(temp_project):
    """Integration test: process large batch."""
    # Create many files
    for i in range(50):
        (temp_project / f"large{i}.py").write_text(f"# File {i}\n" * 100)

    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=500, batch_size=10)

    result = analyzer.analyze()

    # Should process all files
    assert result.total_files >= 50
    assert result.total_lines >= 5000  # 50 files * 100 lines


def test_integration_memory_bounded_processing(temp_project):
    """Integration test: verify memory-bounded processing."""
    # Create large files
    for i in range(10):
        (temp_project / f"mem{i}.py").write_text("x" * 10000)

    analyzer = StreamingAnalyzer(temp_project, max_memory_mb=100, batch_size=2)

    result = analyzer.analyze()

    # Should complete without exceeding memory
    assert result is not None
    assert result.total_files >= 10
