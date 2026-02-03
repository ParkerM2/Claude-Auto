#!/usr/bin/env python3
"""Unit tests for FileIndex."""
import json
import tempfile
import time
from pathlib import Path

import pytest

from apps.backend.analysis.file_index import FileIndex, FileMetadata


@pytest.fixture
def temp_project():
    """Create a temporary project directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create test files
        (project_dir / "test1.py").write_text("print('hello')")
        (project_dir / "test2.js").write_text("console.log('world')")
        (project_dir / "subdir").mkdir()
        (project_dir / "subdir" / "test3.py").write_text("import os")

        yield project_dir


def test_file_index_creation(temp_project):
    """Test FileIndex initialization."""
    index = FileIndex(temp_project)

    assert index.project_dir == temp_project.resolve()
    assert len(index) == 0
    assert index.index_path == (temp_project / ".auto-claude" / "file_index.json").resolve()


def test_track_file_lazy_hash(temp_project):
    """Test tracking file with lazy hash computation."""
    index = FileIndex(temp_project)
    test_file = temp_project / "test1.py"

    # Track without computing hash
    metadata = index.track_file(test_file, compute_hash=False)

    assert metadata.path == "test1.py"
    assert metadata.hash == ""  # Hash not computed
    assert metadata.size > 0
    assert metadata.mtime > 0
    assert len(index) == 1


def test_track_file_eager_hash(temp_project):
    """Test tracking file with eager hash computation."""
    index = FileIndex(temp_project)
    test_file = temp_project / "test1.py"

    # Track with computing hash
    metadata = index.track_file(test_file, compute_hash=True)

    assert metadata.path == "test1.py"
    assert metadata.hash != ""  # Hash computed
    assert len(metadata.hash) == 64  # SHA-256 hex string
    assert len(index) == 1


def test_has_changed_unchanged_file(temp_project):
    """Test detecting unchanged file."""
    index = FileIndex(temp_project)
    test_file = temp_project / "test1.py"

    # Track file with hash
    index.track_file(test_file, compute_hash=True)

    # File should not have changed
    assert not index.has_changed(test_file)


def test_has_changed_modified_file(temp_project):
    """Test detecting modified file."""
    index = FileIndex(temp_project)
    test_file = temp_project / "test1.py"

    # Track file with hash
    index.track_file(test_file, compute_hash=True)

    # Modify file
    time.sleep(0.1)  # Ensure mtime changes
    test_file.write_text("print('modified')")

    # File should have changed
    assert index.has_changed(test_file)


def test_has_changed_new_file(temp_project):
    """Test detecting new file."""
    index = FileIndex(temp_project)
    test_file = temp_project / "test1.py"

    # File not tracked yet
    assert index.has_changed(test_file)


def test_has_changed_deleted_file(temp_project):
    """Test detecting deleted file."""
    index = FileIndex(temp_project)
    test_file = temp_project / "test1.py"

    # Track file
    index.track_file(test_file, compute_hash=True)

    # Delete file
    test_file.unlink()

    # Should detect deletion
    assert index.has_changed(test_file)


def test_has_changed_lazy_hash_on_demand(temp_project):
    """Test hash computation on demand when mtime changes."""
    index = FileIndex(temp_project)
    test_file = temp_project / "test1.py"

    # Track file WITHOUT hash
    index.track_file(test_file, compute_hash=False)

    # Modify file
    time.sleep(0.1)
    test_file.write_text("print('modified')")

    # Should compute hash on demand and detect change
    assert index.has_changed(test_file)

    # Hash should now be computed
    metadata = index.get_metadata(test_file)
    assert metadata.hash != ""


def test_save_and_load(temp_project):
    """Test persistence."""
    index = FileIndex(temp_project)
    test_file = temp_project / "test1.py"

    # Track file
    index.track_file(test_file, compute_hash=True)

    # Save
    index.save()

    # Load in new instance
    index2 = FileIndex.load(temp_project)

    # Should have same data
    assert len(index2) == 1
    assert "test1.py" in index2

    metadata = index2.get_metadata(test_file)
    assert metadata is not None
    assert metadata.path == "test1.py"


def test_save_and_load_with_dir_mtimes(temp_project):
    """Test persistence of directory mtimes."""
    index = FileIndex(temp_project)
    subdir = temp_project / "subdir"

    # Track directory
    index.track_directory(subdir)

    # Save
    index.save()

    # Load in new instance
    index2 = FileIndex.load(temp_project)

    # Should have directory mtime
    assert not index2.dir_has_changed(subdir)


def test_roundtrip_serialization(temp_project):
    """Test save and load roundtrip."""
    index = FileIndex(temp_project)

    # Track multiple files
    for file_path in temp_project.rglob("*.py"):
        index.track_file(file_path, compute_hash=True)

    # Save
    index.save()

    # Load
    index2 = FileIndex.load(temp_project)

    # Should have same files
    assert len(index2) == len(index)
    assert set(index2.get_tracked_files()) == set(index.get_tracked_files())


def test_corrupted_index_handling(temp_project):
    """Test handling of corrupted index file."""
    index = FileIndex(temp_project)

    # Create corrupted index file
    index.index_path.parent.mkdir(parents=True, exist_ok=True)
    index.index_path.write_text("{ invalid json }")

    # Should return empty index on error
    index2 = FileIndex.load(temp_project)
    assert len(index2) == 0


def test_track_directory(temp_project):
    """Test tracking directory mtime."""
    index = FileIndex(temp_project)
    subdir = temp_project / "subdir"

    # Track directory
    index.track_directory(subdir)

    # Should not have changed
    assert not index.dir_has_changed(subdir)


def test_dir_has_changed_new_directory(temp_project):
    """Test detecting new directory."""
    index = FileIndex(temp_project)
    new_dir = temp_project / "newdir"
    new_dir.mkdir()

    # New directory should be considered changed
    assert index.dir_has_changed(new_dir)


def test_dir_has_changed_modified_directory(temp_project):
    """Test detecting modified directory."""
    index = FileIndex(temp_project)
    subdir = temp_project / "subdir"

    # Track directory
    index.track_directory(subdir)

    # Modify directory (add file)
    time.sleep(0.1)
    (subdir / "newfile.py").write_text("pass")

    # Should detect change
    assert index.dir_has_changed(subdir)


def test_get_files_in_dir(temp_project):
    """Test getting files in directory."""
    index = FileIndex(temp_project)

    # Track files
    index.track_file(temp_project / "test1.py", compute_hash=False)
    index.track_file(temp_project / "subdir" / "test3.py", compute_hash=False)

    # Get files in subdir
    files = index.get_files_in_dir(temp_project / "subdir")

    assert len(files) == 1
    assert "subdir/test3.py" in files or "subdir\\test3.py" in files


def test_untrack_file(temp_project):
    """Test removing file from tracking."""
    index = FileIndex(temp_project)
    test_file = temp_project / "test1.py"

    # Track file
    index.track_file(test_file, compute_hash=True)
    assert len(index) == 1

    # Untrack file
    removed = index.untrack_file(test_file)

    assert removed
    assert len(index) == 0
    assert test_file not in index


def test_get_metadata(temp_project):
    """Test getting file metadata."""
    index = FileIndex(temp_project)
    test_file = temp_project / "test1.py"

    # Track file
    index.track_file(test_file, compute_hash=True)

    # Get metadata
    metadata = index.get_metadata(test_file)

    assert metadata is not None
    assert metadata.path == "test1.py"
    assert metadata.hash != ""
    assert metadata.size > 0


def test_clear(temp_project):
    """Test clearing index."""
    index = FileIndex(temp_project)

    # Track files
    index.track_file(temp_project / "test1.py", compute_hash=True)
    index.track_file(temp_project / "test2.js", compute_hash=True)
    assert len(index) == 2

    # Clear
    index.clear()

    assert len(index) == 0
    assert len(index.get_tracked_files()) == 0


def test_clear_cache(temp_project):
    """Test clearing has_changed cache."""
    index = FileIndex(temp_project)
    test_file = temp_project / "test1.py"

    # Track file and check has_changed (caches result)
    index.track_file(test_file, compute_hash=True)
    index.has_changed(test_file)

    # Clear cache
    index.clear_cache()

    # Cache should be empty (no way to directly test, but shouldn't error)
    assert not index.has_changed(test_file)
