#!/usr/bin/env python3
"""
Tests for Pattern Detector
===========================

Tests the pattern_detector.py module functionality including:
- Loop pattern detection (repeated identical approaches)
- Thrashing pattern detection (cycling between 2-3 approaches)
- Repeated failure detection (same error multiple times)
- Timeout detection (subtask exceeding time limit)
- Context exhaustion detection (context/token limit errors)
- Pattern confidence scoring
- Approach and error normalization
"""

import pytest
from datetime import datetime, timedelta
from apps.backend.services.pattern_detector import (
    PatternDetector,
    PatternType,
    PatternMatch,
)


class TestPatternDetectorInit:
    """Tests for PatternDetector initialization."""

    def test_default_thresholds(self):
        """Creates detector with default thresholds."""
        detector = PatternDetector()
        assert detector.loop_threshold == 3
        assert detector.thrashing_threshold == 4
        assert detector.repeated_failure_threshold == 3
        assert detector.timeout_minutes == 30

    def test_custom_thresholds(self):
        """Creates detector with custom thresholds."""
        detector = PatternDetector(
            loop_threshold=5,
            thrashing_threshold=6,
            repeated_failure_threshold=4,
            timeout_minutes=60,
        )
        assert detector.loop_threshold == 5
        assert detector.thrashing_threshold == 6
        assert detector.repeated_failure_threshold == 4
        assert detector.timeout_minutes == 60


class TestLoopDetection:
    """Tests for loop pattern detection."""

    def test_no_loop_too_few_attempts(self):
        """No loop detected with too few attempts."""
        detector = PatternDetector(loop_threshold=3)
        history = [
            {"approach": "Try fixing the import", "error": "ImportError"},
            {"approach": "Try fixing the import", "error": "ImportError"},
        ]
        pattern = detector._detect_loop(history)
        assert pattern is None

    def test_loop_detected_exact_threshold(self):
        """Detects loop at exact threshold."""
        detector = PatternDetector(loop_threshold=3)
        history = [
            {"approach": "Try fixing the import", "error": "ImportError"},
            {"approach": "Try fixing the import", "error": "ImportError"},
            {"approach": "Try fixing the import", "error": "ImportError"},
        ]
        pattern = detector._detect_loop(history)
        assert pattern is not None
        assert pattern.pattern_type == PatternType.LOOP
        assert pattern.confidence > 0
        assert "3 times" in pattern.evidence
        assert "different approach" in pattern.recommendation.lower()

    def test_loop_detected_above_threshold(self):
        """Detects loop above threshold with higher confidence."""
        detector = PatternDetector(loop_threshold=3)
        history = [
            {"approach": "Try fixing the import"},
            {"approach": "Try fixing the import"},
            {"approach": "Try fixing the import"},
            {"approach": "Try fixing the import"},
            {"approach": "Try fixing the import"},
        ]
        pattern = detector._detect_loop(history)
        assert pattern is not None
        assert pattern.pattern_type == PatternType.LOOP
        assert pattern.confidence > 0.5
        assert "5 times" in pattern.evidence

    def test_no_loop_different_approaches(self):
        """No loop when approaches are different."""
        detector = PatternDetector(loop_threshold=3)
        history = [
            {"approach": "Try fixing the import"},
            {"approach": "Update the dependency"},
            {"approach": "Check the file path"},
        ]
        pattern = detector._detect_loop(history)
        assert pattern is None

    def test_loop_normalization_whitespace(self):
        """Detects loop with different whitespace."""
        detector = PatternDetector(loop_threshold=3)
        history = [
            {"approach": "Try   fixing  the import"},
            {"approach": "Try fixing the import"},
            {"approach": "Try  fixing   the  import"},
        ]
        pattern = detector._detect_loop(history)
        assert pattern is not None
        assert pattern.pattern_type == PatternType.LOOP

    def test_loop_normalization_case(self):
        """Detects loop with different casing."""
        detector = PatternDetector(loop_threshold=3)
        history = [
            {"approach": "Try Fixing The Import"},
            {"approach": "try fixing the import"},
            {"approach": "TRY FIXING THE IMPORT"},
        ]
        pattern = detector._detect_loop(history)
        assert pattern is not None
        assert pattern.pattern_type == PatternType.LOOP

    def test_loop_metadata(self):
        """Loop pattern includes correct metadata."""
        detector = PatternDetector(loop_threshold=3)
        history = [
            {"approach": "Fix import"},
            {"approach": "Fix import"},
            {"approach": "Fix import"},
        ]
        pattern = detector._detect_loop(history)
        assert pattern.metadata["approach"] == "fix import"
        assert pattern.metadata["attempt_count"] == 3
        assert pattern.metadata["threshold"] == 3


class TestThrashingDetection:
    """Tests for thrashing pattern detection."""

    def test_no_thrashing_too_few_attempts(self):
        """No thrashing detected with too few attempts."""
        detector = PatternDetector(thrashing_threshold=4)
        history = [
            {"approach": "Approach A"},
            {"approach": "Approach B"},
            {"approach": "Approach A"},
        ]
        pattern = detector._detect_thrashing(history)
        assert pattern is None

    def test_thrashing_two_approaches(self):
        """Detects thrashing between two approaches."""
        detector = PatternDetector(thrashing_threshold=4)
        history = [
            {"approach": "Try import fix"},
            {"approach": "Try path fix"},
            {"approach": "Try import fix"},
            {"approach": "Try path fix"},
        ]
        pattern = detector._detect_thrashing(history)
        assert pattern is not None
        assert pattern.pattern_type == PatternType.THRASHING
        assert "2 approaches" in pattern.evidence
        assert "cycle" in pattern.recommendation.lower()

    def test_thrashing_three_approaches(self):
        """Detects thrashing between three approaches."""
        detector = PatternDetector(thrashing_threshold=6)
        history = [
            {"approach": "Approach A"},
            {"approach": "Approach B"},
            {"approach": "Approach C"},
            {"approach": "Approach A"},
            {"approach": "Approach B"},
            {"approach": "Approach C"},
        ]
        pattern = detector._detect_thrashing(history)
        assert pattern is not None
        assert pattern.pattern_type == PatternType.THRASHING
        assert "3 approaches" in pattern.evidence

    def test_no_thrashing_single_approach(self):
        """No thrashing with single approach (that's a loop)."""
        detector = PatternDetector(thrashing_threshold=4)
        history = [
            {"approach": "Same approach"},
            {"approach": "Same approach"},
            {"approach": "Same approach"},
            {"approach": "Same approach"},
        ]
        pattern = detector._detect_thrashing(history)
        assert pattern is None

    def test_no_thrashing_too_many_approaches(self):
        """No thrashing with more than 3 unique approaches."""
        detector = PatternDetector(thrashing_threshold=4)
        history = [
            {"approach": "Approach A"},
            {"approach": "Approach B"},
            {"approach": "Approach C"},
            {"approach": "Approach D"},
        ]
        pattern = detector._detect_thrashing(history)
        assert pattern is None

    def test_no_thrashing_insufficient_cycles(self):
        """No thrashing if approaches not tried at least twice each."""
        detector = PatternDetector(thrashing_threshold=4)
        history = [
            {"approach": "Approach A"},
            {"approach": "Approach B"},
            {"approach": "Approach C"},
            {"approach": "Approach A"},
        ]
        pattern = detector._detect_thrashing(history)
        assert pattern is None

    def test_thrashing_metadata(self):
        """Thrashing pattern includes correct metadata."""
        detector = PatternDetector(thrashing_threshold=4)
        history = [
            {"approach": "Fix A"},
            {"approach": "Fix B"},
            {"approach": "Fix A"},
            {"approach": "Fix B"},
        ]
        pattern = detector._detect_thrashing(history)
        assert len(pattern.metadata["approaches"]) == 2
        assert pattern.metadata["attempt_count"] == 4
        assert pattern.metadata["cycle_count"] == 2


class TestRepeatedFailureDetection:
    """Tests for repeated failure pattern detection."""

    def test_no_repeated_failure_too_few_attempts(self):
        """No repeated failure with too few attempts."""
        detector = PatternDetector(repeated_failure_threshold=3)
        history = [
            {"approach": "Fix A", "error": "ImportError: No module named 'foo'"},
            {"approach": "Fix B", "error": "ImportError: No module named 'foo'"},
        ]
        pattern = detector._detect_repeated_failure(history)
        assert pattern is None

    def test_repeated_failure_detected(self):
        """Detects repeated failure at threshold."""
        detector = PatternDetector(repeated_failure_threshold=3)
        history = [
            {"approach": "Fix A", "error": "ImportError: No module named 'foo'"},
            {"approach": "Fix B", "error": "ImportError: No module named 'foo'"},
            {"approach": "Fix C", "error": "ImportError: No module named 'foo'"},
        ]
        pattern = detector._detect_repeated_failure(history)
        assert pattern is not None
        assert pattern.pattern_type == PatternType.REPEATED_FAILURE
        assert "3 times" in pattern.evidence
        assert "different solution" in pattern.recommendation.lower()

    def test_no_repeated_failure_different_errors(self):
        """No repeated failure with different errors."""
        detector = PatternDetector(repeated_failure_threshold=3)
        history = [
            {"approach": "Fix A", "error": "ImportError: No module named 'foo'"},
            {"approach": "Fix B", "error": "AttributeError: 'NoneType' object has no attribute 'bar'"},
            {"approach": "Fix C", "error": "ValueError: invalid literal for int()"},
        ]
        pattern = detector._detect_repeated_failure(history)
        assert pattern is None

    def test_no_repeated_failure_no_errors(self):
        """No repeated failure when no errors present."""
        detector = PatternDetector(repeated_failure_threshold=3)
        history = [
            {"approach": "Fix A"},
            {"approach": "Fix B"},
            {"approach": "Fix C"},
        ]
        pattern = detector._detect_repeated_failure(history)
        assert pattern is None

    def test_repeated_failure_normalization(self):
        """Detects repeated failure despite line number differences."""
        detector = PatternDetector(repeated_failure_threshold=3)
        history = [
            {"approach": "Fix A", "error": "Error in /path/to/file.py:42: SyntaxError"},
            {"approach": "Fix B", "error": "Error in /path/to/file.py:45: SyntaxError"},
            {"approach": "Fix C", "error": "Error in /path/to/file.py:50: SyntaxError"},
        ]
        pattern = detector._detect_repeated_failure(history)
        assert pattern is not None
        assert pattern.pattern_type == PatternType.REPEATED_FAILURE

    def test_repeated_failure_metadata(self):
        """Repeated failure pattern includes correct metadata."""
        detector = PatternDetector(repeated_failure_threshold=3)
        history = [
            {"approach": "Fix A", "error": "ImportError"},
            {"approach": "Fix B", "error": "ImportError"},
            {"approach": "Fix C", "error": "ImportError"},
        ]
        pattern = detector._detect_repeated_failure(history)
        assert "importerror" in pattern.metadata["error"]
        assert pattern.metadata["occurrence_count"] == 3
        assert pattern.metadata["threshold"] == 3


class TestTimeoutDetection:
    """Tests for timeout pattern detection."""

    def test_no_timeout_within_limit(self):
        """No timeout when within time limit."""
        detector = PatternDetector(timeout_minutes=30)
        start_time = datetime.now().isoformat()
        history = [{"approach": "Fix A"}]
        pattern = detector._detect_timeout(history, start_time)
        assert pattern is None

    def test_timeout_detected(self):
        """Detects timeout after time limit exceeded."""
        detector = PatternDetector(timeout_minutes=30)
        start_time = (datetime.now() - timedelta(minutes=35)).isoformat()
        history = [{"approach": "Fix A"}]
        pattern = detector._detect_timeout(history, start_time)
        assert pattern is not None
        assert pattern.pattern_type == PatternType.TIMEOUT
        assert "35" in pattern.evidence
        assert "30 minutes" in pattern.evidence
        assert "skip" in pattern.recommendation.lower() or "escalate" in pattern.recommendation.lower()

    def test_timeout_invalid_timestamp(self):
        """No timeout with invalid timestamp."""
        detector = PatternDetector(timeout_minutes=30)
        history = [{"approach": "Fix A"}]
        pattern = detector._detect_timeout(history, "invalid-timestamp")
        assert pattern is None

    def test_timeout_metadata(self):
        """Timeout pattern includes correct metadata."""
        detector = PatternDetector(timeout_minutes=30)
        start_time = (datetime.now() - timedelta(minutes=45)).isoformat()
        history = [{"approach": "Fix A"}, {"approach": "Fix B"}]
        pattern = detector._detect_timeout(history, start_time)
        assert pattern.metadata["elapsed_minutes"] > 44
        assert pattern.metadata["timeout_minutes"] == 30
        assert pattern.metadata["attempt_count"] == 2


class TestContextExhaustionDetection:
    """Tests for context exhaustion pattern detection."""

    def test_no_context_exhaustion_no_errors(self):
        """No context exhaustion when no errors."""
        detector = PatternDetector()
        history = [{"approach": "Fix A"}, {"approach": "Fix B"}]
        pattern = detector._detect_context_exhaustion(history)
        assert pattern is None

    def test_no_context_exhaustion_other_errors(self):
        """No context exhaustion with other types of errors."""
        detector = PatternDetector()
        history = [
            {"approach": "Fix A", "error": "ImportError"},
            {"approach": "Fix B", "error": "SyntaxError"},
            {"approach": "Fix C", "error": "ValueError"},
        ]
        pattern = detector._detect_context_exhaustion(history)
        assert pattern is None

    def test_context_exhaustion_detected_context_keyword(self):
        """Detects context exhaustion with 'context' keyword."""
        detector = PatternDetector()
        history = [
            {"approach": "Fix A", "error": "Error: Context length exceeded"},
            {"approach": "Fix B", "error": "Failed: Context limit reached"},
            {"approach": "Fix C", "error": "Other error"},
        ]
        pattern = detector._detect_context_exhaustion(history)
        assert pattern is not None
        assert pattern.pattern_type == PatternType.CONTEXT_EXHAUSTION
        assert pattern.confidence == 0.9
        assert "smaller pieces" in pattern.recommendation.lower() or "fresh" in pattern.recommendation.lower()

    def test_context_exhaustion_detected_token_limit_keyword(self):
        """Detects context exhaustion with 'token limit' keyword."""
        detector = PatternDetector()
        history = [
            {"approach": "Fix A", "error": "Error: Token limit exceeded"},
            {"approach": "Fix B", "error": "Maximum token limit reached"},
            {"approach": "Fix C"},
        ]
        pattern = detector._detect_context_exhaustion(history)
        assert pattern is not None
        assert pattern.pattern_type == PatternType.CONTEXT_EXHAUSTION

    def test_context_exhaustion_single_occurrence(self):
        """No context exhaustion with single occurrence."""
        detector = PatternDetector()
        history = [
            {"approach": "Fix A", "error": "Error: Context length exceeded"},
            {"approach": "Fix B", "error": "Different error"},
            {"approach": "Fix C", "error": "Another different error"},
        ]
        pattern = detector._detect_context_exhaustion(history)
        assert pattern is None

    def test_context_exhaustion_metadata(self):
        """Context exhaustion pattern includes correct metadata."""
        detector = PatternDetector()
        history = [
            {"approach": "Fix A", "error": "Context limit reached"},
            {"approach": "Fix B", "error": "Token limit exceeded"},
            {"approach": "Fix C", "error": "Other error"},
        ]
        pattern = detector._detect_context_exhaustion(history)
        assert pattern.metadata["context_error_count"] == 2
        assert pattern.metadata["total_attempts"] == 3


class TestApproachNormalization:
    """Tests for approach string normalization."""

    def test_normalize_approach_lowercase(self):
        """Normalizes to lowercase."""
        detector = PatternDetector()
        result = detector._normalize_approach("Fix The Import")
        assert result == "fix the import"

    def test_normalize_approach_whitespace(self):
        """Normalizes whitespace."""
        detector = PatternDetector()
        result = detector._normalize_approach("  Fix   the    import  ")
        assert result == "fix the import"

    def test_normalize_approach_empty(self):
        """Handles empty string."""
        detector = PatternDetector()
        result = detector._normalize_approach("")
        assert result == ""

    def test_normalize_approach_tabs_newlines(self):
        """Normalizes tabs and newlines."""
        detector = PatternDetector()
        result = detector._normalize_approach("Fix\tthe\nimport")
        assert result == "fix the import"


class TestErrorNormalization:
    """Tests for error string normalization."""

    def test_normalize_error_removes_timestamps(self):
        """Removes timestamps from errors."""
        detector = PatternDetector()
        result = detector._normalize_error("Error at 2023-12-01 10:30:45: ImportError")
        assert "2023-12-01" not in result
        assert "10:30:45" not in result
        assert "importerror" in result

    def test_normalize_error_removes_file_paths_unix(self):
        """Removes Unix file paths from errors."""
        detector = PatternDetector()
        result = detector._normalize_error("Error in /home/user/project/file.py: ImportError")
        assert "/home/user/project/file.py" not in result
        assert "importerror" in result

    def test_normalize_error_removes_file_paths_windows(self):
        """Removes Windows file paths from errors."""
        detector = PatternDetector()
        result = detector._normalize_error("Error in C:\\Users\\user\\project\\file.py: ImportError")
        assert "file.py" not in result
        assert "importerror" in result

    def test_normalize_error_removes_line_numbers(self):
        """Removes line numbers from errors."""
        detector = PatternDetector()
        result = detector._normalize_error("Error at line 42: ImportError")
        assert "42" not in result
        assert "importerror" in result

    def test_normalize_error_removes_hex_addresses(self):
        """Removes hex addresses from errors."""
        detector = PatternDetector()
        result = detector._normalize_error("Error at 0x7f8b3c4a5e10: ImportError")
        assert "0x7f8b3c4a5e10" not in result
        assert "importerror" in result

    def test_normalize_error_lowercase(self):
        """Normalizes to lowercase."""
        detector = PatternDetector()
        result = detector._normalize_error("ImportError: Module Not Found")
        assert result == "importerror: module not found"

    def test_normalize_error_whitespace(self):
        """Normalizes whitespace."""
        detector = PatternDetector()
        result = detector._normalize_error("  ImportError:   Module   Not   Found  ")
        assert result == "importerror: module not found"


class TestDetectPatterns:
    """Tests for main detect_patterns method."""

    def test_detect_patterns_empty_history(self):
        """Returns empty list for empty history."""
        detector = PatternDetector()
        patterns = detector.detect_patterns([])
        assert patterns == []

    def test_detect_patterns_multiple_patterns(self):
        """Detects and returns multiple patterns."""
        detector = PatternDetector(
            loop_threshold=3, repeated_failure_threshold=3, timeout_minutes=30
        )
        start_time = (datetime.now() - timedelta(minutes=35)).isoformat()
        history = [
            {"approach": "Fix import", "error": "ImportError"},
            {"approach": "Fix import", "error": "ImportError"},
            {"approach": "Fix import", "error": "ImportError"},
        ]
        patterns = detector.detect_patterns(history, start_time)

        # Should detect loop, repeated failure, and timeout
        assert len(patterns) >= 2
        pattern_types = {p.pattern_type for p in patterns}
        assert PatternType.LOOP in pattern_types
        assert PatternType.REPEATED_FAILURE in pattern_types

    def test_detect_patterns_sorted_by_confidence(self):
        """Returns patterns sorted by confidence (highest first)."""
        detector = PatternDetector(loop_threshold=3, repeated_failure_threshold=3)
        history = [
            {"approach": "Fix import", "error": "ImportError"},
            {"approach": "Fix import", "error": "ImportError"},
            {"approach": "Fix import", "error": "ImportError"},
            {"approach": "Fix import", "error": "ImportError"},
            {"approach": "Fix import", "error": "ImportError"},
        ]
        patterns = detector.detect_patterns(history)

        # Verify sorted by confidence
        for i in range(len(patterns) - 1):
            assert patterns[i].confidence >= patterns[i + 1].confidence

    def test_detect_patterns_no_timeout_without_start_time(self):
        """Does not detect timeout without start_time."""
        detector = PatternDetector(timeout_minutes=30)
        history = [{"approach": "Fix import"}]
        patterns = detector.detect_patterns(history)

        pattern_types = {p.pattern_type for p in patterns}
        assert PatternType.TIMEOUT not in pattern_types


class TestGetStrongestPattern:
    """Tests for get_strongest_pattern method."""

    def test_get_strongest_pattern_returns_highest_confidence(self):
        """Returns pattern with highest confidence."""
        detector = PatternDetector(loop_threshold=3, repeated_failure_threshold=3)
        history = [
            {"approach": "Fix import", "error": "ImportError"},
            {"approach": "Fix import", "error": "ImportError"},
            {"approach": "Fix import", "error": "ImportError"},
            {"approach": "Fix import", "error": "ImportError"},
            {"approach": "Fix import", "error": "ImportError"},
        ]
        pattern = detector.get_strongest_pattern(history)

        assert pattern is not None
        assert isinstance(pattern, PatternMatch)

        # Verify it's the highest confidence
        all_patterns = detector.detect_patterns(history)
        assert pattern.confidence == max(p.confidence for p in all_patterns)

    def test_get_strongest_pattern_returns_none_when_no_patterns(self):
        """Returns None when no patterns detected."""
        detector = PatternDetector()
        history = [{"approach": "Fix A"}, {"approach": "Fix B"}]
        pattern = detector.get_strongest_pattern(history)
        assert pattern is None

    def test_get_strongest_pattern_with_start_time(self):
        """Uses start_time for timeout detection."""
        detector = PatternDetector(timeout_minutes=30)
        start_time = (datetime.now() - timedelta(minutes=35)).isoformat()
        history = [{"approach": "Fix import"}]
        pattern = detector.get_strongest_pattern(history, start_time)

        assert pattern is not None
        assert pattern.pattern_type == PatternType.TIMEOUT


class TestPatternMatchDataclass:
    """Tests for PatternMatch dataclass."""

    def test_pattern_match_creation(self):
        """Creates PatternMatch with all fields."""
        match = PatternMatch(
            pattern_type=PatternType.LOOP,
            confidence=0.85,
            evidence="Same approach tried 5 times",
            recommendation="Try a different approach",
            metadata={"attempt_count": 5},
        )

        assert match.pattern_type == PatternType.LOOP
        assert match.confidence == 0.85
        assert match.evidence == "Same approach tried 5 times"
        assert match.recommendation == "Try a different approach"
        assert match.metadata == {"attempt_count": 5}


class TestPatternTypeEnum:
    """Tests for PatternType enum."""

    def test_pattern_type_values(self):
        """Verifies all pattern types exist."""
        assert PatternType.LOOP.value == "loop"
        assert PatternType.THRASHING.value == "thrashing"
        assert PatternType.REPEATED_FAILURE.value == "repeated_failure"
        assert PatternType.TIMEOUT.value == "timeout"
        assert PatternType.CONTEXT_EXHAUSTION.value == "context_exhaustion"
        assert PatternType.NO_PATTERN.value == "no_pattern"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_approach_strings(self):
        """Handles empty approach strings."""
        detector = PatternDetector(loop_threshold=3)
        history = [
            {"approach": ""},
            {"approach": ""},
            {"approach": ""},
        ]
        pattern = detector._detect_loop(history)
        # Empty approaches should not trigger loop detection
        assert pattern is None

    def test_missing_approach_field(self):
        """Handles missing approach field."""
        detector = PatternDetector(loop_threshold=3)
        history = [
            {"error": "ImportError"},
            {"error": "ImportError"},
            {"error": "ImportError"},
        ]
        pattern = detector._detect_loop(history)
        assert pattern is None

    def test_missing_error_field(self):
        """Handles missing error field."""
        detector = PatternDetector(repeated_failure_threshold=3)
        history = [
            {"approach": "Fix A"},
            {"approach": "Fix B"},
            {"approach": "Fix C"},
        ]
        pattern = detector._detect_repeated_failure(history)
        assert pattern is None

    def test_very_long_approach_strings(self):
        """Handles very long approach strings."""
        detector = PatternDetector(loop_threshold=3)
        long_approach = "Fix " * 1000  # Very long string
        history = [
            {"approach": long_approach},
            {"approach": long_approach},
            {"approach": long_approach},
        ]
        pattern = detector._detect_loop(history)
        assert pattern is not None
        # Evidence should be truncated
        assert len(pattern.evidence) < len(long_approach) * 3

    def test_unicode_in_approach_and_error(self):
        """Handles Unicode characters in approaches and errors."""
        detector = PatternDetector(loop_threshold=3)
        history = [
            {"approach": "修复导入错误", "error": "导入错误"},
            {"approach": "修复导入错误", "error": "导入错误"},
            {"approach": "修复导入错误", "error": "导入错误"},
        ]
        pattern = detector._detect_loop(history)
        assert pattern is not None

    def test_confidence_bounds(self):
        """Ensures confidence is always between 0 and 1."""
        detector = PatternDetector(loop_threshold=3)
        history = [{"approach": "Fix import", "error": "ImportError"}] * 100
        patterns = detector.detect_patterns(history)

        for pattern in patterns:
            assert 0.0 <= pattern.confidence <= 1.0
