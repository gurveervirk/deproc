"""Tests for Python linker."""

from pathlib import Path
from unittest.mock import MagicMock
from deproc.core.context import Context
from deproc.core.runtime import EntityRegistry
from deproc.plugins.python.linker.main import PythonLinker
from deproc.plugins.python.parser.models import PythonModule

def _write_file(path: Path, content: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path

def _make_context(base_path: str, skip_paths: set[str] | None = None) -> Context:
    ctx = Context(base_path=base_path)
    ctx.entity_registry = EntityRegistry()
    if skip_paths:
        ctx.set_skip_paths(skip_paths)
    return ctx

def _registry_fqns(registry: EntityRegistry) -> set[str]:
    return {e.fqn for e in registry.values() if hasattr(e, "fqn")}

class TestLinker:
    """Test Python module linking."""

    def setup_method(self):
        """Set up mock context."""
        self.context = MagicMock(spec=Context)
        self.context.entity_registry = {}
        self.linker = PythonLinker()

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

    def test_skip_patterns_excludes_top_level_dirs(self, tmp_path: Path):
        """Top-level directories matching skip patterns are excluded."""
        _write_file(tmp_path / "mypkg" / "__init__.py")
        _write_file(tmp_path / "mypkg" / "mod.py")
        _write_file(tmp_path / "node_modules" / "dep.js")

        ctx = _make_context(str(tmp_path), {"node_modules"})
        result = self.linker.link_files([], ctx)

        names = {n.fqn for n in result}
        assert "mypkg" in names
        assert "node_modules" not in names

    def test_skip_patterns_glob_matches_suffix(self, tmp_path: Path):
        """Glob patterns like *.dist-info match directory suffix."""
        _write_file(tmp_path / "mypkg" / "__init__.py")
        _write_file(tmp_path / "mypkg-1.0.0.dist-info" / "METADATA")

        ctx = _make_context(str(tmp_path), {"*.dist-info"})
        result = self.linker.link_files([], ctx)

        names = {n.fqn for n in result}
        assert "mypkg" in names
        assert "mypkg-1.0.0.dist-info" not in names

    def test_skip_patterns_excludes_nested_dirs(self, tmp_path: Path):
        """Nested directories matching skip patterns are excluded from entity registry."""
        _write_file(tmp_path / "mypkg" / "__init__.py")
        _write_file(tmp_path / "mypkg" / "subpkg" / "__init__.py")

        ctx = _make_context(str(tmp_path), {"__pycache__"})
        result = self.linker.link_files([], ctx)

        top = {n.fqn for n in result}
        assert "mypkg" in top

        fqns = _registry_fqns(ctx.entity_registry)
        assert "mypkg" in fqns
        assert "mypkg.subpkg" in fqns
        assert "mypkg.__pycache__" not in fqns

    def test_skip_patterns_glob_applies_in_subdirectories(self, tmp_path: Path):
        """Glob patterns correctly filter subdirectories during recursive traversal."""
        _write_file(tmp_path / "pkg" / "__init__.py")
        _write_file(tmp_path / "pkg" / "build" / "helper.py")
        _write_file(tmp_path / "pkg" / "build.dist-info" / "METADATA")

        ctx = _make_context(str(tmp_path), {"*.dist-info"})
        result = self.linker.link_files([], ctx)

        fqns = _registry_fqns(ctx.entity_registry)
        assert "pkg" in fqns
        assert "pkg.build" in fqns
        assert "pkg.build.dist-info" not in fqns

    def test_skip_paths_empty_set_only_skips_pycache(self, tmp_path: Path):
        """Empty skip_paths still excludes __pycache__ (hardcoded)."""
        _write_file(tmp_path / "mypkg" / "__init__.py")
        _write_file(tmp_path / "__pycache__" / "cache.pyc")

        ctx = _make_context(str(tmp_path), set())
        result = self.linker.link_files([], ctx)

        names = {n.fqn for n in result}
        assert "mypkg" in names
        assert "__pycache__" not in names

    def test_skip_patterns_with_linked_modules(self, tmp_path: Path):
        """Skip patterns work correctly when linking actual module nodes."""
        _write_file(tmp_path / "mypkg" / "__init__.py", "from . import sub\n")
        _write_file(tmp_path / "mypkg" / "sub.py", "x = 1\n")

        init_mod = PythonModule(
            id="mod_init",
            fqn="mypkg",
            path="mypkg/__init__.py",
            parent_id=None,
            docstring_range=None,
            source="from . import sub",
        )
        sub_mod = PythonModule(
            id="mod_sub",
            fqn="mypkg.sub",
            path="mypkg/sub.py",
            parent_id=None,
            docstring_range=None,
            source="x = 1",
        )

        ctx = _make_context(str(tmp_path), {"node_modules"})
        result = self.linker.link_files([init_mod, sub_mod], ctx)

        top = {n.fqn for n in result}
        assert "mypkg" in top
        assert sub_mod.parent_id is not None, "sub module should have parent_id set"

        pkg = ctx.entity_registry.get(sub_mod.parent_id)
        assert pkg is not None
        assert sub_mod.id in pkg.submodule_ids

    def test_skip_patterns_multiple_patterns(self, tmp_path: Path):
        """Multiple skip patterns are all applied."""
        _write_file(tmp_path / "src" / "app" / "__init__.py")
        _write_file(tmp_path / "build" / "temp.txt")
        _write_file(tmp_path / "dist" / "package.tar.gz")
        _write_file(tmp_path / "node_modules" / "dep.js")
        _write_file(tmp_path / "src.egg-info" / "PKG-INFO")

        ctx = _make_context(str(tmp_path), {"*.egg-info", "build", "dist", "node_modules"})
        result = self.linker.link_files([], ctx)

        fqns = _registry_fqns(ctx.entity_registry)
        assert "src" in fqns
        assert "src.app" in fqns
        assert "build" not in fqns
        assert "dist" not in fqns
        assert "node_modules" not in fqns
        assert "src.egg-info" not in fqns
