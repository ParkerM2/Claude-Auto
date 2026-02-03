#!/usr/bin/env python3
"""
Performance Benchmark for Large Codebases
==========================================

Benchmarks the large codebase optimization components:
- IncrementalIndexer: Change detection performance
- ContextSelector: Relevance scoring and file selection
- StreamingAnalyzer: Memory-bounded file processing

Tests with configurable file counts (1k, 10k, 100k) to verify:
- Performance degradation < 10% vs baseline
- Memory usage < 500MB
- Cache hit rate > 80%

Usage:
    python tests/benchmark_large_codebase.py --files 1000
    python tests/benchmark_large_codebase.py --files 1000 10000 100000
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
import types
from collections.abc import Generator, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Setup path for imports
REPO_ROOT = Path(__file__).parent.parent
BACKEND_DIR = REPO_ROOT / "apps" / "backend"
ANALYSIS_DIR = BACKEND_DIR / "analysis"

# Create a simple module loader that properly registers modules
import types

def load_module_from_file(module_name: str, file_path: Path, replacements: dict[str, str] = None, inject_globals: dict = None):
    """Load a Python module from file, handling imports."""
    code = file_path.read_text()

    # Apply string replacements to fix imports
    if replacements:
        for old, new in replacements.items():
            code = code.replace(old, new)

    # Create a proper module
    module = types.ModuleType(module_name)
    module.__file__ = str(file_path)

    # Register in sys.modules so dataclasses and other introspection works
    sys.modules[module_name] = module

    # Setup globals with only essential builtins and imports
    # Don't use **globals() as it would inject our argparse and other local variables
    module_globals = {
        "__name__": module_name,
        "__file__": str(file_path),
        "__package__": None,
        "__builtins__": __builtins__,
        # Explicitly add common imports that modules might need
        "Path": Path,
        "sys": sys,
        "os": os,
        "time": time,
        "json": json,
        "Any": Any,
        "Generator": Generator,
        "Iterator": Iterator,
        "dataclass": dataclass,
        "field": field,
    }

    # Inject additional globals if provided
    if inject_globals:
        module_globals.update(inject_globals)

    # Execute the module code
    exec(code, module_globals)

    # Update the module with executed globals
    module.__dict__.update(module_globals)

    return module

# Load modules in dependency order
# 1. file_index.py
file_index_module = load_module_from_file("file_index", ANALYSIS_DIR / "file_index.py")
FileIndex = file_index_module.FileIndex

# 2. incremental_indexer.py
incremental_indexer_module = load_module_from_file(
    "incremental_indexer",
    ANALYSIS_DIR / "incremental_indexer.py",
    replacements={"from .file_index import FileIndex": "# from .file_index import FileIndex"},
    inject_globals={"FileIndex": FileIndex}
)
IncrementalIndexer = incremental_indexer_module.IncrementalIndexer

# 3. base.py (for SKIP_DIRS)
try:
    base_module = load_module_from_file("base", ANALYSIS_DIR / "analyzers" / "base.py")
    SKIP_DIRS = getattr(base_module, "SKIP_DIRS", {"node_modules", ".git", "__pycache__"})
except Exception:
    SKIP_DIRS = {"node_modules", ".git", "__pycache__"}

# 4. context_selector.py
context_selector_module = load_module_from_file(
    "context_selector",
    ANALYSIS_DIR / "context_selector.py",
    replacements={"from .analyzers.base import SKIP_DIRS": "# from .analyzers.base import SKIP_DIRS"},
    inject_globals={"SKIP_DIRS": SKIP_DIRS}
)
ContextSelector = context_selector_module.ContextSelector

# 5. streaming_analyzer.py
streaming_analyzer_module = load_module_from_file(
    "streaming_analyzer",
    ANALYSIS_DIR / "streaming_analyzer.py",
    replacements={"from .analyzers.base import SKIP_DIRS": "# from .analyzers.base import SKIP_DIRS"},
    inject_globals={"SKIP_DIRS": SKIP_DIRS}
)
StreamingAnalyzer = streaming_analyzer_module.StreamingAnalyzer


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""

    file_count: int
    component: str
    operation: str
    duration_seconds: float
    memory_mb: float
    peak_memory_mb: float
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with computed properties."""
        result = asdict(self)
        result['cache_hit_rate'] = self.cache_hit_rate
        return result


@dataclass
class BenchmarkSummary:
    """Summary of all benchmark results."""

    results: list[BenchmarkResult]
    baseline_file_count: int
    max_memory_threshold_mb: int = 500
    max_degradation_percent: int = 10

    def analyze_degradation(self) -> dict[str, Any]:
        """Analyze performance degradation vs baseline."""
        baseline_results = [r for r in self.results if r.file_count == self.baseline_file_count]
        if not baseline_results:
            return {"error": "No baseline results found"}

        # Group by component and operation
        baseline_times = {}
        for result in baseline_results:
            key = f"{result.component}:{result.operation}"
            baseline_times[key] = result.duration_seconds

        # Calculate degradation for each result
        degradations = []
        for result in self.results:
            if result.file_count == self.baseline_file_count:
                continue

            key = f"{result.component}:{result.operation}"
            baseline_time = baseline_times.get(key)
            if baseline_time and baseline_time > 0:
                degradation_pct = ((result.duration_seconds - baseline_time) / baseline_time) * 100
                degradations.append({
                    "file_count": result.file_count,
                    "component": result.component,
                    "operation": result.operation,
                    "baseline_seconds": baseline_time,
                    "current_seconds": result.duration_seconds,
                    "degradation_percent": degradation_pct,
                    "passes": degradation_pct <= self.max_degradation_percent
                })

        return {
            "baseline_file_count": self.baseline_file_count,
            "max_allowed_degradation": self.max_degradation_percent,
            "degradations": degradations
        }

    def check_memory_usage(self) -> dict[str, Any]:
        """Check if memory usage is within threshold."""
        memory_checks = []
        for result in self.results:
            passes = result.peak_memory_mb <= self.max_memory_threshold_mb
            memory_checks.append({
                "file_count": result.file_count,
                "component": result.component,
                "peak_memory_mb": result.peak_memory_mb,
                "threshold_mb": self.max_memory_threshold_mb,
                "passes": passes
            })

        return {
            "max_memory_threshold_mb": self.max_memory_threshold_mb,
            "checks": memory_checks
        }

    def check_cache_hit_rate(self, min_rate: float = 0.8) -> dict[str, Any]:
        """Check if cache hit rate meets minimum threshold."""
        cache_checks = []
        for result in self.results:
            if result.cache_hits + result.cache_misses == 0:
                continue

            passes = result.cache_hit_rate >= min_rate
            cache_checks.append({
                "file_count": result.file_count,
                "component": result.component,
                "cache_hit_rate": result.cache_hit_rate,
                "min_rate": min_rate,
                "passes": passes
            })

        return {
            "min_cache_hit_rate": min_rate,
            "checks": cache_checks
        }


# =============================================================================
# MEMORY TRACKING
# =============================================================================


class MemoryTracker:
    """Track memory usage during benchmark execution."""

    def __init__(self):
        self.start_memory_mb = 0.0
        self.peak_memory_mb = 0.0
        self._process = psutil.Process() if HAS_PSUTIL else None

    def start(self):
        """Start tracking memory."""
        if self._process:
            self.start_memory_mb = self._process.memory_info().rss / 1024 / 1024
            self.peak_memory_mb = self.start_memory_mb

    def update(self):
        """Update peak memory if current usage is higher."""
        if self._process:
            current_mb = self._process.memory_info().rss / 1024 / 1024
            self.peak_memory_mb = max(self.peak_memory_mb, current_mb)

    def get_current_mb(self) -> float:
        """Get current memory usage in MB."""
        if self._process:
            return self._process.memory_info().rss / 1024 / 1024
        return 0.0

    def get_delta_mb(self) -> float:
        """Get memory delta from start."""
        return self.get_current_mb() - self.start_memory_mb


# =============================================================================
# TEST DATA GENERATION
# =============================================================================


def create_test_codebase(base_dir: Path, file_count: int) -> Path:
    """
    Create a test codebase with specified number of files.

    Args:
        base_dir: Base directory for test codebase
        file_count: Number of files to create

    Returns:
        Path to created test codebase
    """
    test_dir = base_dir / f"test_codebase_{file_count}"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create directory structure
    dirs = ["src", "tests", "lib", "utils", "models", "controllers", "views", "api"]
    for dir_name in dirs:
        (test_dir / dir_name).mkdir(exist_ok=True)

    # Calculate files per directory
    files_per_dir = file_count // len(dirs)

    # Create Python files with realistic content
    file_num = 0
    for dir_name in dirs:
        dir_path = test_dir / dir_name
        for i in range(files_per_dir):
            file_path = dir_path / f"module_{i}.py"
            content = f'''"""
{dir_name.title()} Module {i}
"""

def authenticate_user(username, password):
    """Authenticate a user with credentials."""
    if not username or not password:
        return False
    return validate_credentials(username, password)

def validate_credentials(username, password):
    """Validate user credentials against database."""
    user = get_user_by_username(username)
    if not user:
        return False
    return check_password_hash(user.password_hash, password)

def get_user_by_username(username):
    """Retrieve user from database by username."""
    return database.query(User).filter_by(username=username).first()

class User:
    """User model for authentication."""

    def __init__(self, username, password_hash):
        self.username = username
        self.password_hash = password_hash
        self.created_at = datetime.now()

    def check_password(self, password):
        """Check if password matches hash."""
        return check_password_hash(self.password_hash, password)
'''
            file_path.write_text(content)
            file_num += 1

            if file_num >= file_count:
                break

        if file_num >= file_count:
            break

    return test_dir


# =============================================================================
# BENCHMARK OPERATIONS
# =============================================================================


def benchmark_incremental_indexer(
    test_dir: Path,
    file_count: int,
    tracker: MemoryTracker
) -> list[BenchmarkResult]:
    """
    Benchmark IncrementalIndexer operations.

    Tests:
    - Initial indexing
    - Change detection (no changes)
    - Change detection (with changes)
    - Index update
    """
    results = []

    # Initial indexing
    tracker.start()
    start_time = time.time()
    indexer = IncrementalIndexer(str(test_dir))
    changes = indexer.detect_changes()
    duration = time.time() - start_time
    tracker.update()

    results.append(BenchmarkResult(
        file_count=file_count,
        component="IncrementalIndexer",
        operation="initial_index",
        duration_seconds=duration,
        memory_mb=tracker.get_delta_mb(),
        peak_memory_mb=tracker.peak_memory_mb
    ))

    # Update index
    tracker.start()
    start_time = time.time()
    indexer.update_index()
    duration = time.time() - start_time
    tracker.update()

    results.append(BenchmarkResult(
        file_count=file_count,
        component="IncrementalIndexer",
        operation="update_index",
        duration_seconds=duration,
        memory_mb=tracker.get_delta_mb(),
        peak_memory_mb=tracker.peak_memory_mb
    ))

    # Change detection (no changes - should be fast with cache)
    tracker.start()
    start_time = time.time()
    changes = indexer.detect_changes()
    duration = time.time() - start_time
    tracker.update()

    cache_hits = len(changes.unchanged)
    cache_misses = len(changes.added) + len(changes.modified)

    results.append(BenchmarkResult(
        file_count=file_count,
        component="IncrementalIndexer",
        operation="detect_changes_cached",
        duration_seconds=duration,
        memory_mb=tracker.get_delta_mb(),
        peak_memory_mb=tracker.peak_memory_mb,
        cache_hits=cache_hits,
        cache_misses=cache_misses
    ))

    # Modify a file to test change detection
    test_file = test_dir / "src" / "module_0.py"
    if test_file.exists():
        content = test_file.read_text()
        test_file.write_text(content + "\n# Modified\n")
        time.sleep(0.01)  # Ensure mtime changes

        tracker.start()
        start_time = time.time()
        changes = indexer.detect_changes()
        duration = time.time() - start_time
        tracker.update()

        results.append(BenchmarkResult(
            file_count=file_count,
            component="IncrementalIndexer",
            operation="detect_changes_modified",
            duration_seconds=duration,
            memory_mb=tracker.get_delta_mb(),
            peak_memory_mb=tracker.peak_memory_mb,
            cache_hits=len(changes.unchanged),
            cache_misses=len(changes.modified) + len(changes.added)
        ))

    return results


def benchmark_context_selector(
    test_dir: Path,
    file_count: int,
    tracker: MemoryTracker
) -> list[BenchmarkResult]:
    """
    Benchmark ContextSelector operations.

    Tests:
    - File relevance scoring
    - File selection with max_files limit
    - File selection with max_tokens limit
    """
    results = []

    # Create selector
    tracker.start()
    start_time = time.time()
    selector = ContextSelector(str(test_dir))
    duration = time.time() - start_time
    tracker.update()

    results.append(BenchmarkResult(
        file_count=file_count,
        component="ContextSelector",
        operation="initialize",
        duration_seconds=duration,
        memory_mb=tracker.get_delta_mb(),
        peak_memory_mb=tracker.peak_memory_mb
    ))

    # Score relevance for a single file
    test_file = "src/module_0.py"
    task = "implement user authentication"

    tracker.start()
    start_time = time.time()
    score = selector.score_relevance(test_file, task)
    duration = time.time() - start_time
    tracker.update()

    results.append(BenchmarkResult(
        file_count=file_count,
        component="ContextSelector",
        operation="score_single_file",
        duration_seconds=duration,
        memory_mb=tracker.get_delta_mb(),
        peak_memory_mb=tracker.peak_memory_mb
    ))

    # Select files with max_files limit
    tracker.start()
    start_time = time.time()
    selected_files = selector.select_files(task, max_files=min(100, file_count // 10))
    duration = time.time() - start_time
    tracker.update()

    results.append(BenchmarkResult(
        file_count=file_count,
        component="ContextSelector",
        operation="select_files_by_count",
        duration_seconds=duration,
        memory_mb=tracker.get_delta_mb(),
        peak_memory_mb=tracker.peak_memory_mb
    ))

    # Select files with max_tokens limit
    tracker.start()
    start_time = time.time()
    selected_files = selector.select_files(task, max_tokens=50000)
    duration = time.time() - start_time
    tracker.update()

    results.append(BenchmarkResult(
        file_count=file_count,
        component="ContextSelector",
        operation="select_files_by_tokens",
        duration_seconds=duration,
        memory_mb=tracker.get_delta_mb(),
        peak_memory_mb=tracker.peak_memory_mb
    ))

    return results


def benchmark_streaming_analyzer(
    test_dir: Path,
    file_count: int,
    tracker: MemoryTracker
) -> list[BenchmarkResult]:
    """
    Benchmark StreamingAnalyzer operations.

    Tests:
    - Memory-bounded analysis
    - Analysis with different batch sizes
    """
    results = []

    # Analyze with default batch size
    tracker.start()
    start_time = time.time()
    analyzer = StreamingAnalyzer(str(test_dir), max_memory_mb=100)
    analysis_result = analyzer.analyze()
    duration = time.time() - start_time
    tracker.update()

    results.append(BenchmarkResult(
        file_count=file_count,
        component="StreamingAnalyzer",
        operation="analyze_default_batch",
        duration_seconds=duration,
        memory_mb=tracker.get_delta_mb(),
        peak_memory_mb=analysis_result.peak_memory_mb
    ))

    # Analyze with larger batch size
    tracker.start()
    start_time = time.time()
    analyzer = StreamingAnalyzer(str(test_dir), max_memory_mb=200, batch_size=500)
    analysis_result = analyzer.analyze()
    duration = time.time() - start_time
    tracker.update()

    results.append(BenchmarkResult(
        file_count=file_count,
        component="StreamingAnalyzer",
        operation="analyze_large_batch",
        duration_seconds=duration,
        memory_mb=tracker.get_delta_mb(),
        peak_memory_mb=analysis_result.peak_memory_mb
    ))

    return results


# =============================================================================
# MAIN BENCHMARK RUNNER
# =============================================================================


def run_benchmark(file_count: int, temp_dir: Path) -> list[BenchmarkResult]:
    """
    Run all benchmarks for a given file count.

    Args:
        file_count: Number of files to test with
        temp_dir: Temporary directory for test data

    Returns:
        List of benchmark results
    """
    print(f"\n{'='*70}")
    print(f"Running benchmark with {file_count:,} files")
    print(f"{'='*70}")

    # Create test codebase
    print(f"Creating test codebase...")
    test_dir = create_test_codebase(temp_dir, file_count)
    print(f"✓ Test codebase created at {test_dir}")

    tracker = MemoryTracker()
    all_results = []

    # Run benchmarks
    print("\nBenchmarking IncrementalIndexer...")
    results = benchmark_incremental_indexer(test_dir, file_count, tracker)
    all_results.extend(results)
    for result in results:
        print(f"  {result.operation}: {result.duration_seconds:.3f}s, "
              f"memory: {result.peak_memory_mb:.1f}MB")

    print("\nBenchmarking ContextSelector...")
    results = benchmark_context_selector(test_dir, file_count, tracker)
    all_results.extend(results)
    for result in results:
        print(f"  {result.operation}: {result.duration_seconds:.3f}s, "
              f"memory: {result.peak_memory_mb:.1f}MB")

    print("\nBenchmarking StreamingAnalyzer...")
    results = benchmark_streaming_analyzer(test_dir, file_count, tracker)
    all_results.extend(results)
    for result in results:
        print(f"  {result.operation}: {result.duration_seconds:.3f}s, "
              f"memory: {result.peak_memory_mb:.1f}MB")

    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)

    return all_results


def print_summary(summary: BenchmarkSummary):
    """Print benchmark summary and analysis."""
    print(f"\n{'='*70}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*70}")

    # Performance degradation analysis
    degradation = summary.analyze_degradation()
    if "error" not in degradation:
        print(f"\nPerformance Degradation (baseline: {degradation['baseline_file_count']:,} files)")
        print(f"Max allowed: {degradation['max_allowed_degradation']}%\n")

        for deg in degradation['degradations']:
            status = "✓ PASS" if deg['passes'] else "✗ FAIL"
            print(f"{status} {deg['component']}.{deg['operation']}")
            print(f"     {deg['file_count']:,} files: {deg['degradation_percent']:+.1f}% "
                  f"({deg['baseline_seconds']:.3f}s → {deg['current_seconds']:.3f}s)")

    # Memory usage check
    memory_check = summary.check_memory_usage()
    print(f"\nMemory Usage (threshold: {memory_check['max_memory_threshold_mb']}MB)\n")

    for check in memory_check['checks']:
        status = "✓ PASS" if check['passes'] else "✗ FAIL"
        print(f"{status} {check['component']} with {check['file_count']:,} files: "
              f"{check['peak_memory_mb']:.1f}MB")

    # Cache hit rate check
    cache_check = summary.check_cache_hit_rate()
    if cache_check['checks']:
        print(f"\nCache Hit Rate (minimum: {cache_check['min_cache_hit_rate']:.0%})\n")

        for check in cache_check['checks']:
            status = "✓ PASS" if check['passes'] else "✗ FAIL"
            print(f"{status} {check['component']} with {check['file_count']:,} files: "
                  f"{check['cache_hit_rate']:.1%}")

    # Overall result
    print(f"\n{'='*70}")
    all_pass = (
        all(d['passes'] for d in degradation.get('degradations', [])) and
        all(c['passes'] for c in memory_check['checks']) and
        all(c['passes'] for c in cache_check['checks'])
    )

    if all_pass:
        print("✓ BENCHMARK PASSED - All acceptance criteria met")
    else:
        print("✗ BENCHMARK FAILED - Some acceptance criteria not met")
    print(f"{'='*70}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark large codebase optimization components"
    )
    parser.add_argument(
        "--files",
        type=int,
        nargs="+",
        default=[1000],
        help="File counts to test (default: 1000)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="JSON file to write results to"
    )

    args = parser.parse_args()

    if not HAS_PSUTIL:
        print("Warning: psutil not installed, memory tracking will be limited")
        print("Install with: pip install psutil")

    # Run benchmarks
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        all_results = []

        for file_count in args.files:
            results = run_benchmark(file_count, temp_path)
            all_results.extend(results)

        # Create summary
        baseline = min(args.files)
        summary = BenchmarkSummary(results=all_results, baseline_file_count=baseline)

        # Print summary
        print_summary(summary)

        # Write results to file if requested
        if args.output:
            output_data = {
                "results": [r.to_dict() for r in all_results],
                "summary": {
                    "baseline_file_count": baseline,
                    "degradation": summary.analyze_degradation(),
                    "memory": summary.check_memory_usage(),
                    "cache": summary.check_cache_hit_rate()
                }
            }

            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)

            print(f"\nResults written to {args.output}")

    print("\nBenchmark completed")


if __name__ == "__main__":
    main()
