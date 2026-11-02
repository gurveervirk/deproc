# deproc agent instructions

deproc is the language-neutral source-analysis layer. deputy (`../deputy`) is its consumer. Humans follow `CONTRIBUTING.md`; this file adds the rules agents must follow. Owner-specific rules live in `AGENTS.local.md` when present (not tracked).

## Style and sequencing
- Do not add code comments unless the owner asks for them.
- Work linearly: inspect, implement, validate, in that order, to keep context and traceability.
- Follow existing naming, typing, and formatting. Ruff and basedpyright settings are in `pyproject.toml`.

## Git and branch safety
- Never commit or push to `main`. Work on a dedicated `<type>/<slug>` branch (`feat/`, `fix/`, `docs/`, `ci/`, `refactor/`, `test/`, `chore/`).
- Identify the intended base branch before starting; see "Choosing a base" in `CONTRIBUTING.md`.
- Do not merge, close, or delete branches or pull requests without explicit authorization.
- Never discard unrelated working-tree changes. Do not rewrite shared branch history.
- Commit messages are a single line starting with a Conventional Commits tag (`feat:`, `fix(scope):`). No body.
- Do not commit `.gitignore` changes unless asked.
- Request the owner's approval before pushing. The owner reviews and merges pull requests.

## Engineering discipline
- Read the existing implementation and the relevant skill before changing anything.
- Keep changes minimal and cohesive; no unrelated refactoring.
- Add a regression test for each bug fix, and tests for new behaviour and meaningful edge cases.
- Update documentation when public behaviour or interfaces change.
- Public models, resolver and linker interfaces, entity IDs, and serialized forms are consumed by deputy. Check downstream impact before changing them.

## Validation
- Run the relevant commands from `CONTRIBUTING.md` (`ruff check`, `ruff format --check`, `basedpyright`, `pytest`).
- Report exactly what ran and the result. State skipped or unavailable checks. Never claim a check passed that was not run.
- Do not suppress failures to make CI green.

## Pull requests
- Use `.github/pull_request_template.md`; keep the description in step with the final diff.
- Title format: `<type>[scope]: <imperative description>`, lowercase type, no trailing period.
- State compatibility and dependency impact, prerequisite PRs, and branch dependencies. Give a specific review focus.
- After opening, wait for checks with `gh pr checks --watch --fail-fast`; hand off only when green, or report the failing gate.
- Keep titles, descriptions, and comments free of private planning information.

## Cross-repository work
- Make deputy's dependency on deproc API explicit, and name the deproc ref used for integration testing.
- Do not silently change the contract deputy expects.
- Open the deproc PR first, then the deputy PR, then comment the deproc PR URL on the deputy PR. Validate both sides when relevant.

## Skills
- `.agents/skills/deproc`: using the library for analysis.
- `.agents/skills/deproc-core`: core protocols and writing language plugins.
- `.agents/skills/deproc-python`: the Python plugin.

## Branch model and workflow standards (set up 2026-11-01)
- `main` is reviewed work; `integration` is the unapproved agent frontier and is never merged to `main` wholesale; task branches are `<type>/<slug>`.
- `lint` and `pytests` also run on `integration` and on PRs against `integration`, `feat/**`, `fix/**`. Code Provenance remains `main`-only.
- Contribution files: `CONTRIBUTING.md`, `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/`, `.github/RELEASE_CHECKLIST.md`, `.github/adr/0000-template.md`.
- `CLAUDE.md` imports `AGENTS.md` and `AGENTS.local.md`.
- The same set exists in deputy; keep shared conventions identical in both.
