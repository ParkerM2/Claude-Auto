"""
Test Generation Tools
=====================

Tools for automatically generating unit and integration tests.
"""

import logging
from pathlib import Path
from typing import Any

from analysis.test_generator import TestGenerator

try:
    from claude_agent_sdk import tool

    SDK_TOOLS_AVAILABLE = True
except ImportError:
    SDK_TOOLS_AVAILABLE = False
    tool = None


def create_test_generation_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create test generation tools.

    Args:
        spec_dir: Path to the spec directory
        project_dir: Path to the project root

    Returns:
        List of test generation tool functions
    """
    if not SDK_TOOLS_AVAILABLE:
        return []

    tools = []
    generator = TestGenerator()

    # -------------------------------------------------------------------------
    # Tool: generate_tests_for_file
    # -------------------------------------------------------------------------
    @tool(
        "generate_tests_for_file",
        "Generate unit tests for a source code file. Analyzes the file and creates test cases for all functions and classes.",
        {"file_path": str, "framework": str},
    )
    async def generate_tests_for_file(args: dict[str, Any]) -> dict[str, Any]:
        """Generate tests for a complete source file."""
        file_path = args["file_path"]
        framework = args.get("framework", "pytest")

        # Resolve file path relative to project directory
        if not Path(file_path).is_absolute():
            full_path = project_dir / file_path
        else:
            full_path = Path(file_path)

        if not full_path.exists():
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: File not found: {file_path}",
                    }
                ]
            }

        try:
            # Read the source code
            code = full_path.read_text(encoding="utf-8")

            # Detect language from file extension
            ext = full_path.suffix.lower()
            language_map = {
                ".py": "python",
                ".js": "javascript",
                ".jsx": "javascript",
                ".ts": "typescript",
                ".tsx": "typescript",
            }

            if ext not in language_map:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: Unsupported file extension: {ext}. Supported: .py, .js, .jsx, .ts, .tsx",
                        }
                    ]
                }

            language = language_map[ext]

            # Detect if React component
            is_react = "react" in code.lower() or ext in [".jsx", ".tsx"]

            # Generate tests
            test_code = generator.generate_test(
                code, framework=framework, language=language, is_react=is_react
            )

            # Suggest test file path
            if ext == ".py":
                test_file_name = f"test_{full_path.stem}.py"
                test_dir = project_dir / "tests"
            else:
                test_file_name = f"{full_path.stem}.test{ext}"
                test_dir = full_path.parent

            suggested_path = test_dir / test_file_name

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Successfully generated {framework} tests for {file_path}\n\n"
                        f"Suggested test file: {suggested_path.relative_to(project_dir)}\n\n"
                        f"Generated test code:\n\n```{language}\n{test_code}\n```",
                    }
                ]
            }

        except Exception as e:
            logging.error(f"Test generation failed for {file_path}: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error generating tests for {file_path}: {e}",
                    }
                ]
            }

    tools.append(generate_tests_for_file)

    # -------------------------------------------------------------------------
    # Tool: generate_unit_test
    # -------------------------------------------------------------------------
    @tool(
        "generate_unit_test",
        "Generate a unit test for a specific function or code snippet.",
        {"code": str, "framework": str, "language": str},
    )
    async def generate_unit_test(args: dict[str, Any]) -> dict[str, Any]:
        """Generate a unit test for a code snippet."""
        code = args["code"]
        framework = args.get("framework", "pytest")
        language = args.get("language", "python")

        try:
            # Detect if React component
            is_react = "react" in code.lower() and language in [
                "javascript",
                "typescript",
            ]

            # Generate test
            test_code = generator.generate_test(
                code, framework=framework, language=language, is_react=is_react
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Successfully generated {framework} unit test\n\n"
                        f"Generated test code:\n\n```{language}\n{test_code}\n```",
                    }
                ]
            }

        except Exception as e:
            logging.error(f"Unit test generation failed: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error generating unit test: {e}",
                    }
                ]
            }

    tools.append(generate_unit_test)

    # -------------------------------------------------------------------------
    # Tool: generate_integration_test
    # -------------------------------------------------------------------------
    @tool(
        "generate_integration_test",
        "Generate an integration test template for API endpoints or component interactions.",
        {"description": str, "framework": str, "language": str},
    )
    async def generate_integration_test(args: dict[str, Any]) -> dict[str, Any]:
        """Generate an integration test template."""
        description = args["description"]
        framework = args.get("framework", "pytest")
        language = args.get("language", "python")

        try:
            # Generate integration test template based on framework
            if framework in ["pytest", "unittest"]:
                test_code = _generate_python_integration_template(description)
            elif framework in ["vitest", "jest"]:
                test_code = _generate_js_integration_template(description, framework)
            else:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: Unsupported framework: {framework}. Use pytest, unittest, vitest, or jest",
                        }
                    ]
                }

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Successfully generated {framework} integration test template\n\n"
                        f"Description: {description}\n\n"
                        f"Generated test code:\n\n```{language}\n{test_code}\n```",
                    }
                ]
            }

        except Exception as e:
            logging.error(f"Integration test generation failed: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error generating integration test: {e}",
                    }
                ]
            }

    tools.append(generate_integration_test)

    return tools


def _generate_python_integration_template(description: str) -> str:
    """Generate a Python integration test template."""
    return f'''"""
Integration Test
================

{description}
"""

import pytest


@pytest.fixture
def client():
    """Create test client fixture."""
    # TODO: Set up test client (e.g., Flask test client, FastAPI TestClient)
    pass


@pytest.fixture
def db():
    """Create test database fixture."""
    # TODO: Set up test database
    pass


class TestIntegration:
    """Integration test suite."""

    def test_endpoint_success(self, client, db):
        """Test successful API call."""
        # Arrange
        # TODO: Set up test data

        # Act
        # TODO: Make API call
        # response = client.get("/api/endpoint")

        # Assert
        # TODO: Verify response
        # assert response.status_code == 200
        pass

    def test_endpoint_error_handling(self, client, db):
        """Test error handling."""
        # Arrange
        # TODO: Set up error condition

        # Act
        # TODO: Make API call that should fail

        # Assert
        # TODO: Verify error response
        pass

    def test_data_persistence(self, client, db):
        """Test data is correctly persisted."""
        # Arrange
        # TODO: Create test data

        # Act
        # TODO: Perform operations

        # Assert
        # TODO: Verify data in database
        pass
'''


def _generate_js_integration_template(description: str, framework: str) -> str:
    """Generate a JavaScript/TypeScript integration test template."""
    return f"""/**
 * Integration Test
 * ================
 *
 * {description}
 */

import {{ describe, it, expect, beforeEach, afterEach }} from '{framework}';

describe('Integration Test Suite', () => {{
  beforeEach(() => {{
    // TODO: Set up test environment
  }});

  afterEach(() => {{
    // TODO: Clean up test environment
  }});

  it('should handle successful API call', async () => {{
    // Arrange
    // TODO: Set up test data

    // Act
    // TODO: Make API call
    // const response = await fetch('/api/endpoint');

    // Assert
    // TODO: Verify response
    // expect(response.status).toBe(200);
  }});

  it('should handle error cases', async () => {{
    // Arrange
    // TODO: Set up error condition

    // Act
    // TODO: Make API call that should fail

    // Assert
    // TODO: Verify error response
  }});

  it('should persist data correctly', async () => {{
    // Arrange
    // TODO: Create test data

    // Act
    // TODO: Perform operations

    // Assert
    // TODO: Verify data persistence
  }});
}});
"""
