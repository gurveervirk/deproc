import os
import tempfile
from unittest.mock import patch
from deproc.utils.python_env.detect import detect_venv, parse_pyvenv_cfg, _is_venv
from deproc.utils.python_env.discovery import (
    find_site_packages,
    list_installed_packages,
    _parse_metadata,
    _parse_top_level,
)

class TestDetectVenv:
    def test_detect_venv_no_venv(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {}, clear=True):
                result = detect_venv(tmp, {})
                assert result is None

    def test_detect_venv_from_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv_dir = os.path.join(tmp, ".venv")
            os.mkdir(venv_dir)
            open(os.path.join(venv_dir, "pyvenv.cfg"), "w").close()
            result = detect_venv(tmp, {"venv_path": venv_dir})
            assert result == os.path.abspath(venv_dir)

    def test_detect_venv_base_path_convention(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv_dir = os.path.join(tmp, ".venv")
            os.mkdir(venv_dir)
            open(os.path.join(venv_dir, "pyvenv.cfg"), "w").close()
            with patch.dict(os.environ, {}, clear=True):
                result = detect_venv(tmp, {})
                assert result == os.path.abspath(venv_dir)

    def test_is_venv_with_cfg(self):
        with tempfile.TemporaryDirectory() as tmp:
            assert not _is_venv(tmp)
            open(os.path.join(tmp, "pyvenv.cfg"), "w").close()
            assert _is_venv(tmp)

    def test_parse_pyvenv_cfg(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "pyvenv.cfg")
            with open(cfg_path, "w") as f:
                f.write("home = /usr/bin\nversion = 3.12\ninclude-system-site-packages = false\n")
            result = parse_pyvenv_cfg(tmp)
            assert result["home"] == "/usr/bin"
            assert result["version"] == "3.12"
            assert result["include-system-site-packages"] == "false"

    def test_parse_pyvenv_cfg_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = parse_pyvenv_cfg(tmp)
            assert result == {}

class TestDiscovery:
    def test_find_site_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib_python = os.path.join(tmp, "lib", "python3.12", "site-packages")
            os.makedirs(lib_python)
            result = find_site_packages(tmp)
            assert result == os.path.abspath(lib_python)

    def test_find_site_packages_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = find_site_packages(tmp)
            assert result is None

    def test_parse_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta_path = os.path.join(tmp, "METADATA")
            with open(meta_path, "w") as f:
                f.write("Name: requests\nVersion: 2.31.0\nSummary: HTTP library\n\n")
            result = _parse_metadata(meta_path)
            assert result["Name"] == "requests"
            assert result["Version"] == "2.31.0"

    def test_parse_metadata_missing(self):
        result = _parse_metadata("/nonexistent")
        assert result == {}

    def test_parse_top_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            tl_path = os.path.join(tmp, "top_level.txt")
            with open(tl_path, "w") as f:
                f.write("requests\nrequests.models\n")
            result = _parse_top_level(tl_path)
            assert result == ["requests", "requests.models"]

    def test_parse_top_level_missing(self):
        result = _parse_top_level("/nonexistent")
        assert result == []

    def test_list_installed_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            dist_info = os.path.join(tmp, "requests-2.31.0.dist-info")
            os.mkdir(dist_info)
            with open(os.path.join(dist_info, "METADATA"), "w") as f:
                f.write("Name: requests\nVersion: 2.31.0\n\n")
            with open(os.path.join(dist_info, "top_level.txt"), "w") as f:
                f.write("requests\n")
            results = list_installed_packages(tmp)
            assert len(results) == 1
            assert results[0].name == "requests"
            assert results[0].version == "2.31.0"
            assert results[0].top_level_modules == ["requests"]
            assert results[0].editable_origin is None
