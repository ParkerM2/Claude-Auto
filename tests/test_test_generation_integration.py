#!/usr/bin/env python3
"""
Integration Tests for Test Generation Workflow
===============================================

Tests the full end-to-end test generation workflow:
1. Framework detection from code/imports
2. Code analysis (AST extraction)
3. Test generation
4. Verification that generated tests are valid syntax

This verifies the complete integration of:
- TestGenerator (analysis + generation)
- PythonASTAnalyzer
- JavaScriptTypeScriptAnalyzer
- pytest/vitest/jest test generation
"""

import ast
import re
import sys
import tempfile
from pathlib import Path

import pytest

# Add apps/backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from analysis.test_generator import (
    Language,
    TestFramework,
    TestGenerator,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_generator():
    """Create a TestGenerator instance."""
    return TestGenerator()


# =============================================================================
# PYTHON PYTEST INTEGRATION TESTS
# =============================================================================


class TestPythonPytestIntegration:
    """Test full workflow for Python code with pytest."""

    def test_simple_function_workflow(self, test_generator):
        """Test complete workflow for a simple Python function."""
        # Arrange: Python code with imports
        code = """
import pytest

def calculate_total(items, tax_rate=0.1):
    '''Calculate total price with tax.'''
    subtotal = sum(items)
    tax = subtotal * tax_rate
    return subtotal + tax
"""

        # Act 1: Detect framework
        analysis = test_generator.analyze_code(code, language="python")

        # Assert 1: Framework detection
        assert analysis.framework_detected == TestFramework.PYTEST
        assert len(analysis.functions) == 1
        assert analysis.functions[0].name == "calculate_total"
        assert len(analysis.functions[0].parameters) == 2

        # Act 2: Generate test
        test_code = test_generator.generate_test(code, framework="pytest", language="python")

        # Assert 2: Generated test is valid Python syntax
        try:
            ast.parse(test_code)
        except SyntaxError as e:
            pytest.fail(f"Generated pytest code has syntax error: {e}\n\nGenerated code:\n{test_code}")

        # Assert 3: Test contains expected pytest patterns
        assert "import pytest" in test_code
        assert "def test_calculate_total():" in test_code
        assert "# Arrange" in test_code
        assert "# Act" in test_code
        assert "# Assert" in test_code
        assert "calculate_total" in test_code

    def test_async_function_workflow(self, test_generator):
        """Test complete workflow for async Python functions."""
        # Arrange: Async Python code
        code = """
import asyncio
import pytest

async def fetch_user_data(user_id: int) -> dict:
    '''Fetch user data from API.'''
    await asyncio.sleep(0.1)
    return {"id": user_id, "name": "Test User"}
"""

        # Act 1: Analyze code
        analysis = test_generator.analyze_code(code, language="python")

        # Assert 1: Async detection
        assert analysis.has_async is True
        assert analysis.functions[0].is_async is True

        # Act 2: Generate test
        test_code = test_generator.generate_test(code, framework="pytest")

        # Assert 2: Valid Python syntax
        try:
            ast.parse(test_code)
        except SyntaxError as e:
            pytest.fail(f"Generated async pytest code has syntax error: {e}")

        # Assert 3: Async test patterns
        assert "@pytest.mark.asyncio" in test_code
        assert "async def test_fetch_user_data():" in test_code
        assert "await fetch_user_data" in test_code

    def test_class_workflow(self, test_generator):
        """Test complete workflow for Python class."""
        # Arrange: Python class
        code = """
from typing import List

class ShoppingCart:
    '''Shopping cart for e-commerce.'''

    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        self.items = []

    def add_item(self, item_id: str, price: float):
        '''Add item to cart.'''
        self.items.append({"id": item_id, "price": price})

    def get_total(self) -> float:
        '''Get total price.'''
        return sum(item["price"] for item in self.items)
"""

        # Act 1: Analyze code
        analysis = test_generator.analyze_code(code, language="python")

        # Assert 1: Class detection
        assert len(analysis.classes) == 1
        assert analysis.classes[0].name == "ShoppingCart"
        assert len(analysis.classes[0].methods) == 3  # __init__, add_item, get_total

        # Act 2: Generate test
        test_code = test_generator.generate_test(code, framework="pytest")

        # Assert 2: Valid Python syntax
        try:
            ast.parse(test_code)
        except SyntaxError as e:
            pytest.fail(f"Generated class test has syntax error: {e}")

        # Assert 3: Class test patterns
        assert "class TestShoppingCart:" in test_code
        assert "@pytest.fixture" in test_code
        assert "def shoppingcart_instance():" in test_code
        assert "def test_init(self):" in test_code
        assert "def test_add_item(self" in test_code
        assert "def test_get_total(self" in test_code

    def test_file_analysis_workflow(self, test_generator, temp_dir):
        """Test analyzing a Python file and generating tests."""
        # Arrange: Create a Python source file
        source_file = temp_dir / "utils.py"
        source_file.write_text("""
def format_currency(amount: float, currency: str = "USD") -> str:
    '''Format amount as currency string.'''
    return f"{currency} {amount:.2f}"

def validate_email(email: str) -> bool:
    '''Basic email validation.'''
    return "@" in email and "." in email
""")

        # Act 1: Analyze file
        analysis = test_generator.analyze_file(source_file)

        # Assert 1: File analysis
        assert analysis.language == Language.PYTHON
        assert len(analysis.functions) == 2
        assert str(source_file) in analysis.file_path

        # Act 2: Generate test from file content
        code = source_file.read_text()
        test_code = test_generator.generate_test(code, framework="pytest")

        # Assert 2: Valid test generated
        try:
            ast.parse(test_code)
        except SyntaxError as e:
            pytest.fail(f"Generated test from file has syntax error: {e}")

        assert "def test_format_currency():" in test_code
        assert "def test_validate_email():" in test_code


# =============================================================================
# JAVASCRIPT/TYPESCRIPT VITEST INTEGRATION TESTS
# =============================================================================


class TestJavaScriptVitestIntegration:
    """Test full workflow for JavaScript/TypeScript code with vitest."""

    def test_javascript_function_workflow(self, test_generator):
        """Test complete workflow for JavaScript functions."""
        # Arrange: JavaScript code
        code = """
import { describe, it, expect } from 'vitest';

export function calculateDiscount(price, percentage) {
    if (percentage < 0 || percentage > 100) {
        throw new Error('Invalid percentage');
    }
    return price * (percentage / 100);
}

export const formatPrice = (amount) => {
    return `$${amount.toFixed(2)}`;
};
"""

        # Act 1: Analyze code
        analysis = test_generator.analyze_code(code, language="javascript")

        # Assert 1: Framework and function detection
        assert analysis.framework_detected == TestFramework.VITEST
        assert len(analysis.functions) == 2
        func_names = [f.name for f in analysis.functions]
        assert "calculateDiscount" in func_names
        assert "formatPrice" in func_names

        # Act 2: Generate test
        test_code = test_generator.generate_test(code, framework="vitest", language="javascript")

        # Assert 2: Valid JavaScript test patterns
        assert "import { describe, it, expect" in test_code
        assert "describe('calculateDiscount'" in test_code
        assert "describe('formatPrice'" in test_code
        assert "it('should work correctly'" in test_code
        assert "// Arrange" in test_code
        assert "// Act" in test_code
        assert "// Assert" in test_code

    def test_typescript_async_workflow(self, test_generator):
        """Test complete workflow for TypeScript async functions."""
        # Arrange: TypeScript async code
        code = """
export async function fetchUserProfile(userId: number): Promise<UserProfile> {
    const response = await fetch(`/api/users/${userId}`);
    const data = await response.json();
    return data;
}
"""

        # Act 1: Analyze code
        analysis = test_generator.analyze_code(code, language="typescript")

        # Assert 1: Async detection
        assert analysis.has_async is True
        assert analysis.functions[0].is_async is True
        assert analysis.functions[0].return_type == "Promise<UserProfile>"

        # Act 2: Generate test
        test_code = test_generator.generate_test(code, framework="vitest", language="typescript")

        # Assert 2: Async test patterns
        assert "it('should work correctly', async () => {" in test_code
        assert "await fetchUserProfile" in test_code

    def test_react_component_workflow(self, test_generator):
        """Test complete workflow for React components."""
        # Arrange: React component
        code = """
import React from 'react';

export function UserCard({ name, email, onEdit }) {
    return (
        <div className="user-card">
            <h2>{name}</h2>
            <p>{email}</p>
            <button onClick={onEdit}>Edit</button>
        </div>
    );
}
"""

        # Act 1: Analyze code
        analysis = test_generator.analyze_code(code, language="javascript")

        # Assert 1: Component detection
        assert len(analysis.functions) == 1
        assert analysis.functions[0].name == "UserCard"
        # Component should be detected by PascalCase naming
        assert analysis.functions[0].name[0].isupper()

        # Act 2: Generate test with React flag
        test_code = test_generator.generate_test(
            code, framework="vitest", language="javascript", is_react=True
        )

        # Assert 2: React testing patterns
        assert "import { render, screen, fireEvent }" in test_code
        assert "describe('UserCard'" in test_code
        assert "render(<UserCard" in test_code
        assert "it('should render successfully'" in test_code
        assert "it('should render with props'" in test_code

    def test_typescript_class_workflow(self, test_generator):
        """Test complete workflow for TypeScript class."""
        # Arrange: TypeScript class
        code = """
export class DataService {
    private cache: Map<string, any>;

    constructor(baseUrl: string) {
        this.cache = new Map();
    }

    async fetchData(endpoint: string): Promise<any> {
        if (this.cache.has(endpoint)) {
            return this.cache.get(endpoint);
        }
        const data = await fetch(endpoint).then(r => r.json());
        this.cache.set(endpoint, data);
        return data;
    }

    clearCache(): void {
        this.cache.clear();
    }
}
"""

        # Act 1: Analyze code
        analysis = test_generator.analyze_code(code, language="typescript")

        # Assert 1: Class detection
        assert len(analysis.classes) == 1
        assert analysis.classes[0].name == "DataService"
        method_names = [m.name for m in analysis.classes[0].methods]
        assert "constructor" in method_names
        assert "fetchData" in method_names
        assert "clearCache" in method_names

        # Act 2: Generate test
        test_code = test_generator.generate_test(code, framework="vitest", language="typescript")

        # Assert 2: Class test patterns
        assert "describe('DataService'" in test_code
        assert "let instance: any;" in test_code
        assert "beforeEach(() => {" in test_code
        assert "instance = new DataService" in test_code
        assert "it('should test fetchData'" in test_code
        assert "it('should test clearCache'" in test_code


# =============================================================================
# JEST INTEGRATION TESTS
# =============================================================================


class TestJestIntegration:
    """Test full workflow for Jest framework."""

    def test_jest_function_workflow(self, test_generator):
        """Test complete workflow for Jest tests."""
        # Arrange: JavaScript code with Jest imports
        code = """
import { jest } from '@jest/globals';

export function processPayment(amount, method) {
    if (amount <= 0) {
        throw new Error('Invalid amount');
    }
    return { amount, method, status: 'success' };
}
"""

        # Act 1: Analyze code
        analysis = test_generator.analyze_code(code, language="javascript")

        # Assert 1: Framework detection
        assert analysis.framework_detected == TestFramework.JEST

        # Act 2: Generate test
        test_code = test_generator.generate_test(code, framework="jest", language="javascript")

        # Assert 2: Jest-specific patterns
        assert "import { describe, it, expect" in test_code
        assert "@jest/globals" in test_code
        assert "describe('processPayment'" in test_code


# =============================================================================
# FRAMEWORK DETECTION TESTS
# =============================================================================


class TestFrameworkDetection:
    """Test framework auto-detection from code."""

    def test_pytest_detection_from_imports(self, test_generator):
        """Test pytest detection from imports."""
        code = "import pytest\n\ndef test_something():\n    pass"
        analysis = test_generator.analyze_code(code, language="python")
        assert analysis.framework_detected == TestFramework.PYTEST

    def test_vitest_detection_from_imports(self, test_generator):
        """Test vitest detection from imports."""
        code = "import { describe, it } from 'vitest';\n"
        analysis = test_generator.analyze_code(code, language="javascript")
        assert analysis.framework_detected == TestFramework.VITEST

    def test_jest_detection_from_imports(self, test_generator):
        """Test jest detection from imports."""
        code = "import { jest } from '@jest/globals';\n"
        analysis = test_generator.analyze_code(code, language="javascript")
        assert analysis.framework_detected == TestFramework.JEST

    def test_no_framework_detected(self, test_generator):
        """Test when no framework is detected."""
        code = "def add(a, b):\n    return a + b"
        analysis = test_generator.analyze_code(code, language="python")
        assert analysis.framework_detected is None


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Test error handling in the integration workflow."""

    def test_invalid_python_syntax(self, test_generator):
        """Test handling of invalid Python syntax."""
        code = "def broken( :\n    pass"  # Invalid syntax

        with pytest.raises(SyntaxError):
            test_generator.analyze_code(code, language="python")

    def test_unsupported_language(self, test_generator):
        """Test handling of unsupported language."""
        code = "func main() {}"  # Go code

        with pytest.raises(ValueError, match="Unsupported language"):
            test_generator.analyze_code(code, language="golang")

    def test_unsupported_framework(self, test_generator):
        """Test handling of unsupported framework."""
        code = "def test(): pass"

        with pytest.raises(ValueError, match="Unsupported test framework"):
            test_generator.generate_test(code, framework="mocha")

    def test_file_not_found(self, test_generator):
        """Test handling of missing file."""
        with pytest.raises(FileNotFoundError):
            test_generator.analyze_file("/nonexistent/file.py")

    def test_unsupported_file_extension(self, test_generator, temp_dir):
        """Test handling of unsupported file extension."""
        go_file = temp_dir / "main.go"
        go_file.write_text("package main")

        with pytest.raises(ValueError, match="Unsupported file extension"):
            test_generator.analyze_file(go_file)


# =============================================================================
# FULL WORKFLOW VALIDATION TESTS
# =============================================================================


class TestFullWorkflowValidation:
    """Test that generated tests are fully valid and runnable."""

    def test_generated_pytest_is_importable(self, test_generator, temp_dir):
        """Test that generated pytest code can be parsed and imported."""
        # Arrange: Generate test for a simple function
        code = """
def multiply(x, y):
    return x * y
"""
        test_code = test_generator.generate_test(code, framework="pytest")

        # Act: Write to file and try to parse as module
        test_file = temp_dir / "test_generated.py"
        test_file.write_text(test_code)

        # Assert: File can be parsed as valid Python module
        try:
            ast.parse(test_code)
        except SyntaxError as e:
            pytest.fail(f"Generated test is not valid Python: {e}")

        # Verify test structure
        tree = ast.parse(test_code)
        # Should have imports and function definitions
        assert any(isinstance(node, ast.Import) for node in ast.walk(tree))
        assert any(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))

    def test_generated_test_has_proper_structure(self, test_generator):
        """Test that generated tests follow proper AAA pattern."""
        code = """
def process_order(order_id, items):
    total = sum(item['price'] for item in items)
    return {'order_id': order_id, 'total': total}
"""
        test_code = test_generator.generate_test(code, framework="pytest")

        # Verify AAA pattern is present
        assert "# Arrange" in test_code
        assert "# Act" in test_code
        assert "# Assert" in test_code

        # Verify proper test structure
        assert test_code.startswith('"""')  # Has docstring
        assert "import pytest" in test_code
        assert "def test_process_order():" in test_code

    def test_end_to_end_workflow(self, test_generator, temp_dir):
        """Test complete end-to-end workflow from file to generated test."""
        # Step 1: Create source file
        source_file = temp_dir / "calculator.py"
        source_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b

    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
""")

        # Step 2: Analyze file
        analysis = test_generator.analyze_file(source_file)
        assert analysis.language == Language.PYTHON
        assert len(analysis.classes) == 1
        assert analysis.classes[0].name == "Calculator"

        # Step 3: Generate test
        code = source_file.read_text()
        test_code = test_generator.generate_test(code, framework="pytest")

        # Step 4: Validate generated test
        # Should be valid Python
        try:
            ast.parse(test_code)
        except SyntaxError as e:
            pytest.fail(f"Generated test has syntax error: {e}")

        # Should have test class
        assert "class TestCalculator:" in test_code

        # Should have fixture for instance
        assert "@pytest.fixture" in test_code

        # Should have test methods
        assert "def test_add(self" in test_code
        assert "def test_divide(self" in test_code

        # Step 5: Verify test file could be written
        test_file = temp_dir / "test_calculator.py"
        test_file.write_text(test_code)
        assert test_file.exists()
        assert test_file.read_text() == test_code
