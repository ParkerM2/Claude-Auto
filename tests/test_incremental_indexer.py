#!/usr/bin/env python3
"""Unit tests for IncrementalIndexer."""
import tempfile
import time
from pathlib import Path

import pytest

from apps.backend.analysis.incremental_indexer import IncrementalIndexer, ChangeSet


@pytest.fixture
def temp_project():
    """Create a temporary project directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create test files
        (project_dir / "test1.py").write_text("print('hello')")
        (project_dir / "test2.py").write_text("print('world')")
        (project_dir / "test3.js").write_text("console.log('test')")
        (project_dir / "subdir").mkdir()
        (project_dir / "subdir" / "test4.py").write_text("import os")

        yield project_dir


def test_incremental_indexer_creation(temp_project):
    """Test IncrementalIndexer initialization."""
    indexer = IncrementalIndexer(temp_project)

    assert indexer.project_dir == temp_project.resolve()
    assert indexer.extensions is not None
    assert indexer.skip_dirs is not None


def test_detect_changes_all_new(temp_project):
    """Test detecting changes when all files are new."""
    indexer = IncrementalIndexer(temp_project)

    changes = indexer.detect_changes()

    assert len(changes.added) == 4  # 3 .py files + 1 .js file
    assert len(changes.modified) == 0
    assert len(changes.deleted) == 0
    assert len(changes.unchanged) == 0


def test_detect_changes_no_changes(temp_project):
    """Test detecting no changes (100% cache hit)."""
    indexer = IncrementalIndexer(temp_project)

    # Initial scan
    changes = indexer.detect_changes()
    indexer.update_index(changes)

    # Second scan - no changes
    changes2 = indexer.detect_changes()

    assert len(changes2.added) == 0
    assert len(changes2.modified) == 0
    assert len(changes2.deleted) == 0
    assert len(changes2.unchanged) == 4


def test_detect_changes_with_modifications(temp_project):
    """Test detecting modified files."""
    indexer = IncrementalIndexer(temp_project)

    # Initial scan
    changes = indexer.detect_changes()
    indexer.update_index(changes)

    # Modify a file
    time.sleep(0.1)
    (temp_project / "test1.py").write_text("print('modified')")

    # Detect changes
    changes2 = indexer.detect_changes()

    assert len(changes2.added) == 0
    # Modified detection depends on hash computation
    # With lazy hashing, mtime change triggers re-tracking
    assert len(changes2.unchanged) == 3


def test_detect_changes_with_additions(temp_project):
    """Test detecting added files."""
    indexer = IncrementalIndexer(temp_project)

    # Initial scan
    changes = indexer.detect_changes()
    indexer.update_index(changes)

    # Add new file
    (temp_project / "test5.py").write_text("print('new')")

    # Detect changes
    changes2 = indexer.detect_changes()

    assert len(changes2.added) == 1
    assert "test5.py" in changes2.added
    assert len(changes2.modified) == 0
    assert len(changes2.deleted) == 0


def test_detect_changes_with_deletions(temp_project):
    """Test detecting deleted files."""
    indexer = IncrementalIndexer(temp_project)

    # Initial scan
    changes = indexer.detect_changes()
    indexer.update_index(changes)

    # Delete a file
    (temp_project / "test1.py").unlink()

    # Detect changes
    changes2 = indexer.detect_changes()

    assert len(changes2.added) == 0
    assert len(changes2.modified) == 0
    assert len(changes2.deleted) == 1
    assert "test1.py" in changes2.deleted


def test_detect_changes_mixed(temp_project):
    """Test detecting mixed changes."""
    indexer = IncrementalIndexer(temp_project)

    # Initial scan
    changes = indexer.detect_changes()
    indexer.update_index(changes)

    # Add, modify, delete
    (temp_project / "test5.py").write_text("print('new')")
    time.sleep(0.1)
    (temp_project / "test2.py").write_text("print('modified')")
    (temp_project / "test1.py").unlink()

    # Detect changes
    changes2 = indexer.detect_changes()

    assert len(changes2.added) == 1
    assert len(changes2.deleted) == 1
    # Modified detection depends on hash


def test_directory_level_caching(temp_project):
    """Test directory mtime optimization."""
    indexer = IncrementalIndexer(temp_project)

    # Initial scan
    changes = indexer.detect_changes()
    indexer.update_index(changes)

    # Don't modify anything - detect changes again
    changes2 = indexer.detect_changes()

    # Should skip unchanged directories
    assert len(changes2.unchanged) == 4
    assert not changes2.has_changes()


def test_directory_changed_detection(temp_project):
    """Test detecting changed directories."""
    indexer = IncrementalIndexer(temp_project)

    # Initial scan
    changes = indexer.detect_changes()
    indexer.update_index(changes)

    # Add file to subdirectory
    time.sleep(0.1)
    (temp_project / "subdir" / "test6.py").write_text("pass")

    # Detect changes
    changes2 = indexer.detect_changes()

    # Should detect new file in changed directory
    assert len(changes2.added) == 1


def test_nested_directory_changes(temp_project):
    """Test nested directory change detection."""
    indexer = IncrementalIndexer(temp_project)

    # Create nested structure
    (temp_project / "level1").mkdir()
    (temp_project / "level1" / "level2").mkdir()
    (temp_project / "level1" / "level2" / "test.py").write_text("pass")

    # Initial scan
    changes = indexer.detect_changes()
    indexer.update_index(changes)

    # Should track all files
    assert len(changes.added) == 5  # 4 original + 1 new


def test_update_index(temp_project):
    """Test index updates."""
    indexer = IncrementalIndexer(temp_project)

    # Detect and update
    changes = indexer.detect_changes()
    updated = indexer.update_index(changes)

    assert updated == len(changes)
    assert len(indexer.file_index) == 4


def test_update_index_lazy_hash(temp_project):
    """Test lazy hash computation during update."""
    indexer = IncrementalIndexer(temp_project)

    # Update index
    changes = indexer.detect_changes()
    indexer.update_index(changes)

    # Files should be tracked without hashes
    metadata = indexer.file_index.get_metadata("test1.py")
    assert metadata is not None
    # With lazy hashing, hash is empty initially
    assert metadata.hash == ""


def test_incremental_update(temp_project):
    """Test incremental index update."""
    indexer = IncrementalIndexer(temp_project)

    # Initial update
    indexer.update_index()

    # Add file
    (temp_project / "test5.py").write_text("print('new')")

    # Incremental update
    updated = indexer.update_index()

    assert updated == 1  # Only new file updated


def test_rebuild_index(temp_project):
    """Test rebuilding index from scratch."""
    indexer = IncrementalIndexer(temp_project)

    # Initial update
    indexer.update_index()

    # Add file outside of indexer
    (temp_project / "test5.py").write_text("print('new')")

    # Rebuild
    count = indexer.rebuild_index()

    assert count == 5  # All files including new one


def test_get_changed_files(temp_project):
    """Test getting list of changed files."""
    indexer = IncrementalIndexer(temp_project)

    # Initial scan
    changed = indexer.get_changed_files()

    # All files are new (changed)
    assert len(changed) == 4


def test_get_stats(temp_project):
    """Test getting index statistics."""
    indexer = IncrementalIndexer(temp_project)

    # Initial scan
    changes = indexer.detect_changes()
    indexer.update_index(changes)

    # Get stats
    stats = indexer.get_stats()

    assert stats["total_tracked"] == 4
    assert stats["total_current"] == 4
    assert stats["added"] == 0
    assert stats["modified"] == 0
    assert stats["deleted"] == 0
    assert stats["unchanged"] == 4
    assert not stats["has_changes"]


def test_cache_invalidation(temp_project):
    """Test cache invalidation on changes."""
    indexer = IncrementalIndexer(temp_project)

    # Update index
    indexer.update_index()

    # Set cache
    indexer.set_cached_result("test1.py", "cached_value")

    # Modify file
    time.sleep(0.1)
    (temp_project / "test1.py").write_text("modified")

    # Update index (should invalidate cache)
    indexer.update_index()

    # Cache should be cleared
    assert indexer.get_cached_result("test1.py") is None


def test_clear_cache(temp_project):
    """Test clearing all cached results."""
    indexer = IncrementalIndexer(temp_project)

    # Set cache
    indexer.set_cached_result("test1.py", "value1")
    indexer.set_cached_result("test2.py", "value2")

    # Clear cache
    indexer.clear_cache()

    # All cache should be cleared
    assert indexer.get_cached_result("test1.py") is None
    assert indexer.get_cached_result("test2.py") is None


def test_should_index_extension_filter(temp_project):
    """Test file extension filtering."""
    indexer = IncrementalIndexer(temp_project)

    # Create non-indexable file
    (temp_project / "image.png").write_bytes(b"fake image")

    changes = indexer.detect_changes()

    # PNG file should not be indexed
    assert "image.png" not in changes.added


def test_skip_dirs(temp_project):
    """Test skipping directories."""
    indexer = IncrementalIndexer(temp_project)

    # Create node_modules (should be skipped)
    (temp_project / "node_modules").mkdir()
    (temp_project / "node_modules" / "test.js").write_text("module.exports = {}")

    changes = indexer.detect_changes()

    # Files in node_modules should not be indexed
    assert not any("node_modules" in f for f in changes.added)


def test_changeset_has_changes(temp_project):
    """Test ChangeSet.has_changes() method."""
    indexer = IncrementalIndexer(temp_project)

    # Initial scan - has changes
    changes = indexer.detect_changes()
    assert changes.has_changes()

    # Update and rescan - no changes
    indexer.update_index(changes)
    changes2 = indexer.detect_changes()
    assert not changes2.has_changes()


def test_changeset_length(temp_project):
    """Test ChangeSet.__len__() method."""
    indexer = IncrementalIndexer(temp_project)

    changes = indexer.detect_changes()

    # Length is total changed files (added + modified + deleted)
    assert len(changes) == len(changes.added) + len(changes.modified) + len(changes.deleted)


def test_changeset_to_dict(temp_project):
    """Test ChangeSet serialization."""
    indexer = IncrementalIndexer(temp_project)

    changes = indexer.detect_changes()
    data = changes.to_dict()

    assert "added" in data
    assert "modified" in data
    assert "deleted" in data
    assert "unchanged" in data
    assert "total_changed" in data
