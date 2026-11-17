import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = sorted(path.parent.name for path in ROOT.glob("deproc-*/pyproject.toml"))


def test_every_package_is_checked():
    assert {"deproc-core", "deproc-python", "deproc-java"} <= set(PACKAGES)


@pytest.mark.parametrize("package", PACKAGES)
def test_package_publishes_its_readme_as_the_description(package):
    project = tomllib.loads((ROOT / package / "pyproject.toml").read_text())["project"]

    assert project.get("readme") == "README.md"
    readme = ROOT / package / "README.md"
    assert readme.is_file()
    assert readme.read_text(encoding="utf-8").startswith(f"# {package}\n")
