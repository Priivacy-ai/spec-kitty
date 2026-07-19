---
work_package_id: WP03
title: Render-path no-op-stability guard (#2373 render surface)
dependencies: []
requirement_refs:
- FR-005
- FR-008
- NFR-001
tracker_refs:
- '#2373'
- '#1914'
planning_base_branch: feat/charter-deadcode-noop-campsite
merge_target_branch: feat/charter-deadcode-noop-campsite
branch_strategy: Planning artifacts for this mission were generated on feat/charter-deadcode-noop-campsite. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-deadcode-noop-campsite unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
history: []
agent_profile: python-pedro
authoritative_surface: tests/charter/
create_intent:
- tests/charter/test_context_noop_stability.py
execution_mode: code_change
owned_files:
- tests/charter/test_context_noop_stability.py
role: implementer
tags: []
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1597951"
shell_pid_created_at: "1784429557.67"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile via `/ad-hoc-profile-load python-pedro`
(implementer). Load the YAML — do not act on the persona name alone.

## Objective

Lock in the already-shipped #2773 render-path fix with a **red-first regression guard**:
`build_charter_context` must write NO git-tracked artifact (only untracked runtime state). No
production change is expected — this guard prevents the fix from silently regressing.

**Authoritative grounding** (read first): [`research.md` §3](../research.md),
[`contracts/no-op-stability.contract.md`](../contracts/no-op-stability.contract.md) (G1, G3),
[`data-model.md` LM-1](../data-model.md).

## Context / grounding

- At HEAD, `src/charter/context.py::build_charter_context` writes only
  `.kittify/charter/context-state.json` (via `_write_state`, `context.py:2896`), which is gitignored
  (`.gitignore:88`). It no longer writes tracked doctrine (sync retired by #2773).
- **LM-1 — the masking landmine:** this working checkout has a local `.git/info/exclude` entry
  (`.kittify/doctrine/`) that hides doctrine churn; the committed `.gitignore` TRACKS those
  artifacts. A meaningful cleanliness assertion MUST run where doctrine is tracked — the test fixture
  must build a temp repo WITHOUT that exclude (fresh `git init` + the committed `.gitignore`), or the
  assertion is vacuous.

## Subtasks

### T009 — Add the red-first render-cleanliness guard
Create `tests/charter/test_context_noop_stability.py`. In a doctrine-tracked temp repo (a real
charter + doctrine on disk, no `.git/info/exclude` mask), from a clean tree:
- run `build_charter_context(repo_root, action="advise", …)` (or the `charter context` CLI path),
- assert `git status --porcelain` reports no MODIFIED/ADDED **tracked** doctrine artifact
  (`.kittify/doctrine/**`, `charter.yaml`) — untracked `context-state.json` is allowed.

### T010 — Assert G1 + G3; confirm green
- G1: single render → 0 tracked-file diffs.
- G3: render **twice** → 2nd run also 0 tracked-file diffs.
- This SHOULD pass at HEAD (the fix already shipped). **If it fails**, you have found a live #2773
  regression — do NOT paper over it; surface it and coordinate a real fix (out of this WP's test-only
  scope). Note the outcome in the handoff.

### T011 — Verify
- `PWHEADLESS=1 pytest tests/charter/test_context_noop_stability.py -q` → green.
- `ruff check tests/charter/test_context_noop_stability.py` and `mypy --strict` on it → clean.

## Definition of Done
- A committed guard asserting render-path tracked-tree cleanliness (G1/G3) against a doctrine-tracked
  fixture, green at HEAD. If red, an escalation note is filed instead of a silent pass.

## Landmines
- **LM-1**: assert in a doctrine-tracked fixture, never rely on this masked checkout.

## Reviewer guidance
Confirm the fixture actually tracks doctrine (the exclude mask is not in play) — a green test against
a masked fixture is a false pass. Confirm the assertion targets tracked artifacts, not untracked
runtime state.

## Activity Log

- 2026-07-19T02:37:59Z – claude:sonnet:python-pedro:implementer – shell_pid=1510808 – Assigned agent via action command
- 2026-07-19T02:49:21Z – claude:sonnet:python-pedro:implementer – shell_pid=1510808 – render-cleanliness guard, doctrine-tracked fixture, green at HEAD
- 2026-07-19T02:51:38Z – claude:sonnet:python-pedro:implementer – shell_pid=1510808 – Pre-review gate reported no_coverage due to a stale lane .venv (pytest not yet installed); ran 'uv sync --frozen --all-extras --dev' to fix, then verified 'PWHEADLESS=1 .venv/bin/python3 -m pytest tests/charter/test_context_noop_stability.py -q' green (3 passed) using the same interpreter path the gate invokes.
- 2026-07-19T02:52:40Z – claude:opus:reviewer-renata:reviewer – shell_pid=1597951 – Started review via action command
