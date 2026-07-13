from deproc.core.context import Context
from deproc.core.discovery import find_source_files
from pathlib import Path

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
