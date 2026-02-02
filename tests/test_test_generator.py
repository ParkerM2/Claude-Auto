#!/usr/bin/env python3
"""
Tests for the TestGenerator module.

Tests cover:
- Data classes (Parameter, FunctionInfo, ClassInfo, CodeAnalysis)
- PythonASTAnalyzer for Python code analysis
- TestGenerator for test generation
- pytest test template generation
- Framework detection
- AST parsing and extraction
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add auto-claude to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from analysis.test_generator import (
    ClassInfo,
    CodeAnalysis,
    FunctionInfo,
    FunctionType,
    Language,
    Parameter,
    PythonASTAnalyzer,
    TestFramework,
    TestGenerator,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def simple_python_code():
    """Simple Python code with a basic function."""
    return """
def add(a, b):
    return a + b

def greet(name):
    if name:
        return f"Hello, {name}"
    return "Hello, stranger"
"""


@pytest.fixture
def async_python_code():
    """Python code with async functions."""
    return """
import asyncio

async def fetch_data(url):
    # Simulate async operation
    await asyncio.sleep(1)
    return {"data": "result"}

async def process_data(data):
    processed = data.upper()
    return processed
"""


@pytest.fixture
def class_python_code():
    """Python code with a class."""
    return """
class Calculator:
    def __init__(self, initial_value=0):
        self.value = initial_value

    def add(self, x):
        self.value += x
        return self.value

    def subtract(self, x):
        self.value -= x
        return self.value

    def reset(self):
        self.value = 0
"""


@pytest.fixture
def complex_class_code():
    """Python code with a complex class including async methods and decorators."""
    return """
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int

    @property
    def is_adult(self):
        return self.age >= 18

    @classmethod
    def from_dict(cls, data):
        return cls(name=data['name'], age=data['age'])

    @staticmethod
    def validate_age(age):
        return 0 <= age <= 150

    async def save(self):
        # Simulate async save
        return True
"""


@pytest.fixture
def python_analyzer():
    """Create a PythonASTAnalyzer instance."""
    return PythonASTAnalyzer()


@pytest.fixture
def test_generator():
    """Create a TestGenerator instance."""
    return TestGenerator()


# =============================================================================
# DATA CLASS TESTS
# =============================================================================


def test_parameter_creation():
    """Test Parameter dataclass creation."""
    param = Parameter(
        name="x",
        type_hint="int",
        default="0",
        is_optional=True
    )
    assert param.name == "x"
    assert param.type_hint == "int"
    assert param.default == "0"
    assert param.is_optional is True


def test_parameter_without_defaults():
    """Test Parameter creation without optional fields."""
    param = Parameter(name="y")
    assert param.name == "y"
    assert param.type_hint is None
    assert param.default is None
    assert param.is_optional is False


def test_function_info_creation():
    """Test FunctionInfo dataclass creation."""
    func = FunctionInfo(
        name="test_func",
        type=FunctionType.FUNCTION,
        parameters=[Parameter(name="x")],
        return_type="str",
        docstring="Test function",
        line_number=10,
        is_async=False,
        is_generator=False,
        decorators=["decorator1"],
        class_name=None
    )
    assert func.name == "test_func"
    assert func.type == FunctionType.FUNCTION
    assert len(func.parameters) == 1
    assert func.return_type == "str"
    assert func.docstring == "Test function"
    assert func.line_number == 10


def test_class_info_creation():
    """Test ClassInfo dataclass creation."""
    cls = ClassInfo(
        name="TestClass",
        methods=[],
        base_classes=["BaseClass"],
        docstring="Test class",
        line_number=5,
        decorators=["dataclass"],
        is_dataclass=True
    )
    assert cls.name == "TestClass"
    assert cls.base_classes == ["BaseClass"]
    assert cls.is_dataclass is True


def test_code_analysis_creation():
    """Test CodeAnalysis dataclass creation."""
    analysis = CodeAnalysis(
        language=Language.PYTHON,
        functions=[],
        classes=[],
        imports=["os", "sys"],
        file_path="/path/to/file.py",
        has_async=True,
        framework_detected=TestFramework.PYTEST
    )
    assert analysis.language == Language.PYTHON
    assert analysis.imports == ["os", "sys"]
    assert analysis.has_async is True
    assert analysis.framework_detected == TestFramework.PYTEST


# =============================================================================
# PYTHON AST ANALYZER TESTS
# =============================================================================


def test_analyze_simple_function(python_analyzer, simple_python_code):
    """Test analyzing simple Python functions."""
    analysis = python_analyzer.analyze(simple_python_code)

    assert analysis.language == Language.PYTHON
    assert len(analysis.functions) == 2
    assert analysis.functions[0].name == "add"
    assert analysis.functions[1].name == "greet"
    assert analysis.has_async is False


def test_analyze_function_parameters(python_analyzer, simple_python_code):
    """Test extracting function parameters."""
    analysis = python_analyzer.analyze(simple_python_code)

    add_func = analysis.functions[0]
    assert len(add_func.parameters) == 2
    assert add_func.parameters[0].name == "a"
    assert add_func.parameters[1].name == "b"


def test_analyze_async_functions(python_analyzer, async_python_code):
    """Test analyzing async functions."""
    analysis = python_analyzer.analyze(async_python_code)

    assert len(analysis.functions) == 2
    assert analysis.functions[0].name == "fetch_data"
    assert analysis.functions[0].is_async is True
    assert analysis.functions[0].type == FunctionType.ASYNC_FUNCTION
    assert analysis.has_async is True


def test_analyze_class(python_analyzer, class_python_code):
    """Test analyzing a Python class."""
    analysis = python_analyzer.analyze(class_python_code)

    assert len(analysis.classes) == 1
    calculator = analysis.classes[0]
    assert calculator.name == "Calculator"
    assert len(calculator.methods) == 4  # __init__, add, subtract, reset


def test_analyze_class_methods(python_analyzer, class_python_code):
    """Test extracting class methods."""
    analysis = python_analyzer.analyze(class_python_code)

    calculator = analysis.classes[0]
    method_names = [m.name for m in calculator.methods]
    assert "__init__" in method_names
    assert "add" in method_names
    assert "subtract" in method_names
    assert "reset" in method_names

    # Verify method parameters
    init_method = next(m for m in calculator.methods if m.name == "__init__")
    assert len(init_method.parameters) == 1  # initial_value (self is skipped)
    assert init_method.parameters[0].name == "initial_value"


def test_analyze_complex_class(python_analyzer, complex_class_code):
    """Test analyzing class with decorators and special methods."""
    analysis = python_analyzer.analyze(complex_class_code)

    user_class = analysis.classes[0]
    assert user_class.name == "User"
    assert user_class.is_dataclass is True
    assert "dataclass" in user_class.decorators

    # Check method types
    methods_by_name = {m.name: m for m in user_class.methods}

    assert methods_by_name["is_adult"].type == FunctionType.PROPERTY
    assert methods_by_name["from_dict"].type == FunctionType.CLASS_METHOD
    assert methods_by_name["validate_age"].type == FunctionType.STATIC_METHOD
    assert methods_by_name["save"].is_async is True
    assert analysis.has_async is True


def test_extract_imports(python_analyzer, async_python_code):
    """Test extracting import statements."""
    analysis = python_analyzer.analyze(async_python_code)

    assert "asyncio" in analysis.imports


def test_detect_pytest_framework(python_analyzer):
    """Test detecting pytest framework from imports."""
    code = """
import pytest

def test_something():
    assert True
"""
    analysis = python_analyzer.analyze(code)
    assert analysis.framework_detected == TestFramework.PYTEST


def test_detect_unittest_framework(python_analyzer):
    """Test detecting unittest framework from imports."""
    code = """
import unittest

class TestCase(unittest.TestCase):
    def test_something(self):
        self.assertTrue(True)
"""
    analysis = python_analyzer.analyze(code)
    assert analysis.framework_detected == TestFramework.UNITTEST


def test_analyze_invalid_python_code(python_analyzer):
    """Test analyzing invalid Python code raises SyntaxError."""
    invalid_code = "def invalid( syntax error"

    with pytest.raises(SyntaxError) as exc_info:
        python_analyzer.analyze(invalid_code)

    assert "Failed to parse Python code" in str(exc_info.value)


def test_extract_function_with_type_hints(python_analyzer):
    """Test extracting function with type hints."""
    code = """
def typed_func(x: int, y: str = "default") -> bool:
    return True
"""
    analysis = python_analyzer.analyze(code)

    func = analysis.functions[0]
    assert func.return_type == "bool"
    assert func.parameters[0].type_hint == "int"
    assert func.parameters[1].type_hint == "str"
    assert func.parameters[1].default == "'default'"
    assert func.parameters[1].is_optional is True


def test_extract_function_with_varargs(python_analyzer):
    """Test extracting function with *args and **kwargs."""
    code = """
def varargs_func(x, *args, **kwargs):
    pass
"""
    analysis = python_analyzer.analyze(code)

    func = analysis.functions[0]
    param_names = [p.name for p in func.parameters]
    assert "x" in param_names
    assert "*args" in param_names
    assert "**kwargs" in param_names


def test_skip_self_and_cls_parameters(python_analyzer):
    """Test that self and cls parameters are skipped."""
    code = """
class MyClass:
    def instance_method(self, x):
        pass

    @classmethod
    def class_method(cls, y):
        pass
"""
    analysis = python_analyzer.analyze(code)

    cls = analysis.classes[0]
    instance_method = next(m for m in cls.methods if m.name == "instance_method")
    class_method = next(m for m in cls.methods if m.name == "class_method")

    # self and cls should not be in parameters
    assert len(instance_method.parameters) == 1
    assert instance_method.parameters[0].name == "x"
    assert len(class_method.parameters) == 1
    assert class_method.parameters[0].name == "y"


def test_extract_generator_function(python_analyzer):
    """Test detecting generator functions."""
    code = """
def generator_func():
    yield 1
    yield 2
"""
    analysis = python_analyzer.analyze(code)

    func = analysis.functions[0]
    assert func.is_generator is True


# =============================================================================
# TEST GENERATOR TESTS
# =============================================================================


def test_test_generator_initialization(test_generator):
    """Test TestGenerator initialization."""
    assert test_generator is not None
    assert test_generator.python_analyzer is not None


def test_analyze_code_python(test_generator, simple_python_code):
    """Test TestGenerator.analyze_code for Python."""
    analysis = test_generator.analyze_code(simple_python_code, language="python")

    assert analysis.language == Language.PYTHON
    assert len(analysis.functions) == 2


def test_analyze_code_with_language_enum(test_generator, simple_python_code):
    """Test analyze_code with Language enum."""
    analysis = test_generator.analyze_code(simple_python_code, language=Language.PYTHON)

    assert analysis.language == Language.PYTHON


def test_analyze_code_unsupported_language(test_generator):
    """Test analyze_code with unsupported language raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        test_generator.analyze_code("code", language="rust")

    assert "Unsupported language" in str(exc_info.value)


def test_analyze_code_javascript_not_implemented(test_generator):
    """Test analyze_code for JavaScript raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        test_generator.analyze_code("function test() {}", language="javascript")


def test_analyze_file_python(test_generator, temp_dir, simple_python_code):
    """Test analyze_file for Python file."""
    # Create Python file
    py_file = temp_dir / "test.py"
    py_file.write_text(simple_python_code)

    analysis = test_generator.analyze_file(py_file)

    assert analysis.language == Language.PYTHON
    assert len(analysis.functions) == 2
    assert str(py_file) in analysis.file_path


def test_analyze_file_not_found(test_generator, temp_dir):
    """Test analyze_file with non-existent file raises FileNotFoundError."""
    non_existent = temp_dir / "does_not_exist.py"

    with pytest.raises(FileNotFoundError) as exc_info:
        test_generator.analyze_file(non_existent)

    assert "File not found" in str(exc_info.value)


def test_analyze_file_unsupported_extension(test_generator, temp_dir):
    """Test analyze_file with unsupported extension raises ValueError."""
    # Create file with unsupported extension
    txt_file = temp_dir / "file.txt"
    txt_file.write_text("some text")

    with pytest.raises(ValueError) as exc_info:
        test_generator.analyze_file(txt_file)

    assert "Unsupported file extension" in str(exc_info.value)


@pytest.mark.parametrize("extension,language", [
    (".py", Language.PYTHON),
    (".js", Language.JAVASCRIPT),
    (".jsx", Language.JAVASCRIPT),
    (".ts", Language.TYPESCRIPT),
    (".tsx", Language.TYPESCRIPT),
])
def test_analyze_file_language_detection(test_generator, temp_dir, extension, language):
    """Test language detection from file extensions."""
    # Create file with specific extension
    file_path = temp_dir / f"test{extension}"
    file_path.write_text("# placeholder")

    # Only test Python files (others raise NotImplementedError)
    if language == Language.PYTHON:
        analysis = test_generator.analyze_file(file_path)
        assert analysis.language == language
    else:
        with pytest.raises(NotImplementedError):
            test_generator.analyze_file(file_path)


def test_generate_test_simple_function(test_generator, simple_python_code):
    """Test generating pytest test for simple function."""
    test_code = test_generator.generate_test(simple_python_code, framework="pytest")

    # Verify test structure
    assert "def test_add():" in test_code
    assert "def test_greet():" in test_code
    assert "import pytest" in test_code
    assert "# Arrange" in test_code
    assert "# Act" in test_code
    assert "# Assert" in test_code


def test_generate_test_async_function(test_generator, async_python_code):
    """Test generating pytest test for async function."""
    test_code = test_generator.generate_test(async_python_code, framework="pytest")

    # Verify async test structure
    assert "@pytest.mark.asyncio" in test_code
    assert "async def test_fetch_data():" in test_code
    assert "await fetch_data(" in test_code
    assert "import asyncio" in test_code


def test_generate_test_class(test_generator, class_python_code):
    """Test generating pytest test for class."""
    test_code = test_generator.generate_test(class_python_code, framework="pytest")

    # Verify class test structure
    assert "class TestCalculator:" in test_code
    assert "def test_init(self):" in test_code
    assert "def test_add(self, calculator_instance):" in test_code
    assert "def test_subtract(self, calculator_instance):" in test_code
    assert "@pytest.fixture" in test_code


def test_generate_test_with_framework_enum(test_generator, simple_python_code):
    """Test generate_test with TestFramework enum."""
    test_code = test_generator.generate_test(
        simple_python_code,
        framework=TestFramework.PYTEST
    )

    assert "def test_add():" in test_code


def test_generate_test_unsupported_framework(test_generator, simple_python_code):
    """Test generate_test with unsupported framework raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        test_generator.generate_test(simple_python_code, framework="mocha")

    assert "Unsupported test framework" in str(exc_info.value)


def test_generate_test_unittest_not_implemented(test_generator, simple_python_code):
    """Test generate_test with unittest raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        test_generator.generate_test(simple_python_code, framework="unittest")


def test_generate_test_vitest_not_implemented(test_generator, simple_python_code):
    """Test generate_test with vitest raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        test_generator.generate_test(simple_python_code, framework="vitest")


def test_generate_pytest_imports_basic(test_generator):
    """Test generating pytest imports for basic code."""
    analysis = CodeAnalysis(
        language=Language.PYTHON,
        has_async=False
    )

    imports = test_generator._generate_pytest_imports(analysis)

    assert "import pytest" in imports
    assert "from unittest.mock import MagicMock, Mock, patch" in imports


def test_generate_pytest_imports_with_async(test_generator):
    """Test generating pytest imports for async code."""
    analysis = CodeAnalysis(
        language=Language.PYTHON,
        has_async=True
    )

    imports = test_generator._generate_pytest_imports(analysis)

    assert "import pytest" in imports
    assert "import asyncio" in imports


def test_generate_class_fixture(test_generator):
    """Test generating fixture for class instantiation."""
    cls = ClassInfo(
        name="MyClass",
        methods=[
            FunctionInfo(
                name="__init__",
                type=FunctionType.METHOD,
                parameters=[
                    Parameter(name="x"),
                    Parameter(name="y")
                ]
            )
        ]
    )

    fixture_lines = test_generator._generate_class_fixture(cls)
    fixture_str = "\n".join(fixture_lines)

    assert "@pytest.fixture" in fixture_str
    assert "def myclass_instance():" in fixture_str
    assert "x = Mock()" in fixture_str
    assert "y = Mock()" in fixture_str
    assert "return MyClass(x, y)" in fixture_str


def test_generate_class_fixture_no_init(test_generator):
    """Test generating fixture for class without __init__ parameters."""
    cls = ClassInfo(
        name="SimpleClass",
        methods=[]
    )

    fixture_lines = test_generator._generate_class_fixture(cls)
    fixture_str = "\n".join(fixture_lines)

    assert "return SimpleClass()" in fixture_str


def test_generate_function_test_with_parameters(test_generator):
    """Test generating test for function with parameters."""
    func = FunctionInfo(
        name="add",
        type=FunctionType.FUNCTION,
        parameters=[
            Parameter(name="a", type_hint="int"),
            Parameter(name="b", type_hint="int")
        ],
        return_type="int"
    )

    test_lines = test_generator._generate_pytest_function_test(func)
    test_str = "\n".join(test_lines)

    assert "def test_add():" in test_str
    assert "# Arrange" in test_str
    assert "a = None  # TODO: Provide test value for int" in test_str
    assert "b = None  # TODO: Provide test value for int" in test_str
    assert "result = add(a, b)" in test_str
    assert "# Assert" in test_str


def test_generate_function_test_no_parameters(test_generator):
    """Test generating test for function without parameters."""
    func = FunctionInfo(
        name="get_default",
        type=FunctionType.FUNCTION,
        parameters=[],
        return_type="str"
    )

    test_lines = test_generator._generate_pytest_function_test(func)
    test_str = "\n".join(test_lines)

    assert "def test_get_default():" in test_str
    assert "result = get_default()" in test_str
    assert "assert result is not None" in test_str


def test_generate_async_function_test(test_generator):
    """Test generating test for async function."""
    func = FunctionInfo(
        name="fetch",
        type=FunctionType.ASYNC_FUNCTION,
        parameters=[Parameter(name="url")],
        is_async=True
    )

    test_lines = test_generator._generate_pytest_function_test(func)
    test_str = "\n".join(test_lines)

    assert "@pytest.mark.asyncio" in test_str
    assert "async def test_fetch():" in test_str
    assert "result = await fetch(url)" in test_str


def test_generate_init_test(test_generator):
    """Test generating test for __init__ method."""
    cls = ClassInfo(name="MyClass")
    method = FunctionInfo(
        name="__init__",
        type=FunctionType.METHOD,
        parameters=[
            Parameter(name="x"),
            Parameter(name="y")
        ]
    )

    test_lines = test_generator._generate_init_test(cls, method)
    test_str = "\n".join(test_lines)

    assert "def test_init(self):" in test_str
    assert "x = Mock()" in test_str
    assert "y = Mock()" in test_str
    assert "instance = MyClass(x, y)" in test_str
    assert "assert instance is not None" in test_str


def test_generate_method_test(test_generator):
    """Test generating test for class method."""
    cls = ClassInfo(name="Calculator")
    method = FunctionInfo(
        name="add",
        type=FunctionType.METHOD,
        parameters=[Parameter(name="x", type_hint="int")],
        return_type="int"
    )

    test_lines = test_generator._generate_method_test(cls, method)
    test_str = "\n".join(test_lines)

    assert "def test_add(self, calculator_instance):" in test_str
    assert "x = None  # TODO: Provide test value for int" in test_str
    assert "result = calculator_instance.add(x)" in test_str


def test_generate_async_method_test(test_generator):
    """Test generating test for async class method."""
    cls = ClassInfo(name="AsyncWorker")
    method = FunctionInfo(
        name="process",
        type=FunctionType.ASYNC_METHOD,
        parameters=[],
        is_async=True
    )

    test_lines = test_generator._generate_method_test(cls, method)
    test_str = "\n".join(test_lines)

    assert "@pytest.mark.asyncio" in test_str
    assert "async def test_process(self, asyncworker_instance):" in test_str
    assert "result = await asyncworker_instance.process()" in test_str


def test_generate_test_end_to_end(test_generator, complex_class_code):
    """Test full test generation workflow end-to-end."""
    # Generate test code
    test_code = test_generator.generate_test(complex_class_code, framework="pytest")

    # Verify structure
    assert 'Generated test file' in test_code
    assert 'import pytest' in test_code
    assert 'from unittest.mock import' in test_code
    assert 'class TestUser:' in test_code
    assert '@pytest.fixture' in test_code

    # Verify methods are tested (but not __init__ since it's a dataclass)
    assert 'def test_is_adult' in test_code
    assert 'def test_from_dict' in test_code
    assert 'def test_validate_age' in test_code

    # Verify async support
    assert 'import asyncio' in test_code
    assert '@pytest.mark.asyncio' in test_code
    assert 'async def test_save' in test_code

    # Verify it's valid Python syntax
    compile(test_code, '<string>', 'exec')


def test_generate_test_file_path_in_docstring(test_generator, simple_python_code):
    """Test that file path is included in test docstring when provided."""
    analysis = test_generator.analyze_code(
        simple_python_code,
        file_path="/path/to/module.py"
    )

    test_code = test_generator._generate_pytest_tests(analysis)

    assert "Tests for: /path/to/module.py" in test_code


def test_private_methods_skipped(test_generator):
    """Test that private methods are not included in generated tests."""
    code = """
class MyClass:
    def public_method(self):
        pass

    def _private_method(self):
        pass

    def __very_private_method(self):
        pass
"""

    test_code = test_generator.generate_test(code, framework="pytest")

    # Public method should be tested
    assert "def test_public_method" in test_code

    # Private methods should not be tested
    assert "test__private_method" not in test_code
    assert "test___very_private_method" not in test_code


def test_varargs_parameters_skipped_in_calls(test_generator):
    """Test that *args and **kwargs are not passed in test calls."""
    code = """
def flexible_func(x, *args, **kwargs):
    return x
"""

    test_code = test_generator.generate_test(code, framework="pytest")

    # Should only pass x, not *args or **kwargs
    assert "result = flexible_func(x)" in test_code
    # Should not have parameters for *args and **kwargs
    assert "args = None" not in test_code


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================


def test_empty_code(test_generator):
    """Test analyzing empty code."""
    analysis = test_generator.analyze_code("")

    assert analysis.language == Language.PYTHON
    assert len(analysis.functions) == 0
    assert len(analysis.classes) == 0


def test_code_with_only_imports(test_generator):
    """Test analyzing code with only imports."""
    code = """
import os
import sys
from pathlib import Path
"""

    analysis = test_generator.analyze_code(code)

    assert len(analysis.imports) >= 2
    assert "os" in analysis.imports
    assert "sys" in analysis.imports


def test_nested_functions_extracted(test_generator):
    """Test that nested functions are currently extracted (implementation limitation)."""
    code = """
def outer():
    def inner():
        return "nested"
    return inner()
"""

    analysis = test_generator.analyze_code(code)

    # Currently extracts both outer and inner (implementation limitation)
    # Future enhancement: could filter out nested functions
    assert len(analysis.functions) >= 1
    function_names = [f.name for f in analysis.functions]
    assert "outer" in function_names


def test_nested_classes_extracted(test_generator):
    """Test that nested classes are currently extracted (implementation limitation)."""
    code = """
class Outer:
    class Inner:
        pass

    def method(self):
        pass
"""

    analysis = test_generator.analyze_code(code)

    # Currently extracts both Outer and Inner (implementation limitation)
    # Future enhancement: could filter out nested classes
    assert len(analysis.classes) >= 1
    class_names = [c.name for c in analysis.classes]
    assert "Outer" in class_names


def test_function_with_no_return_type(test_generator):
    """Test generating test for function without return type annotation."""
    code = """
def no_return_type():
    print("hello")
"""

    test_code = test_generator.generate_test(code, framework="pytest")

    # Should still generate test, with TODO comment
    assert "def test_no_return_type():" in test_code
    assert "# TODO: Add assertions" in test_code


def test_class_with_no_methods(test_generator):
    """Test analyzing class with no methods."""
    code = """
class EmptyClass:
    pass
"""

    analysis = test_generator.analyze_code(code)

    assert len(analysis.classes) == 1
    assert analysis.classes[0].name == "EmptyClass"
    assert len(analysis.classes[0].methods) == 0


def test_base_classes_extraction(test_generator):
    """Test extracting base classes from inheritance."""
    code = """
class Base1:
    pass

class Base2:
    pass

class Derived(Base1, Base2):
    pass
"""

    analysis = test_generator.analyze_code(code)

    derived = next(c for c in analysis.classes if c.name == "Derived")
    assert "Base1" in derived.base_classes
    assert "Base2" in derived.base_classes


def test_docstring_extraction(test_generator):
    """Test extracting function and class docstrings."""
    code = '''
def documented_function():
    """This is a docstring."""
    pass

class DocumentedClass:
    """This is a class docstring."""
    pass
'''

    analysis = test_generator.analyze_code(code)

    func = analysis.functions[0]
    assert func.docstring == "This is a docstring."

    cls = analysis.classes[0]
    assert cls.docstring == "This is a class docstring."
