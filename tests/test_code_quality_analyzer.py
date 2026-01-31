#!/usr/bin/env python3
"""
Tests for the CodeQualityAnalyzer module.

Tests cover:
- Data classes (FunctionMetrics, FileMetrics, CodeQualityMetrics, SonarQubeConfig)
- SonarQube client and integration
- Code file discovery
- Python file analysis with radon
- JavaScript/TypeScript basic analysis
- Aggregate metrics computation
- Technical debt score calculation
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add auto-claude to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from analysis.analyzers.code_quality_analyzer import (
    CodeQualityAnalyzer,
    CodeQualityMetrics,
    FileMetrics,
    FunctionMetrics,
    SonarQubeClient,
    SonarQubeConfig,
    HAS_RADON,
    HAS_REQUESTS,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def python_project(temp_dir):
    """Create a Python project with test files."""
    # Simple Python file
    (temp_dir / "simple.py").write_text(
        """
def hello():
    return "world"

def greet(name):
    if name:
        return f"Hello, {name}"
    return "Hello, stranger"
"""
    )

    # Complex Python file with high complexity
    (temp_dir / "complex.py").write_text(
        """
def complex_function(x, y, z, w):
    if x > 0:
        if y > 0:
            if z > 0:
                if w > 0:
                    return x + y + z + w
                elif w < 0:
                    return x + y + z - w
                else:
                    return x + y + z
            elif z < 0:
                if w > 0:
                    return x + y - z + w
                else:
                    return x + y - z
            else:
                return x + y
        elif y < 0:
            if z > 0:
                if w > 0:
                    return x - y + z + w
                else:
                    return x - y + z
            else:
                return x - y
        else:
            return x
    elif x < 0:
        if y > 0:
            if z > 0:
                return -x + y + z
            else:
                return -x + y
        else:
            return -x - y
    else:
        return 0
"""
    )

    return temp_dir


@pytest.fixture
def javascript_project(temp_dir):
    """Create a JavaScript/TypeScript project."""
    (temp_dir / "app.js").write_text(
        """
function hello() {
    return "world";
}

// This is a comment
function greet(name) {
    if (name) {
        return `Hello, ${name}`;
    }
    return "Hello, stranger";
}
"""
    )

    (temp_dir / "types.ts").write_text(
        """
interface User {
    name: string;
    age: number;
}

function createUser(name: string, age: number): User {
    return { name, age };
}
"""
    )

    return temp_dir


@pytest.fixture
def mixed_project(temp_dir):
    """Create a project with multiple languages."""
    # Python files
    (temp_dir / "app.py").write_text("print('hello')\n")

    # JavaScript files
    (temp_dir / "index.js").write_text("console.log('hello');\n")

    # TypeScript files
    (temp_dir / "types.ts").write_text("export const x: number = 1;\n")

    return temp_dir


@pytest.fixture
def project_with_skip_dirs(temp_dir):
    """Create a project with directories that should be skipped."""
    # Valid Python file
    (temp_dir / "app.py").write_text("print('hello')\n")

    # Files in skipped directories
    node_modules = temp_dir / "node_modules" / "package"
    node_modules.mkdir(parents=True)
    (node_modules / "index.js").write_text("console.log('skip');\n")

    venv = temp_dir / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "module.py").write_text("print('skip')\n")

    return temp_dir


@pytest.fixture
def sonarqube_config():
    """Create a valid SonarQube configuration."""
    return SonarQubeConfig(
        url="https://sonarqube.example.com",
        token="test_token",
        project_key="test_project",
        enabled=True,
    )


@pytest.fixture
def mock_sonarqube_response():
    """Mock SonarQube API response."""
    return {
        "component": {
            "key": "test_project",
            "name": "Test Project",
            "measures": [
                {"metric": "bugs", "value": "5"},
                {"metric": "vulnerabilities", "value": "2"},
                {"metric": "code_smells", "value": "10"},
                {"metric": "coverage", "value": "85.5"},
                {"metric": "duplicated_lines_density", "value": "3.2"},
                {"metric": "ncloc", "value": "1000"},
                {"metric": "sqale_index", "value": "120"},
                {"metric": "reliability_rating", "value": "2"},
                {"metric": "security_rating", "value": "1"},
                {"metric": "sqale_rating", "value": "2"},
            ],
        }
    }


# =============================================================================
# DATA CLASS TESTS
# =============================================================================


class TestFunctionMetrics:
    """Tests for FunctionMetrics dataclass."""

    def test_create_function_metrics(self):
        """Test creating function metrics."""
        metrics = FunctionMetrics(
            name="test_function",
            line=10,
            complexity=5,
            rank="B",
        )

        assert metrics.name == "test_function"
        assert metrics.line == 10
        assert metrics.complexity == 5
        assert metrics.rank == "B"


class TestFileMetrics:
    """Tests for FileMetrics dataclass."""

    def test_create_file_metrics(self):
        """Test creating file metrics."""
        func = FunctionMetrics(name="func", line=1, complexity=2, rank="A")
        metrics = FileMetrics(
            file_path="test.py",
            language="Python",
            lines_of_code=50,
            complexity=3.5,
            maintainability_index=75.0,
            functions=[func],
        )

        assert metrics.file_path == "test.py"
        assert metrics.language == "Python"
        assert metrics.lines_of_code == 50
        assert metrics.complexity == 3.5
        assert metrics.maintainability_index == 75.0
        assert len(metrics.functions) == 1

    def test_file_metrics_optional_fields(self):
        """Test file metrics with optional fields."""
        metrics = FileMetrics(
            file_path="test.js",
            language="JavaScript",
            lines_of_code=30,
            complexity=0.0,
        )

        assert metrics.maintainability_index is None
        assert metrics.functions == []


class TestCodeQualityMetrics:
    """Tests for CodeQualityMetrics dataclass."""

    def test_create_code_quality_metrics(self):
        """Test creating code quality metrics."""
        metrics = CodeQualityMetrics()

        assert metrics.total_files == 0
        assert metrics.total_lines == 0
        assert metrics.average_complexity == 0.0
        assert metrics.average_maintainability == 0.0
        assert metrics.high_complexity_count == 0
        assert metrics.critical_complexity_count == 0
        assert metrics.files == []
        assert metrics.technical_debt_score == 0.0
        assert metrics.sonarqube_metrics is None

    def test_metrics_with_data(self):
        """Test metrics with actual data."""
        file_metrics = FileMetrics(
            file_path="test.py",
            language="Python",
            lines_of_code=100,
            complexity=5.0,
        )

        metrics = CodeQualityMetrics(
            total_files=1,
            total_lines=100,
            average_complexity=5.0,
            files=[file_metrics],
        )

        assert metrics.total_files == 1
        assert metrics.total_lines == 100
        assert metrics.average_complexity == 5.0


class TestSonarQubeConfig:
    """Tests for SonarQubeConfig dataclass."""

    def test_create_config(self):
        """Test creating SonarQube config."""
        config = SonarQubeConfig(
            url="https://sonarqube.example.com",
            token="test_token",
            project_key="test_project",
            enabled=True,
        )

        assert config.url == "https://sonarqube.example.com"
        assert config.token == "test_token"
        assert config.project_key == "test_project"
        assert config.enabled is True

    def test_from_env_with_url(self):
        """Test creating config from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "SONARQUBE_URL": "https://sonarqube.example.com/",
                "SONARQUBE_TOKEN": "test_token",
                "SONARQUBE_PROJECT_KEY": "test_project",
            },
        ):
            config = SonarQubeConfig.from_env()

            assert config.url == "https://sonarqube.example.com"  # Trailing slash removed
            assert config.token == "test_token"
            assert config.project_key == "test_project"
            assert config.enabled is True

    def test_from_env_without_url(self):
        """Test config is disabled when URL not set."""
        with patch.dict("os.environ", {}, clear=True):
            config = SonarQubeConfig.from_env()

            assert config.url == ""
            assert config.enabled is False

    def test_is_valid(self):
        """Test config validation."""
        valid_config = SonarQubeConfig(
            url="https://sonarqube.example.com",
            enabled=True,
        )
        assert valid_config.is_valid() is True

        invalid_config = SonarQubeConfig(url="", enabled=False)
        assert invalid_config.is_valid() is False


# =============================================================================
# SONARQUBE CLIENT TESTS
# =============================================================================


class TestSonarQubeClient:
    """Tests for SonarQubeClient class."""

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not available")
    def test_client_initialization(self, sonarqube_config):
        """Test SonarQube client initialization."""
        client = SonarQubeClient(sonarqube_config)

        assert client.config == sonarqube_config
        assert client.session is not None
        assert client.session.auth == ("test_token", "")

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not available")
    def test_client_without_token(self):
        """Test client initialization without token."""
        config = SonarQubeConfig(
            url="https://sonarqube.example.com",
            enabled=True,
        )
        client = SonarQubeClient(config)

        assert client.session is not None
        assert client.session.auth is None

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not available")
    @patch("requests.Session.get")
    def test_fetch_project_metrics_success(
        self, mock_get, sonarqube_config, mock_sonarqube_response
    ):
        """Test fetching project metrics successfully."""
        mock_response = Mock()
        mock_response.json.return_value = mock_sonarqube_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = SonarQubeClient(sonarqube_config)
        result = client.fetch_project_metrics("test_project")

        assert "error" not in result
        assert result["project_key"] == "test_project"
        assert "metrics" in result
        assert result["metrics"]["bugs"] == 5
        assert result["metrics"]["coverage"] == 85.5

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not available")
    @patch("requests.Session.get")
    def test_fetch_project_metrics_http_error(self, mock_get, sonarqube_config):
        """Test handling HTTP errors."""
        import requests

        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")

        client = SonarQubeClient(sonarqube_config)
        result = client.fetch_project_metrics("test_project")

        assert "error" in result
        assert "Failed to fetch SonarQube metrics" in result["error"]

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not available")
    def test_fetch_project_metrics_without_project_key(self, sonarqube_config):
        """Test fetching metrics without project key."""
        client = SonarQubeClient(sonarqube_config)
        result = client.fetch_project_metrics(None)

        # Should use config project key
        assert "error" not in result or "error" in result

    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not available")
    @patch("requests.Session.get")
    def test_search_projects(self, mock_get, sonarqube_config):
        """Test searching for projects."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "components": [
                {"key": "project1", "name": "Project 1", "qualifier": "TRK"},
                {"key": "project2", "name": "Project 2", "qualifier": "TRK"},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = SonarQubeClient(sonarqube_config)
        projects = client.search_projects()

        assert len(projects) == 2
        assert projects[0]["key"] == "project1"
        assert projects[1]["name"] == "Project 2"


# =============================================================================
# CODE QUALITY ANALYZER TESTS
# =============================================================================


class TestCodeQualityAnalyzerInitialization:
    """Tests for CodeQualityAnalyzer initialization."""

    def test_init_with_path(self, temp_dir):
        """Test initializing analyzer with path."""
        analyzer = CodeQualityAnalyzer(temp_dir)

        assert analyzer.path == temp_dir.resolve()
        assert isinstance(analyzer.metrics, CodeQualityMetrics)
        assert isinstance(analyzer.sonarqube_config, SonarQubeConfig)

    @patch.dict("os.environ", {"SONARQUBE_URL": "https://sonarqube.example.com"})
    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not available")
    def test_init_with_sonarqube_enabled(self, temp_dir):
        """Test initialization with SonarQube enabled."""
        analyzer = CodeQualityAnalyzer(temp_dir)

        assert analyzer.sonarqube_config.enabled is True
        assert analyzer.sonarqube_client is not None


class TestCodeFileDiscovery:
    """Tests for finding code files."""

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_find_python_files(self, python_project):
        """Test finding Python files."""
        analyzer = CodeQualityAnalyzer(python_project)
        files = analyzer._find_code_files()

        file_names = [f.name for f in files]
        assert "simple.py" in file_names
        assert "complex.py" in file_names

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_find_javascript_files(self, javascript_project):
        """Test finding JavaScript/TypeScript files."""
        analyzer = CodeQualityAnalyzer(javascript_project)
        files = analyzer._find_code_files()

        file_names = [f.name for f in files]
        assert "app.js" in file_names
        assert "types.ts" in file_names

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_find_mixed_files(self, mixed_project):
        """Test finding files in mixed language project."""
        analyzer = CodeQualityAnalyzer(mixed_project)
        files = analyzer._find_code_files()

        file_names = [f.name for f in files]
        assert "app.py" in file_names
        assert "index.js" in file_names
        assert "types.ts" in file_names

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_skip_directories(self, project_with_skip_dirs):
        """Test that skipped directories are excluded."""
        analyzer = CodeQualityAnalyzer(project_with_skip_dirs)
        files = analyzer._find_code_files()

        # Should only find app.py, not files in node_modules or .venv
        assert len(files) == 1
        assert files[0].name == "app.py"


class TestPythonFileAnalysis:
    """Tests for Python file analysis."""

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_analyze_simple_python_file(self, python_project):
        """Test analyzing a simple Python file."""
        analyzer = CodeQualityAnalyzer(python_project)
        file_path = python_project / "simple.py"

        content = file_path.read_text()
        metrics = analyzer._analyze_python_file(file_path, content)

        assert metrics is not None
        assert metrics.language == "Python"
        assert metrics.lines_of_code > 0
        assert len(metrics.functions) == 2  # hello and greet
        assert metrics.maintainability_index is not None

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_analyze_complex_python_file(self, python_project):
        """Test analyzing a complex Python file."""
        analyzer = CodeQualityAnalyzer(python_project)
        file_path = python_project / "complex.py"

        content = file_path.read_text()
        metrics = analyzer._analyze_python_file(file_path, content)

        assert metrics is not None
        assert len(metrics.functions) == 1
        # Complex function should have high complexity
        assert metrics.functions[0].complexity > 10

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_analyze_python_file_with_syntax_error(self, temp_dir):
        """Test handling Python file with syntax errors."""
        analyzer = CodeQualityAnalyzer(temp_dir)
        bad_file = temp_dir / "bad.py"
        bad_file.write_text("def broken(\n")  # Syntax error

        content = bad_file.read_text()
        metrics = analyzer._analyze_python_file(bad_file, content)

        assert metrics is None

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_count_python_loc(self, temp_dir):
        """Test counting Python lines of code."""
        analyzer = CodeQualityAnalyzer(temp_dir)
        content = """
# This is a comment
def hello():
    # Another comment
    return "world"

# More comments

def goodbye():
    return "farewell"
"""
        loc = analyzer._count_python_loc(content)
        assert loc > 0  # Should count actual code lines, not comments


class TestJavaScriptFileAnalysis:
    """Tests for JavaScript/TypeScript file analysis."""

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_analyze_javascript_file(self, javascript_project):
        """Test analyzing JavaScript file."""
        analyzer = CodeQualityAnalyzer(javascript_project)
        file_path = javascript_project / "app.js"

        content = file_path.read_text()
        metrics = analyzer._analyze_javascript_file(file_path, content)

        assert metrics is not None
        assert metrics.language == "JavaScript/TypeScript"
        assert metrics.lines_of_code > 0
        assert metrics.complexity == 0.0  # Basic metrics only
        assert metrics.maintainability_index is None
        assert metrics.functions == []

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_analyze_typescript_file(self, javascript_project):
        """Test analyzing TypeScript file."""
        analyzer = CodeQualityAnalyzer(javascript_project)
        file_path = javascript_project / "types.ts"

        content = file_path.read_text()
        metrics = analyzer._analyze_javascript_file(file_path, content)

        assert metrics is not None
        assert metrics.language == "JavaScript/TypeScript"

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_count_javascript_loc(self, temp_dir):
        """Test counting JavaScript lines of code."""
        analyzer = CodeQualityAnalyzer(temp_dir)
        content = """
// This is a comment
function hello() {
    return "world";
}

// Another comment

function goodbye() {
    return "farewell";
}
"""
        loc = analyzer._count_javascript_loc(content)
        assert loc > 0  # Should exclude comments and blank lines


class TestAggregateMetrics:
    """Tests for aggregate metrics computation."""

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_compute_aggregate_metrics(self, python_project):
        """Test computing aggregate metrics."""
        analyzer = CodeQualityAnalyzer(python_project)

        # Manually add some file metrics
        analyzer.metrics.files = [
            FileMetrics(
                file_path="test1.py",
                language="Python",
                lines_of_code=100,
                complexity=5.0,
                maintainability_index=80.0,
                functions=[
                    FunctionMetrics("func1", 1, 5, "B"),
                    FunctionMetrics("func2", 10, 15, "C"),  # High complexity
                ],
            ),
            FileMetrics(
                file_path="test2.py",
                language="Python",
                lines_of_code=50,
                complexity=3.0,
                maintainability_index=90.0,
                functions=[
                    FunctionMetrics("func3", 1, 3, "A"),
                ],
            ),
        ]

        analyzer._compute_aggregate_metrics()

        assert analyzer.metrics.total_files == 2
        assert analyzer.metrics.total_lines == 150
        assert analyzer.metrics.average_complexity > 0
        assert analyzer.metrics.average_maintainability > 0
        assert analyzer.metrics.high_complexity_count == 1  # func2 has complexity 15
        assert analyzer.metrics.critical_complexity_count == 0

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_technical_debt_score(self, temp_dir):
        """Test technical debt score calculation."""
        analyzer = CodeQualityAnalyzer(temp_dir)

        # Project with high complexity and low maintainability
        analyzer.metrics.files = [
            FileMetrics(
                file_path="bad.py",
                language="Python",
                lines_of_code=100,
                complexity=15.0,
                maintainability_index=30.0,  # Low maintainability
                functions=[
                    FunctionMetrics("func1", 1, 15, "D"),
                    FunctionMetrics("func2", 20, 25, "F"),  # Critical complexity
                ],
            ),
        ]

        analyzer._compute_aggregate_metrics()

        # Should have high debt score
        assert analyzer.metrics.technical_debt_score > 0
        assert analyzer.metrics.technical_debt_score <= 100

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_empty_project_metrics(self, temp_dir):
        """Test aggregate metrics with no files."""
        analyzer = CodeQualityAnalyzer(temp_dir)
        analyzer._compute_aggregate_metrics()

        assert analyzer.metrics.total_files == 0
        assert analyzer.metrics.average_complexity == 0.0


class TestFullAnalysis:
    """Tests for full project analysis."""

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_analyze_python_project(self, python_project):
        """Test full analysis of Python project."""
        analyzer = CodeQualityAnalyzer(python_project)
        result = analyzer.analyze()

        assert "error" not in result
        assert result["total_files"] > 0
        assert result["total_lines"] > 0
        assert "files" in result
        assert len(result["files"]) > 0

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_analyze_mixed_project(self, mixed_project):
        """Test analysis of mixed language project."""
        analyzer = CodeQualityAnalyzer(mixed_project)
        result = analyzer.analyze()

        assert result["total_files"] == 3  # app.py, index.js, types.ts
        languages = [f["language"] for f in result["files"]]
        assert "Python" in languages
        assert "JavaScript/TypeScript" in languages

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_analyze_empty_project(self, temp_dir):
        """Test analyzing empty project."""
        analyzer = CodeQualityAnalyzer(temp_dir)
        result = analyzer.analyze()

        assert result["total_files"] == 0
        assert result["total_lines"] == 0
        assert result["files"] == []

    def test_analyze_without_radon(self, temp_dir):
        """Test analysis fails gracefully without radon."""
        with patch("analysis.analyzers.code_quality_analyzer.HAS_RADON", False):
            analyzer = CodeQualityAnalyzer(temp_dir)
            result = analyzer.analyze()

            assert "error" in result
            assert "radon library not installed" in result["error"]


class TestSonarQubeIntegration:
    """Tests for SonarQube integration."""

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not available")
    @patch.dict(
        "os.environ",
        {
            "SONARQUBE_URL": "https://sonarqube.example.com",
            "SONARQUBE_PROJECT_KEY": "test_project",
        },
    )
    def test_sonarqube_enabled(self, temp_dir):
        """Test SonarQube integration when enabled."""
        analyzer = CodeQualityAnalyzer(temp_dir)

        assert analyzer.is_sonarqube_enabled() is True

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_sonarqube_disabled(self, temp_dir):
        """Test SonarQube integration when disabled."""
        with patch.dict("os.environ", {}, clear=True):
            analyzer = CodeQualityAnalyzer(temp_dir)

            assert analyzer.is_sonarqube_enabled() is False

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not available")
    @patch.dict(
        "os.environ",
        {
            "SONARQUBE_URL": "https://sonarqube.example.com",
            "SONARQUBE_PROJECT_KEY": "test_project",
        },
    )
    @patch("requests.Session.get")
    def test_fetch_sonarqube_metrics_success(
        self, mock_get, python_project, mock_sonarqube_response
    ):
        """Test fetching SonarQube metrics successfully."""
        mock_response = Mock()
        mock_response.json.return_value = mock_sonarqube_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        analyzer = CodeQualityAnalyzer(python_project)
        analyzer._fetch_sonarqube_metrics()

        assert analyzer.metrics.sonarqube_metrics is not None
        assert "project_key" in analyzer.metrics.sonarqube_metrics

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not available")
    @patch.dict(
        "os.environ",
        {
            "SONARQUBE_URL": "https://sonarqube.example.com",
            "SONARQUBE_PROJECT_KEY": "test_project",
        },
    )
    @patch("requests.Session.get")
    def test_fetch_sonarqube_metrics_with_error(self, mock_get, python_project):
        """Test SonarQube metrics fetch handles errors gracefully."""
        import requests

        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")

        analyzer = CodeQualityAnalyzer(python_project)
        analyzer._fetch_sonarqube_metrics()

        # Should silently fail without crashing
        assert analyzer.metrics.sonarqube_metrics is None

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    @pytest.mark.skipif(not HAS_REQUESTS, reason="requests library not available")
    @patch.dict(
        "os.environ",
        {
            "SONARQUBE_URL": "https://sonarqube.example.com",
            "SONARQUBE_PROJECT_KEY": "test_project",
        },
    )
    @patch("requests.Session.get")
    def test_full_analysis_with_sonarqube(
        self, mock_get, python_project, mock_sonarqube_response
    ):
        """Test full analysis includes SonarQube metrics."""
        mock_response = Mock()
        mock_response.json.return_value = mock_sonarqube_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        analyzer = CodeQualityAnalyzer(python_project)
        result = analyzer.analyze()

        assert "sonarqube" in result
        assert result["sonarqube"]["project_key"] == "test_project"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_analyze_file_with_unicode(self, temp_dir):
        """Test analyzing file with unicode characters."""
        analyzer = CodeQualityAnalyzer(temp_dir)
        unicode_file = temp_dir / "unicode.py"
        unicode_file.write_text("# Héllo Wörld 🚀\ndef test():\n    return '✓'\n")

        files = analyzer._find_code_files()
        assert len(files) == 1

        result = analyzer.analyze()
        assert result["total_files"] == 1

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_analyze_file_read_error(self, temp_dir):
        """Test handling file read errors."""
        analyzer = CodeQualityAnalyzer(temp_dir)
        test_file = temp_dir / "test.py"
        test_file.write_text("print('test')\n")

        # Simulate read error by mocking
        with patch.object(Path, "read_text", side_effect=OSError("Read failed")):
            metrics = analyzer._analyze_file(test_file)
            assert metrics is None

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_relative_path_handling(self, temp_dir):
        """Test correct relative path handling."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "test.py").write_text("print('test')\n")

        analyzer = CodeQualityAnalyzer(temp_dir)
        result = analyzer.analyze()

        assert result["total_files"] == 1
        file_path = result["files"][0]["file_path"]
        # Should be relative path like "subdir/test.py" or "subdir\test.py"
        assert "test.py" in file_path


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_full_python_project_workflow(self, python_project):
        """Test complete workflow for Python project."""
        analyzer = CodeQualityAnalyzer(python_project)
        result = analyzer.analyze()

        # Verify result structure
        assert isinstance(result, dict)
        assert "total_files" in result
        assert "total_lines" in result
        assert "average_complexity" in result
        assert "average_maintainability" in result
        assert "high_complexity_count" in result
        assert "critical_complexity_count" in result
        assert "technical_debt_score" in result
        assert "files" in result

        # Verify files have expected structure
        for file_info in result["files"]:
            assert "file_path" in file_info
            assert "language" in file_info
            assert "lines_of_code" in file_info
            assert "complexity" in file_info
            assert "functions" in file_info

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_high_complexity_detection(self, python_project):
        """Test that high complexity functions are detected."""
        analyzer = CodeQualityAnalyzer(python_project)
        result = analyzer.analyze()

        # complex.py has a function with complexity > 10
        assert result["high_complexity_count"] > 0

    @pytest.mark.skipif(not HAS_RADON, reason="radon library not available")
    def test_technical_debt_calculation(self, python_project):
        """Test technical debt score is calculated."""
        analyzer = CodeQualityAnalyzer(python_project)
        result = analyzer.analyze()

        assert result["technical_debt_score"] >= 0
        assert result["technical_debt_score"] <= 100
