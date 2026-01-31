"""
Code Quality Analyzer Module
=============================

Analyzes code quality metrics including cyclomatic complexity and maintainability index.
Uses radon library for Python code analysis and supports basic metrics for other languages.

Optional SonarQube Integration:
- Set SONARQUBE_URL environment variable to enable
- Optionally set SONARQUBE_TOKEN for authenticated access
- Fetches additional metrics: bugs, vulnerabilities, code smells, coverage, duplications
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .base import SKIP_DIRS, BaseAnalyzer

try:
    from radon.complexity import cc_visit, cc_rank
    from radon.metrics import mi_visit

    HAS_RADON = True
except ImportError:
    HAS_RADON = False

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


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
        sonarqube_metrics: Optional SonarQube metrics (if integration enabled)
    """

    total_files: int = 0
    total_lines: int = 0
    average_complexity: float = 0.0
    average_maintainability: float = 0.0
    high_complexity_count: int = 0
    critical_complexity_count: int = 0
    files: list[FileMetrics] = field(default_factory=list)
    technical_debt_score: float = 0.0
    sonarqube_metrics: dict[str, Any] | None = None


@dataclass
class SonarQubeConfig:
    """
    Configuration for SonarQube integration.

    Attributes:
        url: SonarQube server URL
        token: Optional authentication token
        project_key: Optional project key (auto-detected if not provided)
        enabled: Whether SonarQube integration is enabled
    """

    url: str = ""
    token: str = ""
    project_key: str = ""
    enabled: bool = False

    @classmethod
    def from_env(cls) -> "SonarQubeConfig":
        """Create configuration from environment variables."""
        url = os.environ.get("SONARQUBE_URL", "").strip()
        token = os.environ.get("SONARQUBE_TOKEN", "").strip()
        project_key = os.environ.get("SONARQUBE_PROJECT_KEY", "").strip()

        # Remove trailing slash from URL
        if url.endswith("/"):
            url = url[:-1]

        enabled = bool(url)

        return cls(
            url=url,
            token=token,
            project_key=project_key,
            enabled=enabled,
        )

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return self.enabled and bool(self.url)


# =============================================================================
# SONARQUBE CLIENT
# =============================================================================


class SonarQubeClient:
    """
    Client for interacting with SonarQube API.

    Fetches code quality metrics from a SonarQube server.
    """

    def __init__(self, config: SonarQubeConfig):
        """
        Initialize SonarQube client.

        Args:
            config: SonarQube configuration
        """
        self.config = config
        self.session = None

        if HAS_REQUESTS and config.is_valid():
            self.session = requests.Session()
            if config.token:
                # SonarQube uses token as username with empty password
                self.session.auth = (config.token, "")

    def fetch_project_metrics(self, project_key: str | None = None) -> dict[str, Any]:
        """
        Fetch project-level metrics from SonarQube.

        Args:
            project_key: SonarQube project key (uses config default if not provided)

        Returns:
            Dictionary of metrics or error information
        """
        if not self.session:
            return {"error": "SonarQube client not initialized"}

        project_key = project_key or self.config.project_key
        if not project_key:
            return {"error": "No project key provided"}

        try:
            # Fetch project measures
            metrics = [
                "bugs",
                "vulnerabilities",
                "code_smells",
                "coverage",
                "duplicated_lines_density",
                "ncloc",
                "sqale_index",  # Technical debt
                "reliability_rating",
                "security_rating",
                "sqale_rating",  # Maintainability rating
            ]

            url = f"{self.config.url}/api/measures/component"
            params = {
                "component": project_key,
                "metricKeys": ",".join(metrics),
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            component = data.get("component", {})
            measures = component.get("measures", [])

            # Convert measures to dictionary
            result = {
                "project_key": project_key,
                "metrics": {},
            }

            for measure in measures:
                metric_key = measure.get("metric")
                value = measure.get("value")

                # Convert to appropriate type
                try:
                    # Try float first
                    if "." in str(value):
                        result["metrics"][metric_key] = float(value)
                    else:
                        result["metrics"][metric_key] = int(value)
                except (ValueError, TypeError):
                    result["metrics"][metric_key] = value

            return result

        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to fetch SonarQube metrics: {e!s}"}
        except (ValueError, KeyError) as e:
            return {"error": f"Failed to parse SonarQube response: {e!s}"}

    def search_projects(self) -> list[dict[str, Any]]:
        """
        Search for projects in SonarQube.

        Returns:
            List of project information dictionaries
        """
        if not self.session:
            return []

        try:
            url = f"{self.config.url}/api/components/search"
            params = {
                "qualifiers": "TRK",  # Projects only
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            components = data.get("components", [])

            return [
                {
                    "key": comp.get("key"),
                    "name": comp.get("name"),
                    "qualifier": comp.get("qualifier"),
                }
                for comp in components
            ]

        except requests.exceptions.RequestException:
            return []


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
        self.sonarqube_config = SonarQubeConfig.from_env()
        self.sonarqube_client = None

        # Initialize SonarQube client if enabled
        if self.sonarqube_config.is_valid() and HAS_REQUESTS:
            self.sonarqube_client = SonarQubeClient(self.sonarqube_config)

    def analyze(self) -> dict[str, Any]:
        """
        Analyze code quality metrics for all supported files.

        Includes optional SonarQube metrics if SONARQUBE_URL is configured.

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

        # Fetch SonarQube metrics if enabled
        self._fetch_sonarqube_metrics()

        # Return structured results
        result = {
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

        # Include SonarQube metrics if available
        if self.metrics.sonarqube_metrics:
            result["sonarqube"] = self.metrics.sonarqube_metrics

        return result

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
                        rank=cc_rank(result.complexity),
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

    def is_sonarqube_enabled(self) -> bool:
        """
        Check if SonarQube integration is enabled and available.

        Returns:
            True if SonarQube integration is configured and active
        """
        return (
            self.sonarqube_config.is_valid()
            and self.sonarqube_client is not None
            and HAS_REQUESTS
        )

    def _fetch_sonarqube_metrics(self) -> None:
        """
        Fetch metrics from SonarQube and add to self.metrics.

        Only activates when SONARQUBE_URL is set in environment.
        """
        if not self.is_sonarqube_enabled():
            return

        try:
            sonarqube_data = self.sonarqube_client.fetch_project_metrics()
            if "error" not in sonarqube_data:
                self.metrics.sonarqube_metrics = sonarqube_data
        except Exception:
            # Silently skip SonarQube errors - it's an optional feature
            pass
