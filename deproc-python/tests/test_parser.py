"""Tests for Python parser."""

import tempfile as tf

from deproc.core.context import Context
from deproc.plugins.python.parser import PythonSourceParser
from deproc.plugins.python.parser.models import (
    ComplexBinding,
    PythonConstant,
    SimpleBinding,
    VariableDeclaration,
)

parser = PythonSourceParser()
context = Context()


def _create_temp_file(content: str) -> str:
    """Helper to create a temporary file with given content."""
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".py") as tmp:
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

    def test_entities_have_source_id(self):
        """All entities with source_range get source_file_id set."""
        code = """
import os
from typing import List

class MyClass:
    def method(self) -> None:
        pass

def func():
    x = 1
"""
        temp_file = _create_temp_file(code)
        ctx = Context()
        source_file = parser.parse_file(temp_file, ctx)
        for entity in ctx.entity_registry.values():
            sr = getattr(entity, "source_range", None)
            if sr is not None:
                assert sr.source_id == source_file.id, (
                    f"{type(entity).__name__} missing source_id"
                )

    def test_source_id_on_control_flow_entities(self):
        """Control flow entities also get source_id set on their source_range."""
        code = """
if True:
    class X:
        pass
elif False:
    def y():
        pass
else:
    z = 1
"""
        temp_file = _create_temp_file(code)
        ctx = Context()
        source_file = parser.parse_file(temp_file, ctx)
        for entity in ctx.entity_registry.values():
            sr = getattr(entity, "source_range", None)
            if sr is not None:
                assert sr.source_id == source_file.id, (
                    f"{type(entity).__name__} missing source_id"
                )

    def test_parse_empty_code(self):
        """Handle empty code."""
        code = ""
        temp_file = _create_temp_file(code)
        ast = parser.parse_file(temp_file, context)
        assert ast is not None


class TestVariableExtraction:
    """Test variable declaration extraction with fqn and parent_id."""

    def _get_variable(self, code: str, index: int = 0):
        import tempfile as tf

        ctx = Context()
        with tf.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        source_file = parser.parse_file(tmp_path, ctx)
        var_id = source_file.variable_ids[index]
        return ctx.entity_registry.get(var_id), source_file

    def test_simple_assignment_fqn(self):
        var_decl, source_file = self._get_variable("x = 1")
        assert isinstance(var_decl, VariableDeclaration)
        assert var_decl.parent_id == source_file.id
        assert isinstance(var_decl.variable_binding, SimpleBinding)
        assert var_decl.variable_binding.name == "x"
        assert var_decl.variable_binding.fqn.endswith(".x")

    def test_annotated_assignment_fqn(self):
        var_decl, source_file = self._get_variable("x: int = 1")
        assert isinstance(var_decl, VariableDeclaration)
        assert var_decl.parent_id == source_file.id
        assert isinstance(var_decl.variable_binding, SimpleBinding)
        assert var_decl.variable_binding.name == "x"
        assert var_decl.variable_binding.fqn.endswith(".x")
        assert var_decl.type_annotation is not None

    def test_constant_detection(self):
        var_decl, _ = self._get_variable("FOO = 'bar'")
        assert isinstance(var_decl, PythonConstant)
        assert isinstance(var_decl.variable_binding, SimpleBinding)
        assert var_decl.variable_binding.fqn.endswith(".FOO")

    def test_tuple_unpacking(self):
        var_decl, source_file = self._get_variable("a, b = 1, 2")
        assert isinstance(var_decl, VariableDeclaration)
        assert var_decl.parent_id == source_file.id
        assert isinstance(var_decl.variable_binding, ComplexBinding)


class TestControlFlowImports:
    """Test imports inside control flow blocks get proper FQN and source_id."""

    def _find_import_aliases(self, ctx, source_file):
        aliases = []
        for entity in ctx.entity_registry.values():
            from deproc.plugins.python.parser.models import PythonImportAlias

            if isinstance(entity, PythonImportAlias):
                aliases.append(entity)
        return aliases

    def test_imports_in_if_elif_else_get_fqn(self):
        """IMPORT_ALIAS inside if/elif/else blocks has proper FQN (not None)."""
        code = """
import sys

if sys.platform == "win32":
    from .impl import WinHandler
elif sys.platform == "darwin":
    from .impl import MacHandler
else:
    from .impl import LinuxHandler
"""
        import tempfile as tf

        ctx = Context()
        with tf.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        parser.parse_file(tmp_path, ctx)

        for entity in ctx.entity_registry.values():
            from deproc.plugins.python.parser.models import PythonImportAlias

            if isinstance(entity, PythonImportAlias):
                assert entity.fqn is not None, (
                    f"IMPORT_ALIAS '{entity.name}' has fqn=None"
                )

    def test_import_aliases_in_if_branches_have_correct_fqn(self):
        """Each IMPORT_ALIAS in different if/elif/else branches gets its own correct FQN."""
        code = """
import sys

if sys.platform == "win32":
    from .platforms import Config
elif sys.platform == "darwin":
    from .platforms import Config
else:
    from .platforms import Config
"""
        import tempfile as tf

        ctx = Context()
        with tf.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        parser.parse_file(tmp_path, ctx)

        config_aliases = [
            e
            for e in self._find_import_aliases(ctx, None)
            if getattr(e, "name", "") == "Config"
        ]
        assert len(config_aliases) >= 1, "Expected at least one Config alias"
        for alias in config_aliases:
            assert alias.fqn is not None
            assert alias.fqn.endswith(".Config")

    def test_aliased_import_in_control_flow(self):
        """IMPORT_ALIAS with 'as' alias inside a control flow block gets FQN."""
        code = """
import sys

if sys.platform == "win32":
    from .backends import WinHandler as Handler
else:
    from .backends import LinuxHandler as Handler
"""
        import tempfile as tf

        ctx = Context()
        with tf.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        parser.parse_file(tmp_path, ctx)

        aliases = [
            e
            for e in ctx.entity_registry.values()
            if type(e).__name__ == "PythonImportAlias"
        ]
        for alias in aliases:
            if alias.name in ("WinHandler", "LinuxHandler"):
                assert alias.fqn is not None, f"alias {alias.name} fqn is None"
                assert alias.fqn.endswith(".Handler"), (
                    f"alias fqn {alias.fqn} should end with .Handler"
                )

    def test_source_id_on_imports_in_control_flow(self):
        """IMPORT_ALIAS and IMPORT_STATEMENT inside control flow blocks have source_id."""
        code = """
if True:
    import os
    from typing import List
elif False:
    from collections import defaultdict
else:
    from datetime import datetime
"""
        import tempfile as tf

        ctx = Context()
        with tf.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        source_file = parser.parse_file(tmp_path, ctx)
        for entity in ctx.entity_registry.values():
            sr = getattr(entity, "source_range", None)
            if sr is not None:
                assert sr.source_id == source_file.id, (
                    f"{type(entity).__name__} missing source_id"
                )

    def test_import_statements_in_try_except_get_fqn(self):
        """IMPORT_ALIAS inside try/except/finally blocks has proper FQN."""
        code = """
import sys

try:
    from .stable import ModuleA
except ImportError:
    from .fallback import ModuleB
else:
    from .alt import ModuleC
finally:
    from .cleanup import ModuleD
"""
        import tempfile as tf

        ctx = Context()
        with tf.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        parser.parse_file(tmp_path, ctx)

        for entity in ctx.entity_registry.values():
            from deproc.plugins.python.parser.models import PythonImportAlias

            if isinstance(entity, PythonImportAlias):
                assert entity.fqn is not None, (
                    f"IMPORT_ALIAS '{entity.name}' in try/except has fqn=None"
                )

    def test_nested_control_flow_imports(self):
        """Import inside nested control flow blocks (if inside if) get proper FQN."""
        code = """
import sys

if sys.platform == "linux":
    if sys.version_info >= (3, 11):
        from .impl import NewFeature
    else:
        from .impl import LegacyFeature
"""
        import tempfile as tf

        ctx = Context()
        with tf.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        parser.parse_file(tmp_path, ctx)

        aliases = [
            e
            for e in ctx.entity_registry.values()
            if type(e).__name__ == "PythonImportAlias"
            and "Feature" in str(getattr(e, "name", ""))
        ]
        for alias in aliases:
            assert alias.fqn is not None, (
                f"nested IMPORT_ALIAS '{alias.name}' has fqn=None"
            )
            assert alias.fqn.endswith(f".{alias.name}"), (
                f"alias fqn {alias.fqn} should end with .{alias.name}"
            )


class TestAllExports:
    def test_all_exports_list(self):
        code = '__all__ = ["Foo", "Bar"]\n'
        ctx = Context()
        with tf.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        sf = parser.parse_file(tmp_path, ctx)
        assert sf.all_exports == ["Foo", "Bar"]

    def test_all_exports_no_all(self):
        code = "x = 1\n"
        ctx = Context()
        with tf.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        sf = parser.parse_file(tmp_path, ctx)
        assert sf.all_exports is None

    def test_all_exports_tuple(self):
        code = '__all__ = ("Foo", "Bar")\n'
        ctx = Context()
        with tf.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        sf = parser.parse_file(tmp_path, ctx)
        assert sf.all_exports == ["Foo", "Bar"]

    def test_all_exports_with_imports(self):
        code = (
            'from .submod import helper_func\n__all__ = ["helper_func", "SomeClass"]\n'
        )
        ctx = Context()
        with tf.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        sf = parser.parse_file(tmp_path, ctx)
        assert sf.all_exports == ["helper_func", "SomeClass"]
