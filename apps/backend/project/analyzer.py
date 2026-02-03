"""
Main Project Analyzer
=====================

Orchestrates project analysis to build dynamic security profiles.
Coordinates stack detection, framework detection, and structure analysis.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .command_registry import (
    BASE_COMMANDS,
    CLOUD_COMMANDS,
    CODE_QUALITY_COMMANDS,
    DATABASE_COMMANDS,
    FRAMEWORK_COMMANDS,
    INFRASTRUCTURE_COMMANDS,
    LANGUAGE_COMMANDS,
    PACKAGE_MANAGER_COMMANDS,
    VERSION_MANAGER_COMMANDS,
)
from .config_parser import ConfigParser
from .framework_detector import FrameworkDetector
from .models import SecurityProfile
from .stack_detector import StackDetector
from .structure_analyzer import StructureAnalyzer

if TYPE_CHECKING:
    from analysis.incremental_indexer import IncrementalIndexer


class ProjectAnalyzer:
    """
    Analyzes a project's structure to determine safe commands.

    Detection methods:
    1. File extensions and patterns
    2. Config file presence (package.json, pyproject.toml, etc.)
    3. Dependency parsing (frameworks, libraries)
    4. Script detection (npm scripts, Makefile targets)
    5. Infrastructure files (Dockerfile, k8s manifests)
    """

    PROFILE_FILENAME = ".auto-claude-security.json"

    def __init__(self, project_dir: Path, spec_dir: Path | None = None):
        """
        Initialize analyzer.

        Args:
            project_dir: Root directory of the project
            spec_dir: Optional spec directory for storing profile
        """
        self.project_dir = Path(project_dir).resolve()
        self.spec_dir = Path(spec_dir).resolve() if spec_dir else None
        self.profile = SecurityProfile()
        self.parser = ConfigParser(project_dir)
        self._indexer = None  # Lazy initialization to avoid circular imports

    @property
    def indexer(self) -> "IncrementalIndexer":
        """Lazy-load the incremental indexer to avoid circular imports."""
        if self._indexer is None:
            from analysis.incremental_indexer import IncrementalIndexer

            self._indexer = IncrementalIndexer(self.project_dir)
        return self._indexer

    def get_profile_path(self) -> Path:
        """Get the path where profile should be stored."""
        if self.spec_dir:
            return self.spec_dir / self.PROFILE_FILENAME
        return self.project_dir / self.PROFILE_FILENAME

    def load_profile(self) -> SecurityProfile | None:
        """Load existing profile if it exists."""
        profile_path = self.get_profile_path()
        if not profile_path.exists():
            return None

        try:
            with open(profile_path, encoding="utf-8") as f:
                data = json.load(f)
            return SecurityProfile.from_dict(data)
        except (OSError, json.JSONDecodeError, KeyError):
            return None

    def save_profile(self, profile: SecurityProfile) -> None:
        """Save profile to disk."""
        profile_path = self.get_profile_path()
        profile_path.parent.mkdir(parents=True, exist_ok=True)

        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2)

    def compute_project_hash(self) -> str:
        """
        Compute a hash of key project files to detect changes.

        This allows us to know when to re-analyze.
        """
        hash_files = [
            # JavaScript/TypeScript
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            # Python
            "pyproject.toml",
            "requirements.txt",
            "Pipfile",
            "poetry.lock",
            # Rust
            "Cargo.toml",
            "Cargo.lock",
            # Go
            "go.mod",
            "go.sum",
            # Ruby
            "Gemfile",
            "Gemfile.lock",
            # PHP
            "composer.json",
            "composer.lock",
            # Dart/Flutter
            "pubspec.yaml",
            "pubspec.lock",
            # Java/Kotlin/Scala
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "settings.gradle",
            "settings.gradle.kts",
            "build.sbt",
            # Swift
            "Package.swift",
            # Infrastructure
            "Makefile",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
        ]

        # Glob patterns for project files that can be anywhere in the tree
        glob_patterns = [
            "*.csproj",  # C# projects
            "*.sln",  # Visual Studio solutions
            "*.fsproj",  # F# projects
            "*.vbproj",  # VB.NET projects
        ]

        hasher = hashlib.md5(usedforsecurity=False)
        files_found = 0

        for filename in hash_files:
            filepath = self.project_dir / filename
            if filepath.exists():
                try:
                    stat = filepath.stat()
                    hasher.update(f"{filename}:{stat.st_mtime}:{stat.st_size}".encode())
                    files_found += 1
                except OSError:
                    continue

        # Check glob patterns for project files that can be anywhere
        for pattern in glob_patterns:
            for filepath in self.project_dir.glob(f"**/{pattern}"):
                try:
                    stat = filepath.stat()
                    rel_path = filepath.relative_to(self.project_dir)
                    hasher.update(f"{rel_path}:{stat.st_mtime}:{stat.st_size}".encode())
                    files_found += 1
                except OSError:
                    continue

        # If no config files found, hash the project directory structure
        # to at least detect when files are added/removed
        if files_found == 0:
            # Count source files as a proxy for project structure
            source_exts = [
                "*.py",
                "*.js",
                "*.ts",
                "*.go",
                "*.rs",
                "*.dart",
                "*.cs",
                "*.swift",
                "*.kt",
                "*.java",
            ]
            for ext in source_exts:
                count = len(list(self.project_dir.glob(f"**/{ext}")))
                hasher.update(f"{ext}:{count}".encode())
            # Also include the project directory name for uniqueness
            hasher.update(self.project_dir.name.encode())

        return hasher.hexdigest()

    def should_reanalyze(self, profile: SecurityProfile) -> bool:
        """Check if project has changed since last analysis.

        Never re-analyzes inherited profiles (from worktrees) since they
        came from a validated parent project with full context (e.g., node_modules).
        """
        # Never re-analyze inherited profiles - they came from a validated parent
        # But validate that inherited_from points to a legitimate parent
        if profile.inherited_from:
            parent = Path(profile.inherited_from)
            # Validate the inherited_from path:
            # 1. Must exist and be a directory
            # 2. Current project must be a descendant of the parent
            # 3. Parent must contain a valid security profile
            if (
                parent.exists()
                and parent.is_dir()
                and self._is_descendant_of(self.project_dir, parent)
                and (parent / self.PROFILE_FILENAME).exists()
            ):
                return False
            # If validation fails, treat as non-inherited and check hash
        current_hash = self.compute_project_hash()
        return current_hash != profile.project_hash

    def _is_descendant_of(self, child: Path, parent: Path) -> bool:
        """Check if child path is a descendant of parent path."""
        try:
            child.resolve().relative_to(parent.resolve())
            return True
        except ValueError:
            return False

    def has_file_changes(self) -> bool:
        """
        Check if any tracked files have changed using incremental indexing.

        Returns:
            True if files have been added, modified, or deleted
        """
        try:
            changes = self.indexer.detect_changes()
            return changes.has_changes()
        except Exception as e:
            # If incremental indexing fails, fall back to assuming changes
            print(f"Warning: Incremental indexing failed: {e}")
            return True

    def get_file_changes(self) -> dict:
        """
        Get detailed file changes using incremental indexing.

        Returns:
            Dictionary with added, modified, deleted, and unchanged file lists
        """
        try:
            changes = self.indexer.detect_changes()
            return changes.to_dict()
        except Exception as e:
            print(f"Warning: Failed to detect file changes: {e}")
            return {
                "added": [],
                "modified": [],
                "deleted": [],
                "unchanged": [],
                "total_changed": 0,
            }

    def update_file_index(self) -> int:
        """
        Update the file index with current filesystem state.

        Returns:
            Number of files updated in the index
        """
        try:
            return self.indexer.update_index()
        except Exception as e:
            print(f"Warning: Failed to update file index: {e}")
            return 0

    def analyze(self, force: bool = False) -> SecurityProfile:
        """
        Perform full project analysis.

        Uses incremental indexing to detect file changes and avoid
        unnecessary re-analysis on large codebases.

        Args:
            force: Force re-analysis even if profile exists

        Returns:
            SecurityProfile with all detected commands
        """
        # Check for existing profile
        existing = self.load_profile()
        if existing and not force:
            # Use incremental indexing to check for file changes
            has_changes = self.has_file_changes()
            should_reanalyze = self.should_reanalyze(existing)

            # Skip re-analysis if no changes detected
            if not has_changes and not should_reanalyze:
                if existing.inherited_from:
                    print("Using inherited security profile from parent project")
                else:
                    print(
                        f"Using cached security profile (hash: {existing.project_hash[:8]})"
                    )
                    changes = self.get_file_changes()
                    print(
                        f"  No file changes detected (tracked: {len(changes['unchanged'])} files)"
                    )
                return existing

            # If changes detected, show what changed
            if has_changes:
                changes = self.get_file_changes()
                print(
                    f"File changes detected: +{len(changes['added'])} "
                    f"~{len(changes['modified'])} -{len(changes['deleted'])}"
                )

        print("Analyzing project structure for security profile...")

        # Start fresh
        self.profile = SecurityProfile()
        self.profile.base_commands = BASE_COMMANDS.copy()
        self.profile.project_dir = str(self.project_dir)

        # Run detection
        self._detect_stack()
        self._detect_frameworks()
        self._detect_structure()

        # Build stack commands from detected technologies
        self._build_stack_commands()

        # Finalize
        self.profile.created_at = datetime.now().isoformat()
        self.profile.project_hash = self.compute_project_hash()

        # Save
        self.save_profile(self.profile)

        # Update file index with current state
        updated_count = self.update_file_index()
        if updated_count > 0:
            print(f"Updated file index ({updated_count} files)")

        # Print summary
        self._print_summary()

        return self.profile

    def _detect_stack(self) -> None:
        """Detect technology stack."""
        detector = StackDetector(self.project_dir)
        self.profile.detected_stack = detector.detect_all()

    def _detect_frameworks(self) -> None:
        """Detect frameworks from dependencies."""
        detector = FrameworkDetector(self.project_dir)
        self.profile.detected_stack.frameworks = detector.detect_all()

    def _detect_structure(self) -> None:
        """Detect project structure and custom scripts."""
        analyzer = StructureAnalyzer(self.project_dir)
        scripts, script_commands, custom_commands = analyzer.analyze()
        self.profile.custom_scripts = scripts
        self.profile.script_commands = script_commands
        self.profile.custom_commands = custom_commands

    # Public methods for backward compatibility with tests
    def _detect_languages(self) -> None:
        """Detect programming languages (backward compatibility)."""
        detector = StackDetector(self.project_dir)
        detector.detect_languages()
        self.profile.detected_stack.languages = detector.stack.languages

    def _detect_package_managers(self) -> None:
        """Detect package managers (backward compatibility)."""
        detector = StackDetector(self.project_dir)
        detector.detect_package_managers()
        self.profile.detected_stack.package_managers = detector.stack.package_managers

    def _detect_databases(self) -> None:
        """Detect databases (backward compatibility)."""
        detector = StackDetector(self.project_dir)
        detector.detect_databases()
        self.profile.detected_stack.databases = detector.stack.databases

    def _detect_infrastructure(self) -> None:
        """Detect infrastructure (backward compatibility)."""
        detector = StackDetector(self.project_dir)
        detector.detect_infrastructure()
        self.profile.detected_stack.infrastructure = detector.stack.infrastructure

    def _detect_cloud_providers(self) -> None:
        """Detect cloud providers (backward compatibility)."""
        detector = StackDetector(self.project_dir)
        detector.detect_cloud_providers()
        self.profile.detected_stack.cloud_providers = detector.stack.cloud_providers

    def _detect_code_quality_tools(self) -> None:
        """Detect code quality tools (backward compatibility)."""
        detector = StackDetector(self.project_dir)
        detector.detect_code_quality_tools()
        self.profile.detected_stack.code_quality_tools = (
            detector.stack.code_quality_tools
        )

    def _detect_version_managers(self) -> None:
        """Detect version managers (backward compatibility)."""
        detector = StackDetector(self.project_dir)
        detector.detect_version_managers()
        self.profile.detected_stack.version_managers = detector.stack.version_managers

    def _detect_custom_scripts(self) -> None:
        """Detect custom scripts (backward compatibility)."""
        analyzer = StructureAnalyzer(self.project_dir)
        scripts, script_commands, _ = analyzer.analyze()
        self.profile.custom_scripts = scripts
        self.profile.script_commands = script_commands

    def _load_custom_allowlist(self) -> None:
        """Load custom allowlist (backward compatibility)."""
        analyzer = StructureAnalyzer(self.project_dir)
        _, _, custom_commands = analyzer.analyze()
        self.profile.custom_commands = custom_commands

    def _build_stack_commands(self) -> None:
        """Build the set of allowed commands from detected stack."""
        stack = self.profile.detected_stack
        commands = self.profile.stack_commands

        # Add language commands
        for lang in stack.languages:
            if lang in LANGUAGE_COMMANDS:
                commands.update(LANGUAGE_COMMANDS[lang])

        # Add package manager commands
        for pm in stack.package_managers:
            if pm in PACKAGE_MANAGER_COMMANDS:
                commands.update(PACKAGE_MANAGER_COMMANDS[pm])

        # Add framework commands
        for fw in stack.frameworks:
            if fw in FRAMEWORK_COMMANDS:
                commands.update(FRAMEWORK_COMMANDS[fw])

        # Add database commands
        for db in stack.databases:
            if db in DATABASE_COMMANDS:
                commands.update(DATABASE_COMMANDS[db])

        # Add infrastructure commands
        for infra in stack.infrastructure:
            if infra in INFRASTRUCTURE_COMMANDS:
                commands.update(INFRASTRUCTURE_COMMANDS[infra])

        # Add cloud commands
        for cloud in stack.cloud_providers:
            if cloud in CLOUD_COMMANDS:
                commands.update(CLOUD_COMMANDS[cloud])

        # Add code quality commands
        for tool in stack.code_quality_tools:
            if tool in CODE_QUALITY_COMMANDS:
                commands.update(CODE_QUALITY_COMMANDS[tool])

        # Add version manager commands
        for vm in stack.version_managers:
            if vm in VERSION_MANAGER_COMMANDS:
                commands.update(VERSION_MANAGER_COMMANDS[vm])

    def _print_summary(self) -> None:
        """Print a summary of what was detected."""
        stack = self.profile.detected_stack
        scripts = self.profile.custom_scripts

        print("\n" + "=" * 60)
        print("  SECURITY PROFILE ANALYSIS")
        print("=" * 60)

        if stack.languages:
            print(f"\nLanguages: {', '.join(stack.languages)}")

        if stack.package_managers:
            print(f"Package Managers: {', '.join(stack.package_managers)}")

        if stack.frameworks:
            print(f"Frameworks: {', '.join(stack.frameworks)}")

        if stack.databases:
            print(f"Databases: {', '.join(stack.databases)}")

        if stack.infrastructure:
            print(f"Infrastructure: {', '.join(stack.infrastructure)}")

        if stack.cloud_providers:
            print(f"Cloud Providers: {', '.join(stack.cloud_providers)}")

        if scripts.npm_scripts:
            print(f"NPM Scripts: {len(scripts.npm_scripts)} detected")

        if scripts.make_targets:
            print(f"Make Targets: {len(scripts.make_targets)} detected")

        total_commands = len(self.profile.get_all_allowed_commands())
        print(f"\nTotal Allowed Commands: {total_commands}")

        print("-" * 60)
