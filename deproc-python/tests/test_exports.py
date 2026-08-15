from deproc.core.runtime.registries.entity import EntityRegistry
from deproc.plugins.python.parser.models import PythonModule
from deproc.plugins.python.utils.exports import build_module_exports


def _make_module(fqn, all_exports=None):
    m = PythonModule(
        fqn=fqn,
        path=f"{fqn.replace('.', '/')}.py",
        docstring_range=None,
        source="# placeholder",
    )
    m.all_exports = all_exports
    return m


class TestBuildModuleExports:
    def test_with_all_exports(self):
        reg = EntityRegistry()
        m = _make_module("pkg.mod", ["foo", "bar"])
        reg.add(m)
        result = build_module_exports(reg)
        assert result == {"pkg.mod": {"foo", "bar"}}

    def test_without_all_exports(self):
        reg = EntityRegistry()
        m = _make_module("pkg.mod")
        reg.add(m)
        result = build_module_exports(reg)
        assert result == {}

    def test_ignores_non_module_entities(self):
        reg = EntityRegistry()
        func = PythonModule(
            fqn="pkg.func", path="pkg/func.py", docstring_range=None, source="# x"
        )
        reg.add(func)
        result = build_module_exports(reg)
        assert result == {}
