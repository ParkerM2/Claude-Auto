"""
Spec Commands
=============

CLI commands for managing specs (listing, finding, etc.)
"""

import sys
from pathlib import Path

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from progress import count_subtasks
from workspace import get_existing_build_worktree

from .utils import get_specs_dir


def import_jira_issue(
    issue_key: str, project_dir: Path, spec_name: str | None = None
) -> None:
    """
    Import a Jira issue as an Auto Claude spec.

    Args:
        issue_key: Jira issue key (e.g., "ES-1234")
        project_dir: Project root directory
        spec_name: Optional spec name (e.g., "001-feature"). If None, generates from issue key
    """
    import asyncio
    import os

    from runners.jira.jira_client import JiraClient, JiraConfig

    # Get Jira configuration from environment
    base_url = os.environ.get("JIRA_BASE_URL")
    email = os.environ.get("JIRA_EMAIL")
    api_token = os.environ.get("JIRA_API_TOKEN")
    project_key = os.environ.get("JIRA_PROJECT_KEY")

    # Validate required configuration
    if not base_url:
        print("\nError: JIRA_BASE_URL is not set")
        print("Set it in apps/backend/.env:")
        print("  JIRA_BASE_URL=https://your-company.atlassian.net")
        sys.exit(1)

    if not email:
        print("\nError: JIRA_EMAIL is not set")
        print("Set it in apps/backend/.env:")
        print("  JIRA_EMAIL=your.email@company.com")
        sys.exit(1)

    if not api_token:
        print("\nError: JIRA_API_TOKEN is not set")
        print("Set it in apps/backend/.env:")
        print("  JIRA_API_TOKEN=your-api-token")
        print(
            "\nGenerate a token at: https://id.atlassian.com/manage-profile/security/api-tokens"
        )
        sys.exit(1)

    # Create Jira client
    config = JiraConfig(
        base_url=base_url,
        email=email,
        api_token=api_token,
        project_key=project_key,
    )
    client = JiraClient(config)

    # Get specs directory
    specs_dir = get_specs_dir(project_dir)

    # Import the issue
    print(f"\nImporting Jira issue {issue_key}...")
    try:
        spec_dir = asyncio.run(client.import_issue(issue_key, specs_dir, spec_name))
        print(f"✓ Successfully imported {issue_key}")
        print(f"  Spec created at: {spec_dir}")
        print("\nTo build this spec:")
        print(f"  python auto-claude/run.py --spec {spec_dir.name}")
    except Exception as e:
        print(f"\n✗ Failed to import {issue_key}")
        print(f"  Error: {e}")
        sys.exit(1)


def list_specs(project_dir: Path) -> list[dict]:
    """
    List all specs in the project.

    Args:
        project_dir: Project root directory

    Returns:
        List of spec info dicts with keys: number, name, path, status, progress
    """
    specs_dir = get_specs_dir(project_dir)
    specs = []

    if not specs_dir.exists():
        return specs

    for spec_folder in sorted(specs_dir.iterdir()):
        if not spec_folder.is_dir():
            continue

        # Parse folder name (e.g., "001-initial-app")
        folder_name = spec_folder.name
        parts = folder_name.split("-", 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue

        number = parts[0]
        name = parts[1]

        # Check for spec.md
        spec_file = spec_folder / "spec.md"
        if not spec_file.exists():
            continue

        # Check for existing build in worktree
        has_build = get_existing_build_worktree(project_dir, folder_name) is not None

        # Check progress via implementation_plan.json
        plan_file = spec_folder / "implementation_plan.json"
        if plan_file.exists():
            completed, total = count_subtasks(spec_folder)
            if total > 0:
                if completed == total:
                    status = "complete"
                else:
                    status = "in_progress"
                progress = f"{completed}/{total}"
            else:
                status = "initialized"
                progress = "0/0"
        else:
            status = "pending"
            progress = "-"

        # Add build indicator
        if has_build:
            status = f"{status} (has build)"

        specs.append(
            {
                "number": number,
                "name": name,
                "folder": folder_name,
                "path": spec_folder,
                "status": status,
                "progress": progress,
                "has_build": has_build,
            }
        )

    return specs


def print_specs_list(project_dir: Path, auto_create: bool = True) -> None:
    """Print a formatted list of all specs.

    Args:
        project_dir: Project root directory
        auto_create: If True and no specs exist, automatically launch spec creation
    """
    import subprocess

    specs = list_specs(project_dir)

    if not specs:
        print("\nNo specs found.")

        if auto_create:
            # Get the backend directory and find spec_runner.py
            backend_dir = Path(__file__).parent.parent
            spec_runner = backend_dir / "runners" / "spec_runner.py"

            # Find Python executable - use current interpreter
            python_path = sys.executable

            if spec_runner.exists() and python_path:
                # Quick prompt for task description
                print("\n" + "=" * 60)
                print("  QUICK START")
                print("=" * 60)
                print("\nWhat do you want to build?")
                print(
                    "(Enter a brief description, or press Enter for interactive mode)\n"
                )

                try:
                    task = input("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nCancelled.")
                    return

                if task:
                    # Direct mode: create spec and start building
                    print(f"\nStarting build for: {task}\n")
                    subprocess.run(
                        [
                            python_path,
                            str(spec_runner),
                            "--task",
                            task,
                            "--complexity",
                            "simple",
                            "--auto-approve",
                        ],
                        cwd=project_dir,
                    )
                else:
                    # Interactive mode
                    print("\nLaunching interactive mode...\n")
                    subprocess.run(
                        [python_path, str(spec_runner), "--interactive"],
                        cwd=project_dir,
                    )
                return
            else:
                print("\nCreate your first spec:")
                print("  python runners/spec_runner.py --interactive")
        else:
            print("\nCreate your first spec:")
            print("  python runners/spec_runner.py --interactive")
        return

    print("\n" + "=" * 70)
    print("  AVAILABLE SPECS")
    print("=" * 70)
    print()

    # Status symbols
    status_symbols = {
        "complete": "[OK]",
        "in_progress": "[..]",
        "initialized": "[--]",
        "pending": "[  ]",
    }

    for spec in specs:
        # Get base status for symbol
        base_status = spec["status"].split(" ")[0]
        symbol = status_symbols.get(base_status, "[??]")

        print(f"  {symbol} {spec['folder']}")
        status_line = f"       Status: {spec['status']} | Subtasks: {spec['progress']}"
        print(status_line)
        print()

    print("-" * 70)
    print("\nTo run a spec:")
    print("  python auto-claude/run.py --spec 001")
    print("  python auto-claude/run.py --spec 001-feature-name")
    print()
