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
        else:
            # JavaScript/TypeScript analysis will be added in phase 2
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
        # This method will be fully implemented in subtask-1-2
        # For now, just ensure the class can be imported
        raise NotImplementedError("Test generation will be implemented in subtask-1-2")
