"""Sample Python file for testing code quality analysis."""


def simple_function(x, y):
    """A simple function with low complexity."""
    return x + y


def moderate_complexity(value):
    """A function with moderate complexity."""
    if value < 0:
        return -value
    elif value == 0:
        return 0
    elif value < 10:
        return value * 2
    elif value < 100:
        return value * 3
    else:
        return value * 4


def high_complexity_function(data):
    """A function with higher cyclomatic complexity."""
    result = 0

    for item in data:
        if isinstance(item, int):
            if item > 0:
                if item % 2 == 0:
                    result += item * 2
                else:
                    result += item * 3
            elif item < 0:
                if item % 2 == 0:
                    result -= item
                else:
                    result -= item * 2
        elif isinstance(item, str):
            try:
                num = int(item)
                if num > 100:
                    result += num
                else:
                    result += num // 2
            except ValueError:
                pass
        elif isinstance(item, list):
            for sub_item in item:
                if sub_item:
                    result += 1

    return result


class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.memory = 0

    def add(self, x, y):
        """Add two numbers."""
        return x + y

    def subtract(self, x, y):
        """Subtract two numbers."""
        return x - y

    def multiply(self, x, y):
        """Multiply two numbers."""
        return x * y

    def divide(self, x, y):
        """Divide two numbers."""
        if y == 0:
            raise ValueError("Cannot divide by zero")
        return x / y
