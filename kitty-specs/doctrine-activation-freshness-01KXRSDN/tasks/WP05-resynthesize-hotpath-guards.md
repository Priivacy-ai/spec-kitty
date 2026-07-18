---
work_package_id: WP05
title: --resynthesize opt-in + hot-path guards (NFR-001/003)
dependencies:
- WP03
requirement_refs:
- FR-007
- NFR-001
- NFR-003
tracker_refs:
- '#2759'
- '#2519'
planning_base_branch: feat/doctrine-activation-freshness
merge_target_branch: feat/doctrine-activation-freshness
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-activation-freshness. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-activation-freshness unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/charter/
create_intent:
- tests/specify_cli/cli/commands/charter/test_resynthesize_and_hotpath.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/charter/activate.py
- src/specify_cli/cli/commands/charter/deactivate.py
- tests/specify_cli/cli/commands/charter/test_resynthesize_and_hotpath.py
- CHANGELOG.md
role: implementer
tags: []
shell_pid: "3468300"
shell_pid_created_at: "1784327014.39"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (implementer). Do not act on the persona name alone — load the YAML.

## Objective

Give operators an eager-refresh escape hatch — `charter activate/deactivate --resynthesize` —
so fail-closed-by-default (WP03) is ergonomic, while **proving the default path stays cheap**.
Without the flag, activation stays fast (config write only) and the signal simply reports stale
until a later reconcile; with the flag, the derived bundle/DRG are refreshed as part of the
command.

**Anchor convention**: line numbers are indicative — resolve by symbol name.

## Hard constraints

- **C-001 layer**: the eager synthesize orchestration lives in the `specify_cli` CLI command
  (`activate.py`/`deactivate.py`), which may orchestrate the synthesize pipeline.
  `commit_plan`/`activation_engine.py` (charter) is **NOT** edited.
- **Single authority**: `--resynthesize` orchestrates the EXISTING synthesize pipeline (the
  same one `charter synthesize`/`resynthesize` uses), not a new one.
- **NFR-001**: default `charter activate`/`deactivate` (no flag) spawns **zero**
  synthesis/`regenerate-graph` subprocess and adds no new filesystem graph walk.
- **NFR-003**: the `spec-kitty upgrade` migration + `org_charter` `promote_activations` paths
  trigger no synthesis (they route through the same `commit_plan` chokepoint, which stays
  write-only).
- Depends on **WP03** (`--resynthesize` refreshes the signal WP03 made visible; the NFR-001
  spy asserts the seam added no eager regen to the default path).

## Subtasks

### T017 — Red-first: NFR-001 spy
- Add `tests/specify_cli/cli/commands/charter/test_resynthesize_and_hotpath.py`. Install a
  subprocess/call-count spy on the synthesize/`regenerate-graph` entry points.
- Assert the TARGET: default `charter activate <kind> <id>` performs **zero** synthesis calls.
  (Write this as the guard that must hold — it should already hold today; it becomes the
  regression net that the new flag path does not leak eager work into the default path.)

### T018 — Add `--resynthesize`
- Add a `--resynthesize/--no-resynthesize` flag (default off) to `charter activate` and
  `charter deactivate`. When set, after the config write, invoke the existing synthesize
  orchestration so the derived bundle/DRG (and thus the freshness signal) are refreshed.
- Keep the flag plumbing thin; the orchestration reuses the existing pipeline entry point.
  Complexity ≤15; hoist any repeated strings.

### T019 — Tests
- `charter activate … --resynthesize` → freshness signal is FRESH immediately afterward.
- Default `charter activate …` → signal STALE **and** the spy records ZERO synthesis subprocess (NFR-001).
- `deactivate --resynthesize` symmetric.
- NFR-003: exercise the `promote_activations` path (migration/`org_charter` shape) and assert
  no synthesis is triggered.

### T020 — Gate
- `PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/charter/ -q` green.
- `ruff check` + `uv run mypy --strict` clean on `activate.py`/`deactivate.py`; complexity ≤15.
- Confirm `git diff` does not touch `activation_engine.py`/`commit_plan` (C-001).

## Branch Strategy

Planning base + merge target: `feat/doctrine-activation-freshness`. Worktree from `lanes.json`.
Depends on WP03.

## Definition of Done

- [ ] `--resynthesize` on activate + deactivate; default off.
- [ ] With flag → signal FRESH immediately; reuses the existing synthesize pipeline (single authority).
- [ ] Default path → STALE + ZERO synthesis subprocess (NFR-001 spy).
- [ ] NFR-003: migration/`promote_activations` path triggers no synthesis.
- [ ] `commit_plan`/`activation_engine.py` untouched (C-001).
- [ ] CHANGELOG.md entry for the new `--resynthesize` operator-facing flag (help text is inline in activate.py; a changelog line is expected for a new CLI flag).
- [ ] ruff + mypy --strict clean; complexity ≤15.

## Risks

- **Default path made eager** (R-04) → the NFR-001 spy is the guard; flag-gate the eager path strictly.
- **New parallel synthesize pipeline** → reuse the existing orchestration; do not duplicate.

## Reviewer guidance (reviewer-renata, opus)

Verify: the flag reuses the existing synthesize pipeline; default path proven zero-synthesis via
spy; migration path unaffected; `commit_plan` untouched; symmetric on deactivate.

## Activity Log

- 2026-07-17T21:57:09Z – claude:sonnet:python-pedro:implementer – shell_pid=3417407 – Assigned agent via action command
- 2026-07-17T22:22:02Z – claude:sonnet:python-pedro:implementer – shell_pid=3417407 – --resynthesize reuses existing pipeline; default path zero-synthesis (spy); commit_plan untouched; CHANGELOG added; gates green
- 2026-07-17T22:23:36Z – claude:opus:reviewer-renata:reviewer – shell_pid=3468300 – Started review via action command
