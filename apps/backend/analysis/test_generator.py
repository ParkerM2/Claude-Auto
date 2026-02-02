#!/usr/bin/env python3
"""
Test Generator Module
=====================

Automatically generates unit tests for Python, JavaScript, and TypeScript code.
Uses AST analysis to extract functions, classes, and methods, then generates
framework-appropriate test templates (pytest for Python, vitest/jest for JS/TS).

This module powers the QA agent's test generation capabilities, ensuring
AI-generated code includes comprehensive test coverage from the start.

The test generator analyzes:
- Python: Functions, classes, methods, async functions
- JavaScript/TypeScript: Functions, classes, React components
- Frameworks: pytest, vitest, jest, @testing-library/react

Usage:
    from analysis.test_generator import TestGenerator

    generator = TestGenerator()

    # Analyze Python code
    analysis = generator.analyze_code(python_code, language="python")

    # Generate pytest tests
    test_code = generator.generate_test(python_code, framework="pytest")
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# =============================================================================
# ENUMS
# =============================================================================


class Language(str, Enum):
    """Supported programming languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"


class TestFramework(str, Enum):
    """Supported test frameworks."""

    __test__ = False  # Prevent pytest from collecting this as a test class

    PYTEST = "pytest"
    UNITTEST = "unittest"
    VITEST = "vitest"
    JEST = "jest"


class FunctionType(str, Enum):
    """Types of functions that can be tested."""

    FUNCTION = "function"
    METHOD = "method"
    ASYNC_FUNCTION = "async_function"
    ASYNC_METHOD = "async_method"
    CLASS_METHOD = "classmethod"
    STATIC_METHOD = "staticmethod"
    PROPERTY = "property"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class Parameter:
    """
    Represents a function parameter.

    Attributes:
        name: Parameter name
        type_hint: Type annotation if available
        default: Default value if any
        is_optional: Whether parameter has a default value
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    name: str
    type_hint: str | None = None
    default: str | None = None
    is_optional: bool = False


@dataclass
class FunctionInfo:
    """
    Information about a function extracted from AST.

    Attributes:
        name: Function name
        type: Type of function (function, method, async, etc.)
        parameters: List of parameters
        return_type: Return type annotation if available
        docstring: Function docstring
        line_number: Starting line number in source
        is_async: Whether function is async
        is_generator: Whether function is a generator
        decorators: List of decorator names
        class_name: Name of containing class if method
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    name: str
    type: FunctionType
    parameters: list[Parameter] = field(default_factory=list)
    return_type: str | None = None
    docstring: str | None = None
    line_number: int = 0
    is_async: bool = False
    is_generator: bool = False
    decorators: list[str] = field(default_factory=list)
    class_name: str | None = None


@dataclass
class ClassInfo:
    """
    Information about a class extracted from AST.

    Attributes:
        name: Class name
        methods: List of methods in the class
        base_classes: List of base class names
        docstring: Class docstring
        line_number: Starting line number in source
        decorators: List of decorator names
        is_dataclass: Whether class is a dataclass
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    name: str
    methods: list[FunctionInfo] = field(default_factory=list)
    base_classes: list[str] = field(default_factory=list)
    docstring: str | None = None
    line_number: int = 0
    decorators: list[str] = field(default_factory=list)
    is_dataclass: bool = False


@dataclass
class CodeAnalysis:
    """
    Result of code analysis for test generation.

    Attributes:
        language: Programming language detected
        functions: List of top-level functions
        classes: List of classes with their methods
        imports: List of import statements
        file_path: Source file path if analyzing a file
        has_async: Whether code contains async functions
        framework_detected: Test framework detected from imports
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    language: Language
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    file_path: str | None = None
    has_async: bool = False
    framework_detected: TestFramework | None = None


# =============================================================================
# AST ANALYZERS
# =============================================================================


class PythonASTAnalyzer:
    """
    Analyzes Python code using AST to extract testable elements.

    Extracts functions, classes, methods, and their signatures for test generation.
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    def analyze(self, code: str, file_path: str | None = None) -> CodeAnalysis:
        """
        Analyze Python code and extract testable elements.

        Args:
            code: Python source code
            file_path: Optional file path for context

        Returns:
            CodeAnalysis with extracted functions and classes

        Raises:
            SyntaxError: If code cannot be parsed
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise SyntaxError(f"Failed to parse Python code: {e}")

        analysis = CodeAnalysis(
            language=Language.PYTHON,
            file_path=file_path,
        )

        # Extract imports
        analysis.imports = self._extract_imports(tree)

        # Detect test framework from imports
        analysis.framework_detected = self._detect_framework(analysis.imports)

        # Extract top-level functions and classes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Only process top-level functions (not methods)
                if self._is_top_level_function(node, tree):
                    func_info = self._extract_function_info(node)
                    analysis.functions.append(func_info)
                    if func_info.is_async:
                        analysis.has_async = True

            elif isinstance(node, ast.ClassDef):
                # Only process top-level classes
                if self._is_top_level_class(node, tree):
                    class_info = self._extract_class_info(node)
                    analysis.classes.append(class_info)
                    # Check if any methods are async
                    if any(m.is_async for m in class_info.methods):
                        analysis.has_async = True

        return analysis

    def _extract_imports(self, tree: ast.AST) -> list[str]:
        """Extract import statements from AST."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports

    def _detect_framework(self, imports: list[str]) -> TestFramework | None:
        """Detect test framework from imports."""
        if "pytest" in imports:
            return TestFramework.PYTEST
        elif "unittest" in imports:
            return TestFramework.UNITTEST
        return None

    def _is_top_level_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, tree: ast.AST) -> bool:
        """Check if function is at module level (not a method)."""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                for child in parent.body:
                    if child is node:
                        return False
        return True

    def _is_top_level_class(self, node: ast.ClassDef, tree: ast.AST) -> bool:
        """Check if class is at module level (not nested)."""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef) and parent is not node:
                for child in parent.body:
                    if child is node:
                        return False
        return True

    def _extract_function_info(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        class_name: str | None = None
    ) -> FunctionInfo:
        """Extract detailed information about a function."""
        is_async = isinstance(node, ast.AsyncFunctionDef)

        # Determine function type
        func_type = FunctionType.ASYNC_FUNCTION if is_async else FunctionType.FUNCTION
        if class_name:
            func_type = FunctionType.ASYNC_METHOD if is_async else FunctionType.METHOD

        # Check for special decorators
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        if "classmethod" in decorators:
            func_type = FunctionType.CLASS_METHOD
        elif "staticmethod" in decorators:
            func_type = FunctionType.STATIC_METHOD
        elif "property" in decorators:
            func_type = FunctionType.PROPERTY

        # Extract parameters
        parameters = self._extract_parameters(node.args)

        # Extract return type
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else None

        # Extract docstring
        docstring = ast.get_docstring(node)

        # Check if generator
        is_generator = any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node))

        return FunctionInfo(
            name=node.name,
            type=func_type,
            parameters=parameters,
            return_type=return_type,
            docstring=docstring,
            line_number=node.lineno,
            is_async=is_async,
            is_generator=is_generator,
            decorators=decorators,
            class_name=class_name,
        )

    def _extract_parameters(self, args: ast.arguments) -> list[Parameter]:
        """Extract parameter information from function arguments."""
        parameters = []

        # Regular args
        all_args = args.args
        defaults = [None] * (len(all_args) - len(args.defaults)) + args.defaults

        for arg, default in zip(all_args, defaults):
            # Skip 'self' and 'cls' parameters
            if arg.arg in ('self', 'cls'):
                continue

            type_hint = None
            if arg.annotation:
                type_hint = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else None

            default_value = None
            has_default = default is not None
            if has_default:
                try:
                    default_value = ast.unparse(default) if hasattr(ast, 'unparse') else None
                except Exception:
                    default_value = "..."

            parameters.append(Parameter(
                name=arg.arg,
                type_hint=type_hint,
                default=default_value,
                is_optional=has_default,
            ))

        # *args
        if args.vararg:
            parameters.append(Parameter(
                name=f"*{args.vararg.arg}",
                type_hint=None,
                is_optional=True,
            ))

        # **kwargs
        if args.kwarg:
            parameters.append(Parameter(
                name=f"**{args.kwarg.arg}",
                type_hint=None,
                is_optional=True,
            ))

        return parameters

    def _extract_class_info(self, node: ast.ClassDef) -> ClassInfo:
        """Extract detailed information about a class."""
        # Extract base classes
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif hasattr(ast, 'unparse'):
                base_classes.append(ast.unparse(base))

        # Extract decorators
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        is_dataclass = "dataclass" in decorators

        # Extract docstring
        docstring = ast.get_docstring(node)

        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self._extract_function_info(item, class_name=node.name)
                methods.append(method_info)

        return ClassInfo(
            name=node.name,
            methods=methods,
            base_classes=base_classes,
            docstring=docstring,
            line_number=node.lineno,
            decorators=decorators,
            is_dataclass=is_dataclass,
        )

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Extract decorator name from decorator node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id
        elif hasattr(ast, 'unparse'):
            return ast.unparse(decorator)
        return "unknown"


# =============================================================================
# TEST GENERATOR
# =============================================================================


class JavaScriptTypeScriptAnalyzer:
    """
    Analyzes JavaScript/TypeScript code using regex to extract testable elements.

    Since we don't have a full AST parser for JS/TS in Python without heavy
    dependencies, we use regex-based parsing for basic extraction.
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    def analyze(
        self, code: str, language: Language, file_path: str | None = None
    ) -> CodeAnalysis:
        """
        Analyze JavaScript/TypeScript code and extract testable elements.

        Args:
            code: JavaScript/TypeScript source code
            language: Language.JAVASCRIPT or Language.TYPESCRIPT
            file_path: Optional file path for context

        Returns:
            CodeAnalysis with extracted functions and classes
        """
        analysis = CodeAnalysis(
            language=language,
            file_path=file_path,
        )

        # Extract imports
        analysis.imports = self._extract_imports(code)

        # Detect test framework from imports
        analysis.framework_detected = self._detect_framework(analysis.imports)

        # Extract functions (regular and arrow functions)
        analysis.functions = self._extract_functions(code)

        # Extract classes
        analysis.classes = self._extract_classes(code)

        # Check if any functions/methods are async
        analysis.has_async = any(f.is_async for f in analysis.functions) or any(
            any(m.is_async for m in cls.methods) for cls in analysis.classes
        )

        return analysis

    def _extract_imports(self, code: str) -> list[str]:
        """Extract import statements from JavaScript/TypeScript code."""
        imports = []

        # Match: import X from 'module'
        # Match: import { X, Y } from 'module'
        # Match: import * as X from 'module'
        import_pattern = r"import\s+(?:[\w{},\s*]+)\s+from\s+['\"]([^'\"]+)['\"]"
        for match in re.finditer(import_pattern, code):
            imports.append(match.group(1))

        # Match: import 'module' (side-effect imports)
        side_effect_pattern = r"import\s+['\"]([^'\"]+)['\"]"
        for match in re.finditer(side_effect_pattern, code):
            module = match.group(1)
            if module not in imports:
                imports.append(module)

        return imports

    def _detect_framework(self, imports: list[str]) -> TestFramework | None:
        """Detect test framework from imports."""
        if "vitest" in imports or any("vitest" in imp for imp in imports):
            return TestFramework.VITEST
        elif "jest" in imports or "@jest" in imports:
            return TestFramework.JEST
        return None

    def _extract_functions(self, code: str) -> list[FunctionInfo]:
        """Extract function declarations and expressions."""
        functions = []

        # Pattern for regular function declarations
        # function myFunc(arg1: type, arg2): ReturnType
        # async function myFunc(...)
        func_pattern = r"(?:export\s+)?(async\s+)?function\s+(\w+)\s*\((.*?)\)(?:\s*:\s*([^{]+))?\s*\{"
        for match in re.finditer(func_pattern, code, re.MULTILINE):
            is_async = match.group(1) is not None  # Check if 'async' was captured
            func_name = match.group(2)
            params_str = match.group(3)
            return_type = match.group(4).strip() if match.group(4) else None

            # Parse parameters
            parameters = self._parse_parameters(params_str)

            functions.append(FunctionInfo(
                name=func_name,
                type=FunctionType.ASYNC_FUNCTION if is_async else FunctionType.FUNCTION,
                parameters=parameters,
                return_type=return_type,
                is_async=is_async,
                line_number=code[:match.start()].count('\n') + 1,
            ))

        # Pattern for arrow functions assigned to const/let/var
        # const myFunc = (arg1, arg2) => { }
        # const myFunc = async (arg1) => { }
        arrow_pattern = r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(async\s+)?\((.*?)\)(?:\s*:\s*([^=]+?))?\s*=>"
        for match in re.finditer(arrow_pattern, code, re.MULTILINE):
            is_async = match.group(2) is not None  # Check if 'async' was captured
            func_name = match.group(1)
            params_str = match.group(3)
            return_type = match.group(4).strip() if match.group(4) else None

            # Parse parameters
            parameters = self._parse_parameters(params_str)

            functions.append(FunctionInfo(
                name=func_name,
                type=FunctionType.ASYNC_FUNCTION if is_async else FunctionType.FUNCTION,
                parameters=parameters,
                return_type=return_type,
                is_async=is_async,
                line_number=code[:match.start()].count('\n') + 1,
            ))

        return functions

    def _extract_classes(self, code: str) -> list[ClassInfo]:
        """Extract class declarations."""
        classes = []

        # Pattern for class declarations
        # class MyClass extends BaseClass { }
        class_pattern = r"(?:export\s+)?class\s+(\w+)(?:\s+extends\s+([\w.]+))?\s*\{"
        for match in re.finditer(class_pattern, code, re.MULTILINE):
            class_name = match.group(1)
            base_class = match.group(2) if match.group(2) else None

            # Find the class body (everything until the matching closing brace)
            class_start = match.end()
            brace_count = 1
            class_end = class_start
            for i in range(class_start, len(code)):
                if code[i] == '{':
                    brace_count += 1
                elif code[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        class_end = i
                        break

            class_body = code[class_start:class_end]

            # Extract methods from class body
            methods = self._extract_methods(class_body, class_name)

            classes.append(ClassInfo(
                name=class_name,
                methods=methods,
                base_classes=[base_class] if base_class else [],
                line_number=code[:match.start()].count('\n') + 1,
            ))

        return classes

    def _extract_methods(self, class_body: str, class_name: str) -> list[FunctionInfo]:
        """Extract methods from class body."""
        methods = []

        # Pattern for method declarations
        # methodName(arg1, arg2): ReturnType { }
        # async methodName(arg1): ReturnType { }
        method_pattern = r"(async\s+)?(\w+)\s*\((.*?)\)(?:\s*:\s*([^{]+))?\s*\{"
        for match in re.finditer(method_pattern, class_body, re.MULTILINE):
            is_async = match.group(1) is not None  # Check if 'async' was captured
            method_name = match.group(2)

            # Skip if this looks like a control structure (if, for, while, etc.)
            if method_name in ('if', 'for', 'while', 'switch', 'catch'):
                continue

            params_str = match.group(3)
            return_type = match.group(4).strip() if match.group(4) else None

            # Parse parameters
            parameters = self._parse_parameters(params_str)

            methods.append(FunctionInfo(
                name=method_name,
                type=FunctionType.ASYNC_METHOD if is_async else FunctionType.METHOD,
                parameters=parameters,
                return_type=return_type,
                is_async=is_async,
                class_name=class_name,
                line_number=class_body[:match.start()].count('\n') + 1,
            ))

        return methods

    def _parse_parameters(self, params_str: str) -> list[Parameter]:
        """Parse parameter string into Parameter objects."""
        parameters = []

        if not params_str.strip():
            return parameters

        # Split by comma, but be careful with nested types like Array<string, number>
        params = []
        current_param = ""
        angle_depth = 0
        paren_depth = 0

        for char in params_str + ",":
            if char == '<':
                angle_depth += 1
            elif char == '>':
                angle_depth -= 1
            elif char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == ',' and angle_depth == 0 and paren_depth == 0:
                if current_param.strip():
                    params.append(current_param.strip())
                current_param = ""
                continue
            current_param += char

        # Parse each parameter
        for param in params:
            # Handle destructured parameters like { x, y }
            if param.startswith('{') or param.startswith('['):
                # Simplified: just use the whole thing as the name
                parameters.append(Parameter(
                    name=param.split(':')[0].strip() if ':' in param else param.strip(),
                    type_hint=None,
                ))
                continue

            # Check for default value: param = defaultValue
            has_default = '=' in param
            if has_default:
                param = param.split('=')[0].strip()

            # Check for type annotation: param: Type
            if ':' in param:
                parts = param.split(':', 1)
                param_name = parts[0].strip()
                type_hint = parts[1].strip()
            else:
                param_name = param.strip()
                type_hint = None

            # Handle rest parameters: ...args
            if param_name.startswith('...'):
                param_name = param_name[3:].strip()
                type_hint = f"...{type_hint}" if type_hint else "...any"

            if param_name:  # Skip empty parameters
                parameters.append(Parameter(
                    name=param_name,
                    type_hint=type_hint,
                    is_optional=has_default,
                ))

        return parameters


class TestGenerator:
    """
    Main test generator class.

    Analyzes code and generates framework-appropriate test templates.
    Supports Python (pytest, unittest) and JavaScript/TypeScript (vitest, jest).
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    def __init__(self):
        """Initialize test generator with language-specific analyzers."""
        self.python_analyzer = PythonASTAnalyzer()
        self.js_ts_analyzer = JavaScriptTypeScriptAnalyzer()

    def analyze_code(
        self,
        code: str,
        language: str | Language = "python",
        file_path: str | None = None,
    ) -> CodeAnalysis:
        """
        Analyze code and extract testable elements.

        Args:
            code: Source code to analyze
            language: Programming language (python, javascript, typescript)
            file_path: Optional file path for context

        Returns:
            CodeAnalysis with extracted functions and classes

        Raises:
            ValueError: If language is not supported
            SyntaxError: If code cannot be parsed
        """
        if isinstance(language, str):
            try:
                language = Language(language.lower())
            except ValueError:
                raise ValueError(f"Unsupported language: {language}")

        if language == Language.PYTHON:
            return self.python_analyzer.analyze(code, file_path)
        elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            return self.js_ts_analyzer.analyze(code, language, file_path)
        else:
            raise NotImplementedError(f"Analysis for {language} not yet implemented")

    def analyze_file(self, file_path: str | Path) -> CodeAnalysis:
        """
        Analyze a code file and extract testable elements.

        Args:
            file_path: Path to source code file

        Returns:
            CodeAnalysis with extracted functions and classes

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If file extension is not supported
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Detect language from file extension
        ext = path.suffix.lower()
        language_map = {
            ".py": Language.PYTHON,
            ".js": Language.JAVASCRIPT,
            ".jsx": Language.JAVASCRIPT,
            ".ts": Language.TYPESCRIPT,
            ".tsx": Language.TYPESCRIPT,
        }

        if ext not in language_map:
            raise ValueError(f"Unsupported file extension: {ext}")

        language = language_map[ext]
        code = path.read_text(encoding="utf-8")

        return self.analyze_code(code, language=language, file_path=str(path))

    def generate_test(
        self,
        code: str,
        framework: str | TestFramework = "pytest",
        language: str | Language = "python",
        is_react: bool = False,
    ) -> str:
        """
        Generate test code for the given source code.

        Args:
            code: Source code to generate tests for
            framework: Test framework to use (pytest, vitest, jest, unittest)
            language: Programming language
            is_react: Whether code contains React components

        Returns:
            Generated test code as a string

        Raises:
            ValueError: If framework or language is not supported
            NotImplementedError: If framework support is not yet implemented
        """
        # Convert string inputs to enums
        if isinstance(framework, str):
            try:
                framework = TestFramework(framework.lower())
            except ValueError:
                raise ValueError(f"Unsupported test framework: {framework}")

        if isinstance(language, str):
            try:
                language = Language(language.lower())
            except ValueError:
                raise ValueError(f"Unsupported language: {language}")

        # Analyze code to extract testable elements
        analysis = self.analyze_code(code, language=language)

        # Generate tests based on framework
        if framework == TestFramework.PYTEST:
            return self._generate_pytest_tests(analysis)
        elif framework == TestFramework.UNITTEST:
            raise NotImplementedError("unittest generation not yet implemented")
        elif framework == TestFramework.VITEST:
            return self._generate_vitest_tests(analysis, is_react)
        elif framework == TestFramework.JEST:
            return self._generate_jest_tests(analysis, is_react)
        else:
            raise ValueError(f"Unsupported framework: {framework}")

    def _generate_pytest_tests(self, analysis: CodeAnalysis) -> str:
        """
        Generate pytest test code from code analysis.

        Args:
            analysis: Code analysis results

        Returns:
            Generated pytest test code
        """
        lines = []

        # Add header comment
        lines.append('"""')
        lines.append("Generated test file")
        if analysis.file_path:
            lines.append(f"Tests for: {analysis.file_path}")
        lines.append('"""')
        lines.append("")

        # Add imports
        imports = self._generate_pytest_imports(analysis)
        lines.extend(imports)
        lines.append("")

        # Add fixtures if needed
        fixtures = self._generate_pytest_fixtures(analysis)
        if fixtures:
            lines.extend(fixtures)
            lines.append("")

        # Generate tests for top-level functions
        for func in analysis.functions:
            test_func = self._generate_pytest_function_test(func)
            lines.extend(test_func)
            lines.append("")

        # Generate tests for classes
        for cls in analysis.classes:
            class_tests = self._generate_pytest_class_tests(cls)
            lines.extend(class_tests)
            lines.append("")

        return "\n".join(lines)

    def _generate_pytest_imports(self, analysis: CodeAnalysis) -> list[str]:
        """Generate import statements for pytest tests."""
        imports = [
            "from unittest.mock import MagicMock, Mock, patch",
            "",
            "import pytest",
        ]

        # Add async support if needed
        if analysis.has_async:
            imports.append("import asyncio")

        return imports

    def _generate_pytest_fixtures(self, analysis: CodeAnalysis) -> list[str]:
        """Generate pytest fixtures based on code analysis."""
        fixtures = []

        # Generate fixtures for classes that need instances
        for cls in analysis.classes:
            fixture_lines = self._generate_class_fixture(cls)
            if fixture_lines:
                fixtures.extend(fixture_lines)
                fixtures.append("")

        return fixtures

    def _generate_class_fixture(self, cls: ClassInfo) -> list[str]:
        """Generate a fixture for instantiating a class."""
        fixture_name = cls.name.lower() + "_instance"
        lines = [
            "@pytest.fixture",
            f"def {fixture_name}():",
            f'    """Create a {cls.name} instance for testing."""',
        ]

        # Determine constructor parameters
        init_method = None
        for method in cls.methods:
            if method.name == "__init__":
                init_method = method
                break

        if init_method and init_method.parameters:
            # Create mock parameters
            lines.append("    # Mock dependencies")
            for param in init_method.parameters:
                if param.name not in ("self", "cls"):
                    lines.append(f"    {param.name} = Mock()")

            # Instantiate with mocks
            param_names = [p.name for p in init_method.parameters if p.name not in ("self", "cls")]
            params_str = ", ".join(param_names)
            lines.append(f"    return {cls.name}({params_str})")
        else:
            # Simple instantiation
            lines.append(f"    return {cls.name}()")

        return lines

    def _generate_pytest_function_test(self, func: FunctionInfo) -> list[str]:
        """Generate pytest test for a function."""
        lines = []

        # Generate test function signature
        test_name = f"test_{func.name}"

        # Check if we need async test
        if func.is_async:
            lines.append("@pytest.mark.asyncio")
            lines.append(f"async def {test_name}():")
        else:
            lines.append(f"def {test_name}():")

        # Add docstring
        lines.append(f'    """Test {func.name} function."""')

        # Generate test body
        if func.parameters:
            # Arrange: Create test data
            lines.append("    # Arrange")
            for param in func.parameters:
                if param.name.startswith("*"):
                    continue
                if param.type_hint:
                    lines.append(f"    {param.name} = None  # TODO: Provide test value for {param.type_hint}")
                else:
                    lines.append(f"    {param.name} = None  # TODO: Provide test value")
            lines.append("")

            # Act: Call function
            lines.append("    # Act")
            param_names = [p.name for p in func.parameters if not p.name.startswith("*")]
            params_str = ", ".join(param_names)
            if func.is_async:
                lines.append(f"    result = await {func.name}({params_str})")
            else:
                lines.append(f"    result = {func.name}({params_str})")
            lines.append("")

            # Assert: Check result
            lines.append("    # Assert")
            if func.return_type and func.return_type != "None":
                lines.append(f"    assert result is not None  # TODO: Add specific assertions")
            else:
                lines.append("    # TODO: Add assertions")
        else:
            # Simple function with no parameters
            lines.append("    # Act")
            if func.is_async:
                lines.append(f"    result = await {func.name}()")
            else:
                lines.append(f"    result = {func.name}()")
            lines.append("")
            lines.append("    # Assert")
            if func.return_type and func.return_type != "None":
                lines.append(f"    assert result is not None  # TODO: Add specific assertions")
            else:
                lines.append("    # TODO: Add assertions")

        return lines

    def _generate_pytest_class_tests(self, cls: ClassInfo) -> list[str]:
        """Generate pytest tests for a class and its methods."""
        lines = []

        # Generate test class
        lines.append(f"class Test{cls.name}:")
        lines.append(f'    """Tests for {cls.name} class."""')
        lines.append("")

        # Generate tests for each method
        for method in cls.methods:
            # Skip private methods and __init__
            if method.name.startswith("_") and method.name != "__init__":
                continue

            if method.name == "__init__":
                # Test instantiation
                test_lines = self._generate_init_test(cls, method)
            else:
                # Test regular method
                test_lines = self._generate_method_test(cls, method)

            # Indent all lines for class body
            indented_lines = ["    " + line if line else "" for line in test_lines]
            lines.extend(indented_lines)
            lines.append("")

        return lines

    def _generate_init_test(self, cls: ClassInfo, method: FunctionInfo) -> list[str]:
        """Generate test for class instantiation."""
        lines = [
            "def test_init(self):",
            f'    """Test {cls.name} instantiation."""',
        ]

        if method.parameters:
            lines.append("    # Arrange")
            for param in method.parameters:
                if param.name not in ("self", "cls"):
                    lines.append(f"    {param.name} = Mock()")
            lines.append("")
            lines.append("    # Act")
            param_names = [p.name for p in method.parameters if p.name not in ("self", "cls")]
            params_str = ", ".join(param_names)
            lines.append(f"    instance = {cls.name}({params_str})")
        else:
            lines.append("    # Act")
            lines.append(f"    instance = {cls.name}()")

        lines.append("")
        lines.append("    # Assert")
        lines.append("    assert instance is not None")

        return lines

    def _generate_method_test(self, cls: ClassInfo, method: FunctionInfo) -> list[str]:
        """Generate test for a class method."""
        lines = []

        test_name = f"test_{method.name}"
        fixture_name = cls.name.lower() + "_instance"

        # Check if we need async test
        if method.is_async:
            lines.append("@pytest.mark.asyncio")
            lines.append(f"async def {test_name}(self, {fixture_name}):")
        else:
            lines.append(f"def {test_name}(self, {fixture_name}):")

        lines.append(f'    """Test {cls.name}.{method.name} method."""')

        # Generate test body
        if method.parameters:
            # Arrange
            lines.append("    # Arrange")
            for param in method.parameters:
                if param.name.startswith("*"):
                    continue
                if param.type_hint:
                    lines.append(f"    {param.name} = None  # TODO: Provide test value for {param.type_hint}")
                else:
                    lines.append(f"    {param.name} = None  # TODO: Provide test value")
            lines.append("")

            # Act
            lines.append("    # Act")
            param_names = [p.name for p in method.parameters if not p.name.startswith("*")]
            params_str = ", ".join(param_names)
            if method.is_async:
                lines.append(f"    result = await {fixture_name}.{method.name}({params_str})")
            else:
                lines.append(f"    result = {fixture_name}.{method.name}({params_str})")
            lines.append("")

            # Assert
            lines.append("    # Assert")
            if method.return_type and method.return_type != "None":
                lines.append(f"    assert result is not None  # TODO: Add specific assertions")
            else:
                lines.append("    # TODO: Add assertions")
        else:
            # Simple method with no parameters
            lines.append("    # Act")
            if method.is_async:
                lines.append(f"    result = await {fixture_name}.{method.name}()")
            else:
                lines.append(f"    result = {fixture_name}.{method.name}()")
            lines.append("")
            lines.append("    # Assert")
            if method.return_type and method.return_type != "None":
                lines.append(f"    assert result is not None  # TODO: Add specific assertions")
            else:
                lines.append("    # TODO: Add assertions")

        return lines

    def _generate_vitest_tests(self, analysis: CodeAnalysis, is_react: bool = False) -> str:
        """
        Generate vitest test code from code analysis.

        Args:
            analysis: Code analysis results
            is_react: Whether code contains React components

        Returns:
            Generated vitest test code
        """
        lines = []

        # Add header comment
        lines.append("/**")
        lines.append(" * Generated test file")
        if analysis.file_path:
            lines.append(f" * Tests for: {analysis.file_path}")
        lines.append(" */")
        lines.append("")

        # Add imports
        imports = self._generate_vitest_imports(analysis, is_react)
        lines.extend(imports)
        lines.append("")

        # Generate tests for top-level functions
        for func in analysis.functions:
            test_func = self._generate_vitest_function_test(func)
            lines.extend(test_func)
            lines.append("")

        # Generate tests for classes
        for cls in analysis.classes:
            class_tests = self._generate_vitest_class_tests(cls)
            lines.extend(class_tests)
            lines.append("")

        return "\n".join(lines)

    def _generate_vitest_imports(self, analysis: CodeAnalysis, is_react: bool) -> list[str]:
        """Generate import statements for vitest tests."""
        imports = ["import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';"]

        # Add React testing library imports if needed
        if is_react:
            imports.append("import { render, screen, fireEvent } from '@testing-library/react';")
            imports.append("import '@testing-library/jest-dom/vitest';")

        imports.append("")

        # Add TODO comment to import the code being tested
        if analysis.file_path:
            imports.append(f"// TODO: Import functions/classes from '{analysis.file_path}'")
        else:
            imports.append("// TODO: Import functions/classes to test")

        return imports

    def _generate_vitest_function_test(self, func: FunctionInfo) -> list[str]:
        """Generate vitest test for a function."""
        lines = []

        # Generate describe block
        lines.append(f"describe('{func.name}', () => {{")

        # Add test case
        if func.is_async:
            lines.append(f"  it('should work correctly', async () => {{")
        else:
            lines.append(f"  it('should work correctly', () => {{")

        # Generate test body
        if func.parameters:
            # Arrange: Create test data
            lines.append("    // Arrange")
            for param in func.parameters:
                if param.name.startswith("..."):
                    continue
                if param.type_hint:
                    lines.append(f"    const {param.name} = null; // TODO: Provide test value for {param.type_hint}")
                else:
                    lines.append(f"    const {param.name} = null; // TODO: Provide test value")
            lines.append("")

            # Act: Call function
            lines.append("    // Act")
            param_names = [p.name for p in func.parameters if not p.name.startswith("...")]
            params_str = ", ".join(param_names)
            if func.is_async:
                lines.append(f"    const result = await {func.name}({params_str});")
            else:
                lines.append(f"    const result = {func.name}({params_str});")
            lines.append("")

            # Assert: Check result
            lines.append("    // Assert")
            if func.return_type and func.return_type not in ("void", "undefined"):
                lines.append("    expect(result).toBeDefined(); // TODO: Add specific assertions")
            else:
                lines.append("    // TODO: Add assertions")
        else:
            # Simple function with no parameters
            lines.append("    // Act")
            if func.is_async:
                lines.append(f"    const result = await {func.name}();")
            else:
                lines.append(f"    const result = {func.name}();")
            lines.append("")
            lines.append("    // Assert")
            if func.return_type and func.return_type not in ("void", "undefined"):
                lines.append("    expect(result).toBeDefined(); // TODO: Add specific assertions")
            else:
                lines.append("    // TODO: Add assertions")

        lines.append("  });")
        lines.append("});")

        return lines

    def _generate_vitest_class_tests(self, cls: ClassInfo) -> list[str]:
        """Generate vitest tests for a class and its methods."""
        lines = []

        # Generate describe block for class
        lines.append(f"describe('{cls.name}', () => {{")

        # Add beforeEach hook to create instance
        lines.append("  let instance: any;")
        lines.append("")
        lines.append("  beforeEach(() => {")

        # Find constructor parameters
        constructor_method = None
        for method in cls.methods:
            if method.name == "constructor":
                constructor_method = method
                break

        if constructor_method and constructor_method.parameters:
            lines.append("    // Mock dependencies")
            for param in constructor_method.parameters:
                lines.append(f"    const {param.name} = vi.fn();")
            param_names = [p.name for p in constructor_method.parameters]
            params_str = ", ".join(param_names)
            lines.append(f"    instance = new {cls.name}({params_str});")
        else:
            lines.append(f"    instance = new {cls.name}();")

        lines.append("  });")
        lines.append("")

        # Generate tests for each method
        for method in cls.methods:
            # Skip constructor and private methods
            if method.name == "constructor" or method.name.startswith("_"):
                continue

            test_lines = self._generate_vitest_method_test(cls, method)
            # Indent all lines for describe block
            indented_lines = ["  " + line if line else "" for line in test_lines]
            lines.extend(indented_lines)
            lines.append("")

        lines.append("});")

        return lines

    def _generate_vitest_method_test(self, cls: ClassInfo, method: FunctionInfo) -> list[str]:
        """Generate vitest test for a class method."""
        lines = []

        # Add test case
        if method.is_async:
            lines.append(f"it('should test {method.name}', async () => {{")
        else:
            lines.append(f"it('should test {method.name}', () => {{")

        # Generate test body
        if method.parameters:
            # Arrange
            lines.append("  // Arrange")
            for param in method.parameters:
                if param.name.startswith("..."):
                    continue
                if param.type_hint:
                    lines.append(f"  const {param.name} = null; // TODO: Provide test value for {param.type_hint}")
                else:
                    lines.append(f"  const {param.name} = null; // TODO: Provide test value")
            lines.append("")

            # Act
            lines.append("  // Act")
            param_names = [p.name for p in method.parameters if not p.name.startswith("...")]
            params_str = ", ".join(param_names)
            if method.is_async:
                lines.append(f"  const result = await instance.{method.name}({params_str});")
            else:
                lines.append(f"  const result = instance.{method.name}({params_str});")
            lines.append("")

            # Assert
            lines.append("  // Assert")
            if method.return_type and method.return_type not in ("void", "undefined"):
                lines.append("  expect(result).toBeDefined(); // TODO: Add specific assertions")
            else:
                lines.append("  // TODO: Add assertions")
        else:
            # Simple method with no parameters
            lines.append("  // Act")
            if method.is_async:
                lines.append(f"  const result = await instance.{method.name}();")
            else:
                lines.append(f"  const result = instance.{method.name}();")
            lines.append("")
            lines.append("  // Assert")
            if method.return_type and method.return_type not in ("void", "undefined"):
                lines.append("  expect(result).toBeDefined(); // TODO: Add specific assertions")
            else:
                lines.append("  // TODO: Add assertions")

        lines.append("});")

        return lines

    def _generate_jest_tests(self, analysis: CodeAnalysis, is_react: bool = False) -> str:
        """
        Generate jest test code from code analysis.

        Jest and vitest have very similar syntax, so we reuse the vitest logic
        with minor adjustments.

        Args:
            analysis: Code analysis results
            is_react: Whether code contains React components

        Returns:
            Generated jest test code
        """
        # Jest and vitest have nearly identical syntax, so we can reuse the generation logic
        # The main difference is the imports
        lines = []

        # Add header comment
        lines.append("/**")
        lines.append(" * Generated test file")
        if analysis.file_path:
            lines.append(f" * Tests for: {analysis.file_path}")
        lines.append(" */")
        lines.append("")

        # Add imports (Jest-specific)
        imports = self._generate_jest_imports(analysis, is_react)
        lines.extend(imports)
        lines.append("")

        # Generate tests for top-level functions (reuse vitest logic)
        for func in analysis.functions:
            test_func = self._generate_vitest_function_test(func)
            lines.extend(test_func)
            lines.append("")

        # Generate tests for classes (reuse vitest logic)
        for cls in analysis.classes:
            class_tests = self._generate_vitest_class_tests(cls)
            lines.extend(class_tests)
            lines.append("")

        return "\n".join(lines)

    def _generate_jest_imports(self, analysis: CodeAnalysis, is_react: bool) -> list[str]:
        """Generate import statements for jest tests."""
        imports = ["import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';"]

        # Add React testing library imports if needed
        if is_react:
            imports.append("import { render, screen, fireEvent } from '@testing-library/react';")
            imports.append("import '@testing-library/jest-dom';")

        imports.append("")

        # Add TODO comment to import the code being tested
        if analysis.file_path:
            imports.append(f"// TODO: Import functions/classes from '{analysis.file_path}'")
        else:
            imports.append("// TODO: Import functions/classes to test")

        return imports
