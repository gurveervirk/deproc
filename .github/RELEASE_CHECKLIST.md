# Release checklist

Releases are per package. Pushing a tag named `<package>-v<version>` runs `.github/workflows/publish.yml`, which validates the tag, runs the tests, runs a full Code Provenance scan, and publishes through PyPI trusted publishing. Publishing waits for the scan; if the scanner is rate-limited, rerun the failed job once the limit lifts. Releases are cut from `main` by the owner.

Packages: `deproc-core`, `deproc-python`, `deproc-java`, `deproc-utils-tree-sitter`, `deproc-utils-python-env`.

## Before tagging

- [ ] Release PR is merged to `main`; the release is cut from the merged commit
- [ ] `version` in `<package>/pyproject.toml` is bumped, and follows the compatibility impact of the changes since the last tag
- [ ] Every package that depends on a bumped package has its lower bound updated in its own `pyproject.toml` (for example `deproc-core>=...` in `deproc-python` and `deproc-java`) when it needs the new behaviour
- [ ] `uv.lock` is regenerated with `uv lock` and committed
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run basedpyright` and `uv run pytest` pass locally
- [ ] CI is green on the release commit (`lint`, `pytests`, and Code Provenance)
- [ ] Release notes are drafted: user-visible changes, API or serialization changes, and migration steps. The repository has no changelog file
- [ ] Package README renders correctly where it is used as the PyPI description

## Downstream compatibility

- [ ] deputy tests pass against the release commit (`workflow_dispatch` with `deproc_ref` on deputy's `lint` and `pytests`, or a local deputy checkout with `../deproc` on the release commit)
- [ ] If the release changes API or stored data that deputy relies on, the deputy PR and its dependency lower bounds are prepared and linked
- [ ] Order is deproc first: deputy's published wheel resolves deproc packages from PyPI, so the new versions must be published before a deputy release that requires them

## Tag and publish

- [ ] Tag the merged `main` commit as `<package>-v<version>`; the version must equal `<package>/pyproject.toml`, or the workflow fails
- [ ] Push the tag; `publish.yml` runs `extract-package`, then `test` and `provenance`, then `publish` in the `pypi-<package>` environment
- [ ] Confirm the new version is visible on PyPI and installs in a clean environment
- [ ] Publish the GitHub release for the tag with the release notes

## After release

- [ ] Open the deputy follow-up PR if its dependency lower bounds or `uv.lock` need to move
- [ ] If an `integration` branch exists, bring it up to date with `main`
