from deproc.core.scope import AnalysisScope, RootDescriptor


class TestAnalysisScope:
    def test_groups_roots_and_normalizes_values(self, tmp_path):
        scope = AnalysisScope(
            project_roots=[str(tmp_path / "project")],
            source_roots=[RootDescriptor(str(tmp_path / "src"), provenance="provider")],
            selected_languages=["Python"],
            selected_file_extensions=["py"],
            exclusions=[".venv"],
        )

        assert scope.project_roots[0].kind == "project"
        assert scope.source_roots[0].provenance == "provider"
        assert scope.selected_languages == {"python"}
        assert scope.selected_file_extensions == {".py"}
        assert scope.exclusions == {".venv"}

    def test_root_descriptor_is_immutable(self, tmp_path):
        root = RootDescriptor(str(tmp_path))

        assert root.path == str(tmp_path)
        assert root.kind == "project"
        assert root.provenance == "explicit"
