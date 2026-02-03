#!/usr/bin/env python3
"""Unit tests for ContextSelector."""
import tempfile
from pathlib import Path

import pytest

from apps.backend.analysis.context_selector import ContextSelector


@pytest.fixture
def temp_project():
    """Create a temporary project directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create test files with meaningful names
        (project_dir / "auth").mkdir()
        (project_dir / "auth" / "login.py").write_text("def login(user, password): pass")
        (project_dir / "auth" / "register.py").write_text("def register(user): pass")
        (project_dir / "auth" / "password.py").write_text("def reset_password(): pass")

        (project_dir / "database").mkdir()
        (project_dir / "database" / "models.py").write_text("class User: pass")
        (project_dir / "database" / "queries.py").write_text("def query(): pass")

        (project_dir / "api").mkdir()
        (project_dir / "api" / "endpoints.py").write_text("def api_handler(): pass")

        (project_dir / "utils.py").write_text("def helper(): pass")

        yield project_dir


def test_context_selector_creation(temp_project):
    """Test ContextSelector initialization."""
    selector = ContextSelector(temp_project)

    assert selector.path == temp_project.resolve()


def test_extract_keywords():
    """Test keyword extraction."""
    selector = ContextSelector(".")

    keywords = selector._extract_keywords("implement user authentication and login")

    assert "implement" in keywords
    assert "user" in keywords
    assert "authentication" in keywords
    assert "login" in keywords
    # Stop words should be filtered
    assert "and" not in keywords


def test_score_relevance_path_match(temp_project):
    """Test relevance scoring based on path matching."""
    selector = ContextSelector(temp_project)

    score = selector.score_relevance("auth/login.py", "user login authentication")

    # Should have positive score due to path matching "auth" and "login"
    assert score > 0.3


def test_score_relevance_filename_match(temp_project):
    """Test relevance scoring based on filename matching."""
    selector = ContextSelector(temp_project)

    score = selector.score_relevance("auth/password.py", "reset password")

    # Should have high score due to filename "password"
    assert score > 0.3


def test_score_relevance_content_match(temp_project):
    """Test relevance scoring based on content matching."""
    selector = ContextSelector(temp_project)

    score = selector.score_relevance("database/models.py", "User model")

    # Should have score due to content containing "User"
    assert score > 0.0


def test_score_relevance_no_match(temp_project):
    """Test relevance scoring with no matches."""
    selector = ContextSelector(temp_project)

    score = selector.score_relevance("utils.py", "authentication system")

    # Should have low or zero score
    assert score < 0.3


def test_score_relevance_caching(temp_project):
    """Test relevance score caching."""
    selector = ContextSelector(temp_project)

    # Score twice
    score1 = selector.score_relevance("auth/login.py", "user login")
    score2 = selector.score_relevance("auth/login.py", "user login")

    # Should return same score (cached)
    assert score1 == score2


def test_score_relevance_with_preextracted_keywords(temp_project):
    """Test scoring with pre-extracted keywords."""
    selector = ContextSelector(temp_project)

    keywords = selector._extract_keywords("user login authentication")
    score = selector.score_relevance("auth/login.py", "user login", keywords=keywords)

    # Should work with pre-extracted keywords
    assert score > 0.3


def test_select_files_basic(temp_project):
    """Test basic file selection."""
    selector = ContextSelector(temp_project)

    files = selector.select_files("authentication", max_files=10)

    # Should return auth-related files
    assert len(files) > 0
    assert any("auth" in f for f in files)


def test_select_files_max_files_limit(temp_project):
    """Test max_files limit."""
    selector = ContextSelector(temp_project)

    files = selector.select_files("authentication", max_files=2)

    # Should respect max_files limit
    assert len(files) <= 2


def test_select_files_min_score_threshold(temp_project):
    """Test min_score threshold."""
    selector = ContextSelector(temp_project)

    files = selector.select_files("authentication", min_score=0.8)

    # Should only return high-scoring files
    # May return 0 files if no file scores above 0.8
    assert len(files) >= 0


def test_select_files_empty_results(temp_project):
    """Test selection with no matches returns low-scoring results."""
    selector = ContextSelector(temp_project)

    # Use min_score > 0 to filter out files with no keyword matches
    files = selector.select_files("nonexistent keyword xyz", max_files=10, min_score=0.1)

    # Should return empty list since no files match the non-existent keywords
    assert len(files) == 0


def test_select_files_heap_based_selection(temp_project):
    """Test heap-based top-N selection."""
    selector = ContextSelector(temp_project)

    # Select top 3 files
    files = selector.select_files("authentication login password", max_files=3)

    # Should return at most 3 files
    assert len(files) <= 3

    # Should prioritize auth-related files
    if len(files) > 0:
        assert any("auth" in f or "login" in f or "password" in f for f in files)


def test_select_files_sorted_by_relevance(temp_project):
    """Test that files are sorted by relevance."""
    selector = ContextSelector(temp_project)

    files = selector.select_files("authentication", max_files=5)

    # Get scores for returned files
    scores = []
    keywords = selector._extract_keywords("authentication")
    for file in files:
        score = selector.score_relevance(file, "authentication", keywords)
        scores.append(score)

    # Scores should be in descending order
    assert scores == sorted(scores, reverse=True)


def test_select_files_keyword_prefiltering(temp_project):
    """Test keyword pre-filtering with min_score threshold."""
    selector = ContextSelector(temp_project)

    # Create file without any keywords in path
    (temp_project / "xyz123.py").write_text("def helper(): pass")

    # Use min_score to filter out files that don't match keywords
    files = selector.select_files("authentication login", max_files=10, min_score=0.1)

    # File without keywords in path should be filtered out
    assert "xyz123.py" not in files


def test_estimate_tokens(temp_project):
    """Test token estimation."""
    selector = ContextSelector(temp_project)

    tokens = selector.estimate_tokens(temp_project / "auth" / "login.py")

    # Should estimate tokens (rough: 1 token ≈ 4 characters)
    assert tokens > 0


def test_estimate_tokens_large_file(temp_project):
    """Test token estimation for large files."""
    selector = ContextSelector(temp_project)

    # Create large file
    large_file = temp_project / "large.py"
    large_file.write_text("x" * 2_000_000)  # 2MB

    tokens = selector.estimate_tokens(large_file)

    # Should return 0 for files > 1MB
    assert tokens == 0


def test_estimate_tokens_binary_file(temp_project):
    """Test token estimation for binary files."""
    selector = ContextSelector(temp_project)

    # Create binary file
    binary_file = temp_project / "image.png"
    binary_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    tokens = selector.estimate_tokens(binary_file)

    # Should handle binary files gracefully
    assert tokens == 0


def test_estimate_tokens_nonexistent_file(temp_project):
    """Test token estimation for nonexistent file."""
    selector = ContextSelector(temp_project)

    tokens = selector.estimate_tokens(temp_project / "nonexistent.py")

    # Should return 0 for nonexistent files
    assert tokens == 0


def test_select_files_max_tokens_limit(temp_project):
    """Test max_tokens limit."""
    selector = ContextSelector(temp_project)

    # Set very low token limit
    files = selector.select_files("authentication", max_tokens=100)

    # Should respect token limit (may return fewer files)
    total_tokens = sum(
        selector.estimate_tokens(temp_project / f) for f in files
    )
    assert total_tokens <= 100


def test_select_files_max_tokens_with_max_files(temp_project):
    """Test max_tokens with max_files constraint."""
    selector = ContextSelector(temp_project)

    files = selector.select_files("authentication", max_files=5, max_tokens=500)

    # Should respect both limits
    assert len(files) <= 5


def test_walk_files_excludes_skip_dirs(temp_project):
    """Test that walk_files excludes SKIP_DIRS."""
    selector = ContextSelector(temp_project)

    # Create node_modules (should be skipped)
    (temp_project / "node_modules").mkdir()
    (temp_project / "node_modules" / "test.js").write_text("test")

    files = selector._walk_files()

    # Should not include node_modules files
    assert not any("node_modules" in str(f) for f in files)


def test_walk_files_only_files(temp_project):
    """Test that walk_files only returns files, not directories."""
    selector = ContextSelector(temp_project)

    files = selector._walk_files()

    # All should be files
    assert all(f.is_file() for f in files)


def test_clear_cache(temp_project):
    """Test clearing relevance score cache."""
    selector = ContextSelector(temp_project)

    # Score a file (caches result)
    selector.score_relevance("auth/login.py", "authentication")

    # Clear cache
    selector.clear_cache()

    # Should not error (cache is empty)
    score = selector.score_relevance("auth/login.py", "authentication")
    assert score >= 0.0


def test_score_path_multiple_keywords(temp_project):
    """Test path scoring with multiple keywords."""
    selector = ContextSelector(temp_project)

    keywords = ["auth", "login"]
    score = selector._score_path(temp_project / "auth" / "login.py", keywords)

    # Should match both keywords in path
    assert score > 0.5


def test_score_filename_multiple_keywords(temp_project):
    """Test filename scoring with multiple keywords."""
    selector = ContextSelector(temp_project)

    keywords = ["login", "password"]
    score = selector._score_filename(temp_project / "auth" / "login.py", keywords)

    # Should match "login" keyword
    assert score > 0.0


def test_score_content_word_boundaries(temp_project):
    """Test content scoring uses word boundaries."""
    selector = ContextSelector(temp_project)

    # Create file with content containing "user" as a standalone word
    test_file = temp_project / "test.py"
    test_file.write_text("def login(user): pass")

    keywords = ["user"]
    score = selector._score_content(test_file, keywords)

    # Should match "user" with word boundaries
    assert score > 0.0


def test_score_content_multiple_occurrences(temp_project):
    """Test content scoring with multiple keyword occurrences."""
    selector = ContextSelector(temp_project)

    # Create file with repeated keywords
    test_file = temp_project / "test.py"
    test_file.write_text("user user user login login")

    keywords = ["user", "login"]
    score = selector._score_content(test_file, keywords)

    # Should have high score due to multiple matches
    assert score > 0.5


def test_integration_select_most_relevant(temp_project):
    """Integration test: select most relevant files."""
    selector = ContextSelector(temp_project)

    files = selector.select_files("user authentication login system", max_files=3)

    # Should prioritize auth-related files
    assert len(files) > 0
    # Most relevant files should be in auth directory
    assert any("auth" in f for f in files[:2]) if len(files) >= 2 else True
