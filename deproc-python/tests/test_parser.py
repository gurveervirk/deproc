"""Tests for Python parser."""

from deproc.plugins.python.parser import PythonSourceParser
from deproc.core.context import Context

parser = PythonSourceParser()
context = Context()

def _create_temp_file(content: str) -> str:
    """Helper to create a temporary file with given content."""
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.py') as tmp:
        tmp.write(content)
        return tmp.name

class TestParser:
    """Test Python source parsing."""

    def test_parse_simple_function(self):
        """Parse simple function definition."""
        code = """
def hello(name: str) -> str:
    return f"Hello {name}"
"""
        temp_file = _create_temp_file(code)
        ast = parser.parse_file(temp_file, context)
        assert ast is not None

    def test_parse_class(self):
        """Parse class definition."""
        code = """
class MyClass:
    def __init__(self):
        pass
"""
        temp_file = _create_temp_file(code)
        ast = parser.parse_file(temp_file, context)
        assert ast is not None

    def test_parse_imports(self):
        """Parse import statements."""
        code = """
import os
from typing import List
from . import local_module
"""
        temp_file = _create_temp_file(code)
        ast = parser.parse_file(temp_file, context)
        assert ast is not None

    def test_parse_empty_code(self):
        """Handle empty code."""
        code = ""
        temp_file = _create_temp_file(code)
        ast = parser.parse_file(temp_file, context)
        assert ast is not None
