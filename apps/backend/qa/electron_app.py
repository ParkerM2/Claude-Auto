"""
Electron App Lifecycle Management for QA
=========================================

Manages starting and stopping the Electron app in test mode for QA validation.
This enables the QA agent to interact with the running app via Electron MCP tools.

Usage:
    async with ElectronAppManager(project_dir) as app:
        # App is running with CDP on port 9222
        # Run QA validation here
    # App is automatically stopped
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from debug import debug, debug_error, debug_section, debug_success, debug_warning

# Default CDP port for Electron debugging
DEFAULT_CDP_PORT = 9222

# Timeout for app startup (seconds)
APP_STARTUP_TIMEOUT = 30

# Timeout for app shutdown (seconds)
APP_SHUTDOWN_TIMEOUT = 10


class ElectronAppManager:
    """
    Context manager for running Electron app during QA validation.

    Handles:
    - Starting the app with --remote-debugging-port
    - Waiting for CDP to be available
    - Stopping the app on exit
    - Using isolated test user data directory
    """

    def __init__(
        self,
        project_dir: Path,
        port: int = DEFAULT_CDP_PORT,
        use_test_env: bool = True,
    ):
        """
        Initialize the Electron app manager.

        Args:
            project_dir: Path to the project directory (or frontend directory)
            port: CDP debug port (default: 9222)
            use_test_env: Use isolated test user data directory
        """
        self.project_dir = Path(project_dir).resolve()
        self.port = port
        self.use_test_env = use_test_env
        self.process: subprocess.Popen | None = None
        self._was_already_running = False

    async def __aenter__(self) -> "ElectronAppManager":
        """Start the Electron app if not already running."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop the Electron app if we started it."""
        await self.stop()

    def _find_frontend_dir(self) -> Path | None:
        """Find the frontend directory containing the Electron app."""
        # Check if project_dir is already the frontend
        if (self.project_dir / "package.json").exists():
            pkg_json = self.project_dir / "package.json"
            try:
                with open(pkg_json, encoding="utf-8") as f:
                    pkg = json.load(f)
                    # Check if it's an Electron app
                    deps = {
                        **pkg.get("dependencies", {}),
                        **pkg.get("devDependencies", {}),
                    }
                    if "electron" in deps:
                        return self.project_dir
            except (json.JSONDecodeError, OSError):
                pass

        # Check for apps/frontend structure (monorepo)
        frontend_dir = self.project_dir / "apps" / "frontend"
        if (frontend_dir / "package.json").exists():
            return frontend_dir

        # Check for frontend directory
        frontend_dir = self.project_dir / "frontend"
        if (frontend_dir / "package.json").exists():
            return frontend_dir

        return None

    def _check_cdp_connection(self, timeout: float = 2.0) -> bool:
        """Check if CDP is available on the debug port."""
        url = f"http://127.0.0.1:{self.port}/json/version"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                data = json.loads(response.read().decode())
                debug(
                    "electron_app", f"CDP connected: {data.get('Browser', 'Unknown')}"
                )
                return True
        except Exception:
            return False

    async def _wait_for_cdp(self, timeout: float = APP_STARTUP_TIMEOUT) -> bool:
        """Wait for CDP to become available."""
        start_time = time.time()
        check_interval = 0.5

        while time.time() - start_time < timeout:
            if self._check_cdp_connection(timeout=1.0):
                return True
            await asyncio.sleep(check_interval)

        return False

    async def start(self) -> bool:
        """
        Start the Electron app with CDP debugging.

        Returns:
            True if app is running (either started or was already running)
        """
        debug_section("electron_app", "Starting Electron App for QA")

        # Check if already running
        if self._check_cdp_connection():
            debug_success(
                "electron_app", f"Electron app already running on port {self.port}"
            )
            self._was_already_running = True
            return True

        # Find the frontend directory
        frontend_dir = self._find_frontend_dir()
        if not frontend_dir:
            debug_warning("electron_app", "Could not find Electron frontend directory")
            return False

        debug("electron_app", f"Found frontend directory: {frontend_dir}")

        # Check if built
        out_dir = frontend_dir / "out"
        if not out_dir.exists():
            debug("electron_app", "Building Electron app...")
            print("Building Electron app for QA testing...")

            build_cmd = ["npm", "run", "build"]
            if sys.platform == "win32":
                build_cmd = ["cmd", "/c", "npm", "run", "build"]

            try:
                result = subprocess.run(
                    build_cmd,
                    cwd=str(frontend_dir),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode != 0:
                    debug_error("electron_app", f"Build failed: {result.stderr[:500]}")
                    return False
                debug_success("electron_app", "Build completed")
            except subprocess.TimeoutExpired:
                debug_error("electron_app", "Build timed out")
                return False
            except Exception as e:
                debug_error("electron_app", f"Build error: {e}")
                return False

        # Prepare environment
        env = os.environ.copy()
        env["NODE_ENV"] = "test"
        env["ELECTRON_MCP_ENABLED"] = "true"
        env["ELECTRON_DEBUG_PORT"] = str(self.port)

        if self.use_test_env:
            # Use isolated test data directory
            test_data_dir = frontend_dir / ".auto-claude-test"
            env["ELECTRON_USER_DATA_PATH"] = str(test_data_dir)

        # Start the app
        is_windows = sys.platform == "win32"

        # Construct command based on platform
        if is_windows:
            electron_path = frontend_dir / "node_modules" / ".bin" / "electron.cmd"
            cmd = [str(electron_path), ".", f"--remote-debugging-port={self.port}"]
            shell = False
        else:
            cmd = ["npx", "electron", ".", f"--remote-debugging-port={self.port}"]
            shell = False

        debug("electron_app", f"Starting: {' '.join(cmd)}")
        print(f"Starting Electron app with CDP on port {self.port}...")

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=str(frontend_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=shell,
            )
        except Exception as e:
            debug_error("electron_app", f"Failed to start app: {e}")
            return False

        # Wait for CDP to be available
        debug("electron_app", "Waiting for CDP connection...")
        if await self._wait_for_cdp():
            debug_success("electron_app", f"Electron app running on port {self.port}")
            print(f"✓ Electron app running (CDP port {self.port})")
            return True
        else:
            debug_error("electron_app", "CDP connection timeout")
            # Try to get error output
            if self.process:
                try:
                    stdout, stderr = self.process.communicate(timeout=2)
                    if stderr:
                        debug_error(
                            "electron_app", f"App stderr: {stderr.decode()[:500]}"
                        )
                except subprocess.TimeoutExpired:
                    pass
            await self.stop()
            return False

    async def stop(self) -> None:
        """Stop the Electron app if we started it."""
        if self._was_already_running:
            debug("electron_app", "App was already running, not stopping")
            return

        if not self.process:
            return

        debug("electron_app", "Stopping Electron app...")

        try:
            # Try graceful termination first
            self.process.terminate()

            # Wait for process to exit
            try:
                self.process.wait(timeout=APP_SHUTDOWN_TIMEOUT)
                debug_success("electron_app", "Electron app stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if graceful termination fails
                debug_warning(
                    "electron_app", "Graceful shutdown timeout, force killing"
                )
                self.process.kill()
                self.process.wait(timeout=5)
                debug("electron_app", "Electron app force killed")

        except Exception as e:
            debug_error("electron_app", f"Error stopping app: {e}")
        finally:
            self.process = None
            print("✓ Electron app stopped")

    def is_running(self) -> bool:
        """Check if the app is running."""
        return self._check_cdp_connection()


def is_electron_project(project_dir: Path) -> bool:
    """
    Check if the project is an Electron application.

    Args:
        project_dir: Path to the project directory

    Returns:
        True if the project contains an Electron app
    """
    paths_to_check = [
        project_dir / "package.json",
        project_dir / "apps" / "frontend" / "package.json",
        project_dir / "frontend" / "package.json",
    ]

    for pkg_path in paths_to_check:
        if pkg_path.exists():
            try:
                with open(pkg_path, encoding="utf-8") as f:
                    pkg = json.load(f)
                    deps = {
                        **pkg.get("dependencies", {}),
                        **pkg.get("devDependencies", {}),
                    }
                    if "electron" in deps:
                        return True
            except (json.JSONDecodeError, OSError):
                continue

    return False


def should_use_electron_mcp(project_dir: Path) -> bool:
    """
    Determine if QA should use Electron MCP for this project.

    Checks:
    1. Project is an Electron app
    2. ELECTRON_MCP_ENABLED is not explicitly disabled

    Args:
        project_dir: Path to the project directory

    Returns:
        True if Electron MCP should be used for QA
    """
    # Check if explicitly disabled
    if os.environ.get("ELECTRON_MCP_ENABLED", "").lower() == "false":
        return False

    # Check if it's an Electron project
    return is_electron_project(project_dir)
