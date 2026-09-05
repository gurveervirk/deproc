from pathlib import Path

from deproc.core.context import Context
from deproc.core.discovery import discover_source_files, find_source_files
from deproc.core.scope import AnalysisScope


class TestFindSourceFiles:
    def test_skips_dirs_in_skip_paths(self, tmp_path):
        (tmp_path / "a.py").write_text("")
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "b.py").write_text("")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "c.py").write_text("")

        ctx = Context(base_path=str(tmp_path))
        ctx.set_language("python", [".py"])
        ctx.set_skip_paths({".venv", ".git"})

        files = find_source_files(ctx)
        paths = {Path(f).name for f in files}
        assert paths == {"a.py"}

    def test_empty_skip_paths_finds_all(self, tmp_path):
        (tmp_path / "a.py").write_text("")
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "b.py").write_text("")

        ctx = Context(base_path=str(tmp_path))
        ctx.set_language("python", [".py"])

        files = find_source_files(ctx)
        assert len(files) == 2

    def test_glob_pattern_in_skip_paths(self, tmp_path):
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "b.py").write_text("")
        (tmp_path / ".venv2").mkdir()
        (tmp_path / ".venv2" / "c.py").write_text("")
        (tmp_path / "a.py").write_text("")

        ctx = Context(base_path=str(tmp_path))
        ctx.set_language("python", [".py"])
        ctx.set_skip_paths({".venv*"})

        files = find_source_files(ctx)
        paths = {Path(f).name for f in files}
        assert paths == {"a.py"}

    def test_glob_pattern_does_not_affect_non_matching(self, tmp_path):
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "b.py").write_text("")
        (tmp_path / "vendor").mkdir()
        (tmp_path / "vendor" / "a.py").write_text("")

        ctx = Context(base_path=str(tmp_path))
        ctx.set_language("python", [".py"])
        ctx.set_skip_paths({"vendor*"})

        files = find_source_files(ctx)
        paths = {Path(f).name for f in files}
        assert paths == {"b.py"}

    def test_discovers_multiple_roots_deterministically_with_provenance(self, tmp_path):
        source_root = tmp_path / "src"
        dependency_root = tmp_path / "dependency"
        source_root.mkdir()
        dependency_root.mkdir()
        (source_root / "z.py").write_text("")
        (dependency_root / "a.py").write_text("")

        scope = AnalysisScope(
            source_roots=[str(source_root)],
            dependency_roots=[str(dependency_root)],
            selected_file_extensions=[".py"],
        )
        files = discover_source_files(Context(scope=scope))

        assert [Path(item.path).name for item in files] == ["a.py", "z.py"]
        assert [item.root_kind for item in files] == ["dependency", "source"]
        assert all(item.provenance == "explicit" for item in files)

    def test_scope_exclusions_apply_to_all_roots(self, tmp_path):
        first = tmp_path / "first"
        second = tmp_path / "second"
        first.mkdir()
        second.mkdir()
        (first / "keep.py").write_text("")
        (second / "skip.py").write_text("")

        scope = AnalysisScope(
            roots=[str(first), str(second)],
            selected_file_extensions=[".py"],
            exclusions=["skip.py"],
        )

        assert [
            Path(path).name for path in find_source_files(Context(scope=scope))
        ] == ["keep.py"]
