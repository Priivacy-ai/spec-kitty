---
work_package_id: WPB1
title: Add a CI workflow for the linter
---

## Objective

Add a GitHub Actions workflow that runs ruff and mypy on pull requests.

## Acceptance Criteria

- A new `.github/workflows/lint.yml` exists and is valid YAML (parseable in the
  diff).
- The workflow file references the pinned ruff and mypy versions from
  `pyproject.toml`.
- Running `ruff check .` and `mypy src/` locally passes — the completion is
  observable in this WP's own diff, not after any merge into CI.
