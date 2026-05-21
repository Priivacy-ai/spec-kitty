---
work_package_id: WP13
title: Freshness orchestrator + tests + CI wiring
dependencies:
- WP04
- WP06
requirement_refs:
- FR-008
- FR-020
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T040
- T041
- T042
agent: "claude:opus-4-7:python-pedro:implementer"
shell_pid: "12277"
history:
- actor: planner
  at: '2026-05-21T06:52:04Z'
  action: wp_authored
  notes: Initial authorship by tasks phase.
agent_profile: python-pedro
authoritative_surface: scripts/docs/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- scripts/docs/check_docs_freshness.py
- tests/docs/test_check_docs_freshness.py
- .github/workflows/docs-freshness.yml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Implement the orchestrator script that runs every docs-freshness sub-check and produces a single JSON report. Add pytest coverage and a CI workflow step.

## Context

- Contract: [`contracts/check_docs_freshness.md`](../contracts/check_docs_freshness.md).
- Depends on WP04's `version_leakage_check.py` and WP06's `check_cli_reference_freshness.py`.
- Charter: no new pip deps; mypy `--strict`; ≥ 90% coverage.

**Note on CI workflow ownership.** The owned_files list includes a **new** workflow file `.github/workflows/docs-freshness.yml`. If the team prefers to extend an existing CI quality workflow instead of adding a new one, the implementer requests a scope amendment (the existing workflow file would need to be added to `owned_files`); do not silently edit a workflow outside `owned_files`.

## Subtasks

### T040 — Implement `check_docs_freshness.py`

Implement per contract. Required behavior:

- Same env-flag enforcement as upstream scripts.
- Sub-check sequence: `version_leakage_check`, `check_cli_reference_freshness`, link health (per `--link-check {none,spot,full}`), page-inventory completeness.
- Aggregate findings into a single `FreshnessReport`.
- Exit codes 0/1/2/3 per contract.

### T041 — Implement `test_check_docs_freshness.py`

- Happy path → exit 0.
- One leak + one reference miss → exit 1.
- Missing inventory → exit 2.
- SaaS sync off → exit 3.
- Coverage ≥ 90% on the orchestrator module.

### T042 — Wire CI step

Create `.github/workflows/docs-freshness.yml` (new workflow) with:

- Trigger: `pull_request` against `main` and `push` on `main`.
- Job: `docs-freshness` running on `ubuntu-latest`.
- Steps:
  - Checkout.
  - Set up Python and `uv`.
  - `uv sync`.
  - `SPEC_KITTY_ENABLE_SAAS_SYNC=1 SPEC_KITTY_NO_UPGRADE_CHECK=1 uv run python scripts/docs/check_docs_freshness.py --ci --report freshness.json`.
  - Upload `freshness.json` as a workflow artifact.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Lane: `F`. First WP in lane F; allocates `.worktrees/spec-kitty-3-2-docs-<mid8>-lane-f/`.

## Test Strategy

- Unit + integration tests on the orchestrator.
- CI dry-run: implementer runs `act` locally or pushes a draft to confirm the workflow file parses.
- mypy `--strict` clean.

## Definition of Done

- [ ] `scripts/docs/check_docs_freshness.py` exists; mypy `--strict` clean.
- [ ] `tests/docs/test_check_docs_freshness.py` exists and passes.
- [ ] `.github/workflows/docs-freshness.yml` exists and parses; CI step runs green on a clean checkout.
- [ ] Coverage ≥ 90% on the orchestrator.
- [ ] No files outside `owned_files` modified.

## Risks

- **Workflow file colliding with existing CI** — Mitigation: new file with unique name `docs-freshness.yml`; team can later fold steps into an existing workflow via scope amendment.
- **Link health hitting external rate limits** — Mitigation: default `--link-check spot` (20 random external links); `none` mode available for offline CI.

## Reviewer Guidance

- Confirm orchestrator delegates to sub-checks rather than reimplementing logic.
- Confirm workflow uses `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and uploads the JSON artifact.
- Confirm `--link-check spot` runs in CI by default.

## Implement command

```bash
spec-kitty agent action implement WP13 --agent claude
```

## Activity Log

- 2026-05-21T09:07:13Z – claude:opus-4-7:python-pedro:implementer – shell_pid=12277 – Started implementation via action command
