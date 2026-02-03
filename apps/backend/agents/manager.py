"""
Manager Agent for PR Status Monitoring
======================================

A lightweight background agent that monitors GitHub PR status for tasks
with linked PRs and emits status updates to the frontend.

Communication Protocol:
- Receives task data via stdin (JSON-lines format)
- Emits status updates to stdout using __MANAGER_EVENT__:{json} protocol

Usage:
    python -m agents.manager --project /path/to/project

The manager runs in a polling loop, checking PR status at regular intervals
(default: 60 seconds). It can receive commands via stdin to:
- Add/remove tasks from monitoring
- Force immediate refresh of a specific task
- Shutdown gracefully
"""

import argparse
import json
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass
class PRStatusInfo:
    """PR status information from GitHub."""

    pr_number: int
    state: str  # 'open', 'closed', 'merged'
    review_decision: (
        str | None
    )  # 'approved', 'changes_requested', 'review_required', None
    ci_status: str  # 'passing', 'failing', 'pending', 'none'
    is_draft: bool
    mergeable: str  # 'MERGEABLE', 'CONFLICTING', 'UNKNOWN'
    last_updated: str  # ISO timestamp


@dataclass
class MonitoredTask:
    """Task being monitored for PR status changes."""

    task_id: str
    pr_url: str
    owner: str
    repo: str
    pr_number: int
    last_status: PRStatusInfo | None = None


def emit_event(event_type: str, data: dict) -> None:
    """
    Emit an event to stdout using the manager protocol.

    Format: __MANAGER_EVENT__:{"type": "...", ...}
    """
    event = {"type": event_type, **data}
    print(f"__MANAGER_EVENT__:{json.dumps(event)}", flush=True)


def parse_pr_url(pr_url: str) -> tuple[str, str, int]:
    """
    Parse a GitHub PR URL to extract owner, repo, and PR number.

    Args:
        pr_url: Full GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)

    Returns:
        Tuple of (owner, repo, pr_number)

    Raises:
        ValueError: If URL format is invalid
    """
    # Handle URLs like: https://github.com/owner/repo/pull/123
    parts = pr_url.rstrip("/").split("/")
    if len(parts) < 5 or "github.com" not in pr_url or "/pull/" not in pr_url:
        raise ValueError(f"Invalid GitHub PR URL: {pr_url}")

    # Find the index of 'pull' and extract accordingly
    try:
        pull_idx = parts.index("pull")
        pr_number = int(parts[pull_idx + 1])
        owner = parts[pull_idx - 2]
        repo = parts[pull_idx - 1]
        return owner, repo, pr_number
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid GitHub PR URL: {pr_url}") from e


def get_pr_status(owner: str, repo: str, pr_number: int) -> PRStatusInfo | None:
    """
    Fetch PR status from GitHub using the gh CLI.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number

    Returns:
        PRStatusInfo if successful, None if failed
    """
    try:
        # Use gh pr view to get PR details
        cmd = [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--repo",
            f"{owner}/{repo}",
            "--json",
            "state,isDraft,reviewDecision,mergeable,statusCheckRollup,mergedAt",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            print(f"[Manager] gh pr view failed: {result.stderr}", file=sys.stderr)
            return None

        data = json.loads(result.stdout)

        # Determine state (open, closed, merged)
        state = data.get("state", "OPEN").lower()
        if data.get("mergedAt"):
            state = "merged"
        elif state == "closed":
            state = "closed"
        else:
            state = "open"

        # Determine review decision
        review_decision_raw = data.get("reviewDecision")
        if review_decision_raw:
            review_decision_map = {
                "APPROVED": "approved",
                "CHANGES_REQUESTED": "changes_requested",
                "REVIEW_REQUIRED": "review_required",
            }
            review_decision = review_decision_map.get(review_decision_raw)
        else:
            review_decision = None

        # Determine CI status from statusCheckRollup
        checks = data.get("statusCheckRollup", [])
        ci_status = "none"
        if checks:
            all_passed = all(
                c.get("conclusion") == "SUCCESS" or c.get("state") == "SUCCESS"
                for c in checks
            )
            any_failed = any(
                c.get("conclusion") == "FAILURE" or c.get("state") == "FAILURE"
                for c in checks
            )
            any_pending = any(
                c.get("conclusion") in (None, "PENDING")
                or c.get("state") in (None, "PENDING", "IN_PROGRESS")
                for c in checks
            )

            if any_failed:
                ci_status = "failing"
            elif any_pending:
                ci_status = "pending"
            elif all_passed:
                ci_status = "passing"

        # Determine mergeable status
        mergeable_raw = data.get("mergeable", "UNKNOWN")
        mergeable = (
            mergeable_raw
            if mergeable_raw in ("MERGEABLE", "CONFLICTING", "UNKNOWN")
            else "UNKNOWN"
        )

        return PRStatusInfo(
            pr_number=pr_number,
            state=state,
            review_decision=review_decision,
            ci_status=ci_status,
            is_draft=data.get("isDraft", False),
            mergeable=mergeable,
            last_updated=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )

    except subprocess.TimeoutExpired:
        print(
            f"[Manager] gh pr view timed out for {owner}/{repo}#{pr_number}",
            file=sys.stderr,
        )
        return None
    except json.JSONDecodeError as e:
        print(f"[Manager] Failed to parse gh output: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[Manager] Error fetching PR status: {e}", file=sys.stderr)
        return None


class ManagerAgent:
    """
    Background agent that monitors PR status for tasks.

    Runs in a polling loop, checking PR status at regular intervals
    and emitting status updates when changes are detected.
    """

    def __init__(self, poll_interval: int = 60):
        """
        Initialize the manager agent.

        Args:
            poll_interval: Seconds between status checks (default: 60)
        """
        self.poll_interval = poll_interval
        self.monitored_tasks: dict[str, MonitoredTask] = {}
        self._running = False
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def add_task(self, task_id: str, pr_url: str) -> bool:
        """
        Add a task to monitoring.

        Args:
            task_id: Unique task identifier
            pr_url: GitHub PR URL

        Returns:
            True if added successfully, False if invalid URL
        """
        try:
            owner, repo, pr_number = parse_pr_url(pr_url)

            with self._lock:
                self.monitored_tasks[task_id] = MonitoredTask(
                    task_id=task_id,
                    pr_url=pr_url,
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number,
                )

            print(
                f"[Manager] Added task {task_id} monitoring PR {owner}/{repo}#{pr_number}",
                file=sys.stderr,
            )
            return True

        except ValueError as e:
            print(f"[Manager] Failed to add task: {e}", file=sys.stderr)
            return False

    def remove_task(self, task_id: str) -> bool:
        """
        Remove a task from monitoring.

        Args:
            task_id: Task identifier to remove

        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if task_id in self.monitored_tasks:
                del self.monitored_tasks[task_id]
                print(
                    f"[Manager] Removed task {task_id} from monitoring", file=sys.stderr
                )
                return True
        return False

    def refresh_task(self, task_id: str) -> PRStatusInfo | None:
        """
        Force immediate refresh of a specific task's PR status.

        Args:
            task_id: Task to refresh

        Returns:
            Updated PRStatusInfo or None if failed/not found
        """
        with self._lock:
            task = self.monitored_tasks.get(task_id)
            if not task:
                return None

        status = get_pr_status(task.owner, task.repo, task.pr_number)
        if status:
            with self._lock:
                if task_id in self.monitored_tasks:
                    self.monitored_tasks[task_id].last_status = status

            # Emit update event
            emit_event("pr_status", {"taskId": task_id, "prStatus": asdict(status)})

        return status

    def _check_all_tasks(self) -> None:
        """Check status of all monitored tasks."""
        with self._lock:
            tasks = list(self.monitored_tasks.values())

        for task in tasks:
            if self._stop_event.is_set():
                break

            new_status = get_pr_status(task.owner, task.repo, task.pr_number)
            if not new_status:
                continue

            # Check if status changed
            old_status = task.last_status
            status_changed = (
                old_status is None
                or old_status.state != new_status.state
                or old_status.review_decision != new_status.review_decision
                or old_status.ci_status != new_status.ci_status
                or old_status.is_draft != new_status.is_draft
                or old_status.mergeable != new_status.mergeable
            )

            if status_changed:
                with self._lock:
                    if task.task_id in self.monitored_tasks:
                        self.monitored_tasks[task.task_id].last_status = new_status

                # Emit update event
                emit_event(
                    "pr_status",
                    {"taskId": task.task_id, "prStatus": asdict(new_status)},
                )

                print(
                    f"[Manager] PR status changed for task {task.task_id}",
                    file=sys.stderr,
                )

    def _stdin_reader(self) -> None:
        """Read commands from stdin in a separate thread."""
        try:
            for line in sys.stdin:
                if self._stop_event.is_set():
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    cmd = json.loads(line)
                    self._handle_command(cmd)
                except json.JSONDecodeError:
                    print(f"[Manager] Invalid JSON command: {line}", file=sys.stderr)

        except Exception as e:
            print(f"[Manager] stdin reader error: {e}", file=sys.stderr)

    def _handle_command(self, cmd: dict) -> None:
        """Handle an incoming command."""
        cmd_type = cmd.get("type")

        if cmd_type == "add_task":
            task_id = cmd.get("taskId")
            pr_url = cmd.get("prUrl")
            if task_id and pr_url:
                self.add_task(task_id, pr_url)

        elif cmd_type == "remove_task":
            task_id = cmd.get("taskId")
            if task_id:
                self.remove_task(task_id)

        elif cmd_type == "refresh_task":
            task_id = cmd.get("taskId")
            if task_id:
                self.refresh_task(task_id)

        elif cmd_type == "stop":
            self._stop_event.set()

        elif cmd_type == "ping":
            emit_event(
                "pong",
                {
                    "timestamp": datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
                },
            )

        else:
            print(f"[Manager] Unknown command type: {cmd_type}", file=sys.stderr)

    def run(self) -> None:
        """Run the manager agent main loop."""
        self._running = True
        self._stop_event.clear()

        # Start stdin reader thread
        stdin_thread = threading.Thread(target=self._stdin_reader, daemon=True)
        stdin_thread.start()

        emit_event(
            "started",
            {
                "timestamp": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            },
        )
        print(
            f"[Manager] Started with poll interval {self.poll_interval}s",
            file=sys.stderr,
        )

        try:
            while not self._stop_event.is_set():
                self._check_all_tasks()

                # Wait for next poll interval or stop event
                if self._stop_event.wait(timeout=self.poll_interval):
                    break

        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            emit_event(
                "stopped",
                {
                    "timestamp": datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
                },
            )
            print("[Manager] Stopped", file=sys.stderr)

    def stop(self) -> None:
        """Signal the manager to stop."""
        self._stop_event.set()


def main():
    """Main entry point for the manager agent."""
    parser = argparse.ArgumentParser(
        description="Manager agent for PR status monitoring"
    )
    parser.add_argument("--project", required=True, help="Project path")
    parser.add_argument(
        "--poll-interval", type=int, default=60, help="Poll interval in seconds"
    )

    args = parser.parse_args()

    agent = ManagerAgent(poll_interval=args.poll_interval)
    agent.run()


if __name__ == "__main__":
    main()
