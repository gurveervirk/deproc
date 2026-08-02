import pytest
from deproc.plugins.python.inheritance import c3_merge, compute_mro_from_bases


class TestC3Merge:
    def test_simple_merge(self):
        assert c3_merge([["B", "O"], ["C", "O"], ["B", "C"]]) == ["B", "C", "O"]

    def test_inconsistent_hierarchy_raises(self):
        with pytest.raises(ValueError):
            c3_merge([["X", "O"], ["Y", "O"], ["Y", "X"], ["X", "Y"]])

    def test_empty_lists(self):
        assert c3_merge([]) == []

    def test_single_list(self):
        assert c3_merge([["A", "B", "C"]]) == ["A", "B", "C"]


class TestComputeMroFromBases:
    def test_single_inheritance(self):
        result = compute_mro_from_bases("Child", {"Base": ["Base"]}, ["Base"])
        assert result == ["Child", "Base"]

    def test_diamond(self):
        base_mros = {"Base": ["Base", "object"], "Mixin": ["Mixin", "object"]}
        base_fqns = ["Base", "Mixin"]
        result = compute_mro_from_bases("Child", base_mros, base_fqns)
        assert result is not None
        assert result[0] == "Child"
        assert result.index("Base") < result.index("Mixin")
        assert "object" in result

    def test_unresolved_base_returns_none(self):
        result = compute_mro_from_bases("Child", {"Base": None}, ["Base"])
        assert result is None

    def test_no_bases(self):
        result = compute_mro_from_bases("Standalone", {}, [])
        assert result == ["Standalone"]

    def test_inconsistent_returns_none(self):
        result = compute_mro_from_bases(
            "Child",
            {"A": ["A", "O"], "B": ["B", "O"]},
            ["A", "B", "O"],
        )
        assert result is None
