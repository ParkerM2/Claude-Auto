"""
CLAUDE.md Generation Orchestrator
==================================

Orchestrates project analysis and CLAUDE.md generation using the Claude Agent SDK.

This orchestrator:
1. Analyzes project structure (files, directories, patterns)
2. Reads dependency manifests (package.json, requirements.txt, etc.)
3. Detects tech stack, frameworks, and build tools
4. Uses Claude to generate comprehensive CLAUDE.md content
5. Writes the output to the project root
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.simple_client import create_simple_client
from debug import debug, debug_error, debug_section, debug_success


class ClaudeMdOrchestrator:
    """Orchestrates CLAUDE.md generation from project analysis."""

    # Config files to read for project context
    CONFIG_FILES = {
        # JavaScript/TypeScript
        "package.json": "npm",
        "tsconfig.json": "typescript",
        # Python
        "pyproject.toml": "python",
        "requirements.txt": "python",
        "setup.py": "python",
        "Pipfile": "python",
        # Rust
        "Cargo.toml": "rust",
        # Go
        "go.mod": "go",
        # Ruby
        "Gemfile": "ruby",
        # PHP
        "composer.json": "php",
        # Java/Kotlin
        "pom.xml": "java",
        "build.gradle": "java",
        "build.gradle.kts": "kotlin",
        # Swift
        "Package.swift": "swift",
        # .NET
        "*.csproj": "dotnet",
        "*.sln": "dotnet",
        # Infrastructure
        "Dockerfile": "docker",
        "docker-compose.yml": "docker",
        "docker-compose.yaml": "docker",
        "Makefile": "make",
    }

    # Directories to analyze for structure understanding
    STRUCTURE_DIRS = [
        "src",
        "lib",
        "app",
        "apps",
        "packages",
        "modules",
        "components",
        "services",
        "api",
        "core",
        "utils",
        "helpers",
        "tests",
        "__tests__",
        "spec",
        "docs",
        "scripts",
        ".github",
    ]

    def __init__(
        self,
        project_dir: Path,
        model: str = "claude-sonnet-4-20250514",
    ):
        """
        Initialize the orchestrator.

        Args:
            project_dir: Path to the project directory
            model: Claude model to use for generation
        """
        self.project_dir = Path(project_dir).resolve()
        self.model = model

        debug_section("claude_md_orchestrator", "CLAUDE.md Orchestrator Initialized")
        debug(
            "claude_md_orchestrator",
            "Configuration",
            project_dir=str(self.project_dir),
            model=self.model,
        )

    async def run(self, progress_callback: callable = None) -> dict[str, Any]:
        """
        Run the complete CLAUDE.md generation process.

        Args:
            progress_callback: Optional callback for progress updates
                              Called with (phase: str, message: str, percent: int)

        Returns:
            Dict with keys: success, content, output_path, error
        """
        debug_section("claude_md_orchestrator", "Starting CLAUDE.md Generation")

        try:
            # Phase 1: Analyze project structure
            if progress_callback:
                progress_callback("analysis", "Analyzing project structure...", 10)

            project_context = await self._analyze_project()

            debug(
                "claude_md_orchestrator",
                "Project analysis complete",
                files_found=len(project_context.get("config_files", {})),
                directories=len(project_context.get("structure", [])),
            )

            # Phase 2: Detect tech stack
            if progress_callback:
                progress_callback("detection", "Detecting tech stack...", 30)

            tech_stack = self._detect_tech_stack(project_context)

            debug(
                "claude_md_orchestrator",
                "Tech stack detected",
                languages=tech_stack.get("languages", []),
                frameworks=tech_stack.get("frameworks", []),
            )

            # Phase 3: Generate CLAUDE.md content using Claude
            if progress_callback:
                progress_callback("generation", "Generating CLAUDE.md content...", 50)

            content = await self._generate_claude_md(project_context, tech_stack)

            debug_success(
                "claude_md_orchestrator",
                "CLAUDE.md content generated",
                content_length=len(content),
            )

            # Phase 4: Write to file
            if progress_callback:
                progress_callback("writing", "Writing CLAUDE.md...", 90)

            output_path = self.project_dir / "CLAUDE.md"
            output_path.write_text(content, encoding="utf-8")

            if progress_callback:
                progress_callback("complete", "CLAUDE.md created successfully!", 100)

            debug_success(
                "claude_md_orchestrator",
                "CLAUDE.md written successfully",
                output_path=str(output_path),
            )

            return {
                "success": True,
                "content": content,
                "output_path": str(output_path),
                "error": None,
            }

        except Exception as e:
            debug_error("claude_md_orchestrator", f"Error generating CLAUDE.md: {e}")
            if progress_callback:
                progress_callback("error", f"Error: {str(e)}", 0)
            return {
                "success": False,
                "content": None,
                "output_path": None,
                "error": str(e),
            }

    async def _analyze_project(self) -> dict[str, Any]:
        """Analyze project structure and gather context."""
        context = {
            "project_name": self.project_dir.name,
            "config_files": {},
            "structure": [],
            "readme_content": None,
            "file_counts": {},
            "has_tests": False,
            "has_docs": False,
            "has_ci": False,
        }

        # Read README if it exists
        for readme_name in ["README.md", "readme.md", "README", "README.txt"]:
            readme_path = self.project_dir / readme_name
            if readme_path.exists():
                try:
                    content = readme_path.read_text(encoding="utf-8")
                    # Truncate to first 5000 chars to keep prompt manageable
                    context["readme_content"] = content[:5000]
                    break
                except Exception:
                    pass

        # Read config files
        for filename, lang in self.CONFIG_FILES.items():
            if "*" in filename:
                # Handle glob patterns
                for found in self.project_dir.glob(filename):
                    if found.is_file():
                        try:
                            content = found.read_text(encoding="utf-8")[:3000]
                            context["config_files"][found.name] = {
                                "language": lang,
                                "content": content,
                            }
                        except Exception:
                            pass
            else:
                filepath = self.project_dir / filename
                if filepath.exists():
                    try:
                        content = filepath.read_text(encoding="utf-8")[:3000]
                        context["config_files"][filename] = {
                            "language": lang,
                            "content": content,
                        }
                    except Exception:
                        pass

        # Analyze directory structure
        for dir_name in self.STRUCTURE_DIRS:
            dir_path = self.project_dir / dir_name
            if dir_path.exists() and dir_path.is_dir():
                context["structure"].append(dir_name)
                if dir_name in ["tests", "__tests__", "spec"]:
                    context["has_tests"] = True
                if dir_name == "docs":
                    context["has_docs"] = True
                if dir_name == ".github":
                    context["has_ci"] = True

        # Count source files by extension
        extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript-react",
            ".jsx": "javascript-react",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".kt": "kotlin",
            ".swift": "swift",
            ".rb": "ruby",
            ".php": "php",
            ".cs": "csharp",
        }

        for ext, lang in extensions.items():
            count = len(list(self.project_dir.glob(f"**/*{ext}")))
            if count > 0:
                context["file_counts"][lang] = count

        return context

    def _detect_tech_stack(self, context: dict[str, Any]) -> dict[str, Any]:
        """Detect tech stack from project context."""
        stack = {
            "languages": [],
            "frameworks": [],
            "build_tools": [],
            "test_frameworks": [],
            "databases": [],
            "infrastructure": [],
        }

        config_files = context.get("config_files", {})

        # Detect languages from file counts
        file_counts = context.get("file_counts", {})
        for lang, count in sorted(file_counts.items(), key=lambda x: -x[1]):
            if count > 0:
                stack["languages"].append(lang)

        # Parse package.json for npm projects
        if "package.json" in config_files:
            try:
                pkg = json.loads(config_files["package.json"]["content"])
                deps = {
                    **pkg.get("dependencies", {}),
                    **pkg.get("devDependencies", {}),
                }

                # Detect frameworks
                framework_map = {
                    "react": "React",
                    "next": "Next.js",
                    "vue": "Vue.js",
                    "nuxt": "Nuxt",
                    "@angular/core": "Angular",
                    "svelte": "Svelte",
                    "express": "Express",
                    "fastify": "Fastify",
                    "nest": "NestJS",
                    "electron": "Electron",
                    "@tauri-apps/api": "Tauri",
                }

                for dep, framework in framework_map.items():
                    if any(d.startswith(dep) for d in deps):
                        stack["frameworks"].append(framework)

                # Detect test frameworks
                test_map = {
                    "jest": "Jest",
                    "mocha": "Mocha",
                    "vitest": "Vitest",
                    "playwright": "Playwright",
                    "cypress": "Cypress",
                }

                for dep, test in test_map.items():
                    if any(d.startswith(dep) for d in deps):
                        stack["test_frameworks"].append(test)

                # Detect build tools
                build_map = {
                    "webpack": "Webpack",
                    "vite": "Vite",
                    "esbuild": "esbuild",
                    "rollup": "Rollup",
                    "turbo": "Turborepo",
                }

                for dep, build in build_map.items():
                    if any(d.startswith(dep) for d in deps):
                        stack["build_tools"].append(build)

            except (json.JSONDecodeError, KeyError):
                pass

        # Parse Python configs
        if "pyproject.toml" in config_files:
            content = config_files["pyproject.toml"]["content"]
            # Simple detection from content
            framework_map = {
                "django": "Django",
                "flask": "Flask",
                "fastapi": "FastAPI",
                "streamlit": "Streamlit",
            }
            for key, framework in framework_map.items():
                if key in content.lower():
                    stack["frameworks"].append(framework)

            test_map = {
                "pytest": "pytest",
                "unittest": "unittest",
            }
            for key, test in test_map.items():
                if key in content.lower():
                    stack["test_frameworks"].append(test)

        # Detect infrastructure
        if "Dockerfile" in config_files or "docker-compose.yml" in config_files:
            stack["infrastructure"].append("Docker")
        if context.get("has_ci"):
            stack["infrastructure"].append("GitHub Actions")

        return stack

    async def _generate_claude_md(
        self, context: dict[str, Any], tech_stack: dict[str, Any]
    ) -> str:
        """Generate CLAUDE.md content using Claude."""
        # Build the prompt
        prompt = self._build_generation_prompt(context, tech_stack)

        # Create a simple client for single-turn generation
        client = create_simple_client(
            agent_type="claude_md_generator",
            model=self.model,
            system_prompt=self._get_system_prompt(),
            max_turns=1,
        )

        # Run the agent session
        result = await asyncio.to_thread(
            client.process_message,
            prompt,
        )

        # Extract the content from the result
        content = result.get("response", "")

        # Clean up the response (remove markdown code blocks if present)
        if content.startswith("```markdown"):
            content = content[len("```markdown") :].strip()
        elif content.startswith("```"):
            content = content[3:].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        return content

    def _get_system_prompt(self) -> str:
        """Get the system prompt for CLAUDE.md generation."""
        return """You are an expert software documentation writer. Your task is to generate a comprehensive CLAUDE.md file for a project.

CLAUDE.md is a special file that provides context and instructions to Claude Code (an AI coding assistant) when working with the project.

The file should be:
1. Comprehensive yet concise
2. Well-structured with clear sections
3. Focused on actionable guidance for AI assistants
4. Written in clear, technical language

Output ONLY the CLAUDE.md content, no explanations or preamble. Start directly with the markdown content."""

    def _build_generation_prompt(
        self, context: dict[str, Any], tech_stack: dict[str, Any]
    ) -> str:
        """Build the generation prompt from context and tech stack."""
        prompt_parts = [
            "Generate a CLAUDE.md file for the following project:\n",
            f"## Project Name: {context.get('project_name', 'Unknown')}\n",
        ]

        # Add tech stack info
        if tech_stack.get("languages"):
            prompt_parts.append(
                f"\n## Languages: {', '.join(tech_stack['languages'])}"
            )
        if tech_stack.get("frameworks"):
            prompt_parts.append(
                f"\n## Frameworks: {', '.join(tech_stack['frameworks'])}"
            )
        if tech_stack.get("build_tools"):
            prompt_parts.append(
                f"\n## Build Tools: {', '.join(tech_stack['build_tools'])}"
            )
        if tech_stack.get("test_frameworks"):
            prompt_parts.append(
                f"\n## Test Frameworks: {', '.join(tech_stack['test_frameworks'])}"
            )

        # Add directory structure
        if context.get("structure"):
            prompt_parts.append(
                f"\n## Directory Structure: {', '.join(context['structure'])}"
            )

        # Add project features
        features = []
        if context.get("has_tests"):
            features.append("Tests")
        if context.get("has_docs"):
            features.append("Documentation")
        if context.get("has_ci"):
            features.append("CI/CD")
        if features:
            prompt_parts.append(f"\n## Features: {', '.join(features)}")

        # Add README excerpt
        if context.get("readme_content"):
            prompt_parts.append(
                f"\n## README Content (excerpt):\n```\n{context['readme_content'][:2000]}\n```"
            )

        # Add package.json scripts if available
        config_files = context.get("config_files", {})
        if "package.json" in config_files:
            try:
                pkg = json.loads(config_files["package.json"]["content"])
                scripts = pkg.get("scripts", {})
                if scripts:
                    scripts_str = "\n".join(
                        f"  - {k}: {v}" for k, v in list(scripts.items())[:15]
                    )
                    prompt_parts.append(f"\n## Available npm Scripts:\n{scripts_str}")
            except (json.JSONDecodeError, KeyError):
                pass

        prompt_parts.append(
            """

## Required CLAUDE.md Sections:

1. **# CLAUDE.md** (title)

2. **## Project Overview** - Brief description of what the project does

3. **## Tech Stack** - List of languages, frameworks, and tools

4. **## Project Structure** - Key directories and their purpose

5. **## Development Commands** - Common commands for building, testing, running

6. **## Architecture Notes** - Key patterns, conventions, important files

7. **## Code Style** - Coding conventions, formatting, naming

Generate the CLAUDE.md content now:"""
        )

        return "\n".join(prompt_parts)
