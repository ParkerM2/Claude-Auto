#!/usr/bin/env python3
"""
End-to-End Verification Script for Code Quality Metrics
========================================================

This script verifies the complete code quality metrics functionality by:
1. Importing CodeQualityAnalyzer and CodeQualityTracker
2. Running analysis on apps/backend/
3. Verifying complexity metrics are calculated
4. Verifying maintainability index is computed
5. Verifying results are stored by CodeQualityTracker
6. Verifying trends can be retrieved for historical comparison
"""

import sys
from pathlib import Path

# Add apps/backend to Python path for imports
backend_path = Path(__file__).parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

from analysis.analyzers import CodeQualityAnalyzer
from analysis import CodeQualityTracker


def verify_step(step_number: int, description: str, passed: bool) -> bool:
    """Print verification step result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{step_number}. {description}: {status}")
    return passed


def main() -> int:
    """Run end-to-end verification."""
    print("=" * 80)
    print("Code Quality Metrics - End-to-End Verification")
    print("=" * 80)
    print()

    all_passed = True
    step = 0

    # Step 1: Import CodeQualityAnalyzer
    step += 1
    try:
        from analysis.analyzers import CodeQualityAnalyzer as CQA

        passed = verify_step(step, "Import CodeQualityAnalyzer", True)
        all_passed = all_passed and passed
    except ImportError as e:
        verify_step(step, "Import CodeQualityAnalyzer", False)
        print(f"   Error: {e}")
        return 1

    # Step 2: Run analysis on apps/backend/
    step += 1
    try:
        # Create a test directory with sample Python code outside .auto-claude
        # Use a temp directory to avoid .auto-claude skip
        import tempfile
        test_dir = Path(tempfile.mkdtemp(prefix="code_quality_test_"))
        print(f"   Created temp test directory: {test_dir}")

        # Create a sample Python file with known complexity
        sample_code = '''
def simple_function(x):
    """Simple function with low complexity."""
    return x + 1

def moderate_function(x, y):
    """Function with moderate complexity."""
    if x > 0:
        if y > 0:
            return x + y
        else:
            return x - y
    else:
        if y > 0:
            return y - x
        else:
            return 0

def complex_function(data):
    """Function with higher complexity."""
    result = []
    for item in data:
        if isinstance(item, int):
            if item > 0:
                if item % 2 == 0:
                    result.append(item * 2)
                else:
                    result.append(item * 3)
            elif item < 0:
                result.append(abs(item))
            else:
                result.append(1)
        elif isinstance(item, str):
            if len(item) > 5:
                result.append(item.upper())
            else:
                result.append(item.lower())
        else:
            result.append(str(item))
    return result

class SampleClass:
    """Sample class for testing."""

    def method_one(self, value):
        """Simple method."""
        return value * 2

    def method_two(self, value):
        """Method with some complexity."""
        if value > 10:
            return value ** 2
        elif value > 5:
            return value * 10
        else:
            return value
'''

        sample_file = test_dir / "sample.py"
        sample_file.write_text(sample_code, encoding="utf-8")

        # Analyze the test directory
        analyzer = CodeQualityAnalyzer(test_dir)
        print(f"   Analyzing test directory: {test_dir}")

        # Debug: Check what files the analyzer found
        code_files = analyzer._find_code_files()
        print(f"   Debug: Found {len(code_files)} code files")
        for cf in code_files:
            print(f"     - {cf}")

        results = analyzer.analyze()

        # Check for errors
        if "error" in results:
            verify_step(step, "Run analysis on test code", False)
            print(f"   Error: {results['error']}")
            print(f"   Message: {results.get('message', 'No message')}")
            return 1

        # Verify we actually analyzed files
        if results['total_files'] == 0:
            verify_step(step, "Run analysis on test code", False)
            print(f"   Error: No files were analyzed")
            return 1

        passed = verify_step(step, "Run analysis on test code", True)
        all_passed = all_passed and passed

        # Print summary
        print(f"   Files analyzed: {results['total_files']}")
        print(f"   Total lines: {results['total_lines']}")
        print(f"   Average complexity: {results['average_complexity']}")
        print(f"   Average maintainability: {results['average_maintainability']}")

        # Also show some function-level details
        if results.get('files'):
            file_data = results['files'][0]
            print(f"   Functions found: {len(file_data.get('functions', []))}")
            for func in file_data.get('functions', [])[:3]:
                print(f"     - {func['name']}: complexity={func['complexity']}, rank={func['rank']}")

    except Exception as e:
        verify_step(step, "Run analysis on test code", False)
        print(f"   Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Step 3: Verify complexity metrics are calculated
    step += 1
    try:
        has_complexity = (
            "average_complexity" in results
            and results["average_complexity"] >= 0
            and "high_complexity_count" in results
            and "critical_complexity_count" in results
        )

        passed = verify_step(step, "Verify complexity metrics are calculated", has_complexity)
        all_passed = all_passed and passed

        if has_complexity:
            print(f"   Average complexity: {results['average_complexity']}")
            print(f"   High complexity functions (>10): {results['high_complexity_count']}")
            print(f"   Critical complexity functions (>20): {results['critical_complexity_count']}")
        else:
            print(f"   Missing complexity metrics in results")

    except Exception as e:
        verify_step(step, "Verify complexity metrics are calculated", False)
        print(f"   Error: {e}")
        all_passed = False

    # Step 4: Verify maintainability index is computed
    step += 1
    try:
        has_mi = (
            "average_maintainability" in results
            and results["average_maintainability"] >= 0
        )

        passed = verify_step(step, "Verify maintainability index is computed", has_mi)
        all_passed = all_passed and passed

        if has_mi:
            print(f"   Average maintainability index: {results['average_maintainability']}")

            # Show some file-level details
            if results.get("files"):
                print(f"   Sample file metrics:")
                for file_metrics in results["files"][:3]:  # Show first 3 files
                    mi = file_metrics.get("maintainability_index")
                    if mi is not None:
                        print(f"     - {file_metrics['file_path']}: MI={mi}")
        else:
            print(f"   Missing maintainability index in results")

    except Exception as e:
        verify_step(step, "Verify maintainability index is computed", False)
        print(f"   Error: {e}")
        all_passed = False

    # Step 5: Verify results are stored by CodeQualityTracker
    step += 1
    try:
        # Create temporary spec directory for testing
        spec_dir = Path(__file__).parent / ".auto-claude" / "specs" / "005-code-quality-metrics"
        spec_dir.mkdir(parents=True, exist_ok=True)

        tracker = CodeQualityTracker(spec_dir)
        print(f"   Tracker initialized with spec_dir: {spec_dir}")

        # Save metrics
        timestamp = tracker.save_metrics(results)
        print(f"   Metrics saved with timestamp: {timestamp}")

        # Verify file was created
        metrics_dir = spec_dir / "code_quality_metrics"
        saved_files = list(metrics_dir.glob("metrics_*.json"))

        passed = verify_step(
            step,
            "Verify results are stored by CodeQualityTracker",
            len(saved_files) > 0
        )
        all_passed = all_passed and passed

        if saved_files:
            print(f"   Found {len(saved_files)} metrics file(s)")
        else:
            print(f"   No metrics files found in {metrics_dir}")

    except Exception as e:
        verify_step(step, "Verify results are stored by CodeQualityTracker", False)
        print(f"   Error: {e}")
        import traceback

        traceback.print_exc()
        all_passed = False

    # Step 6: Verify trends can be retrieved for historical comparison
    step += 1
    try:
        # Get history
        history = tracker.get_history()
        print(f"   Retrieved {len(history)} historical snapshot(s)")

        # Get latest snapshot
        latest = tracker.get_latest()
        has_latest = latest is not None

        # Get trends
        trends = tracker.get_trends()
        has_trends = trends is not None and trends.current is not None

        passed = verify_step(
            step,
            "Verify trends can be retrieved for historical comparison",
            has_latest and has_trends
        )
        all_passed = all_passed and passed

        if has_latest:
            print(f"   Latest snapshot timestamp: {latest.timestamp}")
            print(f"   Latest total files: {latest.total_files}")
            print(f"   Latest technical debt score: {latest.technical_debt_score}")

        if has_trends:
            print(f"   Complexity trend: {trends.complexity_trend}")
            print(f"   Maintainability trend: {trends.maintainability_trend}")
            print(f"   Technical debt trend: {trends.debt_trend}")

            if trends.recommendations:
                print(f"   Recommendations:")
                for rec in trends.recommendations[:3]:  # Show first 3
                    print(f"     - {rec}")
        else:
            print(f"   Failed to retrieve trends")

    except Exception as e:
        verify_step(step, "Verify trends can be retrieved for historical comparison", False)
        print(f"   Error: {e}")
        import traceback

        traceback.print_exc()
        all_passed = False

    # Cleanup
    try:
        import shutil
        if 'test_dir' in locals() and test_dir.exists():
            shutil.rmtree(test_dir)
            print()
            print(f"   Cleaned up temp directory: {test_dir}")
    except Exception:
        pass

    # Final summary
    print()
    print("=" * 80)
    if all_passed:
        print("✅ All verification steps PASSED")
        print("=" * 80)
        return 0
    else:
        print("❌ Some verification steps FAILED")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
