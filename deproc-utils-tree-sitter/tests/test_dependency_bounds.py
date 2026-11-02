import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ("deproc-utils-tree-sitter", "deproc-python", "deproc-java")


def _tree_sitter_requirement(package: str) -> Requirement:
    metadata = tomllib.loads((REPO_ROOT / package / "pyproject.toml").read_text())
    requirements = [Requirement(item) for item in metadata["project"]["dependencies"]]
    (requirement,) = [item for item in requirements if item.name == "tree-sitter"]
    return requirement


@pytest.mark.parametrize("package", PACKAGES)
def test_tree_sitter_is_bounded_below_the_crashing_release(package):
    requirement = _tree_sitter_requirement(package)

    assert not requirement.specifier.contains("0.26.0")
    assert requirement.specifier.contains("0.25.2")
