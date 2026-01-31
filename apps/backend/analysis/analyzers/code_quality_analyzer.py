"""
Code Quality Analyzer Module
=============================

Analyzes code quality metrics including cyclomatic complexity and maintainability index.
Uses radon library for Python code analysis and supports basic metrics for other languages.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .base import SKIP_DIRS, BaseAnalyzer

try:
    from radon.complexity import cc_visit
    from radon.metrics import mi_visit

    HAS_RADON = True
except ImportError:
    HAS_RADON = False


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class FunctionMetrics:
    """
    Metrics for a single function.

    Attributes:
        name: Function name
        line: Starting line number
        complexity: Cyclomatic complexity score
        rank: Complexity rank (A-F, where A is best)
    """

    name: str
    line: int
    complexity: int
    rank: str


@dataclass
class FileMetrics:
    """
    Metrics for a single file.

    Attributes:
        file_path: Relative path to the file
        language: Programming language
        lines_of_code: Total lines of code (excluding blank/comments)
        complexity: Average cyclomatic complexity
        maintainability_index: Maintainability index (0-100, higher is better)
        functions: List of function-level metrics
    """

    file_path: str
    language: str
    lines_of_code: int
    complexity: float
    maintainability_index: float | None = None
    functions: list[FunctionMetrics] = field(default_factory=list)


@dataclass
class CodeQualityMetrics:
    """
    Overall code quality metrics for a project or service.

    Attributes:
        total_files: Number of files analyzed
        total_lines: Total lines of code
        average_complexity: Average cyclomatic complexity across all functions
        average_maintainability: Average maintainability index
        high_complexity_count: Number of functions with complexity > 10
        critical_complexity_count: Number of functions with complexity > 20
        files: List of per-file metrics
        technical_debt_score: Estimated technical debt score (0-100, higher is worse)
    """

    total_files: int = 0
    total_lines: int = 0
    average_complexity: float = 0.0
    average_maintainability: float = 0.0
    high_complexity_count: int = 0
    critical_complexity_count: int = 0
    files: list[FileMetrics] = field(default_factory=list)
    technical_debt_score: float = 0.0


# =============================================================================
# CODE QUALITY ANALYZER
# =============================================================================


class CodeQualityAnalyzer(BaseAnalyzer):
    """
    Analyzes code quality metrics for a project or service.

    Supports Python (via radon) with basic metrics for JavaScript/TypeScript.
    """

    # File extensions to analyze
    PYTHON_EXTENSIONS = {".py"}
    JAVASCRIPT_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx"}
    SUPPORTED_EXTENSIONS = PYTHON_EXTENSIONS | JAVASCRIPT_EXTENSIONS

    def __init__(self, path: Path):
        """
        Initialize the code quality analyzer.

        Args:
            path: Path to the project or service directory
        """
        super().__init__(path)
        self.metrics = CodeQualityMetrics()

    def analyze(self) -> dict[str, Any]:
        """
        Analyze code quality metrics for all supported files.

        Returns:
            Dictionary containing code quality metrics
        """
        if not HAS_RADON:
            return {
                "error": "radon library not installed",
                "message": "Install radon to enable code quality analysis: pip install radon",
            }

        # Find and analyze all supported files
        for file_path in self._find_code_files():
            try:
                file_metrics = self._analyze_file(file_path)
                if file_metrics:
                    self.metrics.files.append(file_metrics)
            except Exception:
                # Skip files that fail to analyze
                continue

        # Compute aggregate metrics
        self._compute_aggregate_metrics()

        # Return structured results
        return {
            "total_files": self.metrics.total_files,
            "total_lines": self.metrics.total_lines,
            "average_complexity": round(self.metrics.average_complexity, 2),
            "average_maintainability": round(self.metrics.average_maintainability, 2),
            "high_complexity_count": self.metrics.high_complexity_count,
            "critical_complexity_count": self.metrics.critical_complexity_count,
            "technical_debt_score": round(self.metrics.technical_debt_score, 2),
            "files": [
                {
                    "file_path": f.file_path,
                    "language": f.language,
                    "lines_of_code": f.lines_of_code,
                    "complexity": round(f.complexity, 2),
                    "maintainability_index": (
                        round(f.maintainability_index, 2)
                        if f.maintainability_index is not None
                        else None
                    ),
                    "functions": [
                        {
                            "name": fn.name,
                            "line": fn.line,
                            "complexity": fn.complexity,
                            "rank": fn.rank,
                        }
                        for fn in f.functions
                    ],
                }
                for f in self.metrics.files
            ],
        }

    def _find_code_files(self) -> list[Path]:
        """
        Find all code files to analyze.

        Returns:
            List of file paths
        """
        code_files = []

        for file_path in self.path.rglob("*"):
            # Skip directories
            if file_path.is_dir():
                continue

            # Skip files in excluded directories
            if any(skip_dir in file_path.parts for skip_dir in SKIP_DIRS):
                continue

            # Check if file has a supported extension
            if file_path.suffix in self.SUPPORTED_EXTENSIONS:
                code_files.append(file_path)

        return code_files

    def _analyze_file(self, file_path: Path) -> FileMetrics | None:
        """
        Analyze a single file.

        Args:
            file_path: Path to the file

        Returns:
            FileMetrics object or None if analysis fails
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        # Determine language
        if file_path.suffix in self.PYTHON_EXTENSIONS:
            return self._analyze_python_file(file_path, content)
        elif file_path.suffix in self.JAVASCRIPT_EXTENSIONS:
            return self._analyze_javascript_file(file_path, content)

        return None

    def _analyze_python_file(self, file_path: Path, content: str) -> FileMetrics | None:
        """
        Analyze a Python file using radon.

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            FileMetrics object or None if analysis fails
        """
        try:
            # Calculate cyclomatic complexity
            complexity_results = cc_visit(content)

            # Calculate maintainability index
            mi_score = mi_visit(content, multi=True)

            # Count lines of code (non-blank, non-comment)
            loc = self._count_python_loc(content)

            # Extract function metrics
            functions = []
            total_complexity = 0

            for result in complexity_results:
                functions.append(
                    FunctionMetrics(
                        name=result.name,
                        line=result.lineno,
                        complexity=result.complexity,
                        rank=result.rank,
                    )
                )
                total_complexity += result.complexity

            # Calculate average complexity
            avg_complexity = (
                total_complexity / len(functions) if functions else 0.0
            )

            # Get relative path
            try:
                rel_path = str(file_path.relative_to(self.path))
            except ValueError:
                rel_path = str(file_path)

            return FileMetrics(
                file_path=rel_path,
                language="Python",
                lines_of_code=loc,
                complexity=avg_complexity,
                maintainability_index=mi_score,
                functions=functions,
            )

        except (SyntaxError, ValueError):
            # Skip files with syntax errors
            return None

    def _analyze_javascript_file(
        self, file_path: Path, content: str
    ) -> FileMetrics | None:
        """
        Analyze a JavaScript/TypeScript file (basic metrics only).

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            FileMetrics object with basic metrics
        """
        # Get relative path
        try:
            rel_path = str(file_path.relative_to(self.path))
        except ValueError:
            rel_path = str(file_path)

        # Count lines of code (basic count)
        loc = self._count_javascript_loc(content)

        # For JS/TS, we provide basic metrics only
        # Full analysis would require a JavaScript AST parser
        return FileMetrics(
            file_path=rel_path,
            language="JavaScript/TypeScript",
            lines_of_code=loc,
            complexity=0.0,
            maintainability_index=None,
            functions=[],
        )

    def _count_python_loc(self, content: str) -> int:
        """
        Count lines of code in Python (excluding blanks and comments).

        Args:
            content: File content

        Returns:
            Number of lines of code
        """
        try:
            tree = ast.parse(content)
            # Count non-blank, non-comment lines
            lines = set()
            for node in ast.walk(tree):
                if hasattr(node, "lineno"):
                    lines.add(node.lineno)
            return len(lines)
        except SyntaxError:
            # Fall back to simple line count
            return len([line for line in content.split("\n") if line.strip()])

    def _count_javascript_loc(self, content: str) -> int:
        """
        Count lines of code in JavaScript/TypeScript (basic count).

        Args:
            content: File content

        Returns:
            Number of lines of code (excluding blank lines)
        """
        lines = content.split("\n")
        loc = 0

        for line in lines:
            stripped = line.strip()
            # Skip blank lines and single-line comments
            if stripped and not stripped.startswith("//"):
                loc += 1

        return loc

    def _compute_aggregate_metrics(self) -> None:
        """Compute aggregate metrics across all analyzed files."""
        if not self.metrics.files:
            return

        total_complexity = 0.0
        total_mi = 0.0
        mi_count = 0
        function_count = 0

        for file_metrics in self.metrics.files:
            self.metrics.total_files += 1
            self.metrics.total_lines += file_metrics.lines_of_code

            # Aggregate complexity
            for func in file_metrics.functions:
                total_complexity += func.complexity
                function_count += 1

                # Count high/critical complexity
                if func.complexity > 10:
                    self.metrics.high_complexity_count += 1
                if func.complexity > 20:
                    self.metrics.critical_complexity_count += 1

            # Aggregate maintainability index
            if file_metrics.maintainability_index is not None:
                total_mi += file_metrics.maintainability_index
                mi_count += 1

        # Calculate averages
        self.metrics.average_complexity = (
            total_complexity / function_count if function_count > 0 else 0.0
        )
        self.metrics.average_maintainability = (
            total_mi / mi_count if mi_count > 0 else 0.0
        )

        # Calculate technical debt score (0-100, higher is worse)
        # Based on complexity and maintainability
        debt_score = 0.0

        # Factor 1: High complexity (0-40 points)
        if function_count > 0:
            high_complexity_ratio = self.metrics.high_complexity_count / function_count
            debt_score += high_complexity_ratio * 40

        # Factor 2: Low maintainability (0-40 points)
        if self.metrics.average_maintainability > 0:
            # MI ranges from 0-100, lower is worse
            # Invert so low MI contributes to higher debt
            mi_debt = (100 - self.metrics.average_maintainability) / 100 * 40
            debt_score += mi_debt

        # Factor 3: Critical complexity (0-20 points)
        if function_count > 0:
            critical_ratio = self.metrics.critical_complexity_count / function_count
            debt_score += critical_ratio * 20

        self.metrics.technical_debt_score = min(debt_score, 100.0)
