---
work_package_id: WP02
title: Index freshness gate
dependencies:
- WP01
requirement_refs:
- FR-005
planning_base_branch: feat/agent-knowledge-canonical-homes
merge_target_branch: feat/agent-knowledge-canonical-homes
branch_strategy: Planning artifacts for this mission were generated on feat/agent-knowledge-canonical-homes. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/agent-knowledge-canonical-homes unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
history:
- at: '2026-07-22T14:56:33Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: scripts/docs/
create_intent:
- tests/docs/test_docs_index_freshness.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- scripts/docs/check_docs_freshness.py
- .github/workflows/docs-freshness.yml
- tests/docs/test_docs_index_freshness.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its directives/tactics; state which you applied in your handoff note.

## Objective

Add a CI-runnable drift check `_check_docs_index_drift` to `scripts/docs/check_docs_freshness.py` that
reds when `docs/development/3-2-docs-retrieval-index.yaml` is stale relative to `docs/`, mirroring the
existing `_check_inventory_lockfile_drift` — and register it in the aggregate as a new `error`-severity
ruler. **Leave `_check_inventory_lockfile_drift` and the page-inventory byte-for-byte untouched (C-001).**

Read `contracts/index-file-contract.md` (freshness-gate section) first. Consume WP01's generator by
importing from **`scripts.docs.docs_index`** (`scripts→scripts` — `generate_index` /
`run_generate_and_compare`); that module in turn imports `compare_index`/`render_index` from the
packaged `specify_cli.docs.index_model`. Do NOT re-implement generation, and do NOT import the packaged
model directly unless you need `compare_index` — prefer the `scripts.docs.docs_index` façade.

## Branch Strategy

Planning base + merge target: **`feat/agent-knowledge-canonical-homes`** (coord topology). Worktree is
allocated per lane by `spec-kitty implement WP02`. **Depends on WP01** — implement only after WP01 is
`approved`.

## Subtasks

### T007 — `_check_docs_index_drift` checker

- In `check_docs_freshness.py`, add `_check_docs_index_drift(...)` that: locates the docs root + the
  committed index path, calls WP01's compare API (regenerate in-memory, diff vs committed), and returns
  the module's finding/report type with `error` severity + a `DOCS-INDEX-DRIFT` rule id when drift is
  found (message names the stale/added/removed pages and the fix: `python scripts/docs/docs_index.py --write`).
- Follow the exact shape of `_check_inventory_lockfile_drift` (same finding dataclass, same return
  convention). Keep complexity ≤15.

### T008 — Register in the aggregate

- Add the new checker to the aggregate ruler list at the same registration site the inventory checker
  uses (the squad flagged `check_docs_freshness.py:~433`). Do NOT modify, reorder, or rewrap the
  existing `_check_inventory_lockfile_drift` entry — append alongside it.
- Ensure `check_docs_freshness --ci` exits non-zero when the new ruler emits an error.

### T009 — Verify CI wiring

- Inspect `.github/workflows/docs-freshness.yml`. If it invokes the aggregate
  (`check_docs_freshness … --ci`), the new checker is covered automatically — record that and change
  nothing. Only if the workflow runs the inventory drift as a *discrete* step (not via the aggregate),
  add a parallel explicit step for the docs index. Prefer the no-op path.

### T010 — Tests

- `tests/docs/test_docs_index_freshness.py`: (a) a fresh index → checker passes; (b) mutate a fixture
  page's heading/description without regenerating → checker emits a finding whose **severity is `error`**
  (assert the severity, not merely a non-zero exit) with rule id `DOCS-INDEX-DRIFT`, and the aggregate
  exits non-zero; (c) regenerate → green again.
- **C-001 ruler snapshot (renata)**: the pre-existing `test_inventory_path_stable.py` /
  `test_inventory_lockfile_untouched` cover the inventory *data file*, but nothing covers the inventory
  *ruler code* this WP edits. Add a check that on a known-drifted inventory fixture the
  `INVENTORY-LOCKFILE-DRIFT` findings (list + severities) are unchanged by this WP's edit — so a
  perturbation of the shared aggregate reds here.
- Run `PWHEADLESS=1 uv run pytest tests/docs/test_docs_index_freshness.py -q` — green.

## Definition of Done

- [ ] `_check_docs_index_drift` added; `DOCS-INDEX-DRIFT` error surfaces on stale index and is caught by `check_docs_freshness --ci`.
- [ ] `_check_inventory_lockfile_drift` and `3-2-page-inventory.yaml` untouched (C-001) — proven by test/inspection.
- [ ] CI wiring verified (aggregate covers it, or an explicit step added only if required).
- [ ] `uv run ruff check` + `uv run mypy` clean on touched files; complexity ≤15.
- [ ] Tests green (foreground, `uv run`).

## Reviewer guidance

Verify the inventory ruler is byte-identical (git diff shows only additive changes around it), the new
ruler is `error` severity and truly reds the aggregate, and the drift message is actionable. Confirm the
CI change (if any) is minimal and justified.

## Risks

- Refactoring the shared aggregate registration could perturb the inventory ruler → keep the edit purely
  additive.
- Depending on WP01 internals that aren't public → consume only the documented `compare` / generate API.
