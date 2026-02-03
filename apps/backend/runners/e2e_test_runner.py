#!/usr/bin/env python3
"""
E2E Test Runner
===============

CLI entry point for Claude-powered E2E testing via MCP Electron server.

This runner orchestrates end-to-end testing of Electron applications by:
1. Loading test scenarios from YAML files
2. Creating a Claude SDK client with Electron MCP enabled
3. Running an agent session with test instructions
4. Parsing agent results and generating reports
5. Checking logs for errors

Prerequisites:
- Electron app running with --remote-debugging-port=9222
- ELECTRON_MCP_ENABLED=true in environment
- Test scenarios in apps/frontend/e2e/scenarios/

Usage:
    python runners/e2e_test_runner.py --project /path/to/project [options]

Options:
    --project <path>     Project directory (required)
    --scenario <name>    Scenario to run: smoke, regression, all (default: smoke)
    --port <port>        CDP debug port (default: 9222)
    --verbose            Enable verbose output
    --report-dir <path>  Report output directory
"""

import sys

# Python version check
if sys.version_info < (3, 10):
    sys.exit(
        f"Error: Auto Claude requires Python 3.10 or higher.\n"
        f"You are running Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )

import io
import os
from pathlib import Path

# Configure safe encoding on Windows
if sys.platform == "win32":
    for _stream_name in ("stdout", "stderr"):
        _stream = getattr(sys, _stream_name)
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
                continue
            except (AttributeError, io.UnsupportedOperation, OSError):
                pass
        try:
            if hasattr(_stream, "buffer"):
                _new_stream = io.TextIOWrapper(
                    _stream.buffer,
                    encoding="utf-8",
                    errors="replace",
                    line_buffering=True,
                )
                setattr(sys, _stream_name, _new_stream)
        except (AttributeError, io.UnsupportedOperation, OSError):
            pass
    del _stream_name, _stream
    if "_new_stream" in dir():
        del _new_stream

# Add auto-claude to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Validate platform dependencies
from core.dependency_validator import validate_platform_dependencies

validate_platform_dependencies()

# Load .env
from cli.utils import import_dotenv

load_dotenv = import_dotenv()

env_file = Path(__file__).parent.parent / ".env"
dev_env_file = Path(__file__).parent.parent.parent / "dev" / "auto-claude" / ".env"
if env_file.exists():
    load_dotenv(env_file)
elif dev_env_file.exists():
    load_dotenv(dev_env_file)

import argparse
import json
import subprocess
import time
import urllib.request
from datetime import datetime
from typing import Any

import yaml

from debug import debug, debug_error, debug_section, debug_success
from ui import Icons, highlight, muted, print_section, print_status


def check_cdp_connection(port: int, timeout: float = 5.0) -> dict[str, Any]:
    """Check if CDP is available on the debug port."""
    url = f"http://127.0.0.1:{port}/json/version"
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                data = json.loads(response.read().decode())
                return {"connected": True, "info": data}
        except Exception:
            time.sleep(0.5)

    return {"connected": False, "error": "Connection timeout"}


def load_scenario(scenario_path: Path) -> dict[str, Any]:
    """Load a test scenario from YAML file."""
    if not scenario_path.exists():
        return {"error": f"Scenario file not found: {scenario_path}"}

    try:
        with open(scenario_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        return {"error": f"Failed to load scenario: {e}"}


def get_scenarios_dir(project_dir: Path) -> Path:
    """Get the scenarios directory for a project."""
    # Check if this is the frontend project
    if (project_dir / "e2e" / "scenarios").exists():
        return project_dir / "e2e" / "scenarios"

    # Check if project has apps/frontend structure
    frontend_scenarios = project_dir / "apps" / "frontend" / "e2e" / "scenarios"
    if frontend_scenarios.exists():
        return frontend_scenarios

    # Default to project's e2e directory
    return project_dir / "e2e" / "scenarios"


def generate_test_prompt(scenario: dict[str, Any], port: int) -> str:
    """Generate the test prompt for the Claude agent."""
    scenario_name = scenario.get("name", "Unknown")
    description = scenario.get("description", "")
    tests = scenario.get("scenarios", [])

    prompt_parts = [
        "# E2E Test Execution",
        "",
        f"**Scenario**: {scenario_name}",
        f"**Description**: {description}",
        "",
        "## Prerequisites",
        f"- Electron app is running with CDP on port {port}",
        "- Use the Electron MCP tools to interact with the app",
        "",
        "## Test Instructions",
        "",
        "For each test scenario below:",
        "1. Execute the test steps using the appropriate Electron MCP tools",
        "2. Verify the expected outcomes",
        "3. Report PASS or FAIL with details",
        "4. Check console logs for errors after each test",
        "",
        "## Test Scenarios",
        "",
    ]

    for i, test in enumerate(tests, 1):
        test_name = test.get("name", f"Test {i}")
        steps = test.get("steps", [])

        prompt_parts.append(f"### {i}. {test_name}")
        prompt_parts.append("")

        for j, step in enumerate(steps, 1):
            action = step.get("action", "unknown")
            args = {k: v for k, v in step.items() if k != "action"}
            args_str = ", ".join(f"{k}={v}" for k, v in args.items()) if args else ""
            prompt_parts.append(f"   {j}. {action}({args_str})")

        prompt_parts.append("")

    prompt_parts.extend(
        [
            "## Reporting",
            "",
            "After running all tests, provide a summary in this format:",
            "",
            "```",
            "TEST RESULTS:",
            "- Test Name: PASS/FAIL - Details",
            "- ...",
            "",
            "CONSOLE ERRORS: [list any console errors found]",
            "",
            "OVERALL: X/Y tests passed",
            "```",
        ]
    )

    return "\n".join(prompt_parts)


def run_agent_tests(
    project_dir: Path,
    scenario: dict[str, Any],
    port: int,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run tests using a Claude agent with Electron MCP tools."""
    from core.client import create_client

    # Create a temporary spec directory for the test session
    test_spec_dir = project_dir / ".auto-claude" / "e2e-tests"
    test_spec_dir.mkdir(parents=True, exist_ok=True)

    # Generate test prompt
    test_prompt = generate_test_prompt(scenario, port)

    if verbose:
        print_section("Test Prompt", test_prompt)

    try:
        # Create Claude SDK client with Electron MCP enabled
        # We use qa_reviewer agent type as it has Electron tools access
        client = create_client(
            project_dir=str(project_dir),
            spec_dir=str(test_spec_dir),
            model="claude-sonnet-4-5-20250929",
            agent_type="qa_reviewer",
            max_thinking_tokens=None,
        )

        print_status(Icons.ROBOT, "Running E2E tests via Claude agent...")

        # Run agent session
        start_time = time.time()
        response = client.create_agent_session(
            name="e2e-test-session",
            starting_message=test_prompt,
        )
        elapsed = time.time() - start_time

        # Parse results from agent response
        results = {
            "scenario": scenario.get("name", "Unknown"),
            "elapsed_seconds": elapsed,
            "agent_response": str(response) if response else None,
            "status": "completed",
        }

        # Try to extract test results from response
        if response:
            response_text = str(response)
            if "OVERALL:" in response_text:
                # Extract pass/fail summary
                for line in response_text.split("\n"):
                    if "OVERALL:" in line:
                        results["summary"] = line.strip()
                        break

        return results

    except Exception as e:
        debug_error("e2e_test_runner", f"Agent test failed: {e}")
        return {
            "scenario": scenario.get("name", "Unknown"),
            "status": "error",
            "error": str(e),
        }


def generate_report(
    results: list[dict[str, Any]],
    report_dir: Path,
) -> Path:
    """Generate a test report."""
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_file = report_dir / f"e2e-report-{timestamp}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "summary": {
            "total": len(results),
            "completed": len([r for r in results if r.get("status") == "completed"]),
            "errors": len([r for r in results if r.get("status") == "error"]),
        },
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print_status(Icons.CHECK, f"Report saved to: {report_file}")
    return report_file


def main():
    """CLI entry point."""
    debug_section("e2e_test_runner", "E2E Test Runner")

    parser = argparse.ArgumentParser(
        description="Claude-powered E2E testing via MCP Electron server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run smoke tests on current project
  python runners/e2e_test_runner.py --project . --scenario smoke

  # Run all tests with verbose output
  python runners/e2e_test_runner.py --project /path/to/project --scenario all --verbose

  # Run with custom port
  python runners/e2e_test_runner.py --project . --port 9223
        """,
    )

    parser.add_argument(
        "--project",
        type=Path,
        required=True,
        help="Project directory containing the Electron app",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="smoke",
        help="Scenario to run: smoke, regression, all (default: smoke)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("ELECTRON_DEBUG_PORT", "9222")),
        help="CDP debug port (default: 9222)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Report output directory (default: <project>/e2e/reports)",
    )

    args = parser.parse_args()

    # Resolve project directory
    project_dir = args.project.resolve()
    if not project_dir.exists():
        print_status(Icons.ERROR, f"Project directory not found: {project_dir}")
        sys.exit(1)

    # Check environment
    if os.environ.get("ELECTRON_MCP_ENABLED", "").lower() != "true":
        print_status(
            Icons.WARNING,
            "ELECTRON_MCP_ENABLED is not set. Setting to 'true' for this session.",
        )
        os.environ["ELECTRON_MCP_ENABLED"] = "true"

    os.environ["ELECTRON_DEBUG_PORT"] = str(args.port)

    # Check CDP connection
    print_status(Icons.CLOCK, f"Checking CDP connection on port {args.port}...")
    cdp_result = check_cdp_connection(args.port)

    if not cdp_result["connected"]:
        print_status(Icons.ERROR, "Electron app not detected on CDP port")
        print(muted("Start the Electron app with: npm run dev:mcp"))
        print(muted(f"Or: electron . --remote-debugging-port={args.port}"))
        sys.exit(1)

    print_status(
        Icons.CHECK,
        f"Connected to: {cdp_result['info'].get('Browser', 'Electron')}",
    )

    # Get scenarios directory
    scenarios_dir = get_scenarios_dir(project_dir)
    if not scenarios_dir.exists():
        print_status(Icons.WARNING, f"Scenarios directory not found: {scenarios_dir}")
        print(muted("Creating default smoke scenario..."))
        scenarios_dir.mkdir(parents=True, exist_ok=True)

        # Create default smoke scenario
        default_smoke = {
            "name": "Smoke Tests",
            "description": "Basic app functionality verification",
            "scenarios": [
                {
                    "name": "App Launch",
                    "steps": [
                        {"action": "verify_app_running"},
                        {"action": "take_screenshot", "name": "initial-load"},
                        {"action": "check_logs", "expect_no_errors": True},
                    ],
                },
            ],
        }
        with open(scenarios_dir / "smoke.yaml", "w", encoding="utf-8") as f:
            yaml.dump(default_smoke, f, default_flow_style=False)

    # Load scenarios
    results = []

    if args.scenario == "all":
        scenario_files = list(scenarios_dir.glob("*.yaml")) + list(
            scenarios_dir.glob("*.yml")
        )
    else:
        scenario_file = scenarios_dir / f"{args.scenario}.yaml"
        if not scenario_file.exists():
            scenario_file = scenarios_dir / f"{args.scenario}.yml"
        scenario_files = [scenario_file] if scenario_file.exists() else []

    if not scenario_files:
        print_status(Icons.ERROR, f"No scenario files found for: {args.scenario}")
        sys.exit(1)

    print_status(Icons.INFO, f"Found {len(scenario_files)} scenario file(s)")

    # Run each scenario
    for scenario_file in scenario_files:
        print_section(f"Running: {scenario_file.name}")

        scenario = load_scenario(scenario_file)
        if "error" in scenario:
            print_status(Icons.ERROR, scenario["error"])
            results.append(
                {
                    "scenario": scenario_file.name,
                    "status": "error",
                    "error": scenario["error"],
                }
            )
            continue

        result = run_agent_tests(
            project_dir=project_dir,
            scenario=scenario,
            port=args.port,
            verbose=args.verbose,
        )
        results.append(result)

        if result.get("status") == "completed":
            print_status(Icons.CHECK, f"Scenario completed: {result.get('summary', 'N/A')}")
        else:
            print_status(Icons.ERROR, f"Scenario failed: {result.get('error', 'Unknown error')}")

    # Generate report
    report_dir = args.report_dir or (project_dir / "e2e" / "reports")
    report_file = generate_report(results, report_dir)

    # Summary
    print_section("Summary")
    completed = len([r for r in results if r.get("status") == "completed"])
    errors = len([r for r in results if r.get("status") == "error"])

    print(f"  Total scenarios: {len(results)}")
    print(f"  Completed: {completed}")
    print(f"  Errors: {errors}")
    print(f"  Report: {report_file}")

    # Exit code
    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()
