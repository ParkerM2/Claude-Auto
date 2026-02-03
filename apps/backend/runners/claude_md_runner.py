#!/usr/bin/env python3
"""
CLAUDE.md Generation Runner - CLI Entry Point

Analyzes a project and generates a CLAUDE.md file using AI.

Usage:
    python claude_md_runner.py --project /path/to/project
    python claude_md_runner.py --project /path/to/project --model sonnet
"""

import sys

# Python version check - must be before any imports using 3.10+ syntax
if sys.version_info < (3, 10):  # noqa: UP036
    sys.exit(
        f"Error: CLAUDE.md generator requires Python 3.10 or higher.\n"
        f"You are running Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n"
        f"\n"
        f"Please upgrade Python: https://www.python.org/downloads/"
    )

import asyncio
import io
import json
from pathlib import Path

# Configure safe encoding on Windows BEFORE any imports that might print
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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file
from cli.utils import import_dotenv

load_dotenv = import_dotenv()
env_file = Path(__file__).parent.parent / ".env"
dev_env_file = Path(__file__).parent.parent.parent / "dev" / "auto-claude" / ".env"
if env_file.exists():
    load_dotenv(env_file)
elif dev_env_file.exists():
    load_dotenv(dev_env_file)

# Initialize Sentry early
from core.sentry import capture_exception, init_sentry

init_sentry(component="claude-md-runner")

from debug import debug, debug_error, debug_section, debug_success
from phase_config import resolve_model_id
from ui import Icons, box, muted, print_section, print_status


def emit_progress(phase: str, message: str, percent: int) -> None:
    """
    Emit progress as JSON for the frontend to parse.

    Progress is emitted on stdout with a special prefix for parsing.
    """
    progress = {
        "type": "progress",
        "phase": phase,
        "message": message,
        "percent": percent,
    }
    # Use special prefix so frontend can distinguish progress from other output
    print(f"CLAUDE_MD_PROGRESS:{json.dumps(progress)}", flush=True)


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate CLAUDE.md file for a project using AI analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate CLAUDE.md for current directory
    python claude_md_runner.py

    # Generate for specific project
    python claude_md_runner.py --project /path/to/project

    # Use a specific model
    python claude_md_runner.py --project /path/to/project --model opus
        """,
    )
    parser.add_argument(
        "--project",
        "--project-dir",
        dest="project_dir",
        type=Path,
        default=Path.cwd(),
        help="Project directory to analyze (default: current directory)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="sonnet",
        help="Model to use for generation (haiku, sonnet, opus, or full model ID)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON (for programmatic use)",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Emit progress updates as JSON (for frontend integration)",
    )

    args = parser.parse_args()

    # Validate project directory
    project_dir = Path(args.project_dir).resolve()
    if not project_dir.exists():
        if args.json:
            print(
                json.dumps(
                    {"success": False, "error": f"Directory not found: {project_dir}"}
                )
            )
        else:
            print_status(f"Directory not found: {project_dir}", "error")
        return 1

    if not project_dir.is_dir():
        if args.json:
            print(
                json.dumps(
                    {"success": False, "error": f"Not a directory: {project_dir}"}
                )
            )
        else:
            print_status(f"Not a directory: {project_dir}", "error")
        return 1

    # Check if CLAUDE.md already exists
    claude_md_path = project_dir / "CLAUDE.md"
    if claude_md_path.exists():
        if args.json:
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": "CLAUDE.md already exists",
                        "existing_path": str(claude_md_path),
                    }
                )
            )
        else:
            print_status(f"CLAUDE.md already exists at {claude_md_path}", "warning")
            print(f"  {muted('Delete it first if you want to regenerate.')}")
        return 1

    # Resolve model
    resolved_model = resolve_model_id(args.model)

    # Print header (unless JSON mode)
    if not args.json:
        print(
            box(
                f"Project: {project_dir}\nModel: {resolved_model}",
                title="CLAUDE.MD GENERATOR",
                style="heavy",
            )
        )

    debug_section("claude_md_runner", "CLAUDE.md Runner")
    debug(
        "claude_md_runner",
        "Configuration",
        project_dir=str(project_dir),
        model=resolved_model,
    )

    # Create progress callback if requested
    progress_callback = emit_progress if args.progress else None

    # Run the orchestrator
    try:
        from runners.claude_md import ClaudeMdOrchestrator

        orchestrator = ClaudeMdOrchestrator(
            project_dir=project_dir,
            model=resolved_model,
        )

        result = asyncio.run(orchestrator.run(progress_callback=progress_callback))

        if result["success"]:
            debug_success(
                "claude_md_runner",
                "CLAUDE.md generated successfully",
                output_path=result["output_path"],
            )

            if args.json:
                print(
                    json.dumps(
                        {
                            "success": True,
                            "output_path": result["output_path"],
                        }
                    )
                )
            else:
                print()
                print_section("COMPLETE", Icons.CHECK)
                print_status(
                    f"CLAUDE.md created at: {result['output_path']}", "success"
                )
            return 0
        else:
            debug_error("claude_md_runner", f"Generation failed: {result['error']}")

            if args.json:
                print(
                    json.dumps(
                        {
                            "success": False,
                            "error": result["error"],
                        }
                    )
                )
            else:
                print_status(f"Generation failed: {result['error']}", "error")
            return 1

    except KeyboardInterrupt:
        debug_error("claude_md_runner", "Generation interrupted by user")
        if args.json:
            print(json.dumps({"success": False, "error": "Interrupted by user"}))
        else:
            print("\n\nGeneration interrupted.")
        return 1
    except Exception as e:
        capture_exception(e)
        debug_error("claude_md_runner", f"Unexpected error: {e}")
        if args.json:
            print(json.dumps({"success": False, "error": str(e)}))
        else:
            print_status(f"Unexpected error: {e}", "error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
