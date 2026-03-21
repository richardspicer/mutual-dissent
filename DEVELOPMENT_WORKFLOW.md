# DEVELOPMENT_WORKFLOW.md

## Purpose

This repository uses a **release-aligned workflow**.

The goal is to keep these aligned:

- the latest tagged release
- the code on `main`
- the version published to PyPI
- the user-facing documentation

A user cloning `main`, installing from PyPI, or following Mintlify docs should get a closely matching experience.

---

## Core policy

- `main` always reflects the latest released and tagged version.
- Do not merge unfinished or unreleased work into `main`.
- All active development happens on short-lived branches.
- Tag releases from `main`.
- Publish PyPI releases from the tagged `main` commit.
- Keep user-facing documentation on `main` aligned with released behavior.

---

## Branch strategy

### `main`

`main` is the stable release branch.

Use `main` for:
- the latest released code
- release version bumps
- changelog or release note updates
- documentation that describes released behavior

Do not use `main` for:
- day-to-day feature development
- exploratory work
- partially complete changes
- unreleased user-visible behavior

### `feature/*`

Use `feature/*` branches for new functionality.

Examples:
- `feature/model-matrix-expansion`
- `feature/finding-export-improvements`

Guidelines:
- branch from `main`
- keep scope focused
- merge only when ready for release

### `fix/*`

Use `fix/*` branches for bug fixes.

Examples:
- `fix/windows-path-resolution`
- `fix/report-rendering`

Guidelines:
- branch from `main`
- keep changes narrow
- merge only when verified and release-ready

### Optional `chore/*` and `docs/*`

These are optional for maintenance and documentation-only changes.

Examples:
- `chore/pre-commit-cleanup`
- `docs/install-clarification`

Use them only when they improve clarity.

---

## Standard development workflow

1. Start from `main`.
2. Create a short-lived branch for the task.
3. Make and verify the change on that branch.
4. Keep docs for unreleased behavior on that branch.
5. Merge to `main` only when the work is ready to become part of the next release.
6. Tag the release from `main`.
7. Publish PyPI from that tagged commit.

---

## Release discipline

Because `main` is release-aligned, merged-but-unreleased work should not live on `main`.

That means:
- keep work on its branch until it is ready
- do not use `main` as a general integration branch
- treat merging to `main` as a release-alignment step, not just a code-integration step

Before merging to `main`, ask:

> If a user installs from PyPI, reads Mintlify docs, and checks out `main`, will those three experiences match closely enough?

If the answer is no, do not merge yet.

---

## Documentation policy

Documentation on `main` should describe released behavior.

When a feature is not yet released:
- keep feature documentation on the feature branch
- do not merge user-facing docs for unreleased behavior into `main`

This prevents drift between:
- Mintlify documentation
- the GitHub repository
- `pip install` / `uv` installation behavior

---

## Release workflow

### Preconditions

Before cutting a release, confirm:

- all intended changes are merged and verified
- no unfinished or unreleased work is on `main`
- tests and required verification pass
- docs reflect released behavior
- version metadata is ready to bump

### Release steps

1. Review the intended release contents.
2. Update the package version.
3. Update changelog or release notes.
4. Update any user-facing docs needed for the release.
5. Run repository verification.
6. Merge release-ready work to `main`.
7. Create a version tag from the release commit on `main`.
8. Publish to PyPI from that tagged commit.
9. Verify the published version matches the tag and repo state.
10. Confirm Mintlify and repo docs match the released behavior.

---

## Verification

Run the repository verification before release:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/mutual_dissent/ && uv run pre-commit run --all-files
```

Also run relevant tests for the release scope.

At minimum, smoke test the CLI:

```bash
mutual-dissent --help
```

---

## Tagging

* Tag releases from `main`
* Use consistent semantic version tags such as:

  * `v0.1.0`
  * `v0.1.1`

The tag should point to the exact commit used for the PyPI release.

---

## Publishing

* Publish PyPI releases from the tagged commit
* Do not publish from a dirty working tree
* Do not publish from an untagged commit
* Do not publish from a non-release-aligned branch

---

## Hotfix workflow

For an urgent patch release:

1. Branch from `main` using `fix/*`.
2. Implement and verify the fix.
3. Merge back to `main`.
4. Tag a patch release.
5. Publish from the tagged commit.
6. Confirm docs still match behavior.

---

## Practical rule of thumb

A release is only complete when all of these are true:

* the code is on `main`
* the version is tagged
* PyPI matches the tag
* docs match the release

---

## Summary

For this repository:

* use `main` as the stable release branch
* use short-lived `feature/*` and `fix/*` branches for all active work
* merge to `main` only when ready for release
* tag and publish from `main`
* keep docs aligned with released behavior
