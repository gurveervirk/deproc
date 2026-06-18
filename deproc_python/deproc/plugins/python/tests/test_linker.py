"""Tests for Python linker."""

from unittest.mock import MagicMock
from deproc.core.context import Context
from deproc.plugins.python.linker.models import PythonModule

class TestLinker:
    """Test Python module linking."""

    def setup_method(self):
        """Set up mock context."""
        self.context = MagicMock(spec=Context)
        self.context.entity_registry = {}

    def test_create_module(self):
        """Create Python module."""
        module = PythonModule(
            id="mod_1",
            fqn="mypackage.mymodule",
            path="/path/to/mymodule.py",
            parent_id=None,
            docstring_range=None,
            source=""
        )
        assert module.fqn == "mypackage.mymodule"
        assert module.path == "/path/to/mymodule.py"

    def test_module_hierarchy(self):
        """Link modules in hierarchy."""
        parent = PythonModule(
            id="pkg_1",
            fqn="mypackage",
            path="/path/to",
            parent_id=None,
            docstring_range=None,
            source=""
        )
        child = PythonModule(
            id="mod_1",
            fqn="mypackage.mymodule",
            path="/path/to/mymodule.py",
            parent_id="pkg_1",
            docstring_range=None,
            source=""
        )
        assert child.parent_id == "pkg_1"
        assert child.fqn.startswith(parent.fqn)
