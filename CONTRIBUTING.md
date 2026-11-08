# Contributing to deproc

deproc is the language-neutral source analysis core and its language plugins. [deputy](https://github.com/gurveervirk/deputy) is its main consumer. The README describes the current scope and contracts.

## Development environment

Python 3.12 or newer and [uv](https://docs.astral.sh/uv/) are required. CI runs the tests on Python 3.12 and 3.13.

```bash
git clone https://github.com/gurveervirk/deproc
cd deproc
uv sync
```

`uv sync` installs the workspace: `deproc-core`, `deproc-python`, `deproc-java`, `deproc-utils-tree-sitter`, and `deproc-utils-python-env`. `.pre-commit-config.yaml` defines ruff, ruff-format, and basedpyright hooks for a pre-commit runner you install yourself.

## Branches

| Branch | Purpose |
| --- | --- |
| `main` | Reviewed and accepted work. Releases are tagged from here. Never commit or push to it directly. |
| `integration` | Advancing frontier that may contain work not yet approved. Used to test unapproved work together. May not exist yet. |
| `<type>/<slug>` | One task per branch, for example `feat/root-aware-semantic-identity`, `fix/analysis-scope-contract`, `docs/...`, `ci/...`, `refactor/...`, `test/...`, `chore/...`. |

### Choosing a base

- **Independent work:** branch from `main` and open the pull request against `main`.
- **Work that needs an unmerged branch:** branch from that prerequisite branch and open the pull request against it (a stacked pull request). Name the prerequisite under *Related Work* in the pull request. When the prerequisite merges, retarget the pull request to `main`.
- **Work that needs unapproved frontier work in `integration`:** branch from `integration`. That branch stays integration-only until its prerequisites are approved, then it is moved onto `main` before a pull request to `main` is opened.
- Stack only on `feat/*`, `fix/*`, or `integration` bases. `lint` and `pytests` run for pull requests against those bases and `main`.

### Promoting reviewed work

A reviewed task branch is merged to `main` through its own pull request. `integration` is then brought up to date by merging `main` into it. `integration` is never merged into `main` wholesale: it contains other branches' unreviewed commits, and merging it would land them without their own review.

Task branches may be merged into `integration` so unapproved work can be tested together. Do not rewrite the history of `main`, `integration`, or any pushed branch that others build on. Rebuilding `integration` from `main` requires the owner's approval.

Code Provenance runs only for pull requests against `main`, and skips draft pull requests. Open the pull request as a draft while iterating and mark it ready for review when it is final; that starts the scan. Pushes after that re-scan, and a newer push cancels a scan still in progress. The scan is not a required check, so a failure from an unavailable scanner (for example a rate limit) does not block the merge. It does block a release: `publish.yml` runs a full scan before publishing. Rerun a failed scan with `gh run rerun <run-id> --failed`, or start a full scan by hand with the `workflow_dispatch` trigger.

## Commits

Use a [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) tag on a single-line message, with an optional scope:

```
fix(scope): harden multi-root semantic identity
feat: add root-aware semantic identity contract
```

Types in use: `feat`, `fix`, `docs`, `test`, `ci`, `refactor`, `build`, `chore`. Pull request titles use the same form, in lowercase and without a trailing period.

## Local validation

These are the commands CI runs (`.github/workflows/lint.yml`, `.github/workflows/pytest.yml`):

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
uv run pytest
```

Run a single package with `uv run pytest deproc-core/tests/` (or `deproc-python/tests/`, `deproc-java/tests/`). CI also collects coverage with `uv run pytest --cov --cov-report=xml`.

## Testing expectations

- Fix a bug with a regression test that fails without the fix.
- Cover new behaviour and its meaningful edge cases.
- Keep analysis deterministic: entity IDs and ordering must be stable across runs.
- Do not weaken or skip a test to make a check pass.

## Pull requests

- Open pull requests with the repository template and keep one purpose per pull request.
- Report each check as passed, failed, skipped, or not run, with the command.
- Keep the description in step with the final diff.
- Call out public API, persistence, serialization, dependency, configuration, and versioning impact, because deputy consumes them.
- Do not put private planning information in pull request text.
- Wait for the required checks (`gh pr checks --watch --fail-fast`) before asking for review.

## Dependencies and compatibility

- `deproc-python` and `deproc-java` require `deproc-core` at a minimum version. Raise the lower bound only when the new code needs the new behaviour.
- Treat public models, resolver and linker interfaces, entity IDs, and anything deputy stores as contracts. Changing them is a compatibility change and needs a plan for deputy.
- Dependency updates arrive through Dependabot (`uv`, weekly). Commit lockfile changes with `uv lock`.

## Releases and versioning

Each package is versioned and released separately. Bump `version` in `<package>/pyproject.toml`, then push a tag `<package>-v<version>`. `publish.yml` checks the tag against the package metadata, runs the tests, and publishes. Follow [.github/RELEASE_CHECKLIST.md](.github/RELEASE_CHECKLIST.md).

## Working across deproc and deputy

deproc is the source-analysis layer and deputy depends on it.

- Open the deproc pull request first, then the deputy pull request.
- Add the deproc pull request URL to the deputy pull request as a separate comment.
- State the deproc ref used for integration testing in both pull requests.
- deputy normally tests against deproc `main`. To test a deputy branch against a deproc branch, set `.github/deproc-ref` in the deputy branch or run `lint`/`pytests` manually with the `deproc_ref` input. The file must be `main` again before the deputy pull request merges.
- Merge deproc first, and publish it to PyPI before releasing a deputy version that requires it.

## Issues and decisions

Use the issue templates for bugs, feature requests, and engineering tasks. Architecture decision records follow [.github/adr/0000-template.md](.github/adr/0000-template.md).
