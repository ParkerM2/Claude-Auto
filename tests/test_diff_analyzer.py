#!/usr/bin/env python3
"""
Unit tests for DiffAnalyzer
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from analysis.diff_analyzer import (
    DiffAnalyzer,
    DiffResult,
    FileDiff,
    DiffHunk,
    DiffLine,
    ChangeType,
    LineType,
)


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)

    # Create initial commit
    test_file = repo_dir / "test.txt"
    test_file.write_text("line 1\nline 2\nline 3\n")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)

    return repo_dir


class TestDiffAnalyzer:
    """Test suite for DiffAnalyzer class."""

    def test_initialization(self, temp_git_repo):
        """Test DiffAnalyzer initialization."""
        analyzer = DiffAnalyzer(temp_git_repo)
        assert analyzer.project_dir == temp_git_repo.resolve()

    def test_initialization_with_string_path(self, temp_git_repo):
        """Test DiffAnalyzer initialization with string path."""
        analyzer = DiffAnalyzer(str(temp_git_repo))
        assert analyzer.project_dir == temp_git_repo.resolve()

    def test_get_diff_file_not_found(self, tmp_path):
        """Test get_diff with non-existent directory."""
        non_existent = tmp_path / "does_not_exist"
        analyzer = DiffAnalyzer(non_existent)

        with pytest.raises(FileNotFoundError):
            analyzer.get_diff()

    def test_get_diff_no_changes(self, temp_git_repo):
        """Test get_diff when there are no changes."""
        analyzer = DiffAnalyzer(temp_git_repo)
        result = analyzer.get_diff(base_ref="HEAD", head_ref="HEAD")

        assert isinstance(result, DiffResult)
        assert len(result.files) == 0
        assert result.total_additions == 0
        assert result.total_deletions == 0
        assert result.files_changed == 0

    def test_get_diff_added_file(self, temp_git_repo):
        """Test get_diff with a newly added file."""
        # Create and commit a new file
        new_file = temp_git_repo / "new.txt"
        new_file.write_text("new content\n")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Add new file"], cwd=temp_git_repo, check=True, capture_output=True)

        analyzer = DiffAnalyzer(temp_git_repo)
        result = analyzer.get_diff(base_ref="HEAD~1", head_ref="HEAD")

        assert len(result.files) == 1
        assert result.files[0].path == "new.txt"
        assert result.files[0].change_type == ChangeType.ADDED
        assert result.files[0].additions > 0
        assert result.files[0].deletions == 0

    def test_get_diff_modified_file(self, temp_git_repo):
        """Test get_diff with a modified file."""
        # Modify existing file
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("line 1\nmodified line 2\nline 3\nnew line 4\n")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Modify file"], cwd=temp_git_repo, check=True, capture_output=True)

        analyzer = DiffAnalyzer(temp_git_repo)
        result = analyzer.get_diff(base_ref="HEAD~1", head_ref="HEAD")

        assert len(result.files) == 1
        assert result.files[0].path == "test.txt"
        assert result.files[0].change_type == ChangeType.MODIFIED
        assert result.files[0].additions > 0
        assert result.files[0].deletions > 0

    def test_get_diff_deleted_file(self, temp_git_repo):
        """Test get_diff with a deleted file."""
        # Delete file
        test_file = temp_git_repo / "test.txt"
        test_file.unlink()
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Delete file"], cwd=temp_git_repo, check=True, capture_output=True)

        analyzer = DiffAnalyzer(temp_git_repo)
        result = analyzer.get_diff(base_ref="HEAD~1", head_ref="HEAD")

        assert len(result.files) == 1
        assert result.files[0].path == "test.txt"
        assert result.files[0].change_type == ChangeType.DELETED
        assert result.files[0].additions == 0
        assert result.files[0].deletions > 0

    def test_get_diff_renamed_file(self, temp_git_repo):
        """Test get_diff with a renamed file."""
        # Rename file
        old_file = temp_git_repo / "test.txt"
        new_file = temp_git_repo / "renamed.txt"
        old_file.rename(new_file)
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Rename file"], cwd=temp_git_repo, check=True, capture_output=True)

        analyzer = DiffAnalyzer(temp_git_repo)
        result = analyzer.get_diff(base_ref="HEAD~1", head_ref="HEAD")

        # Git should detect this as a rename
        assert len(result.files) >= 1
        # Find the renamed file
        renamed_files = [f for f in result.files if f.change_type == ChangeType.RENAMED]
        if renamed_files:
            assert renamed_files[0].path == "renamed.txt"
            assert renamed_files[0].old_path == "test.txt"

    def test_get_diff_hunk_parsing(self, temp_git_repo):
        """Test that hunks are properly parsed."""
        # Modify file to create hunks
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("line 1\nmodified line 2\nline 3\n")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Modify file"], cwd=temp_git_repo, check=True, capture_output=True)

        analyzer = DiffAnalyzer(temp_git_repo)
        result = analyzer.get_diff(base_ref="HEAD~1", head_ref="HEAD")

        assert len(result.files) == 1
        file_diff = result.files[0]
        assert len(file_diff.hunks) > 0

        # Check hunk structure
        hunk = file_diff.hunks[0]
        assert isinstance(hunk, DiffHunk)
        assert hunk.old_start > 0
        assert hunk.new_start > 0
        assert len(hunk.lines) > 0

    def test_get_diff_line_types(self, temp_git_repo):
        """Test that line types (added/deleted/context) are properly detected."""
        # Modify file
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("line 1\nmodified line 2\nline 3\nnew line 4\n")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Modify file"], cwd=temp_git_repo, check=True, capture_output=True)

        analyzer = DiffAnalyzer(temp_git_repo)
        result = analyzer.get_diff(base_ref="HEAD~1", head_ref="HEAD", context_lines=3)

        file_diff = result.files[0]
        hunk = file_diff.hunks[0]

        # Check that we have different line types
        line_types = set(line.type for line in hunk.lines)
        assert LineType.CONTEXT in line_types or LineType.ADDED in line_types or LineType.DELETED in line_types

        # Check line numbers
        for line in hunk.lines:
            if line.type == LineType.ADDED:
                assert line.old_line_number is None
                assert line.new_line_number is not None
            elif line.type == LineType.DELETED:
                assert line.old_line_number is not None
                assert line.new_line_number is None
            elif line.type == LineType.CONTEXT:
                assert line.old_line_number is not None
                assert line.new_line_number is not None

    def test_get_diff_stats(self, temp_git_repo):
        """Test get_diff_stats method."""
        # Modify file
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("line 1\nmodified line 2\nline 3\nnew line 4\n")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Modify file"], cwd=temp_git_repo, check=True, capture_output=True)

        analyzer = DiffAnalyzer(temp_git_repo)
        stats = analyzer.get_diff_stats(base_ref="HEAD~1", head_ref="HEAD")

        assert "files_changed" in stats
        assert "total_additions" in stats
        assert "total_deletions" in stats
        assert "files" in stats
        assert stats["files_changed"] > 0

    def test_get_diff_invalid_ref(self, temp_git_repo):
        """Test get_diff with invalid git reference."""
        analyzer = DiffAnalyzer(temp_git_repo)
        result = analyzer.get_diff(base_ref="nonexistent-ref", head_ref="HEAD")

        # Should return result with error
        assert len(result.errors) > 0

    def test_diff_result_to_dict(self):
        """Test DiffResult serialization to dict."""
        result = DiffResult(
            files=[],
            total_additions=10,
            total_deletions=5,
            files_changed=2,
            base_ref="main",
            head_ref="HEAD",
            errors=[]
        )

        data = result.to_dict()
        assert data["total_additions"] == 10
        assert data["total_deletions"] == 5
        assert data["files_changed"] == 2
        assert data["base_ref"] == "main"
        assert data["head_ref"] == "HEAD"

    def test_file_diff_to_dict(self):
        """Test FileDiff serialization to dict."""
        file_diff = FileDiff(
            path="test.txt",
            change_type=ChangeType.MODIFIED,
            additions=5,
            deletions=2
        )

        data = file_diff.to_dict()
        assert data["path"] == "test.txt"
        assert data["change_type"] == "modified"
        assert data["additions"] == 5
        assert data["deletions"] == 2
